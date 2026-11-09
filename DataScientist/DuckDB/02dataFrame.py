"""DuckDB insieme a Pandas e Polars: SQL sui DataFrame già in memoria.

DuckDB trova da solo le variabili Python che contengono un DataFrame (replacement scan):
nella query basta scrivere il nome della variabile come se fosse una tabella.
I dati non vengono copiati: DuckDB li legge direttamente tramite Apache Arrow.
"""
import duckdb
import pandas as pd
import polars as pl

clienti_pandas = pd.DataFrame({
    "id": [1, 2, 3, 4],
    "nome": ["Alberto", "Valentina", "Andrea", "Pietro"],
    "citta": ["Torino", "Milano", "Torino", "Roma"],
})

ordini_polars = pl.DataFrame({
    "id_cliente": [1, 1, 2, 3, 3, 3, 5],
    "importo": [120.0, 35.5, 89.9, 15.0, 42.0, 300.0, 10.0],
    "stato": ["pagato", "pagato", "annullato", "pagato", "pagato", "in attesa", "pagato"],
})

print("---- SQL su un DataFrame Pandas, usando il nome della variabile ----")
duckdb.sql("SELECT citta, count(*) AS clienti FROM clienti_pandas GROUP BY citta ORDER BY clienti DESC").show()

print("---- SQL su un DataFrame Polars ----")
duckdb.sql("SELECT stato, sum(importo) AS totale FROM ordini_polars GROUP BY ALL ORDER BY totale DESC").show()

print("---- JOIN tra un DataFrame Pandas e uno Polars ----")
per_cliente = duckdb.sql("""
    SELECT c.nome, c.citta, count(o.importo) AS ordini, coalesce(sum(o.importo), 0) AS totale
    FROM clienti_pandas c
    LEFT JOIN ordini_polars o ON o.id_cliente = c.id AND o.stato = 'pagato'
    GROUP BY ALL
    ORDER BY totale DESC
""")
per_cliente.show()

print("---- il risultato torna nel formato che serve ----")
risultato_pandas = per_cliente.df()
risultato_polars = per_cliente.pl()
print(type(risultato_pandas).__name__, risultato_pandas.shape)
print(type(risultato_polars).__name__, risultato_polars.shape)

print("---- ordini con cliente inesistente (anti join) ----")
duckdb.sql("""
    SELECT * FROM ordini_polars o
    ANTI JOIN clienti_pandas c ON c.id = o.id_cliente
""").show()

print("---- registrazione esplicita: utile dentro le funzioni o con nomi diversi ----")
def ordini_sopra(con: duckdb.DuckDBPyConnection, df: pl.DataFrame, soglia: float) -> pl.DataFrame:
    con.register("ordini", df)
    # con.sql accetta i parametri come con.execute e restituisce una relation, convertibile con .pl()
    return con.sql("SELECT * FROM ordini WHERE importo > ? ORDER BY importo", params=[soglia]).pl()

con = duckdb.connect()
print(ordini_sopra(con, ordini_polars, 50))

print("---- Pandas e SQL insieme: preparazione in SQL, grafici o modelli in Pandas ----")
mensile = duckdb.sql("""
    SELECT date_trunc('month', giorno) AS mese, sum(valore) AS totale
    FROM (SELECT DATE '2026-01-01' + CAST(range AS INTEGER) AS giorno, range % 7 AS valore FROM range(90))
    GROUP BY ALL ORDER BY mese
""").df()
print(mensile.set_index("mese"))
