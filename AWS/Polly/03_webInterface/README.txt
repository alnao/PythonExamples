AWS Polly - 03_webInterface
==========================

Interfaccia web completa per AWS Polly con supporto a singolo elemento,
lista di elementi, JSON diretto e visualizzazione degli MP3 generati su S3.

Prerequisiti
------------
- Python 3.10+
- Credenziali AWS configurate (aws configure oppure variabile AWS_PROFILE)
- IAM policy: polly:SynthesizeSpeech, s3:PutObject, s3:GetObject, s3:ListBucket

Avvio
-----
  cd AWS/Polly/03_webInterface
  pip install -r requirements.txt
  python main.py

Oppure con variabili d'ambiente personalizzate:
  AWS_PROFILE=myprofile AWS_REGION=eu-west-1 python main.py

L'app sarà disponibile su http://localhost:8003

Endpoint API
------------
  GET  /                             Interfaccia web principale
  GET  /api/health                   Health check
  GET  /api/voices?language_code=it  Lista voci Polly disponibili
  POST /api/synthesize               Sintetizza lista item e salva su S3
  GET  /api/list-mp3?bucket=...      Lista file MP3 in un bucket S3
  GET  /api/download-mp3?bucket=...&key=...  Download MP3 da S3

Payload POST /api/synthesize
-----------------------------
  {
    "voice_id": "Bianca",
    "engine":   "neural",
    "items": [
      {
        "id":            "1",
        "uuid":          "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx",
        "nome":          "benvenuto",
        "pathS3":        "my-polly-bucket",
        "keyS3":         "audio/benvenuto.mp3",
        "testoDaLeggere": "Benvenuto nel sistema AWS Polly."
      }
    ]
  }

Funzionalità interfaccia
-------------------------
- Tab "Singolo elemento": form per un singolo item con generazione UUID automatica
- Tab "Lista elementi":   tabella con aggiunta/rimozione righe
- Tab "JSON diretto":     editor JSON con formattazione e mostra-esempio
- Sezione MP3 generati:  lista tutti gli MP3 nel bucket con download e preview audio
- Upload automatico di execution.log su S3 ad ogni sintesi
