"""Genera i dati di esempio usando solo SQL di DuckDB (range + random), senza numpy.

Uso:  python genera_dati.py [numero_righe]     (default 2.000.000)
Crea nella cartella dati/ vendite.parquet, vendite.csv e negozi.csv,
con le stesse colonne degli esempi Polars (data, negozio, prodotto, categoria, quantita, prezzo).
"""
import sys
import time
from pathlib import Path

import duckdb

CARTELLA = Path(__file__).parent / "dati"

SQL_GENERA = """
CREATE OR REPLACE TEMP TABLE prodotti AS
SELECT * FROM (VALUES
    (0, 'caffè', 'bar', 1.2), (1, 'cornetto', 'bar', 1.5),
    (2, 'pizza', 'cibo', 8.0), (3, 'pasta', 'cibo', 1.9),
    (4, 'vino', 'bevande', 9.5), (5, 'acqua', 'bevande', 0.6),
    (6, 'giornale', 'edicola', 1.8), (7, 'rivista', 'edicola', 4.5)
) AS t(id, prodotto, categoria, prezzo_base);

CREATE OR REPLACE TEMP TABLE negozi AS
SELECT * FROM (VALUES
    ('N01', 'Torino', 'Piemonte'), ('N02', 'Milano', 'Lombardia'),
    ('N03', 'Genova', 'Liguria'), ('N04', 'Bologna', 'Emilia-Romagna'),
    ('N05', 'Roma', 'Lazio'), ('N06', 'Napoli', 'Campania'),
    ('N07', 'Firenze', 'Toscana')   -- appena aperto: nessuna vendita
) AS t(negozio, citta, regione);

-- range(n) produce n righe; random() un numero tra 0 e 1 diverso per ogni riga
CREATE OR REPLACE TEMP TABLE vendite AS
WITH casuali AS (
    SELECT CAST(floor(random() * 730) AS INTEGER) AS giorno,
           CAST(floor(random() * 6) AS INTEGER) + 1 AS n_negozio,
           CAST(floor(random() * 8) AS INTEGER) AS id_prodotto,
           CAST(floor(random() * 5) AS INTEGER) + 1 AS quantita,
           0.9 + random() * 0.2 AS variazione
    FROM range($righe)
)
SELECT DATE '2024-01-01' + c.giorno AS data,
       'N0' || c.n_negozio AS negozio,
       p.prodotto,
       p.categoria,
       c.quantita,
       round(p.prezzo_base * c.variazione, 2) AS prezzo
FROM casuali c JOIN prodotti p ON p.id = c.id_prodotto;
"""


def main(righe: int) -> None:
    CARTELLA.mkdir(exist_ok=True)
    inizio = time.perf_counter()
    con = duckdb.connect()
    con.execute(SQL_GENERA, {"righe": righe})
    # COPY ... TO scrive il risultato di una query su file (il formato si sceglie con FORMAT)
    con.execute(f"COPY vendite TO '{CARTELLA / 'vendite.parquet'}' (FORMAT parquet)")
    con.execute(f"COPY vendite TO '{CARTELLA / 'vendite.csv'}' (FORMAT csv, HEADER)")
    con.execute(f"COPY negozi TO '{CARTELLA / 'negozi.csv'}' (FORMAT csv, HEADER)")
    print(f"Generate {righe:,} righe in {time.perf_counter() - inizio:.1f}s nella cartella {CARTELLA}")
    con.sql("FROM vendite LIMIT 5").show()


def assicura_dati(righe: int = 2_000_000) -> Path:
    """Genera i dati solo se mancano: la chiamano gli altri script."""
    if not all((CARTELLA / f).exists() for f in ("vendite.parquet", "vendite.csv", "negozi.csv")):
        main(righe)
    return CARTELLA


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000)
