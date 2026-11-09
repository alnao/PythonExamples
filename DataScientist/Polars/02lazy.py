"""Polars lazy: la query si descrive prima e si esegue alla fine con collect().

Con scan_parquet/scan_csv Polars non legge il file subito: costruisce un piano e lo ottimizza.
- projection pushdown: legge dal file solo le colonne usate
- predicate pushdown: applica i filtri durante la lettura
- engine "streaming": elabora il file a blocchi, anche se non sta tutto in memoria
"""
import time

import polars as pl

from genera_dati import assicura_dati

cartella = assicura_dati()

query = (
    pl.scan_parquet(cartella / "vendite.parquet")
    .filter(pl.col("categoria") == "bar")
    .with_columns(incasso=pl.col("quantita") * pl.col("prezzo"))
    .group_by("negozio", "prodotto")
    .agg(pl.col("incasso").sum().round(2), scontrini=pl.len())
    .sort("incasso", descending=True)
)

print("---- piano NON ottimizzato ----")
print(query.explain(optimized=False))
print("---- piano ottimizzato: notare SELECTION e PROJECT dentro la lettura del parquet ----")
print(query.explain())

print("---- collect ----")
inizio = time.perf_counter()
print(query.collect())
print(f"tempo: {time.perf_counter() - inizio:.3f}s")

print("---- collect con engine streaming ----")
inizio = time.perf_counter()
print(query.collect(engine="streaming").head(3))
print(f"tempo: {time.perf_counter() - inizio:.3f}s")

print("---- eager vs lazy sullo stesso CSV ----")
inizio = time.perf_counter()
eager = (pl.read_csv(cartella / "vendite.csv", try_parse_dates=True)
         .filter(pl.col("negozio") == "N01")
         .select(pl.col("quantita").sum()))
t_eager = time.perf_counter() - inizio

inizio = time.perf_counter()
lazy = (pl.scan_csv(cartella / "vendite.csv", try_parse_dates=True)
        .filter(pl.col("negozio") == "N01")
        .select(pl.col("quantita").sum())
        .collect())
t_lazy = time.perf_counter() - inizio
print(f"eager {t_eager:.3f}s  lazy {t_lazy:.3f}s  stesso risultato: {eager.equals(lazy)}")

print("---- sink_parquet: risultato scritto su file senza passare dalla memoria ----")
uscita = cartella / "solo_bar.parquet"
(pl.scan_parquet(cartella / "vendite.parquet")
   .filter(pl.col("categoria") == "bar")
   .sink_parquet(uscita))
print(f"{uscita.name}: {pl.scan_parquet(uscita).select(pl.len()).collect().item():,} righe")
