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
    ```
    docker-compose up --build
    ```
- Creazione un utente:
    ```
    curl -X POST http://localhost:5000/users -H "Content-Type: application/json" -d '{"username": "alnao","name":"Alberto"}'
    curl -X POST http://localhost:5000/users -H "Content-Type: application/json" -d '{"username": "ciri","name":"Cirilla Fiorna Ellen Riannon"}'
    ```
- Lista di tutti gli utenti:
    ```
    curl http://localhost:5000/users
    ```
- Fermare e rimuovere i container, ma mantiene i dati del database grazie al volume persistente.
    ```
    docker-compose down
    ```

## Persistenza dei dati
- La persistenza dei dati del database è garantita grazie all'uso di volumi Docker . Quando utilizzi Docker Compose, il volume postgres_data definito nel file docker-compose.yml assicura che i dati del database PostgreSQL siano salvati in una posizione esterna al container e sopravvivano anche quando il container viene fermato o rimosso.
- Dove sono salvati i dati? Nel file docker-compose.yml, è definito un volume chiamato postgres_data per il servizio db, questo volume mappa la directory `/var/lib/postgresql/data` (dove PostgreSQL memorizza i dati) su un volume Docker gestito dal sistema host. Ma non è la cartella fisica, per recuperare il valore della cartella fisica serve il comando:
    ```
    docker volume inspect 07dockercomposeapi_postgres_data
    ```
- Puoi elencare tutti i volumi Docker con:
    ```
    docker volume ls
    ```
- Quando fermi il container del database (docker-compose down), i dati rimangono salvati nel volume postgres_data e quando riavvii i servizi (docker-compose up), Docker ricollega il volume al container del database, ripristinando i dati precedenti.
- Per cancellare tutti i dati/volumi si può usare il comando
    ```
    docker volume rm my-python-app_postgres_data
    ```

# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*