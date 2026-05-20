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
import logging
from logging.handlers import RotatingFileHandler
import threading
import shutil

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from core import (
    C_MP4, C_MKV, C_OGV, C_VIDEO_TYPES,
    VideoItem,
    seconds_to_timecode, is_fast_seek,
    validate_crf, validate_audio_bitrate, parse_time,
    concat_video, convert_ogv_to_mp4,
)


class GUILogHandler(logging.Handler):
    """
    Logging handler che scrive i record nel widget tk.Text della GUI.

    Thread-safe: usa widget.after(0, ...) per schedulare le scritture
    sul main thread di tkinter, evitando errori da thread secondari.
    Il widget viene referenziato debolmente: se viene distrutto prima
    che il callback venga eseguito, l'eccezione TclError viene ignorata.
    """

    def __init__(self, text_widget: tk.Text):
        super().__init__()
        self._widget = text_widget
        self.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    def emit(self, record: logging.LogRecord):
        msg = self.format(record) + "\n"

        def _append():
            try:
                self._widget.config(state=tk.NORMAL)
                self._widget.insert(tk.END, msg)
                self._widget.see(tk.END)
                self._widget.config(state=tk.DISABLED)
            except tk.TclError:
                pass  # Widget distrutto, ignora silenziosamente

        try:
            self._widget.after(0, _append)
        except tk.TclError:
            pass


# Base class: use TkinterDnD.Tk when available for OS-level drag & drop support
_TkBase = TkinterDnD.Tk if _HAS_DND else tk.Tk


