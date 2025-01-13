"""
Script per scaricare video da YouTube in formato mp3 o mp4.
Utilizza yt-dlp per scaricare i video e Flask per creare un'interfaccia web.

Per installare yt-dlp:
    pip install yt-dlp
    pip install -U yt-dlp --break-system-packages

Per eseguire il server:
    python main.py

Per scaricare un video:
    - Aprire il browser e andare su http://localhost:5001/
    - Incollare l'URL del video di YouTube
    - Selezionare il formato (mp3 o mp4)
    - Fare clic su "Download"

Il video verrà scaricato nella cartella /mnt/Dati/daSmistare/mp3 o /mnt/Dati/daSmistare/mp4
"""

from flask import Flask, render_template, request, jsonify
import yt_dlp
import os
import re
import logging
from pathlib import Path

# Configura il logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurazione percorsi
MP3_PATH = "/mnt/Dati/daSmistare/mp3"
MP4_PATH = "/mnt/Dati/daSmistare/mp4"

def sanitize_filename(filename):
    """Rimuove caratteri non validi dal nome del file"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

class MyLogger:
    def debug(self, msg):
        logger.debug(msg)
    def warning(self, msg):
        logger.warning(msg)
    def error(self, msg):
        logger.error(msg)

def my_hook(d):
    if d['status'] == 'downloading':
        logger.info(f"Downloading: {d.get('_percent_str', '0%')} of {d.get('_total_bytes_str', 'unknown size')}")
    elif d['status'] == 'finished':
        logger.info(f"Download completed. Converting...")

def download_video(url, format_type):
    """
    Scarica il video da YouTube nel formato specificato
    Returns: (success, message)
    """
    try:
        logger.info(f"Iniziando il download dell'URL: {url} in formato {format_type}")
        
        # Configurazione di base comune
        base_opts = {
            'verbose': True,
            'no_warnings': False,
            'progress_hooks': [my_hook],
            'logger': MyLogger(),
        }

        # Configura le opzioni specifiche in base al formato
        if format_type == 'mp3':
            output_template = os.path.join(MP3_PATH, '%(title)s.%(ext)s')
            ydl_opts = {
                **base_opts,
                'format': 'bestaudio/best',
                'outtmpl': output_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:  # mp4
            output_template = os.path.join(MP4_PATH, '%(title)s.%(ext)s')
            ydl_opts = {
                **base_opts,
                'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b',
                'outtmpl': output_template,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'merge_output_format': 'mp4',
            }

        # Esegui il download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Estrazione informazioni video...")
            info = ydl.extract_info(url, download=True)
            filename = sanitize_filename(info.get('title', 'video'))
            logger.info(f"Nome file dopo sanitizzazione: {filename}")
            
            # Verifica che il file sia stato creato correttamente
            if format_type == 'mp3':
                expected_file = os.path.join(MP3_PATH, f"{filename}.mp3")
            else:
                expected_file = os.path.join(MP4_PATH, f"{filename}.mp4")
            
            # Cerca anche file con estensione .ytdl e rinominali
            ytdl_file = f"{expected_file}.ytdl"
            if os.path.exists(ytdl_file):
                try:
                    os.rename(ytdl_file, expected_file)
                    logger.info(f"File .ytdl rinominato in {expected_file}")
                except Exception as e:
                    logger.error(f"Errore nel rinominare il file .ytdl: {str(e)}")
            
            logger.info(f"Cercando il file: {expected_file}")
            if os.path.exists(expected_file):
                file_size = os.path.getsize(expected_file)
                logger.info(f"File trovato! Dimensione: {file_size} bytes")
                return True, f"Scaricato con successo: {filename} ({file_size} bytes)"
            else:
                # Lista i file nella directory per debug
                if format_type == 'mp3':
                    files = os.listdir(MP3_PATH)
                else:
                    files = os.listdir(MP4_PATH)
                logger.error(f"File non trovato. Files in directory: {files}")
                return False, f"File non creato correttamente. Files in directory: {files}"
        
    except Exception as e:
        logger.error(f"Errore durante il download: {str(e)}", exc_info=True)
        error_message = str(e)
        if "HTTP Error 403" in error_message:
            return False, "Errore di accesso: prova ad aggiornare yt-dlp con 'pip install -U yt-dlp'"
        return False, f"Errore durante il download: {error_message}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    urls = data.get('urls', [])
    format_type = data.get('format', 'mp4')
    
    logger.info(f"Richiesta download ricevuta. URLs: {urls}, Formato: {format_type}")
    
    # Assicurati che le directory esistano
    Path(MP3_PATH).mkdir(parents=True, exist_ok=True)
    Path(MP4_PATH).mkdir(parents=True, exist_ok=True)
    
    # Log dei permessi delle directory
    logger.info(f"Permessi MP3_PATH: {oct(os.stat(MP3_PATH).st_mode)[-3:]}")
    logger.info(f"Permessi MP4_PATH: {oct(os.stat(MP4_PATH).st_mode)[-3:]}")
    
    results = []
    for url in urls:
        success, message = download_video(url.strip(), format_type)
        results.append({
            'url': url,
            'success': success,
            'message': message
        })
    
    # Rimuovi eventuali file .part o .yaml rimasti
    for path in [MP3_PATH, MP4_PATH]:
        for file in os.listdir(path):
            if file.endswith(('.part', '.yaml', '.ytdl')):
                try:
                    logger.info(f"Rimuovendo file temporaneo: {file}")
                    os.remove(os.path.join(path, file))
                except Exception as e:
                    logger.error(f"Errore nella rimozione del file {file}: {str(e)}")
    
    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5001)
