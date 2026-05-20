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

C_MP4 = ".mp4"
C_MKV = ".mkv"
C_OGV = ".ogv"
C_VIDEO_TYPES = [("Video files", "*.mp4 *.mkv *.ogv *.avi *.mov"), ("All files", "*.*")]


def run_ffmpeg(cmd_list):
    """Esegue un comando ffmpeg e gestisce errori/log."""
    logging.info(f"Eseguo: {' '.join(cmd_list)}")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Errore ffmpeg: {result.stderr}")
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return result


def concatVideo(file_paths, out_path):
    """Concatena una lista di file video (percorsi assoluti) nel file di output specificato."""
    tmp_dir = os.path.dirname(out_path) or os.getcwd()
    list_ts = []
    for i, file_path in enumerate(file_paths):
        logging.info(f"Inizio a processare il video: {file_path}")
        ts_path = os.path.join(tmp_dir, f"_fileIntermediate{i}.ts")
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-c", "copy", "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", ts_path
        ]
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


def convertOgvToMp4(file_path):
    """Converte un file OGV in MP4 nella stessa cartella."""
    out_file = file_path.replace(C_OGV, C_MP4)
    cmd = ["ffmpeg", "-y", "-i", file_path, "-vcodec", "libx264", out_file]
    run_ffmpeg(cmd)
    return out_file


class VideoConcatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VideoConcat - ffmpeg")
        self.resizable(True, True)
        self.minsize(620, 480)
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
        for p in paths:
            self.listbox.insert(tk.END, p)

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Seleziona cartella")
        if not folder:
            return
        video_exts = {C_MP4, C_MKV, C_OGV, ".avi", ".mov"}
        files = sorted([
            join(folder, f) for f in listdir(folder)
            if isfile(join(folder, f)) and os.path.splitext(f)[1].lower() in video_exts
        ])
        for f in files:
            self.listbox.insert(tk.END, f)

    def _remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)

    def _clear_list(self):
        self.listbox.delete(0, tk.END)

    def _move_up(self):
        selection = self.listbox.curselection()
        for i in selection:
            if i == 0:
                continue
            text = self.listbox.get(i)
            self.listbox.delete(i)
            self.listbox.insert(i - 1, text)
            self.listbox.selection_set(i - 1)

    def _move_down(self):
        selection = self.listbox.curselection()
        for i in reversed(selection):
            if i == self.listbox.size() - 1:
                continue
            text = self.listbox.get(i)
            self.listbox.delete(i)
            self.listbox.insert(i + 1, text)
            self.listbox.selection_set(i + 1)

    def _choose_output(self):
        path = filedialog.asksaveasfilename(
            title="Scegli il file di output",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("All files", "*.*")]
        )
        if path:
            self.out_var.set(path)

    def _run(self):
        files = list(self.listbox.get(0, tk.END))
        if not files:
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
                for f in files:
                    if f.lower().endswith(C_OGV):
                        self._log(f"Conversione OGV→MP4: {f}")
                        mp4 = convertOgvToMp4(f)
                        converted.append(mp4)
                        self._log(f"  → {mp4}")
                    else:
                        converted.append(f)

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
