"""DuckDB: SQL analitico sui 2 milioni di vendite generate da genera_dati.py.

Funzioni finestra, QUALIFY, PIVOT, ROLLUP, serie temporali e liste.
Le stesse analisi sono fatte con Polars in ../Polars/03groupbyJoin.py.
"""
import duckdb

from genera_dati import assicura_dati

cartella = assicura_dati()
con = duckdb.connect()
# una vista sul file: le query leggono il Parquet senza caricarlo prima in una tabella
con.execute(f"""
    CREATE VIEW vendite AS
    SELECT *, round(quantita * prezzo, 2) AS incasso FROM '{cartella / 'vendite.parquet'}'
""")
con.execute(f"CREATE VIEW negozi AS FROM '{cartella / 'negozi.csv'}'")

print("---- aggregazioni con liste ----")
con.sql("""
    SELECT categoria,
           round(sum(incasso), 2) AS incasso_totale,
           round(avg(incasso), 2) AS scontrino_medio,
           sum(quantita) AS pezzi,
           list(DISTINCT prodotto ORDER BY prodotto) AS prodotti
    FROM vendite
    GROUP BY ALL
    ORDER BY incasso_totale DESC
""").show()

print("---- join con l'anagrafica e negozi senza vendite ----")
con.sql("""
    SELECT n.regione, n.citta, round(sum(v.incasso), 2) AS incasso
    FROM negozi n LEFT JOIN vendite v USING (negozio)
    GROUP BY ALL
    ORDER BY incasso DESC NULLS LAST
""").show()

print("---- funzioni finestra: quota del prodotto sulla sua categoria ----")
# prima si aggrega (CTE), poi le funzioni finestra lavorano sulle righe già aggregate
con.sql("""
    WITH per_prodotto AS (
        SELECT categoria, prodotto, round(sum(incasso), 2) AS incasso
        FROM vendite
        GROUP BY categoria, prodotto
    )
    SELECT *,
           round(100 * incasso / sum(incasso) OVER (PARTITION BY categoria), 1) AS quota_pct,
           rank() OVER (PARTITION BY categoria ORDER BY incasso DESC) AS posizione
    FROM per_prodotto
    ORDER BY categoria, posizione
""").show()

print("---- QUALIFY: i 2 prodotti più venduti di ogni negozio (filtro sul risultato della finestra) ----")
con.sql("""
    SELECT negozio, prodotto, sum(quantita) AS pezzi
    FROM vendite
    GROUP BY negozio, prodotto
    QUALIFY row_number() OVER (PARTITION BY negozio ORDER BY pezzi DESC) <= 2
    ORDER BY negozio, pezzi DESC
""").show()

print("---- PIVOT: negozi sulle righe, categorie sulle colonne ----")
con.sql("""
    PIVOT (SELECT negozio, categoria, incasso FROM vendite)
    ON categoria USING round(sum(incasso), 0)
    ORDER BY negozio
""").show()

print("---- ROLLUP: subtotali per anno e categoria, più il totale generale ----")
con.sql("""
    SELECT coalesce(CAST(year(data) AS VARCHAR), 'TOTALE') AS anno,
           coalesce(categoria, '(tutte)') AS categoria,
           round(sum(incasso), 0) AS incasso
    FROM vendite
    GROUP BY ROLLUP (year(data), categoria)
    ORDER BY year(data) NULLS LAST, categoria NULLS LAST
""").show(max_rows=20)

print("---- serie mensile: media mobile su 3 mesi e variazione sul mese precedente ----")
con.sql("""
    WITH mensile AS (
        SELECT CAST(date_trunc('month', data) AS DATE) AS mese, round(sum(incasso), 0) AS incasso
        FROM vendite GROUP BY ALL
    )
    SELECT mese, incasso,
           round(avg(incasso) OVER (ORDER BY mese ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS media_3_mesi,
           round(100 * (incasso / lag(incasso) OVER (ORDER BY mese) - 1), 1) AS variazione_pct
    FROM mensile
    ORDER BY mese
    LIMIT 6
""").show()

print("---- giorno della settimana con più incasso ----")
con.sql("""
    SELECT dayname(data) AS giorno, round(sum(incasso), 0) AS incasso
    FROM vendite GROUP BY ALL ORDER BY incasso DESC
""").show()

print("---- EXPLAIN: il piano di esecuzione (filtro e colonne spinti nella lettura del Parquet) ----")
print(con.sql(f"""
    EXPLAIN SELECT negozio, sum(quantita)
    FROM '{cartella / 'vendite.parquet'}' WHERE categoria = 'bar' GROUP BY negozio
""").fetchall()[0][1])
