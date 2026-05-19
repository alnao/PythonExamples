AWS Polly – Save MP3 to S3
==========================

Descrizione
-----------
Applicazione FastAPI che riceve una lista di elementi
(id, uuid, nome, pathS3, keyS3, testoDaLeggere), sintetizza
ogni testo con AWS Polly (formato MP3) e carica il file audio
sul bucket Amazon S3 indicato.

Prerequisiti
------------
- Python 3.9+
- Credenziali AWS configurate (aws configure) o variabili d'ambiente
  AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN
- Il bucket S3 deve già esistere e il profilo IAM deve avere i permessi:
    polly:SynthesizeSpeech
    s3:PutObject

Installazione
-------------
    pip install -r requirements.txt

Avvio
-----
    uvicorn main:app --reload --port 8001

Aprire il browser su:  http://localhost:8001

Variabili d'ambiente opzionali
-------------------------------
    AWS_PROFILE   (default: "default")
    AWS_REGION    (default: "eu-west-1")

API
---
  GET  /          – Interfaccia web
  GET  /voices    – Lista voci Polly disponibili
                    ?language_code=it-IT  (opzionale)
  POST /synthesize – Sintetizza e salva su S3
    Body JSON:
    {
      "voice_id": "Bianca",
      "engine":   "neural",
      "items": [
        {
          "id":             "1",
          "uuid":           "abc-123",
          "nome":           "benvenuto",
          "pathS3":         "my-bucket",
          "keyS3":          "audio/benvenuto.mp3",
          "testoDaLeggere": "Benvenuto nel sistema!"
        }
      ]
    }

    Risposta:
    {
      "results": [
        {
          "id":      "1",
          "uuid":    "abc-123",
          "nome":    "benvenuto",
          "s3_uri":  "s3://my-bucket/audio/benvenuto.mp3",
          "status":  "success",
          "message": "MP3 saved to S3 successfully"
        }
      ]
    }
