"""Gestore spese: versione testabile di Simple/expense_manager.py.

Differenze rispetto all'originale:
- la logica (GestoreSpese) è separata dall'interfaccia a menu (main), così si testa senza tastiera;
- Spesa è una dataclass immutabile che valida i dati alla creazione (data vera, importo positivo);
- i metodi restituiscono valori invece di stampare;
- le spese si possono salvare e ricaricare da un file JSON.
"""
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


def oggi() -> date:
    """Isolata in una funzione così i test possono sostituirla (monkeypatch)."""
    return date.today()


@dataclass(frozen=True)
class Spesa:
    data: date
    descrizione: str
    importo: float
    categoria: str = "varie"

    def __post_init__(self):
        if not isinstance(self.data, date):
            raise TypeError("data deve essere un datetime.date")
        if not self.descrizione.strip():
            raise ValueError("La descrizione è obbligatoria")
        if self.importo <= 0:
            raise ValueError(f"L'importo deve essere positivo, ricevuto {self.importo}")

    @classmethod
    def da_testo(cls, data: str, descrizione: str, importo: str, categoria: str = "") -> "Spesa":
        """Crea una spesa dai valori digitati dall'utente. Data vuota = oggi."""
        giorno = oggi() if not data.strip() else date.fromisoformat(data.strip())
        try:
            valore = float(importo.replace(",", "."))
        except ValueError as errore:
            raise ValueError(f"Importo non numerico: {importo!r}") from errore
        return cls(giorno, descrizione.strip(), valore, categoria.strip() or "varie")


class GestoreSpese:
    def __init__(self, spese: list[Spesa] | None = None):
        self._spese: list[Spesa] = list(spese or [])

    def __len__(self) -> int:
        return len(self._spese)

    def aggiungi(self, spesa: Spesa) -> None:
        self._spese.append(spesa)

    def rimuovi(self, indice: int) -> Spesa:
        """Rimuove la spesa in posizione `indice` (base 0) e la restituisce."""
        if not 0 <= indice < len(self._spese):
            raise IndexError(f"Indice {indice} fuori intervallo (0..{len(self._spese) - 1})")
        return self._spese.pop(indice)

    def elenco(self) -> list[Spesa]:
        """Copia della lista: chi la riceve non può alterare lo stato interno."""
        return list(self._spese)

    def totale(self) -> float:
        return round(sum(s.importo for s in self._spese), 2)

    def totale_per_categoria(self) -> dict[str, float]:
        totali: dict[str, float] = defaultdict(float)
        for spesa in self._spese:
            totali[spesa.categoria] += spesa.importo
        return {categoria: round(valore, 2) for categoria, valore in sorted(totali.items())}

    def filtra_mese(self, anno: int, mese: int) -> list[Spesa]:
        if not 1 <= mese <= 12:
            raise ValueError(f"Mese non valido: {mese}")
        return [s for s in self._spese if s.data.year == anno and s.data.month == mese]

    def salva_json(self, percorso: Path) -> None:
        righe = [{**asdict(s), "data": s.data.isoformat()} for s in self._spese]
        Path(percorso).write_text(json.dumps(righe, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def carica_json(cls, percorso: Path) -> "GestoreSpese":
        percorso = Path(percorso)
        if not percorso.exists():
            return cls()
        righe = json.loads(percorso.read_text(encoding="utf-8"))
        return cls([Spesa(date.fromisoformat(r["data"]), r["descrizione"], r["importo"],
                          r.get("categoria", "varie")) for r in righe])


def formatta_elenco(spese: list[Spesa]) -> str:
    if not spese:
        return "Nessuna spesa presente"
    return "\n".join(
        f"{i} {s.data.isoformat()} {s.descrizione} [{s.categoria}] {s.importo:.2f} €"
        for i, s in enumerate(spese, start=1)
    )


MENU = """Gestore spese
1 elenco
2 totale
3 aggiungi
4 rimuovi
5 esci"""


def main(percorso: Path | None = None) -> None:
    gestore = GestoreSpese.carica_json(percorso) if percorso else GestoreSpese()
    while True:
        print(MENU)
        scelta = input("Seleziona (1-5): ").strip()
        if scelta == "1":
            print(formatta_elenco(gestore.elenco()))
        elif scelta == "2":
            print(f"Totale spese {gestore.totale():.2f} €")
        elif scelta == "3":
            try:
                spesa = Spesa.da_testo(
                    input("Data (YYYY-MM-DD, vuoto = oggi): "),
                    input("Descrizione: "),
                    input("Importo: "),
                    input("Categoria (vuoto = varie): "),
                )
            except ValueError as errore:
                print(f"Spesa non valida: {errore}")
                continue
            gestore.aggiungi(spesa)
            print("Spesa aggiunta")
        elif scelta == "4":
            indice = input("Numero da rimuovere (0 per annullare): ").strip()
            if indice in ("", "0"):
                continue
            try:
                rimossa = gestore.rimuovi(int(indice) - 1)
                print(f"Rimossa: {rimossa.descrizione}")
            except (ValueError, IndexError):
                print("Numero non valido")
        elif scelta == "5":
            break
        else:
            print("Comando non valido")
    if percorso:
        gestore.salva_json(percorso)
    print("Ciao ciao")


if __name__ == "__main__":
    main(Path(__file__).with_name("spese.json"))