class VideoConcatApp(_TkBase):
    def __init__(self):
        super().__init__()
        self.title("VideoConcat - ffmpeg")
        self.resizable(True, True)
        self.minsize(760, 520)
        self.video_items = []
        self._current_proc = None       # Popen del processo ffmpeg in corso
        self._stop_event = threading.Event()  # Segnala interruzione al thread
        self._drag_start_idx = None     # Indice di inizio per drag-to-reorder
        self._build_ui()
        self._setup_logging()

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

        # Drag-to-reorder tramite mouse
        self.listbox.bind("<Button-1>", self._on_drag_start)
        self.listbox.bind("<B1-Motion>", self._on_drag_motion)
        self.listbox.bind("<ButtonRelease-1>", self._on_drag_release)

        # Drag & drop da file manager (richiede tkinterdnd2)
        if _HAS_DND:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self._on_files_dropped)

        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)

        self._btn_add = tk.Button(btn_frame, text="➕ Aggiungi file", width=18, command=self._add_files)
        self._btn_add.pack(pady=2)
        self._btn_folder = tk.Button(btn_frame, text="📁 Aggiungi cartella", width=18, command=self._add_folder)
        self._btn_folder.pack(pady=2)
        self._btn_up = tk.Button(btn_frame, text="⬆ Su", width=18, command=self._move_up)
        self._btn_up.pack(pady=2)
        self._btn_down = tk.Button(btn_frame, text="⬇ Giù", width=18, command=self._move_down)
        self._btn_down.pack(pady=2)
        self._btn_remove = tk.Button(btn_frame, text="🗑 Rimuovi", width=18, command=self._remove_selected)
        self._btn_remove.pack(pady=2)
        self._btn_clear = tk.Button(btn_frame, text="🧹 Svuota lista", width=18, command=self._clear_list)
        self._btn_clear.pack(pady=2)

        # --- Range frame ---
        range_frame = tk.LabelFrame(self, text="Intervallo per file selezionati (default: intero video)")
        range_frame.pack(fill=tk.X, **pad)
        tk.Label(range_frame, text="Da").pack(side=tk.LEFT, padx=(6, 2))
        self.from_var = tk.StringVar(value="")
        self._entry_from = tk.Entry(range_frame, textvariable=self.from_var, width=14)
        self._entry_from.pack(side=tk.LEFT, padx=(0, 8), pady=4)
        tk.Label(range_frame, text="A").pack(side=tk.LEFT, padx=(0, 2))
        self.to_var = tk.StringVar(value="")
        self._entry_to = tk.Entry(range_frame, textvariable=self.to_var, width=14)
        self._entry_to.pack(side=tk.LEFT, padx=(0, 8), pady=4)
        tk.Label(range_frame, text="(es: 00:01:10.5 oppure 70.5)").pack(side=tk.LEFT, padx=(0, 10))
        self._btn_apply_range = tk.Button(range_frame, text="Applica ai selezionati", command=self._apply_range_to_selected)
        self._btn_apply_range.pack(side=tk.LEFT, padx=4)
        self._btn_reset_range = tk.Button(range_frame, text="Reset (intero video)", command=self._reset_range_on_selected)
        self._btn_reset_range.pack(side=tk.LEFT, padx=4)

        # --- Quality frame ---
        quality_frame = tk.LabelFrame(self, text="Qualità per file selezionati (default: copia stream senza ri-codifica)")
        quality_frame.pack(fill=tk.X, **pad)
        tk.Label(quality_frame, text="CRF video").pack(side=tk.LEFT, padx=(6, 2))
        self.crf_var = tk.StringVar(value="")
        self._entry_crf = tk.Entry(quality_frame, textvariable=self.crf_var, width=6)
        self._entry_crf.pack(side=tk.LEFT, padx=(0, 2), pady=4)
        tk.Label(quality_frame, text="(0-51, 18=alta, 23=default, 28=bassa; vuoto=copia)").pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(quality_frame, text="Bitrate audio").pack(side=tk.LEFT, padx=(10, 2))
        self.audio_var = tk.StringVar(value="")
        self._entry_audio = tk.Entry(quality_frame, textvariable=self.audio_var, width=8)
        self._entry_audio.pack(side=tk.LEFT, padx=(0, 2), pady=4)
        tk.Label(quality_frame, text="(es: 128k, 192k; vuoto=copia)").pack(side=tk.LEFT, padx=(0, 10))
        self._btn_apply_quality = tk.Button(quality_frame, text="Applica ai selezionati", command=self._apply_quality_to_selected)
        self._btn_apply_quality.pack(side=tk.LEFT, padx=4)
        self._btn_reset_quality = tk.Button(quality_frame, text="Reset qualità", command=self._reset_quality_on_selected)
        self._btn_reset_quality.pack(side=tk.LEFT, padx=4)

        # --- Seeking mode frame ---
        seek_frame = tk.LabelFrame(
            self,
            text="Modalità seeking (posizionamento -ss rispetto a -i)"
        )
        seek_frame.pack(fill=tk.X, **pad)

        self.seek_var = tk.StringVar(value="auto")
        seek_options = [
            ("auto",    "Auto (rapido se copia, preciso se ri-codifica)"),
            ("fast",    "⚡ Rapido (−ss prima di −i: keyframe seeking, approssimativo)"),
            ("precise", "🎯 Preciso (−ss dopo −i: frame-accurate, più lento)"),
        ]
        self._seek_radios = []
        for val, label in seek_options:
            rb = tk.Radiobutton(seek_frame, text=label, variable=self.seek_var, value=val)
            rb.pack(side=tk.LEFT, padx=6, pady=4)
            self._seek_radios.append(rb)

        self._btn_apply_seek = tk.Button(seek_frame, text="Applica ai selezionati",
                  command=self._apply_seek_to_selected)
        self._btn_apply_seek.pack(side=tk.LEFT, padx=6, pady=4)
        self._btn_apply_seek_all = tk.Button(seek_frame, text="Applica a tutti",
                  command=self._apply_seek_to_all)
        self._btn_apply_seek_all.pack(side=tk.LEFT, padx=4, pady=4)

        # --- Output file frame ---
        out_frame = tk.LabelFrame(self, text="File di output")
        out_frame.pack(fill=tk.X, **pad)

        self.out_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "output.mp4"))
        self._entry_out = tk.Entry(out_frame, textvariable=self.out_var, width=60)
        self._entry_out.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
        self._btn_browse = tk.Button(out_frame, text="Sfoglia...", command=self._choose_output)
        self._btn_browse.pack(side=tk.LEFT, padx=4, pady=4)

        # Lista di tutti i controlli da disabilitare durante l'elaborazione
        self._all_controls = [
            self._btn_add, self._btn_folder, self._btn_up, self._btn_down,
            self._btn_remove, self._btn_clear,
            self._entry_from, self._entry_to,
            self._btn_apply_range, self._btn_reset_range,
            self._entry_crf, self._entry_audio,
            self._btn_apply_quality, self._btn_reset_quality,
            *self._seek_radios,
            self._btn_apply_seek, self._btn_apply_seek_all,
            self._entry_out, self._btn_browse,
        ]

        # --- Run / Stop buttons ---
        run_frame = tk.Frame(self)
        run_frame.pack(fill=tk.X, **pad)
        self.run_btn = tk.Button(run_frame, text="▶  Avvia concatenazione", bg="#2a7de1", fg="white",
                                 font=("Helvetica", 11, "bold"), command=self._run)
        self.run_btn.pack(side=tk.LEFT, pady=4)
        self.stop_btn = tk.Button(run_frame, text="⏹ Ferma", bg="#c0392b", fg="white",
                                  font=("Helvetica", 11, "bold"), command=self._stop_processing,
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=8, pady=4)

        # --- Progress / log ---
        log_frame = tk.LabelFrame(self, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=False, **pad)

        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, bg="#f4f4f4", wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Progressbar determinata con etichetta di stato
        progress_frame = tk.Frame(self)
        progress_frame.pack(fill=tk.X, padx=8, pady=(2, 0))
        self.progress_label = tk.Label(progress_frame, text="", anchor="w", fg="#444")
        self.progress_label.pack(fill=tk.X)
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(
            progress_frame, mode="determinate",
            variable=self.progress_var, maximum=100,
        )
        self.progress.pack(fill=tk.X, pady=(1, 6))

    # --- Helpers ---

    def _log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _set_progress(self, value: float, label: str = ""):
        """Aggiorna la progressbar e l'etichetta (solo dal main thread)."""
        self.progress_var.set(value)
        self.progress_label.config(text=label)

    def _update_progress(self, value: float, label: str = ""):
        """Thread-safe: schedula _set_progress sul main thread tramite after()."""
        self.after(0, lambda v=value, l=label: self._set_progress(v, l))

    def _set_ui_busy(self, busy: bool):
        """Abilita o disabilita tutti i controlli di input durante l'elaborazione."""
        state = tk.DISABLED if busy else tk.NORMAL
        for widget in self._all_controls:
            try:
                widget.config(state=state)
            except tk.TclError:
                pass
        self.listbox.config(state=tk.DISABLED if busy else tk.NORMAL)
        self.run_btn.config(state=tk.DISABLED if busy else tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL if busy else tk.DISABLED)

    def _stop_processing(self):
        """Chiede all'utente conferma e poi interrompe il processo ffmpeg in corso."""
        if not messagebox.askyesno(
            "Interrompere?",
            "Vuoi interrompere l'elaborazione in corso?\n"
            "Il file di output parziale potrebbe essere incompleto o corrotto."
        ):
            return
        self._stop_event.set()
        if self._current_proc and self._current_proc.poll() is None:
            try:
                self._current_proc.terminate()
            except OSError:
                pass
        self._log("⚠️ Interruzione richiesta dall'utente.")

    # --- Drag & drop from file manager ---

    def _on_files_dropped(self, event):
        """Gestisce file trascinati dalla GUI del sistema operativo (tkinterdnd2)."""
        import re as _re
        raw = event.data
        paths = _re.findall(r'\{([^}]+)\}|(\S+)', raw)
        paths = [p[0] or p[1] for p in paths]
        video_exts = {C_MP4, C_MKV, C_OGV, ".avi", ".mov"}
        valid = [p for p in paths if os.path.isfile(p) and os.path.splitext(p)[1].lower() in video_exts]
        if valid:
            self._add_video_paths(valid)
        else:
            messagebox.showwarning(
                "Formato non supportato",
                "Nessun file video riconosciuto tra quelli trascinati.\n"
                "Formati accettati: .mp4 .mkv .ogv .avi .mov"
            )

    # --- Drag-to-reorder (mouse) ---

    def _on_drag_start(self, event):
        self._drag_start_idx = self.listbox.nearest(event.y)

    def _on_drag_motion(self, event):
        """Mostra feedback visivo durante il trascinamento interno alla listbox."""
        if self._drag_start_idx is None:
            return
        target = self.listbox.nearest(event.y)
        if target != self._drag_start_idx:
            self.listbox.config(cursor="sb_v_double_arrow")
        else:
            self.listbox.config(cursor="")

    def _on_drag_release(self, event):
        """Riordina gli elementi trascinando con il mouse."""
        if self._drag_start_idx is None:
            return
        target = self.listbox.nearest(event.y)
        src = self._drag_start_idx
        self._drag_start_idx = None
        self.listbox.config(cursor="")
        if target < 0 or target == src or not self.video_items:
            return
        item = self.video_items.pop(src)
        self.video_items.insert(target, item)
        self._refresh_listbox()
        self.listbox.selection_set(target)

    def _setup_logging(self):
        """
        Configura due handler sul root logger:
        1. GUILogHandler  → scrive in self.log_text (nella GUI).
        2. RotatingFileHandler → scrive su ~/videoconcat.log (max 2 MB × 3 backup).
        Rimuove eventuali StreamHandler aggiunti da basicConfig per evitare duplicati.
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        for h in root_logger.handlers[:]:
            if isinstance(h, logging.StreamHandler) and not isinstance(h, (logging.FileHandler, RotatingFileHandler)):
                root_logger.removeHandler(h)

        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setLevel(logging.INFO)
        root_logger.addHandler(gui_handler)

        log_file = os.path.join(os.path.expanduser("~"), "videoconcat.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        root_logger.addHandler(file_handler)

        logging.info(f"Log su file: {log_file}")

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
            seek_label = {"fast": " | seek:⚡rapido", "precise": " | seek:🎯preciso"}.get(item.seek_mode, "")
            self.listbox.insert(tk.END, f"{item.path}{rng}{quality}{seek_label}")
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

    def _apply_range_to_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona almeno un file dalla lista.")
            return

        start_raw = self.from_var.get().strip()
        end_raw = self.to_var.get().strip()
        try:
            start_seconds = parse_time(start_raw)
            end_seconds = parse_time(end_raw)
        except ValueError as err:
            messagebox.showerror("Errore", str(err))
            return

        if start_seconds is not None and end_seconds is not None and start_seconds >= end_seconds:
            messagebox.showerror("Errore", "L'intervallo non è valido: 'Da' deve essere minore di 'A'.")
            return

        start_tc = seconds_to_timecode(start_seconds) if start_seconds is not None else ""
        end_tc = seconds_to_timecode(end_seconds) if end_seconds is not None else ""
        for i in selection:
            self.video_items[i].start = start_tc
            self.video_items[i].end = end_tc
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

        ok, err = validate_crf(crf)
        if not ok:
            messagebox.showerror("CRF non valido", err)
            return
        if crf:
            crf = str(int(crf))  # normalizza: rimuove zeri iniziali e spazi

        ok, err = validate_audio_bitrate(audio)
        if not ok:
            messagebox.showerror("Bitrate audio non valido", err)
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

    def _apply_seek_to_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona almeno un file dalla lista.")
            return
        mode = self.seek_var.get()
        for i in selection:
            self.video_items[i].seek_mode = mode
        self._refresh_listbox()
        for i in selection:
            self.listbox.selection_set(i)

    def _apply_seek_to_all(self):
        mode = self.seek_var.get()
        for item in self.video_items:
            item.seek_mode = mode
        self._refresh_listbox()

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

        out_real = os.path.realpath(out_path)
        for item in self.video_items:
            if os.path.realpath(item.path) == out_real:
                messagebox.showerror(
                    "Percorso di output non valido",
                    f"Il file di output coincide con un file di input:\n{item.path}\n\n"
                    "Scegli un percorso diverso per il file di output."
                )
                return

        if os.path.exists(out_path):
            if not messagebox.askyesno(
                "Sovrascrivi file?",
                f"Il file di output esiste già:\n{out_path}\n\n"
                "Vuoi sovrascriverlo?"
            ):
                return

        self._stop_event.clear()
        self._set_ui_busy(True)
        self._set_progress(0.0, "Avvio...")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        stop_event = self._stop_event

        def _set_proc(proc):
            self._current_proc = proc

        def task():
            try:
                converted = []
                for item in self.video_items:
                    if stop_event.is_set():
                        raise RuntimeError("Elaborazione interrotta dall'utente.")
                    if item.path.lower().endswith(C_OGV):
                        self._log(f"Conversione OGV→MP4: {item.path}")
                        self._update_progress(0.0, f"Conversione OGV: {os.path.basename(item.path)}")
                        mp4 = convert_ogv_to_mp4(item.path, item.video_crf, item.audio_bitrate)
                        converted.append(VideoItem(path=mp4, start=item.start, end=item.end,
                                                   video_crf=item.video_crf, audio_bitrate=item.audio_bitrate))
                        self._log(f"  → {mp4}")
                    else:
                        converted.append(VideoItem(path=item.path, start=item.start, end=item.end))

                self._log(f"Avvio concatenazione di {len(converted)} file...")
                result = concat_video(
                    converted, out_path,
                    progress_cb=self._update_progress,
                    proc_cb=_set_proc,
                    stop_event=stop_event,
                )
                self._log(f"✅ DONE → {result}")
                messagebox.showinfo("Completato", f"File creato:\n{result}")
            except Exception as e:
                self._log(f"❌ Errore: {e}")
                if not stop_event.is_set():
                    messagebox.showerror("Errore", str(e))
            finally:
                self._current_proc = None
                self.after(0, lambda: self._set_ui_busy(False))
                self.after(0, lambda: self._set_progress(0.0, ""))

        threading.Thread(target=task, daemon=True).start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if shutil.which("ffmpeg") is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "ffmpeg non trovato",
            "ffmpeg non è installato o non è disponibile nel PATH di sistema.\n\n"
            "Installa ffmpeg e riprova:\n"
            "  • Linux: sudo apt install ffmpeg\n"
            "  • macOS: brew install ffmpeg\n"
            "  • Windows: https://ffmpeg.org/download.html"
        )
        root.destroy()
        raise SystemExit(1)
    app = VideoConcatApp()
    app.mainloop()
