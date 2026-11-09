# DataScientist - DuckDB

Esempi di [DuckDB](https://duckdb.org/): un database SQL analitico che gira dentro il processo Python, senza server da installare (come SQLite, ma pensato per le analisi). Interroga direttamente file CSV, Parquet e JSON e i DataFrame Pandas e Polars già in memoria.

## Quando usarlo
- analisi su file grandi (anche più della RAM) senza caricarli prima in un DataFrame
- chi conosce SQL e preferisce scrivere `GROUP BY` invece di catene di metodi
- preparare i dati in SQL e passarli a Pandas/Polars per grafici o modelli
- database locale su file per un'applicazione di analisi

## Esempi
| File | Contenuto |
|---|---|
| `genera_dati.py` | crea in `dati/` 2 milioni di vendite sintetiche usando **solo SQL** (`range()`, `random()`, `COPY ... TO`), con le stesse colonne degli esempi [Polars](../Polars/) |
| `01basi.py` | query diretta sul CSV [08data.csv](../Pandas/08data.csv) degli esempi Pandas, `DESCRIBE`, `SUMMARIZE`, formati del risultato (`fetchall`, `df()`, `pl()`), query con parametri, SQL "amichevole" (`FROM` per primo, `EXCLUDE`, `GROUP BY ALL`, `COLUMNS()`), API relazionale |
| `02dataFrame.py` | SQL sui DataFrame Pandas e Polars usando il nome della variabile, join tra un DataFrame Pandas e uno Polars, `ANTI JOIN`, `register()` |
| `03databasePersistente.py` | database su file (`dati/negozio.duckdb`): chiave primaria ed esterna, `CHECK`, sequenze, `executemany`, transazioni con rollback, viste, export Parquet e CSV, connessione in sola lettura |
| `04analitica.py` | SQL analitico sulle vendite: liste, funzioni finestra, `QUALIFY`, `PIVOT`, `ROLLUP`, media mobile e `lag`, `EXPLAIN` |
| `05confronto.py` | la stessa elaborazione con Pandas, Polars e DuckDB, sia da CSV sia da Parquet, con verifica che i risultati coincidano |

## Comandi
Dalla cartella `DataScientist/DuckDB`:
```bash
../../.venv/bin/pip install -r requirements.txt
../../.venv/bin/python genera_dati.py           # facoltativo, gli script lo chiamano da soli se i dati mancano
../../.venv/bin/python 01basi.py
../../.venv/bin/python 02dataFrame.py
../../.venv/bin/python 03databasePersistente.py
../../.venv/bin/python 04analitica.py
../../.venv/bin/python 05confronto.py
```

Esempio di risultato di `05confronto.py` con 2 milioni di righe (i numeri dipendono dalla macchina):
```
               CSV   Parquet
Pandas      2.266s    0.626s
Polars      0.134s    0.055s
DuckDB      0.226s    0.017s
Tutti i risultati coincidono (tolleranza 0.01 €)
```
Il formato del file conta quanto la libreria: Parquet è colonnare e compresso, quindi si leggono solo le colonne usate e i filtri si applicano durante la lettura (vedi `EXPLAIN` in `04analitica.py`).

## Note su DuckDB 2
Gli esempi sono scritti e provati con DuckDB 2.0, che rispetto alla 1.x è più rigido:
- `con.sql()` restituisce una *relation* (la query viene rieseguita a ogni chiamata) e non ha più `fetchone()`; `con.execute()` esegue subito e tiene il risultato aperto: dopo un `fetchone()` va chiuso con `complete()` prima di altre query sulla stessa connessione
- `DATE + BIGINT` non è più accettato: serve `DATE + CAST(n AS INTEGER)`
- con le funzioni finestra conviene aggregare prima in una CTE e usare `GROUP BY` esplicito invece di `GROUP BY ALL`

La cartella `dati/` è generata e quindi esclusa da git.


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

