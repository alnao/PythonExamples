"""Gestore spese con interfaccia grafica nel terminale (Textual).

È lo stesso programma di ../expense_manager.py, ma invece del menu numerato ha:
modulo di inserimento con validazione, tabella navigabile, finestra di conferma,
riepilogo per categoria aggiornato in automatico, salvataggio su file JSON.

Uso:  python spese.py [file.json]      (default spese.json in questa cartella)
"""
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.validation import Function, Number
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Select, Static

CATEGORIE = ["cibo", "casa", "auto", "svago", "salute", "varie"]


@dataclass(frozen=True)
class Spesa:
    data: str
    descrizione: str
    importo: float
    categoria: str


def data_valida(testo: str) -> bool:
    try:
        date.fromisoformat(testo)
        return True
    except ValueError:
        return False


def carica(percorso: Path | None) -> list[Spesa]:
    if percorso is None or not percorso.exists():
        return []
    return [Spesa(**riga) for riga in json.loads(percorso.read_text(encoding="utf-8"))]


def salva(percorso: Path, spese: list[Spesa]) -> None:
    percorso.write_text(json.dumps([asdict(s) for s in spese], indent=2, ensure_ascii=False), encoding="utf-8")


class ConfermaElimina(ModalScreen[bool]):
    """Finestra modale: restituisce True/False a chi l'ha aperta con dismiss()."""

    BINDINGS = [("escape", "annulla", "Annulla")]

    def __init__(self, descrizione: str):
        super().__init__()
        self.descrizione = descrizione

    def compose(self) -> ComposeResult:
        with Vertical(id="dialogo"):
            yield Label(f"Eliminare la spesa [b]{self.descrizione}[/b]?")
            with Horizontal(id="pulsanti-dialogo"):
                yield Button("Elimina", variant="error", id="si")
                yield Button("Annulla", variant="primary", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "si")

    def action_annulla(self) -> None:
        self.dismiss(False)


class GestoreSpeseApp(App):
    CSS_PATH = "spese.tcss"          # stile in un file separato
    TITLE = "Gestore spese"
    BINDINGS = [
        Binding("ctrl+s", "salva", "Salva"),
        Binding("delete", "elimina", "Elimina riga"),
        Binding("ctrl+t", "tema", "Tema"),
        Binding("ctrl+q", "esci", "Salva ed esci"),
    ]

    # lista reattiva: assegnando una nuova lista, tabella e riepilogo si aggiornano (watch_spese)
    spese: reactive[list[Spesa]] = reactive(list, init=False, always_update=True)

    def __init__(self, percorso: Path | None = None):
        super().__init__()
        self.percorso = percorso
        self.sub_title = percorso.name if percorso else "senza salvataggio"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="corpo"):
            with VerticalScroll(id="modulo"):     # scorre se il terminale è basso
                yield Label("Nuova spesa", classes="titolo")
                yield Input(value=date.today().isoformat(), placeholder="Data (YYYY-MM-DD)", id="data",
                            validators=[Function(data_valida, "Data non valida")])
                yield Input(placeholder="Descrizione", id="descrizione",
                            validators=[Function(lambda t: bool(t.strip()), "Descrizione obbligatoria")])
                yield Input(placeholder="Importo", id="importo", type="number",
                            validators=[Number(minimum=0.01, failure_description="Importo non valido")])
                yield Select([(c.capitalize(), c) for c in CATEGORIE], value="varie",
                             allow_blank=False, id="categoria")
                yield Button("Aggiungi", variant="success", id="aggiungi")
                yield Label("Riepilogo", classes="titolo")
                yield Static(id="riepilogo")
            yield DataTable(id="tabella", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        tabella = self.query_one(DataTable)
        tabella.add_columns("Data", "Descrizione", "Categoria", "Importo")
        tabella.border_title = "Spese"
        self.spese = carica(self.percorso)
        self.query_one("#descrizione").focus()

    def watch_spese(self, spese: list[Spesa]) -> None:
        tabella = self.query_one(DataTable)
        tabella.clear()
        for spesa in sorted(spese, key=lambda s: s.data, reverse=True):
            tabella.add_row(spesa.data, spesa.descrizione, spesa.categoria,
                            Text(f"{spesa.importo:.2f} €", justify="right"),
                            key=str(spese.index(spesa)))   # la chiave è la posizione nella lista
        self.query_one("#riepilogo", Static).update(self.testo_riepilogo(spese))

    @staticmethod
    def testo_riepilogo(spese: list[Spesa]) -> Text:
        totali: dict[str, float] = {}
        for spesa in spese:
            totali[spesa.categoria] = totali.get(spesa.categoria, 0) + spesa.importo
        testo = Text()
        for categoria, valore in sorted(totali.items(), key=lambda kv: -kv[1]):
            testo.append(f"{categoria:<10}{valore:>10.2f} €\n")
        testo.append(f"{'TOTALE':<10}{sum(totali.values()):>10.2f} €", style="bold")
        return testo

    # lo stesso metodo risponde al pulsante e al tasto Invio in uno dei campi
    @on(Button.Pressed, "#aggiungi")
    @on(Input.Submitted)
    def aggiungi(self) -> None:
        campi = {nome: self.query_one(f"#{nome}", Input) for nome in ("data", "descrizione", "importo")}
        errori = [msg for campo in campi.values()
                  if (esito := campo.validate(campo.value)) and not esito.is_valid
                  for msg in esito.failure_descriptions]
        if errori:
            self.notify("\n".join(errori), title="Spesa non valida", severity="error")
            return
        nuova = Spesa(campi["data"].value, campi["descrizione"].value.strip(),
                      round(float(campi["importo"].value), 2), self.query_one(Select).value)
        self.spese = [*self.spese, nuova]     # nuova lista => scatta watch_spese
        campi["descrizione"].clear()
        campi["importo"].clear()
        campi["descrizione"].focus()
        self.notify(f"Aggiunta: {nuova.descrizione}")

    def action_elimina(self) -> None:
        tabella = self.query_one(DataTable)
        if not self.spese or not tabella.has_focus:
            return
        chiave, _ = tabella.coordinate_to_cell_key(tabella.cursor_coordinate)
        indice = int(chiave.value)

        def esito(conferma: bool | None) -> None:
            if conferma:
                self.spese = [s for i, s in enumerate(self.spese) if i != indice]
                self.notify("Spesa eliminata")

        self.push_screen(ConfermaElimina(self.spese[indice].descrizione), esito)

    def action_salva(self) -> None:
        if self.percorso:
            salva(self.percorso, self.spese)
            self.notify(f"Salvate {len(self.spese)} spese in {self.percorso.name}")

    def action_esci(self) -> None:
        self.action_salva()
        self.exit()

    def action_tema(self) -> None:
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"


if __name__ == "__main__":
    file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("spese.json")
    GestoreSpeseApp(file).run()
