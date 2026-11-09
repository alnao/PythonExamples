"""DuckDB come database su file: tabelle con vincoli, transazioni, viste ed export.

Il database è un singolo file (dati/negozio.duckdb), come SQLite, ma pensato per le analisi
(memorizzazione per colonne) invece che per tante piccole scritture.
"""
from pathlib import Path

import duckdb

CARTELLA = Path(__file__).parent / "dati"
CARTELLA.mkdir(exist_ok=True)
FILE_DB = CARTELLA / "negozio.duckdb"

with duckdb.connect(str(FILE_DB)) as con:     # il with chiude la connessione alla fine
    print("---- tabelle con chiave primaria, chiave esterna e CHECK ----")
    con.execute("DROP TABLE IF EXISTS movimenti")
    con.execute("DROP TABLE IF EXISTS articoli")
    con.execute("DROP SEQUENCE IF EXISTS seq_movimenti")
    con.execute("""
        CREATE TABLE articoli (
            codice      VARCHAR PRIMARY KEY,
            descrizione VARCHAR NOT NULL,
            prezzo      DECIMAL(10, 2) NOT NULL CHECK (prezzo > 0),
            giacenza    INTEGER NOT NULL DEFAULT 0 CHECK (giacenza >= 0)
        )
    """)
    con.execute("CREATE SEQUENCE seq_movimenti START 1")
    con.execute("""
        CREATE TABLE movimenti (
            id        INTEGER PRIMARY KEY DEFAULT nextval('seq_movimenti'),
            codice    VARCHAR NOT NULL REFERENCES articoli(codice),
            quantita  INTEGER NOT NULL,
            momento   TIMESTAMP NOT NULL DEFAULT current_timestamp
        )
    """)

    print("---- inserimento di più righe con executemany ----")
    con.executemany("INSERT INTO articoli (codice, descrizione, prezzo, giacenza) VALUES (?, ?, ?, ?)", [
        ("A001", "Penna blu", 1.20, 100),
        ("A002", "Quaderno A4", 2.50, 40),
        ("A003", "Zaino", 35.00, 5),
    ])
    con.sql("FROM articoli").show()

    def vendi(codice: str, quantita: int) -> None:
        """Movimento + aggiornamento giacenza: o tutti e due o nessuno (transazione)."""
        con.begin()
        try:
            con.execute("INSERT INTO movimenti (codice, quantita) VALUES (?, ?)", [codice, -quantita])
            con.execute("UPDATE articoli SET giacenza = giacenza - ? WHERE codice = ?", [quantita, codice])
            con.commit()
            print(f"venduti {quantita} x {codice}")
        except duckdb.Error as errore:
            con.rollback()
            print(f"vendita {quantita} x {codice} annullata: {type(errore).__name__}")

    print("---- transazioni ----")
    vendi("A001", 10)
    vendi("A003", 7)      # giacenza 5: il CHECK fallisce, anche il movimento viene annullato
    vendi("X999", 1)      # articolo inesistente: fallisce la chiave esterna
    con.sql("FROM articoli ORDER BY codice").show()
    con.sql("SELECT codice, quantita FROM movimenti").show()

    print("---- vista ----")
    con.execute("""
        CREATE OR REPLACE VIEW valore_magazzino AS
        SELECT codice, descrizione, giacenza, prezzo * giacenza AS valore
        FROM articoli
    """)
    con.sql("FROM valore_magazzino UNION ALL BY NAME SELECT 'TOTALE' AS codice, sum(valore) AS valore FROM valore_magazzino").show()

    print("---- export su Parquet e CSV ----")
    con.execute(f"COPY articoli TO '{CARTELLA / 'articoli.parquet'}' (FORMAT parquet)")
    con.execute(f"COPY (FROM valore_magazzino) TO '{CARTELLA / 'magazzino.csv'}' (FORMAT csv, HEADER, DELIMITER ';')")
    print((CARTELLA / "magazzino.csv").read_text())

print("---- riapertura in sola lettura: i dati sono rimasti sul file ----")
with duckdb.connect(str(FILE_DB), read_only=True) as con:
    print(con.sql("SELECT codice, giacenza FROM articoli ORDER BY codice").fetchall())
    print("tabelle:", [r[0] for r in con.sql("SHOW TABLES").fetchall()])
    try:
        con.execute("DELETE FROM articoli")
    except duckdb.Error as errore:
        print("scrittura rifiutata:", type(errore).__name__)
