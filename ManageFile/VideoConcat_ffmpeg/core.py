#!/usr/bin/env python3
"""
core.py — Logica di processing pura per VideoConcat_ffmpeg.

Contiene tutte le funzioni e strutture dati indipendenti dalla GUI:
costanti, VideoItem, helper ffmpeg, concatVideo, convertOgvToMp4.
Questo modulo non importa tkinter e può essere usato/testato senza display.
"""

import os
import re
import subprocess
import logging
import threading
import tempfile
from dataclasses import dataclass

C_MP4 = ".mp4"
C_MKV = ".mkv"
C_OGV = ".ogv"
C_VIDEO_TYPES = [("Video files", "*.mp4 *.mkv *.ogv *.avi *.mov"), ("All files", "*.*")]

# Regex per bitrate audio valido: numero (intero o decimale) seguito da k, K, m o M
# Esempi validi: 128k, 192K, 2M, 1.5M
BITRATE_RE = re.compile(r'^\d+(\.\d+)?[kKmM]$')


@dataclass
class VideoItem:
    path: str
    start: str = ""
    end: str = ""
    video_crf: str = ""      # CRF 0-51 (vuoto = copia stream)
    audio_bitrate: str = ""  # es. "128k" (vuoto = copia stream)
    seek_mode: str = "auto"  # "auto" | "fast" | "precise"


# ---------------------------------------------------------------------------
# Seek mode: differenza tra -ss prima e dopo -i
# ---------------------------------------------------------------------------
#
# FAST SEEK  (-ss PRIMA di -i, "input seeking"):
#   ffmpeg salta direttamente al keyframe più vicino al timestamp richiesto.
#   Pro: velocissimo, nessuna decodifica extra.
#   Contro: il punto di inizio può essere impreciso (fino al GOP precedente).
#   Quando usarlo: copia stream (nessuna ri-codifica) dove la velocità conta
#                  più della precisione al frame.
#
# PRECISE SEEK  (-ss DOPO -i, "output seeking"):
#   ffmpeg decodifica tutti i frame dall'inizio e li scarta fino al timestamp.
#   Pro: precisione al frame esatta.
#   Contro: lento per seek lontani dall'inizio.
#   Quando usarlo: ri-codifica (libx264, ecc.) — il costo computazionale della
#                  codifica è già elevato, quindi la decodifica extra è accettabile
#                  e la precisione dell'intervallo è fondamentale.
#
# MODALITÀ AUTO (default):
#   - copia stream  → fast seek
#   - ri-codifica   → precise seek
# ---------------------------------------------------------------------------


def seconds_to_timecode(secs: float) -> str:
    """Converte secondi float nel formato HH:MM:SS.sss accettato da ffmpeg."""
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def is_fast_seek(item: VideoItem, is_reencode: bool) -> bool:
    """Restituisce True se si deve usare fast seek (-ss prima di -i)."""
    if item.seek_mode == "fast":
        return True
    if item.seek_mode == "precise":
        return False
    # "auto": fast se copia stream, precise se si ri-codifica
    return not is_reencode


def validate_crf(crf: str) -> tuple[bool, str]:
    """
    Valida il valore CRF. Restituisce (ok, messaggio_errore).
    Se ok è True, messaggio_errore è vuoto.
    """
    if not crf:
        return True, ""
    try:
        crf_val = int(crf)
        if not (0 <= crf_val <= 51):
            return False, (
                f"Il valore CRF '{crf}' è fuori range.\n"
                "Deve essere un intero tra 0 (qualità massima) e 51 (qualità minima).\n"
                "Valori consigliati: 18 (alta qualità), 23 (default), 28 (bassa qualità)."
            )
        return True, ""
    except ValueError:
        return False, (
            f"Il valore CRF '{crf}' non è un numero intero.\n"
            "Inserisci un intero tra 0 e 51 (es: 18, 23, 28)."
        )


def validate_audio_bitrate(audio: str) -> tuple[bool, str]:
    """
    Valida il bitrate audio. Restituisce (ok, messaggio_errore).
    Se ok è True, messaggio_errore è vuoto.
    """
    if not audio:
        return True, ""
    if not BITRATE_RE.match(audio):
        return False, (
            f"Il bitrate audio '{audio}' non è nel formato corretto.\n"
            "Usa un numero seguito da k o M (es: 128k, 192k, 320k, 2M)."
        )
    return True, ""


