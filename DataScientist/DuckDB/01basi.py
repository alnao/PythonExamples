"""DuckDB: le basi. Un database SQL analitico che gira dentro il processo Python, senza server.

Si interroga direttamente un file (CSV, Parquet, JSON) come se fosse una tabella,
e il risultato si ottiene come lista di tuple, DataFrame Pandas o DataFrame Polars.
Il file usato è lo stesso degli esempi Pandas (../Pandas/08data.csv).
"""
from pathlib import Path

import duckdb

FILE_CSV = str(Path(__file__).parent.parent / "Pandas" / "08data.csv")

# connessione in memoria: sparisce alla chiusura del programma (per un file vedere 03)
con = duckdb.connect()

print("---- query diretta sul file CSV: separatore e tipi riconosciuti in automatico ----")
con.sql(f"SELECT * FROM '{FILE_CSV}'").show()

print("---- read_csv con opzioni esplicite ----")
con.sql(f"SELECT * FROM read_csv('{FILE_CSV}', delim=';', header=true) WHERE age > 40").show()

print("---- DESCRIBE e SUMMARIZE: schema e statistiche ----")
con.sql(f"DESCRIBE SELECT * FROM '{FILE_CSV}'").show()
con.sql(f"SUMMARIZE SELECT * FROM '{FILE_CSV}'").show()

print("---- una tabella vera, creata dal file ----")
con.execute(f"CREATE TABLE persone AS SELECT * FROM '{FILE_CSV}'")

print("---- formati del risultato ----")
rel = con.sql("SELECT name, age FROM persone ORDER BY age DESC LIMIT 3")
print("fetchall  ->", rel.fetchall())
# con.sql() restituisce una "relation": la query viene rieseguita a ogni chiamata (in DuckDB 2 non ha fetchone).
# con.execute() esegue subito e tiene il risultato aperto sulla connessione: dopo fetchone()
# va chiuso con complete() (oppure letto fino in fondo) prima di lanciare altre query
risultato = con.execute("SELECT count(*) FROM persone")
print("fetchone  ->", risultato.fetchone())
risultato.complete()
print("df()      ->", type(rel.df()))     # Pandas
print("pl()      ->", type(rel.pl()))     # Polars
print(rel.df())

print("---- parametri: mai concatenare valori nella stringa SQL ----")
eta_minima = 50
print(con.execute("SELECT name, age FROM persone WHERE age >= ? ORDER BY age", [eta_minima]).fetchall())
print(con.execute("SELECT name FROM persone WHERE name LIKE $iniziale || '%'",
                  {"iniziale": "a"}).fetchall())

print("---- SQL 'amichevole' di DuckDB ----")
# FROM prima di SELECT, SELECT * EXCLUDE, GROUP BY ALL, ORDER BY ALL
con.sql("FROM persone SELECT * EXCLUDE (date_column_2) LIMIT 3").show()
con.sql("""
    SELECT year(date_column_1) AS anno, count(*) AS persone, round(avg(age), 1) AS eta_media
    FROM persone
    GROUP BY ALL
    ORDER BY ALL
""").show()
# COLUMNS(regex) applica la stessa funzione a più colonne
con.sql("SELECT max(COLUMNS('date_.*')) FROM persone").show()

print("---- API relazionale: la query costruita con metodi Python ----")
(con.table("persone")
    .filter("age BETWEEN 10 AND 60")
    .project("name, age, age * 12 AS mesi")
    .order("age")
    .show())

print("---- funzioni su date e stringhe ----")
con.sql("""
    SELECT name,
           upper(name[1]) || name[2:] AS nome,
           date_diff('day', date_column_2, date_column_1) AS giorni,
           strftime(date_column_1, '%d/%m/%Y') AS data_it,
           CASE WHEN age < 18 THEN 'minorenne' WHEN age < 65 THEN 'adulto' ELSE 'senior' END AS fascia
    FROM persone
""").show()

con.close()
