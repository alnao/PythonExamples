"""
## NOTA: questa versione usa pytube che non funziona dal 2024
# vedere main.py per la versione aggiornata con yt-dlp

# esempio preso dal video https://www.youtube.com/watch?v=EMlM6QTzJo0
# installare pytube con
    pip install pytube

"""
    
"""
Versione base e semplice
from pytube import YouTube

def downloader(link):
    youtubeObject = YouTube(link)
    youtubeObject = youtubeObject.streams.get_highest_resolution()
    try:
        youtubeObject.download()
    except Exception as e:
        print ("Errore downloading")
        print (e)
    print("Downloaded")

if __name__ == '__main__':
    link = input("Youtube link URL:")
    downloader(link)
"""



"""
Versione con flask che non funziona
"""
from flask import Flask, render_template, request, jsonify
from pytube import YouTube
import os
import re
from pathlib import Path

app = Flask(__name__)

# Configurazione percorsi
MP3_PATH = "/mnt/Dati/daSmistare/mp3"
MP4_PATH = "/mnt/Dati/daSmistare/mp4"

def sanitize_filename(filename):
    """Rimuove caratteri non validi dal nome del file"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def download_video(url, format_type):
    """
    Scarica il video da YouTube nel formato specificato
    Returns: (success, message)
    """
    try:
        # Crea l'oggetto YouTube
        yt = YouTube(url)
        
        # Seleziona il percorso base in base al formato
        base_path = MP3_PATH if format_type == 'mp3' else MP4_PATH
        
        # Assicurati che la directory esista
        Path(base_path).mkdir(parents=True, exist_ok=True)
        
        if format_type == 'mp3':
            # Scarica l'audio
            video = yt.streams.filter(only_audio=True).first()
            out_file = video.download(base_path)
            
            # Converti in MP3
            base, _ = os.path.splitext(out_file)
            new_file = base + '.mp3'
            os.rename(out_file, new_file)
            filename = os.path.basename(new_file)
            
        else:  # mp4
            # Scarica il video in alta qualità
            video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            out_file = video.download(base_path)
            filename = os.path.basename(out_file)
        
        return True, f"Scaricato con successo: {filename}"
        
    except Exception as e:
        return False, f"Errore durante il download: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    urls = data.get('urls', [])
    format_type = data.get('format', 'mp4')
    
    results = []
    for url in urls:
        success, message = download_video(url.strip(), format_type)
        results.append({
            'url': url,
            'success': success,
            'message': message
        })
    
    return jsonify({'results': results})

if __name__ == '__main__':
    # Assicurati che le directory esistano
    Path(MP3_PATH).mkdir(parents=True, exist_ok=True)
    Path(MP4_PATH).mkdir(parents=True, exist_ok=True)
    app.run(debug=True, host='0.0.0.0',port=5001)