def parse_time(value: str) -> float | None:
    """
    Analizza una stringa di tempo (HH:MM:SS, MM:SS, o secondi float).
    Restituisce i secondi come float, oppure None se la stringa è vuota.
    Solleva ValueError per formati non validi.
    """
    raw = value.strip()
    if not raw:
        return None
    parts = raw.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError as exc:
        raise ValueError(f"Formato tempo non valido: '{value}'") from exc
    raise ValueError(f"Formato tempo non valido: '{value}'")


def run_ffmpeg(cmd_list: list) -> subprocess.CompletedProcess:
    """Esegue un comando ffmpeg e gestisce errori/log."""
    logging.info(f"Eseguo: {' '.join(cmd_list)}")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Errore ffmpeg: {result.stderr}")
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return result


def get_video_duration(path: str) -> float:
    """Restituisce la durata del video in secondi tramite ffprobe (0.0 se non disponibile)."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True, text=True, timeout=15,
        )
        return max(0.0, float(result.stdout.strip()))
    except Exception:
        return 0.0


def run_ffmpeg_with_progress(cmd_list: list, duration_secs: float = 0.0,
                             progress_cb=None, proc_cb=None, stop_event=None):
    """
    Esegue ffmpeg con -progress pipe:1 per aggiornamenti di avanzamento in tempo reale.

    Nota ffmpeg: nonostante il nome, 'out_time_ms' nel formato -progress contiene
    microsecondi (us), non millisecondi. Si divide per 1_000_000 per ottenere secondi.

    progress_cb(pct: float) viene chiamata con valori 0.0–100.0 durante l'esecuzione.
    Se duration_secs == 0 non viene chiamata (durata ignota).
    proc_cb(proc) viene chiamata subito dopo Popen per permettere al chiamante di
    conservare il riferimento al processo (es. per terminarlo).
    stop_event: threading.Event — se impostato, termina il processo e rilancia
    RuntimeError("Elaborazione interrotta dall'utente.").
    """
    full_cmd = [cmd_list[0], "-progress", "pipe:1", "-nostats"] + cmd_list[1:]
    logging.info(f"Eseguo (con progress): {' '.join(full_cmd)}")

    proc = subprocess.Popen(
        full_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    if proc_cb:
        proc_cb(proc)

    stderr_lines: list = []

    def _read_stderr():
        for line in proc.stderr:
            stderr_lines.append(line)

    stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
    stderr_thread.start()

    for line in proc.stdout:
        if stop_event and stop_event.is_set():
            proc.terminate()
            proc.wait()
            stderr_thread.join(timeout=2)
            raise RuntimeError("Elaborazione interrotta dall'utente.")
        line = line.strip()
        if line.startswith("out_time_ms=") and progress_cb and duration_secs > 0:
            try:
                # 'out_time_ms' contiene microsecondi (us) nonostante il nome
                out_time_us = int(line.split("=", 1)[1])
                pct = min(100.0, max(0.0, out_time_us / (duration_secs * 1_000_000) * 100))
                progress_cb(pct)
            except (ValueError, ZeroDivisionError):
                pass

    proc.wait()
    stderr_thread.join(timeout=2)

    if stop_event and stop_event.is_set():
        raise RuntimeError("Elaborazione interrotta dall'utente.")

    if proc.returncode != 0:
        stderr_text = "".join(stderr_lines)
        logging.error(f"Errore ffmpeg: {stderr_text}")
        raise RuntimeError(f"ffmpeg failed: {stderr_text}")


def build_encode_args(item: VideoItem) -> list:
    """Restituisce gli argomenti ffmpeg per video/audio basandosi sui parametri di qualità."""
    has_video_quality = bool(item.video_crf.strip())
    has_audio_quality = bool(item.audio_bitrate.strip())
    if not has_video_quality and not has_audio_quality:
        # Nessuna ri-codifica: copia stream con bitstream filter per mpegts
        return ["-c", "copy", "-bsf:v", "h264_mp4toannexb"]
    args = []
    if has_video_quality:
        args.extend(["-c:v", "libx264", "-crf", item.video_crf.strip()])
    else:
        args.extend(["-c:v", "copy"])
    if has_audio_quality:
        args.extend(["-c:a", "aac", "-b:a", item.audio_bitrate.strip()])
    else:
        args.extend(["-c:a", "copy"])
    return args


def concat_video(file_paths: list[VideoItem], out_path: str,
                 progress_cb=None, proc_cb=None, stop_event=None) -> str:
    """
    Concatena una lista di VideoItem nel file di output specificato.

    progress_cb(value: float, label: str) — aggiornamenti 0-100 con etichetta.
    I file rappresentano il 90% del progresso totale; il 10% finale è la concat.
    proc_cb(proc) — propagato a run_ffmpeg_with_progress per accesso al processo.
    stop_event — threading.Event che segnala l'interruzione.
    Restituisce out_path al completamento.
    """
    n = len(file_paths)

    durations = [get_video_duration(item.path) for item in file_paths]
    total_dur = sum(durations)
    completed_dur = 0.0

    def _make_step_cb(base_dur: float, step_dur: float, idx: int):
        """Crea un callback che converte il progresso del singolo file in overall."""
        def _cb(pct: float):
            if not progress_cb:
                return
            if total_dur > 0:
                done = base_dur + (pct / 100.0) * step_dur
                overall = done / total_dur * 90.0
            else:
                overall = (idx + pct / 100.0) / n * 90.0
            progress_cb(min(overall, 90.0), f"Elaborazione file {idx + 1}/{n}: {pct:.0f}%")
        return _cb

    with tempfile.TemporaryDirectory() as tmp_dir:
        list_ts = []
        for i, item in enumerate(file_paths):
            if stop_event and stop_event.is_set():
                raise RuntimeError("Elaborazione interrotta dall'utente.")
            logging.info(
                f"Processando: {item.path} "
                f"[da={item.start or 'inizio'} a={item.end or 'fine'} "
                f"crf={item.video_crf or 'copy'} audio={item.audio_bitrate or 'copy'}]"
            )
            ts_path = os.path.join(tmp_dir, f"intermediate_{i}.ts")
            encode_args = build_encode_args(item)
            is_reencode = bool(item.video_crf.strip() or item.audio_bitrate.strip())
            fast = is_fast_seek(item, is_reencode)

            cmd = ["ffmpeg", "-y"]
            if fast and item.start:
                cmd.extend(["-ss", item.start])
            if fast and item.end:
                cmd.extend(["-to", item.end])
            cmd.extend(["-i", item.path])
            if not fast and item.start:
                cmd.extend(["-ss", item.start])
            if not fast and item.end:
                cmd.extend(["-to", item.end])
            cmd.extend(encode_args)
            cmd.extend(["-f", "mpegts", ts_path])
            list_ts.append(ts_path)

            run_ffmpeg_with_progress(
                cmd, durations[i], _make_step_cb(completed_dur, durations[i], i),
                proc_cb=proc_cb, stop_event=stop_event,
            )
            completed_dur += durations[i]

        logging.info("Finito il ciclo, inizio ad unire i video")
        if stop_event and stop_event.is_set():
            raise RuntimeError("Elaborazione interrotta dall'utente.")
        if progress_cb:
            progress_cb(91.0, "Unione file finali...")

        list_ts_str = "|".join(list_ts)
        cmd = [
            "ffmpeg", "-y", "-i", f"concat:{list_ts_str}",
            "-c", "copy", "-bsf:a", "aac_adtstoasc", out_path,
        ]
        run_ffmpeg_with_progress(cmd, proc_cb=proc_cb, stop_event=stop_event)

        if progress_cb:
            progress_cb(100.0, "✅ Completato!")
    return out_path


def convert_ogv_to_mp4(file_path: str, video_crf: str = "", audio_bitrate: str = "") -> str:
    """Converte un file OGV in MP4 nella stessa cartella (con qualità opzionale)."""
    out_file = file_path.replace(C_OGV, C_MP4)
    cmd = ["ffmpeg", "-y", "-i", file_path, "-vcodec", "libx264"]
    if video_crf:
        cmd.extend(["-crf", video_crf])
    if audio_bitrate:
        cmd.extend(["-b:a", audio_bitrate])
    cmd.append(out_file)
    run_ffmpeg(cmd)
    return out_file
