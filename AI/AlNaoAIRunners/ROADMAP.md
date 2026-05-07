# Roadmap di Sviluppo:AlNaoAIRunners (AI Runners)

Questo documento definisce il piano di lavoro incrementale per la costruzione dell'architetturaAlNaoAIRunners. La progettazione è modulare per permettere test mirati, facilitare la ripresa dopo crash e consentire in futuro l'integrazione di molteplici strumenti a riga di comando (CLI).

## Fase 1: Fondamenta e Struttura Dati (Database & Core)
L'obiettivo di questa fase è preparare le basi dell'applicazione, il database SQLite locale e l'astrazione per manipolare il repository.

1. **Inizializzazione Flask e configurazione**
   - Setup ambiente Python, `requirements.txt`.
   - Lettura impostazioni dal file `.env` (percorsi, chiavi, modelli disponibili, nomi di branch).
2. **Setup SQLite (Persistenza dello stato)**
   - Creazione schema per `Plan`, `Task`, `ExecutionState`, `Log`.
   - Predisposizione dei campi necessari per la ripresa dell'esecuzione (`last_commit_hash`, `status`, ecc.).
3. **Inizializzazione GitManager**
   - Modulo per interfacciarsi con il repository: `clone` in locale, `checkout`/creazione branch, `commit` incrementali e `push`.

## Fase 2: Astrazione CLI e Costruzione dei Prompt
Preparazione dell'interfaccia verso i modelli AI in modo che il codice non sia legato a una singola CLI, rispettando il requisito di scalabilità per il futuro.

1. **Pattern `AbstractCLIProvider`**
   - Creazione classe base/interfaccia con metodi come `execute(prompt)`, `check_rate_limit()`, `parse_response()`.
2. **Implementazione Provider Specifici (Completato)**
   - Implementazione di `ClaudeCLIProvider` (chiamata reale a `claude -p`).
   - Implementazione di `GeminiCLIProvider` (richiede `npm install -g @google/gemini-cli`, usa `gemini -p`).
   - *Nota: Questa struttura rende banale l'aggiunta futura di altre CLI (es. OpenAI, Cursor).*
3. **Agent Context Builder (Compositore di Prompt)**
   - Modulo per unire i file di identità (`.md` dell'agente), il task specifico dell'utente, i constraints (regola "STOP_FAILURE") e la lettura della cronologia nella cartella log.

## Fase 3: Esecutore Singolo Step (Milestone Intermedia)
*Questa è la fase centrale richiesta: eseguire un singolo task prima di complicare il sistema con loop, piani complessi e concorrenza.*

1. **Implementazione di `SingleStepRunner`**
   - Riceve in input i dettagli di un *singolo* Task.
   - Chiama l'`Agent Context Builder` per assemblare la richiesta.
   - Interroga il modello tramite l'`AbstractCLIProvider` configurato.
   - Salva i ragionamenti e le modifiche in `.AlNaoAgent/logs/<id_plan>/<id_step>.md`.
2. **Meccanismo di Compilazione/Test e Auto-Fix**
   - Dopo l'esecuzione della CLI, esegue comandi locali per validare il codice.
   - Se fallisce, tenta `max_fix_attempts` di re-interrogare il modello per correggere l'errore.
   - Gestione caso "STOP_FAILURE" (prevenzione di loop infiniti e blocco del task).
3. **Gestione Base dei Rate Limit**
   - Se l'esecutore rileva "limit/rate raggiunti", mette lo stato in `WAITING_CREDITS` per essere ripreso.
4. **Script/Endpoint di Test Singolo**
   - Script CLI o rotta di debug per far partire e osservare un task isolato dal resto del piano.

## Fase 4: Orchestrazione Multi-Step (Pipeline Complessa)
Avendo un esecutore di step affidabile, si procede alla costruzione dell'intero piano in sequenza.

1. **Implementazione di `PlanOrchestrator`**
   - Carica un Piano dal DB.
   - Delega a `GitManager` il `clone` iniziale.
   - In un ciclo sequenziale, richiama `SingleStepRunner` per ogni Task associato al piano.
   - Assicura che la concorrenza locale impedisca due task/piani sovrapposti.
2. **Commit e Ripristino di Stato**
   - Dopo il successo di un `SingleStepRunner`, delega a `GitManager` il salvataggio (`git commit`).
   - Aggiorna su DB il `last_commit_hash` in modo che se la macchina EC2 si riavvia o si blocca, sa esattamente da che stato Git ripartire e quale log di task saltare.
3. **Push Finale**
   - Completato il ciclo dei task, esegue il `push` del branch e segna il piano come completato.

## Fase 5: Background Worker e Schedulazione (Autonomia)
Gestione dell'esecuzione automatica non presidiata.

1. **Integrazione Task Queue/APScheduler**
   - Spostamento di `PlanOrchestrator` all'interno di un processo background.
   - Schedulazione dei piani in base all'orario impostato nel DB.
2. **Polling e Resuming Automatico**
   - All'avvio del worker, controlla se esistono task in stato interrotto, `WAITING_CREDITS` (se è passato il tempo necessario o viene dato il comando) e ne tenta la ripresa a partire dal `last_commit_hash`.

## Fase 6: Dashboard Flask di Controllo (Web UI)
Il front-end di amministrazione per il controllo e monitoraggio in locale o su rete protetta.

1. **Gestione CRUD**
   - Inserimento/Modifica piani e task con relativi orari, modelli, prompt.
2. **Pannello di Monitoraggio (Execution View)**
   - Visualizzazione dei timing per ogni singolo step.
   - Feed in tempo reale (o polling) per mostrare `stdout`/`stderr` della CLI correntemente in esecuzione (effettuando strip-ansi per renderlo leggibile in HTML).
3. **Controllo di Flusso Manuale**
   - Bottoni per arrestare un task, metterlo in pausa, ignorarlo passando al successivo o comandare il "continua" forzato (es. dopo il ripristino di una ricarica crediti API).

## Fase 7: Sicurezza, Deploy e Ottimizzazione EC2
Ultime configurazioni legate all'ambiente AWS richiesto.

1. **Hardening Sicurezza OS**
   - Permessi utente limitati (`chroot` o `chmod` rigidi per limitare l'app solo alla sua cartella e quella del workspace).
2. **Gestione Risorse (Spegnimento Auto)**
   - Configurazione/Scrittura di uno script o logica env per notificare l'utente o spegnere direttamente la EC2 tramite chiamata di sistema o Boto3 se non ci sono più piani programmati per risparmiare risorse.

## Fase 8: Interfaccia Inserimento e Logging Esteso
Gestione dei form per l'utente finale e tracciabilità dettagliata dell'orchestratore.

1. **Form Creazione Piani (Completato)**
   - Aggiunta interfaccia web per inserire branch e fino a 15 task (selezionando agente, modello e prompt). I task lasciati vuoti vengono ignorati.
2. **Worker Logging (Completato)**
   - Il `PlanOrchestrator` salva le sue azioni (clone, inizio/fine task, push, crash) in `.AlNaoAgent/logs/<id_plan>/worker.log` garantendo una cronologia persistente per debug.
