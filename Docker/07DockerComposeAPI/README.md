# Esempio 07 Docker Compose API
Esempio pratico di un progetto Python che utilizza Docker Compose per gestire un'applicazione web con un database PostgreSQL. L'applicazione Python utilizzerà Flask come framework web e SQLAlchemy per interagire con il database.
```
my-python-app/
├── app/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

# Comandi 
- Avvio con Docker Compose
    ```bash
    docker-compose up --build
    ```
- Creazione un utente:
    ```bash
    curl -X POST http://localhost:5000/users -H "Content-Type: application/json" -d '{"username": "alnao","name":"Alberto"}'
    curl -X POST http://localhost:5000/users -H "Content-Type: application/json" -d '{"username": "ciri","name":"Cirilla Fiorna Ellen Riannon"}'
    ```
- Lista di tutti gli utenti:
    ```bash
    curl http://localhost:5000/users
    ```
- Fermare e rimuovere i container, ma mantiene i dati del database grazie al volume persistente.
    ```bash
    docker-compose down
    ```

## Persistenza dei dati
- La persistenza dei dati del database è garantita grazie all'uso di volumi Docker . Quando utilizzi Docker Compose, il volume postgres_data definito nel file docker-compose.yml assicura che i dati del database PostgreSQL siano salvati in una posizione esterna al container e sopravvivano anche quando il container viene fermato o rimosso.
- Dove sono salvati i dati? Nel file docker-compose.yml, è definito un volume chiamato postgres_data per il servizio db, questo volume mappa la directory `/var/lib/postgresql/data` (dove PostgreSQL memorizza i dati) su un volume Docker gestito dal sistema host. Ma non è la cartella fisica, per recuperare il valore della cartella fisica serve il comando:
    ```bash
    docker volume inspect 07dockercomposeapi_postgres_data
    ```
- Puoi elencare tutti i volumi Docker con:
    ```bash
    docker volume ls
    ```
- Quando fermi il container del database (docker-compose down), i dati rimangono salvati nel volume postgres_data e quando riavvii i servizi (docker-compose up), Docker ricollega il volume al container del database, ripristinando i dati precedenti.
- Per cancellare tutti i dati/volumi si può usare il comando
    ```bash
    docker volume rm my-python-app_postgres_data
    ```




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

