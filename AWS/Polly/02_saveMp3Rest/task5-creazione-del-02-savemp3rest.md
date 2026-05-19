# Task 5 of plan Polly Simple Examples3
Model: copilot:gpt-5.3-codex - Agent: DefaultAgent
Commit message: Creazione del 02_saveMp3Rest


Prompt:
Header: DefaultAgent

Context: Leggi lo stato attuale per sapere cosa hanno fatto i predecessori dai files.
/mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task1-ordine-su-esempio-00-simplescript.md
 - /mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task2-creazione-di-01-savemp3.md
 - /mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task3-creazione-di-log-del-01-savemp3.md
 - /mnt/Dati4/todel/workspace/.AlNaoAIRunners/planplan-6a6ae5a6-polly-simple-examples3/task4-creazione-di-log-e-interfaccia-del-01-savemp3.md

Important: Hai il permesso e gli strumenti per modificare direttamente i file nel workspace corrente se necessario.
Important: Non eseguire mai comandi nel repository come commit, push, pull, merge o altri comandi di git. Non uscire mai dalla cartella di lavoro "workspace".

Constraint: Se finisci i tentativi di fix, scrivi 'STOP_FAILURE' e non fare il commit.

Task: poi voglio creare un "02_saveMp3Rest" che espone una API che riceve elenco via REST ed esegue il passo del 01_saveMp3.

Se ti serve usa flask o fast-api e usa bootstrap 5 con fontawesome.



Log content:
Fatto: ho creato **`AWS/Polly/02_saveMp3Rest`** con una app **Flask REST** che riceve una lista (`id, uuid, nome, pathS3, keyS3, testoDaLeggere`) e applica il flusso del `01_saveMp3` (Polly `synthesize_speech` + upload MP3 su S3 + upload `execution.log` sui bucket coinvolti).  
Ho aggiunto anche UI di test con **Bootstrap 5 + Font Awesome** (`GET /`), endpoint `GET /api/health`, endpoint principale `POST /api/synthesize`, più `requirements.txt` e `README.txt` con esempio `curl`; verifica completata con `python -m py_compile main.py` e `python -m compileall -q .` senza errori.  
Per avvio: `cd AWS/Polly/02_saveMp3Rest && pip install -r requirements.txt && python main.py` (porta `8002`).





Status: COMPLETED
