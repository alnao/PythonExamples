AWS Polly - 02_saveMp3Rest
==========================

Descrizione
-----------
Esempio REST con Flask che riceve via JSON una lista di item:
`id, uuid, nome, pathS3, keyS3, testoDaLeggere`.
Per ogni item esegue la stessa logica di `01_saveMp3`:
- sintesi testo con AWS Polly in MP3
- upload MP3 su S3 (`pathS3` bucket, `keyS3` key)
- scrittura `execution.log` sui bucket coinvolti

Prerequisiti
------------
- Python 3.9+
- Credenziali AWS valide
- Permessi IAM: `polly:SynthesizeSpeech`, `s3:PutObject`

Installazione
-------------
    pip install -r requirements.txt

Avvio
-----
    python main.py

Server attivo su:
    http://localhost:8002

Endpoint
--------
- `GET /` UI Bootstrap 5 + Font Awesome per test manuale
- `GET /api/health` health check
- `POST /api/synthesize` endpoint REST principale

Esempio `curl`
--------------
curl -X POST "http://localhost:8002/api/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "voice_id": "Bianca",
    "engine": "neural",
    "items": [
      {
        "id": "1",
        "uuid": "abc-123",
        "nome": "welcome",
        "pathS3": "my-bucket",
        "keyS3": "audio/welcome.mp3",
        "testoDaLeggere": "Benvenuto nel sistema"
      }
    ]
  }'
