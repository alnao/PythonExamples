# DataScientist - Polars

Esempi della libreria [Polars](https://pola.rs/): DataFrame scritti in Rust, multi-thread, con esecuzione *lazy* e ottimizzatore di query. Gli esempi riprendono le operazioni degli script in [Pandas](../Pandas/) e le confrontano.

## Differenze principali rispetto a Pandas
| Pandas | Polars |
|---|---|
| indice delle righe (`loc`, `iloc`, `reset_index`) | nessun indice: si filtra sempre per valore |
| `df["x"] = ...` modifica il DataFrame | ogni operazione restituisce un nuovo DataFrame (`with_columns`) |
| funzioni applicate colonna per colonna, spesso con `apply` | *espressioni* (`pl.col("x") * 2`) eseguite in parallelo |
| esecuzione immediata | esecuzione immediata (`read_*`) o *lazy* (`scan_*` + `collect()`) |
| un solo core | tutti i core della CPU |

## Esempi
| File | Contenuto |
|---|---|
| `genera_dati.py` | crea in `dati/` 2 milioni di vendite sintetiche (CSV e Parquet) e l'anagrafica negozi; gli altri script lo chiamano da soli se i file mancano |
| `01basi.py` | lettura del CSV [08data.csv](../Pandas/08data.csv) degli esempi Pandas, `select`, `filter`, `with_columns`, `when/then/otherwise`, `group_by`, selettori per tipo, valori nulli, stringhe, conversione da e verso Pandas |
| `02lazy.py` | `scan_parquet`, piano di esecuzione con `explain()` (projection e predicate pushdown), engine streaming, eager contro lazy sullo stesso CSV, `sink_parquet` |
| `03groupbyJoin.py` | aggregazioni multiple, join `left`, `anti` e `semi`, funzioni finestra con `over()`, `rank`, `pivot`, `unpivot`, `group_by_dynamic` per serie mensili, media mobile, `pct_change` |
| `04confrontoPandas.py` | la stessa elaborazione (lettura CSV, filtro, join, aggregazione) con Pandas, Polars eager e Polars lazy, con tempi e verifica che i risultati coincidano |

## Comandi
Dalla cartella `DataScientist/Polars`:
```bash
../../.venv/bin/pip install -r requirements.txt
../../.venv/bin/python genera_dati.py            # facoltativo; con un numero si cambia la dimensione: genera_dati.py 10000000
../../.venv/bin/python 01basi.py
../../.venv/bin/python 02lazy.py
../../.venv/bin/python 03groupbyJoin.py
../../.venv/bin/python 04confrontoPandas.py
```

Esempio di risultato di `04confrontoPandas.py` con 2 milioni di righe (il rapporto conta più dei numeri assoluti, che dipendono dalla macchina):
```
Pandas           3.699s
Polars eager     0.278s    13.3x più veloce di Pandas
Polars lazy      0.219s    16.9x più veloce di Pandas
Risultati identici (tolleranza 0.01 €)
```

La cartella `dati/` è generata e quindi esclusa da git.

Vedere anche gli esempi [DuckDB](../DuckDB/), che fanno le stesse analisi in SQL.


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

