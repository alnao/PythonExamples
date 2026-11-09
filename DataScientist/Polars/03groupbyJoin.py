"""Polars: aggregazioni, join, funzioni finestra, pivot e serie temporali."""
import polars as pl

from genera_dati import assicura_dati

cartella = assicura_dati()
pl.Config.set_fmt_float("full")   # niente notazione scientifica (1.1250e6) nelle tabelle
vendite = pl.read_parquet(cartella / "vendite.parquet").with_columns(
    incasso=(pl.col("quantita") * pl.col("prezzo")).round(2)
)
negozi = pl.read_csv(cartella / "negozi.csv")

print("---- group_by con più aggregazioni ----")
print(vendite.group_by("categoria").agg(
    incasso_totale=pl.col("incasso").sum().round(2),
    scontrino_medio=pl.col("incasso").mean().round(2),
    pezzi=pl.col("quantita").sum(),
    prodotti=pl.col("prodotto").unique().sort(),
).sort("incasso_totale", descending=True))

print("---- join con l'anagrafica dei negozi ----")
per_regione = (vendite.join(negozi, on="negozio", how="left")
               .group_by("regione", "citta")
               .agg(pl.col("incasso").sum().round(2))
               .sort("incasso", descending=True))
print(per_regione)

print("---- join anti: negozi in anagrafica senza nessuna vendita ----")
print(negozi.join(vendite.select("negozio").unique(), on="negozio", how="anti"))

print("---- join semi: negozi che hanno venduto vino a Natale 2025 ----")
natale = vendite.filter((pl.col("prodotto") == "vino") & (pl.col("data") == pl.date(2025, 12, 25)))
print(negozi.join(natale, on="negozio", how="semi"))

print("---- funzioni finestra con over(): quota di ogni prodotto sul totale della sua categoria ----")
per_prodotto = vendite.group_by("categoria", "prodotto").agg(pl.col("incasso").sum().round(2))
print(per_prodotto.with_columns(
    quota_pct=(pl.col("incasso") / pl.col("incasso").sum().over("categoria") * 100).round(1),
    posizione=pl.col("incasso").rank(descending=True).over("categoria").cast(pl.Int32),
).sort("categoria", "posizione"))

print("---- pivot: incasso per negozio (righe) e categoria (colonne) ----")
print(vendite.pivot(on="categoria", index="negozio", values="incasso",
                    aggregate_function="sum").sort("negozio")
             .with_columns(pl.exclude("negozio").round(0)))

print("---- group_by_dynamic: incasso mensile (serve la colonna data ordinata) ----")
mensile = (vendite.sort("data")
           .group_by_dynamic("data", every="1mo")
           .agg(pl.col("incasso").sum().round(0)))
print(mensile.head(6))

print("---- media mobile su 3 mesi e variazione rispetto al mese precedente ----")
print(mensile.with_columns(
    media_3_mesi=pl.col("incasso").rolling_mean(window_size=3).round(0),
    variazione_pct=(pl.col("incasso").pct_change() * 100).round(1),
).head(6))

print("---- concat e unpivot (da formato largo a lungo) ----")
largo = pl.DataFrame({"negozio": ["N01", "N02"], "2024": [100, 200], "2025": [150, 210]})
print(largo.unpivot(index="negozio", variable_name="anno", value_name="incasso"))
print(pl.concat([largo, pl.DataFrame({"negozio": ["N03"], "2024": [90], "2025": [95]})]))
