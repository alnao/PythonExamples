# Task 2 of plan Polly Simple Examples3
Model: copilot:claude-sonnet-4.6 - Agent: DefaultAgent
Commit message: Creazione di 01_saveMp3


Prompt:
Header: DefaultAgent

Context: Leggi lo stato attuale per sapere cosa hanno fatto i predecessori dai files.
/mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task1-ordine-su-esempio-00-simplescript.md

Important: Hai il permesso e gli strumenti per modificare direttamente i file nel workspace corrente se necessario.
Important: Non eseguire mai comandi nel repository come commit, push, pull, merge o altri comandi di git. Non uscire mai dalla cartella di lavoro "workspace".

Constraint: Se finisci i tentativi di fix, scrivi 'STOP_FAILURE' e non fare il commit.

Task: poi usando sempre AWS polly voglio creare cartella "01_saveMp3" che usa AWS SDK e polly L'applicazione deve ricevere uno o più testi e salvare mp3 in un bucket. I dati in input sono "id, uuid, nome, pathS3, keyS3, testoDaLeggere" .

Se ti serve usa flask o fast-api e usa bootstrap 5 con fontawesome.



Log content:
Now I have a good picture. I'll create `AWS/Polly/01_saveMp3/` with a FastAPI app that synthesizes text via Polly and saves MP3s to S3.

Tutto creato e sintatticamente corretto. Ecco il riepilogo di `AWS/Polly/01_saveMp3/`:

| File | Ruolo |
|---|---|
| `main.py` | FastAPI app con `GET /`, `GET /voices`, `POST /synthesize` |
| `templates/index.html` | UI Bootstrap 5 + Font Awesome |
| `requirements.txt` | Dipendenze Python |
| `README.txt` | Istruzioni avvio e API |

**Come funziona:**
- La UI permette di aggiungere N elementi con i campi `id, uuid, nome, pathS3 (bucket), keyS3 (chiave S3), testoDaLeggere`
- Al click *Sintetizza e salva su S3*, viene chiamato `POST /synthesize` che per ogni item chiama `polly.synthesize_speech` → salva su S3 con `s3.put_object`
- Ogni risultato viene mostrato con badge success/error e l'URI `s3://bucket/key`

**Avvio:**
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```





Status: COMPLETED
