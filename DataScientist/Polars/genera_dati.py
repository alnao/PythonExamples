"""Genera i dati di esempio (vendite sintetiche) usati dagli script 02, 03 e 04.

Uso:  python genera_dati.py [numero_righe]     (default 2.000.000)
Crea nella cartella dati/:
- vendite.csv e vendite.parquet: una riga per scontrino
- negozi.csv: anagrafica dei negozi, per gli esempi di join
"""
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

CARTELLA = Path(__file__).parent / "dati"

NEGOZI = pl.DataFrame({
    "negozio": ["N01", "N02", "N03", "N04", "N05", "N06", "N07"],
    "citta": ["Torino", "Milano", "Genova", "Bologna", "Roma", "Napoli", "Firenze"],
    "regione": ["Piemonte", "Lombardia", "Liguria", "Emilia-Romagna", "Lazio", "Campania", "Toscana"],
})
NEGOZI_APERTI = NEGOZI["negozio"].to_list()[:6]   # N07 è appena aperto: in anagrafica ma senza vendite

PRODOTTI = {  # prodotto: (categoria, prezzo base)
    "caffè": ("bar", 1.2), "cornetto": ("bar", 1.5), "pizza": ("cibo", 8.0),
    "pasta": ("cibo", 1.9), "vino": ("bevande", 9.5), "acqua": ("bevande", 0.6),
    "giornale": ("edicola", 1.8), "rivista": ("edicola", 4.5),
}


def genera(righe: int, seme: int = 42) -> pl.DataFrame:
    rng = np.random.default_rng(seme)
    nomi = list(PRODOTTI)
    indici = rng.integers(0, len(nomi), righe)
    prezzi_base = np.array([PRODOTTI[n][1] for n in nomi])
    giorni = rng.integers(0, 730, righe)   # due anni di dati
    return pl.DataFrame({
        "data": np.datetime64(date(2024, 1, 1)) + giorni.astype("timedelta64[D]"),
        "negozio": rng.choice(NEGOZI_APERTI, righe),
        "prodotto": np.array(nomi)[indici],
        "categoria": np.array([PRODOTTI[n][0] for n in nomi])[indici],
        "quantita": rng.integers(1, 6, righe),
        # prezzo con una variazione casuale del ±10%
        "prezzo": np.round(prezzi_base[indici] * rng.uniform(0.9, 1.1, righe), 2),
    }).with_columns(pl.col("data").cast(pl.Date))


def assicura_dati(righe: int = 2_000_000) -> Path:
    """Genera i dati solo se mancano: la chiamano gli altri script."""
    if not (CARTELLA / "vendite.parquet").exists() or not (CARTELLA / "negozi.csv").exists():
        main(righe)
    return CARTELLA


def main(righe: int) -> None:
    CARTELLA.mkdir(exist_ok=True)
    inizio = time.perf_counter()
    vendite = genera(righe)
    vendite.write_csv(CARTELLA / "vendite.csv")
    vendite.write_parquet(CARTELLA / "vendite.parquet")
    NEGOZI.write_csv(CARTELLA / "negozi.csv")
    print(f"Generate {vendite.height:,} righe in {time.perf_counter() - inizio:.1f}s nella cartella {CARTELLA}")
    print(vendite.head())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000)
