"""Polars: le basi, con lo stesso file CSV degli esempi Pandas (../Pandas/08data.csv).

In Polars non si modificano le colonne "sul posto" (df["x"] = ...): ogni operazione
restituisce un nuovo DataFrame e le trasformazioni si scrivono come *espressioni* (pl.col(...)).
Non esiste l'indice delle righe: si filtra sempre per valore.
"""
from pathlib import Path

import polars as pl
import polars.selectors as cs

FILE_CSV = Path(__file__).parent.parent / "Pandas" / "08data.csv"

print("---- read_csv (separator e date riconosciute in automatico) ----")
df = pl.read_csv(FILE_CSV, separator=";", try_parse_dates=True)
print(df.schema)        # nome colonna -> tipo
print(df)

print("---- describe ----")
print(df.describe())

print("---- select: scegliere e trasformare colonne ----")
print(df.select("name", "age"))
print(df.select(pl.col("name").str.to_uppercase(), (pl.col("age") * 12).alias("mesi")))

print("---- filter: condizioni combinate con & e | ----")
print(df.filter((pl.col("age") > 18) & (pl.col("date_column_1").dt.year() >= 2021)))

print("---- with_columns: aggiungere colonne calcolate ----")
df2 = df.with_columns(
    anno=pl.col("date_column_1").dt.year(),
    giorni_tra_date=(pl.col("date_column_1") - pl.col("date_column_2")).dt.total_days(),
    fascia=pl.when(pl.col("age") < 18).then(pl.lit("minorenne"))
             .when(pl.col("age") < 65).then(pl.lit("adulto"))
             .otherwise(pl.lit("senior")),
)
print(df2)

print("---- sort su più colonne ----")
print(df2.sort(["fascia", "age"], descending=[False, True]))

print("---- group_by + agg ----")
print(df2.group_by("fascia").agg(
    persone=pl.len(),
    eta_media=pl.col("age").mean(),
    nomi=pl.col("name"),          # raccoglie i nomi in una lista
).sort("fascia"))

print("---- selettori di colonne per tipo ----")
print(df.select(cs.datetime()))
print(df.select(cs.numeric()))

print("---- valori nulli ----")
con_nulli = pl.DataFrame({"a": [1, None, 3], "b": ["x", None, "z"]})
print(con_nulli.null_count())
print(con_nulli.fill_null(strategy="forward"))
print(con_nulli.drop_nulls())

print("---- stringhe ----")
print(df.select(
    pl.col("name"),
    pl.col("name").str.len_chars().alias("lunghezza"),
    pl.col("name").str.contains("^a").alias("inizia_con_a"),
    pl.col("name").str.slice(0, 3).alias("prime3"),
))

print("---- conversione da e verso Pandas (serve pyarrow) ----")
df_pandas = df.to_pandas()
print(type(df_pandas), df_pandas.shape)
print(pl.from_pandas(df_pandas).equals(df))
