
#see https://www.youtube.com/watch?v=EMlM6QTzJo0
#pip install pytube
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

link = input("Youtube link URL:")
downloader(link)
