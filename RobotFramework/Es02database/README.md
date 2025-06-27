# RobotFramework esempio 02 db
Questo progetto mostra come implementare test automatizzati per database utilizzando Robot Framework. Include esempi completi di operazioni CRUD (Create, Read, Update, Delete), test di vincoli e query complesse.
- Test CRUD completi: Inserimento, lettura, aggiornamento ed eliminazione
- Validazione vincoli: Test di unicità e integrità referenziale
- Query complesse: Test con condizioni multiple e join
- Setup automatico: Gestione automatica della connessione e struttura database
- Containerizzazione: Setup rapido con Docker
- Report dettagliati: Output HTML con log completi
- Database useto `MySQL 8.0+` ma compatibile anche con `PostgreSQL 12+`


Struttura progetto
```
├── README.md                    # Questo file
├── requirements.txt             # Dipendenze Python
├── docker-compose.yml          # Configurazione database
├── run-db-tests.sh             # Script esecuzione test
├── database.resource           # Keywords e configurazione
├── database_tests.robot        # Test cases principali
└── output/                     # Report e log (generato)
```

## Comandi
- Esecuzione Rapida: script sh che avvia i DB, esegue i test e poi spegne i DB.
    ```
    ./run-db-tests.sh
    ```
- Esecuzione Manuale: passi eseguiti uno dopo l'altro.
    ```
    pip install -r requirements.txt
    docker-compose up
    robot --outputdir robotoutput database_tests.robot --loglevel DEBUG
    docker-compose down
    ```
- Esecuzione su server esterno: questa versione non prevede l'avvio del docker ma un database MySql disponibile:
    ```
    pip install -r requirements.txt
    robot \
    --outputdir robotoutput \
    --loglevel DEBUG \
    --variable DB_HOST:127.0.0.1 \
    --variable DB_USER:root \
    --variable DB_PASSWORD:alnaoBellissimo \
    database_tests.robot
    ```

# Test semplificati
robot --outputdir output database_simple_tests.robot

# Test con tag specifici
robot --outputdir output --include crud database_tests.robot
robot --outputdir output --include validation database_tests.robot
Esecuzione con Parametri Personalizzati
bashrobot \
    --outputdir output \
     \
    --variable DB_HOST:192.168.1.100 \
    --variable DB_USER:custom_user \
    database_tests.robot

    pip install -r requirements.txt