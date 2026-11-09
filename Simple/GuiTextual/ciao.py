"""Textual: la prima applicazione. Widget, eventi, tasti rapidi e variabili reattive.

Uso:  python ciao.py      (Ctrl+Q per uscire, Ctrl+P per la palette dei comandi)
"""
from textual.app import App, ComposeResult
from textual.containers import Center, Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Digits, Footer, Header, Label


class CiaoApp(App):
    TITLE = "Ciao Textual"
    SUB_TITLE = "contatore di esempio"

    # stile in linguaggio TCSS (simile al CSS del web), qui scritto dentro la classe
    CSS = """
    Screen { align: center middle; }
    #saluto { margin-bottom: 1; text-style: bold; }
    Digits { width: auto; margin: 1 0; color: $accent; }
    Horizontal { height: auto; width: auto; }
    Button { margin: 0 1; }
    """

    # tasto, azione (metodo action_<nome>), descrizione mostrata nel footer
    BINDINGS = [
        ("+", "incrementa", "Più uno"),
        ("-", "decrementa", "Meno uno"),
        ("t", "tema", "Tema chiaro/scuro"),
    ]

    # quando contatore cambia, Textual chiama watch_contatore da solo
    contatore = reactive(0)

    def compose(self) -> ComposeResult:
        """Descrive i widget dello schermo, dall'alto verso il basso."""
        yield Header()
        with Center():
            yield Label("Ciao da Textual!", id="saluto")
        with Center():
            yield Digits("0")
        with Center(), Horizontal():
            yield Button("- 1", id="meno", variant="error")
            yield Button("Azzera", id="azzera")
            yield Button("+ 1", id="piu", variant="success")
        yield Footer()

    def watch_contatore(self, valore: int) -> None:
        self.query_one(Digits).update(str(valore))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Un solo gestore per tutti i pulsanti: si distinguono con l'id."""
        if event.button.id == "piu":
            self.action_incrementa()
        elif event.button.id == "meno":
            self.action_decrementa()
        else:
            self.contatore = 0
            self.notify("Contatore azzerato")

    def action_incrementa(self) -> None:
        self.contatore += 1

    def action_decrementa(self) -> None:
        self.contatore -= 1

    def action_tema(self) -> None:
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"


if __name__ == "__main__":
    CiaoApp().run()
