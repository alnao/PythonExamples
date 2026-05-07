# Annotazioni alnao: prompt usati per generare questo bellissimo progetto!
--------------------------------------------------------------------------------------------------------------------
07/05/2026
ProgettoAlNaoAIRunners (un sistema di EC2 che chiama AI tramite agenti per plan complessi)
una applicazione (python flask , db dynamo con boto3, Task Queue, APScheduler, gitmanager ) che permetta di inserire piano: un id, un orario, un branch e un orario di inizio e una lista di task con prompt/modello/agenti. 
quando è il momento il programma esegue clone del branch, parte dal primo prompt e li esegue uno per uno, ogni step esegue commit nel branch, alla fine fa push nel branch. il prompt viene eseguito con il modello/effort selezionato. 
se il ritorna “limit/rate raggiunti” aspetta di avere credito e poi riprende con comando “continua”. 
Ogni task salva un log in .AlNaoAgent/logs/<id_plan>/<id_step>.md cosa ha fatto attraverso un agente, gli agenti possibili saranno del tipo “leggi la documentazione”, “scrivi la documentazione”, “caveman” ecc. 
I modelli possono essere claude o gemini che usano la CLI di claude-code e di gemini! 
Concorrenza: non possono eseguiti due task nello stesso momento, uno aspetta che gli altri siano completati. 
L’applicazione prevede un worker separato per le schedulazioni, in caso di rate limit salva uno stato e poi riprenderà, il "contesto" per il modello task/modello è lo stato fisico del file system e i log in quel momento. 
Prima di eseguire qualunque commit un agente esegue la compilazione/test e sistema finché non è risolto con max_fix_attempts per evitare loop infiniti. 
Nel flask un pannello controllo di esecuzione con visione dei timing e risposte degli agenti (strip-ansi sia stdout che stderr ) e modelli, loop infiniti controllati con possibilità di fermare un step/task e proseguire con i successivi. 
I dati su cartella, su repository, i possibili branch, i possibili modelli, le key staranno tutto su un file env. L'utente Linux che fa girare il worker deve avere permessi limitati esclusivamente alla cartella /home/xxx/cartella e alla cartella dei log. 
Su database sqlite locale salvare anche task in esecuzione in un momento così in caso di interruzione/riavvio Ec2 riparte da dove si era fermato (last_commit_hash).
per ora non prevedere per parte cloud (sarà fatta una semlice EC2 per ora) , nel env di configurazione di sarà un comando da eseguire alla fine (se non ci sono alti plan successivi così da spegnere la EC2 o notificare all’utente che i plan sono finiti)
tramite un agente ogni step/task salva un log in cartella specifica .AlNaoAgent/logs/ <id_plan>/<id_step>.md indicando cosa ha fatto, i ragionamenti, i compoennti modificati, le analisi fatte in un unico file, questi files saranno il sostituto di una memoria vettoriale e/o un sqlite
agenti (files md , Quando il task parte, il Python legge il file .md, lo concatena al prompt dell'utente e lo passa alla CLI)
Header: Identità dell'agente (es. "Sei Caveman").
Context: "Leggi lo stato attuale nella cartella di log per sapere cosa hanno fatto i tuoi predecessori".
Task: Il prompt specifico dell'utente.
Constraint: "Se finisci i tentativi di fix, scrivi 'STOP_FAILURE' e non fare il commit".
ScriviDoc: Scrivi file nella cartella di log
LeggiDoc: Leggi tutti i files nella cartella di log
Execute: se qualunque momento esegue dei comandi shell, aggiungi comando e 100 righe della risposta nel ScriviDoc “X_Shell” file
Esempio di steps
Dato XX, AA (java), BB (react-game), TT(5), CC(python), DD(php), EE (aws lambda), FF(react-admin)
1 inizializza il contesto: legge documentazione nel repository e scrive un file “1_contesto.md” usando ScriviDoc riassumendo il progetto
2 capisci cosa devi fare, dato un numero XX capisci nel file Roadmap del progetto cosa devi fare e ScriviDoc con tutti i passi da eseguire con le tecnologie principali AA e BB
3 LeggiDoc e inizia a scrivere il codice del codice AA e relative test, continua finchè non compila e i test siano corretti, per un massimo di TT tentativi, , scrivi unit-test per avere almeno 95% di coverage per un massimo di TT tentativi, al termine ScriviDoc “3_<AA>” con tutti i componenti scritti/modificati e decisione prese. Se hai modificato tabelle scrivi anche ScriviDoc  “3_<AA>_DB” e se hai modificato OpenAPI allora ScriviDoc 3_<AA>_API”
4 LeggiDoc e dal passo 3 capisci quali API sono state modificate, aggiungi robot test completi per verificare queste API, verifica che i robot funzionano con massimo tentativi TT, al termine ScriviDoc 4_RobotTest
5: LeggiDoc per capire quali modifiche sono fatte nel linguaggio AA; riporta le stesse modifiche nel backend nel linguaggio CC in modo che i test robot funzionino correttamente ma non modificare codice AA e robot, scrivi unit-test per avere almeno 95% di coverage per un massimo di TT tentativi, alla fine scriviDoc 5_<CC>.md
6: LeggiDoc per capire quali modifiche sono fatte nel linguaggio AA; riporta le stesse modifiche nel backend nel linguaggio DD in modo che i test robot funzionino correttamente ma non modificare codice AA e robot, scrivi unit-test per avere almeno 95% di coverage per un massimo di TT tentativi, alla fine scriviDoc 5_<DD>.md
7: LeggiDoc per capire quali modifiche sono fatte nel linguaggio AA; riporta le stesse modifiche nel backend nel linguaggio EE in modo che i test robot funzionino correttamente ma non modificare codice AA e robot, scrivi unit-test per avere almeno 95% di coverage per un massimo di TT tentativi, alla fine scriviDoc 7_<EE>.md
8: LeggiDoc per avere un contesto, capisci se bisogna fare modifiche al progetto frontend BB , sviluppa con unit test,  per un massimo di TT tentativi, alla fine scriviDoc 8_<BB>.md
9: LeggiDoc per avere un contesto, capisci se bisogna fare modifiche al progetto frontend FF , sviluppa con unit test,  per un massimo di TT tentativi, alla fine scriviDoc 9_<FF>.md
10: LeggiDoc e scrivi un file “GG” complessivo
11: termina con success questa elaborazione

vorrei iniziare questo progetto nella cartella AlNaoAIRunners, mi scrivi un piano di lavoro nel file ROADMAP.md in modo tale che lo sviluppo sia consistente, voglio uno step intermedio che mi permetta di eseguire uno step solo, poi eseguire più step. pensa che in futuro potrei anche aggiunere altre cli

ora procedi con il tuo piano, il flask voglio che usi bootstrap e fontawesome, let's go

ora voglio queste modifiche: nella pagina web fammi un'interfaccia dopo posso creare un nuovo plan da 15 task (se lasciato vuoto non mettere nulla), poi fai in modo che il worker scriva nella cartella di logs (con cartella specifica id plan), poi aggiorna il ROADMAP

fai così: rendi parametrico il path del repository e la cartella ".AlNaoAgent/workspace" 

ma sei sicuro che i comandi che inserisco nel prompt vengano passati al cli claude/gemini ? verifica e casomai implementa le due chiamate, poi aggiorna ROADMAP con aggiornamenti

queste modifiche. il worker gira ogni minuto e scrive log al posto di fare print. ogni classe dentro python deve scrivere nel log al posto di fare print

allora: ci sono due problemi il primo è che il worker schedulato non logga nulla, il secondo è che quando imposto uno step, mi ritorna solo un mock e non esegue nulla. inoltre voglio che ogni volta che vien eseguito un comando (git, claude, gemini, cli) deve essere loggato nei log del plan

se claude ritorna "You've hit your limit" devi metterlo come WAITING_CREDITS. poi controlla il comandi cli google gemini perchè non funziona e aggiorna il ROADMAP

EXEC ERROR: [Errno 2] No such file or directory: 'gemini' devo installare qualcosa ?

genini api come prendo un GEMINI_API_KEY ?

nano /home/alnao/.gemini/settings.json *(Nota: Ho inserito `gemini-1.5-flash` come modello perché è il più veloce ed economico per l'uso da riga di comando, ma puoi cambiarlo in `gemini-1.5-pro` se ti serve più potenza).*

voglio che creando un plan mi permetta di impostare quando è schedulato, un titolo (che sarà da visualizzare il lista),  nel dettaglio di un plan mostra la lista dei step con anche il prompt. nella schermata . poi metti un bottone nella lista dei plan per andare su edit come nuovo

sulla versione claude voglio selezionare il modello "Opus 4.6", "Sonnet 4.6" , "Opus 4.7" e gli altri (c'è api che recupera i modelli ?), voglio una tendina con possibli valori/modelli

aggiungi la possiblità di usare copilot cli , la sintassi è copilot -p "<prompt>" -s --model <modello> dove i modelli sono "gpt-5.3-codex" e "claude-sonnet-4.6" e "gpt-5.2". devi permettere che claude-sonnet sia sia da Claude sia da Copilot

io voglio che sia l'agente che mi crea/modifica il file senza chiedere conferma
copilot -s   --allow-all  --yolo   --model claude-sonnet-4.6 -p "Header: DefaultAgent
    Context: Leggi lo stato attuale per sapere cosa hanno fatto i predecessori.
    Task: crea un file python con funzione che calcola triplo di un numero
"
Importante: devi eseguire i comandi del cli_providers dentro la cartella dove hai eseguito il git clone chiamata XX, sposta la cartella logs dentro alla XX 

voglio queste modifiche: dammi la possiblità di selezionare dove eseguire il git clone (e tutti gli altri comanti) default in ENV = /mnt/Dati4/todel/. Quando si crea un plan mi devi permettere di inserire una "descrizione commit", quando fai il commit metti la descrizione concatenata alla descrizione dello step (permetti inserimento) e concatena id_steps e id_plans. Prova a capire se posso aggiungere l'agente caveman alle esecuzioni e come

cambia nome della cartella dei plan mettendo "plan-<nome>-id" e i file MD devono essere plan-<nomeplan>-<nomeversione>-<Commit Message>-id.md. Poi vorrei che mi aiutassi a risolvere "Authentication failed for 'https://github.com/alnao/PythonExamples.git/'". Eventualmente aggiungi le credenziali nel ENV (con nome, mail e path della chiave)

ho ancora l'errore [2026-05-07T17:08:50.971487] EXEC CMD: git -C /mnt/Dati4/todel/workspace push origin test [2026-05-07T17:08:51.374073] STDERR: /usr/share/antigravity/antigravity: --openssl-legacy-provider is not allowed in NODE_OPTIONS /usr/share/antigravity/antigravity: --openssl-legacy-provider is not allowed in NODE_OPTIONS remote: No anonymous write access. fatal: Authentication failed for 'https://github.com/alnao/PythonExamples.git/'. poi c'è il problema che nei prompt non c'è la lista dei file (con paths assoluto). controlla

usa il REPO_BRANCH come default nel nome branch ma rimane modificabile


--- comandi 
    npm install -g @google/gemini-cli
/mnt/Dati4/Workspace/PythonExamples
source .venv/bin/activate
pip install Flask python-dotenv APScheduler sqlalchemy
cd AI/AlNaoAIRunners
python app.py

---------------------