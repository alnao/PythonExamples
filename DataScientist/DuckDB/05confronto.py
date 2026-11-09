"""Confronto dei tempi: Pandas, Polars e DuckDB sulla stessa elaborazione, da CSV e da Parquet.

Elaborazione (la stessa di ../Polars/04confrontoPandas.py): vendite del 2025, incasso
= quantita * prezzo, join con l'anagrafica negozi, somma per regione e categoria.
I tempi dipendono dalla macchina: conta il rapporto tra i valori.
"""
import time

import duckdb
import pandas as pd
import polars as pl
from polars.testing import assert_frame_equal

from genera_dati import assicura_dati

cartella = assicura_dati()
NEGOZI = cartella / "negozi.csv"


def con_pandas(formato: str) -> pl.DataFrame:
    file = cartella / f"vendite.{formato}"
    df = pd.read_parquet(file) if formato == "parquet" else pd.read_csv(file, parse_dates=["data"])
    df["data"] = pd.to_datetime(df["data"])
    df = df[df["data"].dt.year == 2025]
    df = df.assign(incasso=df["quantita"] * df["prezzo"]).merge(pd.read_csv(NEGOZI), on="negozio")
    risultato = df.groupby(["regione", "categoria"], as_index=False)["incasso"].sum()
    return pl.from_pandas(risultato).sort("regione", "categoria")


def con_polars(formato: str) -> pl.DataFrame:
    file = cartella / f"vendite.{formato}"
    vendite = pl.scan_parquet(file) if formato == "parquet" else pl.scan_csv(file, try_parse_dates=True)
    return (vendite.filter(pl.col("data").dt.year() == 2025)
            .with_columns(incasso=pl.col("quantita") * pl.col("prezzo"))
            .join(pl.scan_csv(NEGOZI), on="negozio")
            .group_by("regione", "categoria").agg(pl.col("incasso").sum())
            .sort("regione", "categoria")
            .collect())


def con_duckdb(formato: str) -> pl.DataFrame:
    return duckdb.sql(f"""
        SELECT n.regione, v.categoria, sum(v.quantita * v.prezzo) AS incasso
        FROM '{cartella / f"vendite.{formato}"}' v
        JOIN '{NEGOZI}' n USING (negozio)
        WHERE year(v.data) = 2025
        GROUP BY ALL
        ORDER BY ALL
    """).pl()


def cronometra(funzione, *argomenti, ripetizioni: int = 3):
    tempi = []
    for _ in range(ripetizioni):
        inizio = time.perf_counter()
        risultato = funzione(*argomenti)
        tempi.append(time.perf_counter() - inizio)
    return min(tempi), risultato


risultati = {}
print(f"{'':<8}{'CSV':>10}{'Parquet':>10}")
for nome, funzione in [("Pandas", con_pandas), ("Polars", con_polars), ("DuckDB", con_duckdb)]:
    tempi = []
    for formato in ("csv", "parquet"):
        tempo, risultati[(nome, formato)] = cronometra(funzione, formato)
        tempi.append(tempo)
    print(f"{nome:<8}{tempi[0]:>9.3f}s{tempi[1]:>9.3f}s")

# tutti i risultati devono coincidere, a meno degli arrotondamenti delle somme di float
riferimento = risultati[("DuckDB", "parquet")]
for chiave, risultato in risultati.items():
    assert_frame_equal(risultato, riferimento, abs_tol=0.01, check_dtypes=False)
print("Tutti i risultati coincidono (tolleranza 0.01 €)")
print(riferimento.head())
