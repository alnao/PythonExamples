"""Confronto dei tempi: la stessa elaborazione con Pandas, Polars eager e Polars lazy.

Elaborazione: leggere il CSV delle vendite, tenere il 2025, calcolare l'incasso,
unire l'anagrafica negozi e sommare l'incasso per regione e categoria.
I tempi dipendono dalla macchina: conta il rapporto tra i valori, non il numero assoluto.
"""
import time

import pandas as pd
import polars as pl

from genera_dati import assicura_dati

cartella = assicura_dati()
CSV, NEGOZI = cartella / "vendite.csv", cartella / "negozi.csv"


def con_pandas() -> pd.DataFrame:
    df = pd.read_csv(CSV, parse_dates=["data"])
    df = df[df["data"].dt.year == 2025]
    df = df.assign(incasso=df["quantita"] * df["prezzo"])
    df = df.merge(pd.read_csv(NEGOZI), on="negozio", how="left")
    return (df.groupby(["regione", "categoria"], as_index=False)["incasso"].sum()
              .sort_values(["regione", "categoria"], ignore_index=True))


def con_polars_eager() -> pl.DataFrame:
    df = pl.read_csv(CSV, try_parse_dates=True)
    df = df.filter(pl.col("data").dt.year() == 2025)
    df = df.with_columns(incasso=pl.col("quantita") * pl.col("prezzo"))
    df = df.join(pl.read_csv(NEGOZI), on="negozio", how="left")
    return df.group_by("regione", "categoria").agg(pl.col("incasso").sum()).sort("regione", "categoria")


def con_polars_lazy() -> pl.DataFrame:
    return (pl.scan_csv(CSV, try_parse_dates=True)
            .filter(pl.col("data").dt.year() == 2025)
            .with_columns(incasso=pl.col("quantita") * pl.col("prezzo"))
            .join(pl.scan_csv(NEGOZI), on="negozio", how="left")
            .group_by("regione", "categoria").agg(pl.col("incasso").sum())
            .sort("regione", "categoria")
            .collect())


def cronometra(funzione, ripetizioni: int = 3):
    tempi = []
    for _ in range(ripetizioni):
        inizio = time.perf_counter()
        risultato = funzione()
        tempi.append(time.perf_counter() - inizio)
    return min(tempi), risultato


t_pd, r_pd = cronometra(con_pandas)
t_eager, r_eager = cronometra(con_polars_eager)
t_lazy, r_lazy = cronometra(con_polars_lazy)

print(r_lazy)
print(f"{'Pandas':<14}{t_pd:8.3f}s")
print(f"{'Polars eager':<14}{t_eager:8.3f}s   {t_pd / t_eager:5.1f}x più veloce di Pandas")
print(f"{'Polars lazy':<14}{t_lazy:8.3f}s   {t_pd / t_lazy:5.1f}x più veloce di Pandas")

# i tre risultati devono coincidere: le somme di float possono differire nelle ultime cifre
# (l'ordine delle addizioni cambia tra le librerie e tra i thread), quindi si confronta con tolleranza
from polars.testing import assert_frame_equal
assert_frame_equal(pl.from_pandas(r_pd), r_lazy, abs_tol=0.01)
assert_frame_equal(r_eager, r_lazy, abs_tol=0.01)
print("Risultati identici (tolleranza 0.01 €)")
