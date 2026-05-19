# Task 6 of plan Polly Simple Examples3
Model: copilot:claude-sonnet-4.6 - Agent: DefaultAgent
Commit message: Creazione del 02_saveMp3Rest con import json


Prompt:
Header: DefaultAgent

Context: Leggi lo stato attuale per sapere cosa hanno fatto i predecessori dai files.
/mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task1-ordine-su-esempio-00-simplescript.md
 - /mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task2-creazione-di-01-savemp3.md
 - /mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task3-creazione-di-log-del-01-savemp3.md
 - /mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task4-creazione-di-log-e-interfaccia-del-01-savemp3.md
 - /mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task5-creazione-del-02-savemp3rest.md

Important: Hai il permesso e gli strumenti per modificare direttamente i file nel workspace corrente se necessario.
Important: Non eseguire mai comandi nel repository come commit, push, pull, merge o altri comandi di git. Non uscire mai dalla cartella di lavoro "workspace".

Constraint: Se finisci i tentativi di fix, scrivi 'STOP_FAILURE' e non fare il commit.

Task: Ciao, crea una interfaccia web che permetta di chiamare l'api con un elemento o una lista o passando un json , dammi anche la possiblità di vedere un json di esempio. Dalla interfaccia vorrei vedere anche tutti gli mp3 generati

Se ti serve usa flask o fast-api e usa bootstrap 5 con fontawesome.



Log content:
Ora creo la cartella `03_webInterface` con un'app Flask completa che ha 3 modalità di input e la visualizzazione degli MP3 generati.

Tutto creato e verificato. Ecco cosa ho realizzato in `AWS/Polly/03_webInterface/`:

| File | Ruolo |
|---|---|
| `main.py` | Flask app porta 8003, endpoints: `/api/synthesize`, `/api/list-mp3`, `/api/download-mp3`, `/api/voices`, `/api/health` |
| `templates/index.html` | UI Bootstrap 5 + Font Awesome |
| `requirements.txt` | Dipendenze |
| `README.txt` | Istruzioni |

**Funzionalità UI:**
- **Tab "Singolo elemento"** – form con tutti i campi + generazione UUID automatica + pulsante "Riempi con esempio"
- **Tab "Lista elementi"** – tabella con add/remove righe, ogni riga ha generazione UUID
- **Tab "JSON diretto"** – editor JSON con pulsanti "Mostra JSON di esempio" (modal), "Carica esempio", "Formatta JSON"
- **Sezione MP3 generati** – lista tutti gli `.mp3` del bucket S3 con colonne: nome, dimensione, data, URI, pulsanti download e **preview audio inline**
- Health check badge in header, aggiornamento automatico lista MP3 dopo ogni sintesi

**Avvio:**
```bash
cd AWS/Polly/03_webInterface
pip install -r requirements.txt
python main.py  # http://localhost:8003
```





Status: COMPLETED
