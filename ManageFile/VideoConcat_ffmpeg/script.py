#!/usr/bin/env python3
# chmod +x script.py
# ./script

# SCRIPT TO CONCAT VIDEO with MPEG
# Permette di selezionare una lista di file video da concatenare e scegliere il file di output
# Usa subprocess.run per tutti i comandi ffmpeg (più sicuro e robusto)
# Gestisce i percorsi con os.path.join (compatibile e sicuro per spazi)
# Logga errori e operazioni con il modulo logging
# Cancella i file temporanei in modo sicuro (con try/except)
# Fornisce feedback chiaro in caso di errori
# SEE https://www.educative.io/answers/how-to-run-a-python-script-in-linux
# https://stackoverflow.com/questions/11295917/how-to-select-a-directory-and-store-the-location-using-tkinter-in-python

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from os import listdir
from os.path import isfile, join
import subprocess
import logging
import threading
from dataclasses import dataclass

C_MP4 = ".mp4"
C_MKV = ".mkv"
C_OGV = ".ogv"
C_VIDEO_TYPES = [("Video files", "*.mp4 *.mkv *.ogv *.avi *.mov"), ("All files", "*.*")]


@dataclass
class VideoItem:
    path: str
    start: str = ""
    end: str = ""
    video_crf: str = ""      # CRF 0-51 (vuoto = copia stream)
    audio_bitrate: str = ""  # es. "128k" (vuoto = copia stream)


def run_ffmpeg(cmd_list):
    """Esegue un comando ffmpeg e gestisce errori/log."""
    logging.info(f"Eseguo: {' '.join(cmd_list)}")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Errore ffmpeg: {result.stderr}")
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return result


def _build_encode_args(item: "VideoItem"):
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


def concatVideo(file_paths, out_path):
    """Concatena una lista di VideoItem nel file di output specificato."""
    tmp_dir = os.path.dirname(out_path) or os.getcwd()
    list_ts = []
    for i, item in enumerate(file_paths):
        logging.info(
            f"Processando: {item.path} "
            f"[da={item.start or 'inizio'} a={item.end or 'fine'} "
            f"crf={item.video_crf or 'copy'} audio={item.audio_bitrate or 'copy'}]"
        )
        ts_path = os.path.join(tmp_dir, f"_fileIntermediate{i}.ts")
        cmd = ["ffmpeg", "-y"]
        if item.start:
            cmd.extend(["-ss", item.start])
        if item.end:
            cmd.extend(["-to", item.end])
        cmd.extend(["-i", item.path])
        cmd.extend(_build_encode_args(item))
        cmd.extend(["-f", "mpegts", ts_path])
        list_ts.append(ts_path)
        run_ffmpeg(cmd)
    logging.info("Finito il ciclo, inizio ad unire i video")
    list_ts_str = "|".join(list_ts)
    cmd = [
        "ffmpeg", "-y", "-i", f"concat:{list_ts_str}",
        "-c", "copy", "-bsf:a", "aac_adtstoasc", out_path
    ]
    run_ffmpeg(cmd)
    for ts in list_ts:
        try:
            os.remove(ts)
        except Exception as e:
            logging.warning(f"Non riesco a cancellare {ts}: {e}")
    return out_path


def convertOgvToMp4(file_path, video_crf="", audio_bitrate=""):
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


class VideoConcatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VideoConcat - ffmpeg")
        self.resizable(True, True)
        self.minsize(760, 520)
        self.video_items = []
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- File list frame ---
        list_frame = tk.LabelFrame(self, text="File video da concatenare (nell'ordine mostrato)")
        list_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=12)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=4)
        self.listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)

        tk.Button(btn_frame, text="➕ Aggiungi file", width=18, command=self._add_files).pack(pady=2)
        tk.Button(btn_frame, text="📁 Aggiungi cartella", width=18, command=self._add_folder).pack(pady=2)
        tk.Button(btn_frame, text="⬆ Su", width=18, command=self._move_up).pack(pady=2)
        tk.Button(btn_frame, text="⬇ Giù", width=18, command=self._move_down).pack(pady=2)
        tk.Button(btn_frame, text="🗑 Rimuovi", width=18, command=self._remove_selected).pack(pady=2)
        tk.Button(btn_frame, text="🧹 Svuota lista", width=18, command=self._clear_list).pack(pady=2)

        # --- Range frame ---
        range_frame = tk.LabelFrame(self, text="Intervallo per file selezionati (default: intero video)")
        range_frame.pack(fill=tk.X, **pad)
        tk.Label(range_frame, text="Da").pack(side=tk.LEFT, padx=(6, 2))
        self.from_var = tk.StringVar(value="")
        tk.Entry(range_frame, textvariable=self.from_var, width=14).pack(side=tk.LEFT, padx=(0, 8), pady=4)
        tk.Label(range_frame, text="A").pack(side=tk.LEFT, padx=(0, 2))
        self.to_var = tk.StringVar(value="")
        tk.Entry(range_frame, textvariable=self.to_var, width=14).pack(side=tk.LEFT, padx=(0, 8), pady=4)
        tk.Label(range_frame, text="(es: 00:01:10.5 oppure 70.5)").pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(range_frame, text="Applica ai selezionati", command=self._apply_range_to_selected).pack(side=tk.LEFT, padx=4)
        tk.Button(range_frame, text="Reset (intero video)", command=self._reset_range_on_selected).pack(side=tk.LEFT, padx=4)

        # --- Quality frame ---
        quality_frame = tk.LabelFrame(self, text="Qualità per file selezionati (default: copia stream senza ri-codifica)")
        quality_frame.pack(fill=tk.X, **pad)
        tk.Label(quality_frame, text="CRF video").pack(side=tk.LEFT, padx=(6, 2))
        self.crf_var = tk.StringVar(value="")
        tk.Entry(quality_frame, textvariable=self.crf_var, width=6).pack(side=tk.LEFT, padx=(0, 2), pady=4)
        tk.Label(quality_frame, text="(0-51, 18=alta, 23=default, 28=bassa; vuoto=copia)").pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(quality_frame, text="Bitrate audio").pack(side=tk.LEFT, padx=(10, 2))
        self.audio_var = tk.StringVar(value="")
        tk.Entry(quality_frame, textvariable=self.audio_var, width=8).pack(side=tk.LEFT, padx=(0, 2), pady=4)
        tk.Label(quality_frame, text="(es: 128k, 192k; vuoto=copia)").pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(quality_frame, text="Applica ai selezionati", command=self._apply_quality_to_selected).pack(side=tk.LEFT, padx=4)
        tk.Button(quality_frame, text="Reset qualità", command=self._reset_quality_on_selected).pack(side=tk.LEFT, padx=4)

        # --- Output file frame ---
        out_frame = tk.LabelFrame(self, text="File di output")
        out_frame.pack(fill=tk.X, **pad)

        self.out_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "output.mp4"))
        tk.Entry(out_frame, textvariable=self.out_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
        tk.Button(out_frame, text="Sfoglia...", command=self._choose_output).pack(side=tk.LEFT, padx=4, pady=4)

        # --- Run button ---
        run_frame = tk.Frame(self)
        run_frame.pack(fill=tk.X, **pad)
        self.run_btn = tk.Button(run_frame, text="▶  Avvia concatenazione", bg="#2a7de1", fg="white",
                                 font=("Helvetica", 11, "bold"), command=self._run)
        self.run_btn.pack(side=tk.LEFT, pady=4)

        # --- Progress / log ---
        log_frame = tk.LabelFrame(self, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=False, **pad)

        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, bg="#f4f4f4", wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=8, pady=(0, 6))

    # --- Helpers ---

    def _log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _add_files(self):
        paths = filedialog.askopenfilenames(title="Seleziona file video", filetypes=C_VIDEO_TYPES)
        self._add_video_paths(paths)

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Seleziona cartella")
        if not folder:
            return
        video_exts = {C_MP4, C_MKV, C_OGV, ".avi", ".mov"}
        files = sorted([
            join(folder, f) for f in listdir(folder)
            if isfile(join(folder, f)) and os.path.splitext(f)[1].lower() in video_exts
        ])
        self._add_video_paths(files)

    def _add_video_paths(self, paths):
        for p in paths:
            self.video_items.append(VideoItem(path=p))
        self._refresh_listbox()

    def _refresh_listbox(self):
        selected = set(self.listbox.curselection())
        self.listbox.delete(0, tk.END)
        for i, item in enumerate(self.video_items):
            rng = f" [{item.start or 'inizio'} → {item.end or 'fine'}]"
            quality_parts = []
            if item.video_crf:
                quality_parts.append(f"CRF={item.video_crf}")
            if item.audio_bitrate:
                quality_parts.append(f"audio={item.audio_bitrate}")
            quality = f" | qualità: {', '.join(quality_parts)}" if quality_parts else ""
            self.listbox.insert(tk.END, f"{item.path}{rng}{quality}")
            if i in selected:
                self.listbox.selection_set(i)

    def _remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            del self.video_items[i]
        self._refresh_listbox()

    def _clear_list(self):
        self.video_items.clear()
        self._refresh_listbox()

    def _move_up(self):
        selection = self.listbox.curselection()
        for i in selection:
            if i == 0:
                continue
            self.video_items[i - 1], self.video_items[i] = self.video_items[i], self.video_items[i - 1]
        self._refresh_listbox()
        for i in selection:
            if i > 0:
                self.listbox.selection_set(i - 1)

    def _move_down(self):
        selection = self.listbox.curselection()
        for i in reversed(selection):
            if i == len(self.video_items) - 1:
                continue
            self.video_items[i + 1], self.video_items[i] = self.video_items[i], self.video_items[i + 1]
        self._refresh_listbox()
        for i in selection:
            if i < len(self.video_items) - 1:
                self.listbox.selection_set(i + 1)

    def _parse_time(self, value):
        raw = value.strip()
        if not raw:
            return None
        parts = raw.split(":")
        try:
            if len(parts) == 1:
                return float(parts[0])
            if len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except ValueError as exc:
            raise ValueError(f"Formato tempo non valido: '{value}'") from exc
        raise ValueError(f"Formato tempo non valido: '{value}'")

    def _apply_range_to_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona almeno un file dalla lista.")
            return

        start_raw = self.from_var.get().strip()
        end_raw = self.to_var.get().strip()
        try:
            start_seconds = self._parse_time(start_raw)
            end_seconds = self._parse_time(end_raw)
        except ValueError as err:
            messagebox.showerror("Errore", str(err))
            return

        if start_seconds is not None and end_seconds is not None and start_seconds >= end_seconds:
            messagebox.showerror("Errore", "L'intervallo non è valido: 'Da' deve essere minore di 'A'.")
            return

        for i in selection:
            self.video_items[i].start = start_raw
            self.video_items[i].end = end_raw
        self._refresh_listbox()
        for i in selection:
            self.listbox.selection_set(i)

    def _reset_range_on_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona almeno un file dalla lista.")
            return
        for i in selection:
            self.video_items[i].start = ""
            self.video_items[i].end = ""
        self._refresh_listbox()
        for i in selection:
            self.listbox.selection_set(i)

    def _apply_quality_to_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona almeno un file dalla lista.")
            return
        crf = self.crf_var.get().strip()
        audio = self.audio_var.get().strip()
        if crf:
            try:
                crf_val = int(crf)
                if not (0 <= crf_val <= 51):
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Errore", "CRF deve essere un numero intero tra 0 e 51.")
                return
        for i in selection:
            self.video_items[i].video_crf = crf
            self.video_items[i].audio_bitrate = audio
        self._refresh_listbox()
        for i in selection:
            self.listbox.selection_set(i)

    def _reset_quality_on_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona almeno un file dalla lista.")
            return
        for i in selection:
            self.video_items[i].video_crf = ""
            self.video_items[i].audio_bitrate = ""
        self._refresh_listbox()
        for i in selection:
            self.listbox.selection_set(i)

    def _choose_output(self):
        path = filedialog.asksaveasfilename(
            title="Scegli il file di output",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("All files", "*.*")]
        )
        if path:
            self.out_var.set(path)

    def _run(self):
        if not self.video_items:
            messagebox.showwarning("Attenzione", "Aggiungi almeno un file video alla lista.")
            return
        out_path = self.out_var.get().strip()
        if not out_path:
            messagebox.showwarning("Attenzione", "Specifica il percorso del file di output.")
            return

        self.run_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        def task():
            try:
                # Convert any OGV files first
                converted = []
                for item in self.video_items:
                    if item.path.lower().endswith(C_OGV):
                        self._log(f"Conversione OGV→MP4: {item.path}")
                        mp4 = convertOgvToMp4(item.path, item.video_crf, item.audio_bitrate)
                        converted.append(VideoItem(path=mp4, start=item.start, end=item.end,
                                                   video_crf=item.video_crf, audio_bitrate=item.audio_bitrate))
                        self._log(f"  → {mp4}")
                    else:
                        converted.append(VideoItem(path=item.path, start=item.start, end=item.end))

                self._log(f"Avvio concatenazione di {len(converted)} file...")
                result = concatVideo(converted, out_path)
                self._log(f"✅ DONE → {result}")
                messagebox.showinfo("Completato", f"File creato:\n{result}")
            except Exception as e:
                self._log(f"❌ Errore: {e}")
                messagebox.showerror("Errore", str(e))
            finally:
                self.run_btn.config(state=tk.NORMAL)
                self.progress.stop()

        threading.Thread(target=task, daemon=True).start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = VideoConcatApp()
    app.mainloop()
