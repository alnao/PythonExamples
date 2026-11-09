# Esempio 16 SQLAlchemyPostgres

API REST di una piccola biblioteca con un database relazionale "serio": **FastAPI** + **SQLAlchemy 2.0** (ORM tipizzato) + **Alembic** (migrazioni) + **PostgreSQL 17**, tutto in Docker Compose.

## Servizi
| Servizio | Porta host | Descrizione |
|---|---|---|
| `db` | 5433 | PostgreSQL 17 con volume persistente `dati_postgres` (5433 per non scontrarsi con un PostgreSQL locale) |
| `api` | 8000 | FastAPI; all'avvio esegue `alembic upgrade head`, inserisce i dati di esempio e avvia uvicorn |
| `adminer` | 8081 | interfaccia web per guardare le tabelle: sistema PostgreSQL, server `db`, utente, password e database `biblioteca` |

## Modello dei dati
```
autori 1 ──── N libri N ──── N categorie
                  │      (libri_categorie)
                  1
                  │
                  N
              prestiti
```
- `autori`: unique su (nome, cognome); cancellando un autore si cancellano i suoi libri (`cascade="all, delete-orphan"` e `ON DELETE CASCADE`)
- `libri`: ISBN unique, `CHECK copie >= 0` e `CHECK prezzo > 0`, prezzo `NUMERIC(8,2)`, indici su titolo e autore
- `categorie`: relazione molti-a-molti tramite la tabella di associazione `libri_categorie`
- `prestiti`: aggiunta con una **seconda migrazione** per mostrare l'evoluzione dello schema

## Struttura
```
16SQLAlchemyPostgres/
├── app/
│   ├── database.py      engine, pool di connessioni, sessione per richiesta
│   ├── models.py        modelli ORM 2.0 (Mapped, mapped_column, relationship)
│   ├── schemas.py       schemi Pydantic di input e output
│   ├── repository.py    tutte le query SQLAlchemy
│   ├── main.py          endpoint FastAPI e gestione errori
│   └── seed.py          dati di esempio
├── alembic/
│   ├── env.py
│   └── versions/        0001_schema_iniziale.py, 0002_prestiti.py
├── tests/               test pytest (SQLite in memoria oppure PostgreSQL)
├── alembic.ini
├── docker-compose.yml
└── Dockerfile
```

## Cosa mostra l'esempio
- **SQLAlchemy 2.0**: modelli con `Mapped[...]` (il tipo Python decide anche se la colonna è nullable), query con `select()`, `session.scalars()`, `session.get()`
- **relazioni** uno-a-molti e molti-a-molti con `back_populates`, cascade e `ondelete`
- **problema N+1**: `selectinload` carica autore e categorie di tutti i libri con una query in più invece di una per libro (si vede con `SQL_ECHO=1`)
- **aggregazioni**: conteggio libri per autore (`outerjoin` + `group_by`), libri per categoria, valore del catalogo
- **filtri dinamici**: la ricerca aggiunge `WHERE` solo per i parametri valorizzati, `ilike`, `any()` sulle relazioni, paginazione con `limit` e `offset`
- **transazioni e concorrenza**: il prestito usa `SELECT ... FOR UPDATE` (`with_for_update()`) per non prestare due volte l'ultima copia
- **vincoli del database**: unique, foreign key e check violati diventano risposte HTTP 409 in un unico exception handler
- **Alembic**: migrazioni versionate, `upgrade`, `downgrade`, `check` (confronta modelli e database), SQL generato offline
- **test**: `dependency_overrides` di FastAPI per usare un database di test, SQLite in memoria con `StaticPool` e chiavi esterne attivate

## Avvio con Docker Compose
```bash
cd Docker/16SQLAlchemyPostgres
docker compose up --build
```
Documentazione interattiva delle API: http://localhost:8000/docs

## Esempi di chiamate
```bash
curl http://localhost:8000/
curl http://localhost:8000/autori
curl "http://localhost:8000/libri?categoria=classici"
curl "http://localhost:8000/libri?q=calvino&anno_da=1960"
curl http://localhost:8000/statistiche

# nuovo autore e nuovo libro (le categorie mancanti vengono create)
curl -X POST http://localhost:8000/autori -H "Content-Type: application/json" \
     -d '{"nome": "Cesare", "cognome": "Pavese", "nato_il": "1908-09-09"}'
curl -X POST http://localhost:8000/libri -H "Content-Type: application/json" \
     -d '{"titolo": "La luna e i falò", "isbn": "9788806219383", "anno": 1950, "prezzo": "12.00", "copie": 1, "autore_id": 5, "categorie": ["romanzo", "classici"]}'

# prestito e restituzione: con una sola copia il secondo prestito risponde 409
curl -X POST http://localhost:8000/libri/8/prestiti -H "Content-Type: application/json" -d '{"utente": "alberto"}'
curl -X POST http://localhost:8000/libri/8/prestiti -H "Content-Type: application/json" -d '{"utente": "valentina"}'
curl -X POST http://localhost:8000/prestiti/2/restituzione
```

## Migrazioni con Alembic
Dalla cartella del progetto, con il database del docker-compose avviato (porta 5433):
```bash
../../.venv/bin/pip install -r requirements-dev.txt
../../.venv/bin/alembic current              # versione applicata al database
../../.venv/bin/alembic history              # elenco delle migrazioni
../../.venv/bin/alembic downgrade -1         # torna indietro di una (elimina la tabella prestiti)
../../.venv/bin/alembic upgrade head         # applica tutte le migrazioni mancanti
../../.venv/bin/alembic check                # verifica che i modelli coincidano con il database
../../.venv/bin/alembic upgrade 0001:0002 --sql    # stampa l'SQL senza eseguirlo

# dopo aver modificato models.py: genera la nuova migrazione confrontando modelli e database
../../.venv/bin/alembic revision --autogenerate -m "descrizione della modifica"
```
La migrazione generata va sempre riletta prima di applicarla: Alembic non riconosce per esempio le colonne rinominate (le vede come una cancellata e una nuova).

## Test
I test non richiedono Docker: di default usano SQLite in memoria.
```bash
../../.venv/bin/pytest -v
```
Per eseguirli sul PostgreSQL vero si usa un database separato, perché ogni test cancella e ricrea le tabelle:
```bash
docker compose exec db createdb -U biblioteca biblioteca_test
TEST_DATABASE_URL=postgresql+psycopg://biblioteca:biblioteca@localhost:5433/biblioteca_test ../../.venv/bin/pytest
```
Risultato atteso in entrambi i casi: `21 passed`.

## Avvio senza Docker per l'API
Con il solo database in Docker:
```bash
docker compose up -d db
../../.venv/bin/alembic upgrade head
../../.venv/bin/python -m app.seed
SQL_ECHO=1 ../../.venv/bin/uvicorn app.main:app --reload     # SQL_ECHO=1 stampa tutte le query
```

## Pulizia
```bash
docker compose down        # ferma i container, i dati restano nel volume
docker compose down -v     # ferma i container e cancella anche il volume con i dati
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

