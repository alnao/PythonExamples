#!/usr/bin/env python3
# chmod +x script.py
# ./script

# SCRIPT TO CONCAT VIDEO with MPEG, source must be in MKV format, output will be in out.mp4 file
# Usa subprocess.run per tutti i comandi ffmpeg (più sicuro e robusto)
# Gestisce i percorsi con os.path.join (compatibile e sicuro per spazi)
# Logga errori e operazioni con il modulo logging
# Cancella i file temporanei in modo sicuro (con try/except)
# Fornisce feedback chiaro in caso di errori
# SEE https://www.educative.io/answers/how-to-run-a-python-script-in-linux
# https://stackoverflow.com/questions/11295917/how-to-select-a-directory-and-store-the-location-using-tkinter-in-python

from tkinter import filedialog
from tkinter import *
import os
from os import listdir
from os.path import isfile, join
import subprocess
import logging

C_MP4=".mp4"
C_MKV=".mkv"
C_OGV=".ogv"

def selectExtension(fileName):
    if fileName.endswith(C_MP4) or fileName.endswith(C_MKV):
        return True
    else:
        return False

def selectFolder():
    root = Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    print("Folder, ",folder_selected)
    return folder_selected

def filesInFolder(folder):
    only_files = [f for f in listdir(folder) if isfile(join(folder, f)) and selectExtension(f)  ]
    return only_files

def run_ffmpeg(cmd_list):
    """Esegue un comando ffmpeg e gestisce errori/log."""
    logging.info(f"Eseguo: {' '.join(cmd_list)}")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Errore ffmpeg: {result.stderr}")
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return result

def concatVideo(folder, files):
    list_ts = []
    for file in files:
        print("--------------------")
        print("Inizio a processare il video", file)
        ts_path = os.path.join(folder, f"fileIntermediate{len(list_ts)}.ts")
        cmd = [
            "ffmpeg", "-i", os.path.join(folder, file),
            "-c", "copy", "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", ts_path
        ]
        list_ts.append(ts_path)
        run_ffmpeg(cmd)
    print("--------------------")
    print("FInito il ciclo, inizio ad unire i video")
    list_ts_str = "|".join(list_ts)
    out_path = os.path.join(folder, "out.mp4")
    cmd = [
        "ffmpeg", "-i", f"concat:{list_ts_str}", "-c", "copy", "-bsf:a", "aac_adtstoasc", out_path
    ]
    run_ffmpeg(cmd)
    for file in list_ts:
        try:
            os.remove(file)
        except Exception as e:
            logging.warning(f"Non riesco a cancellare {file}: {e}")
    return out_path

def concertOgvToMkv(folder):
    files = [f for f in listdir(folder) if isfile(join(folder, f)) and f.endswith(C_OGV)]
    for file in files:
        out_file = os.path.join(folder, file.replace(C_OGV, C_MP4))
        cmd = [
            "ffmpeg", "-i", os.path.join(folder, file), "-vcodec", "libx264", out_file
        ]
        run_ffmpeg(cmd)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    folder = selectFolder()
    concertOgvToMkv(folder)
    files = filesInFolder(folder)
    try:
        out = concatVideo(folder, files)
        print(out)
        print("DONE")
    except Exception as e:
        print(f"Errore durante la concatenazione: {e}")
