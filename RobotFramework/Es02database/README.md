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


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Aggiunta la sezione Changelog |


# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.

