"""Test automatici delle app Textual: run_test() avvia l'app senza terminale e
restituisce un Pilot che simula tasti e clic.

Uso:  pytest test_spese.py -v
"""
import asyncio
import json

from textual.widgets import DataTable, Digits, Input

from ciao import CiaoApp
from spese import GestoreSpeseApp, Spesa

DIMENSIONE = (120, 40)   # colonne e righe del terminale simulato


def esegui(coroutine):
    """Le API di test di Textual sono asincrone: asyncio.run evita plugin aggiuntivi di pytest."""
    return asyncio.run(coroutine)


def test_ciao_contatore():
    async def scenario():
        app = CiaoApp()
        async with app.run_test(size=DIMENSIONE) as pilot:
            # due clic di fila sullo stesso punto sarebbero un doppio clic: un clic e poi la tastiera
            await pilot.click("#piu")
            await pilot.press("+", "+", "-")
            assert app.contatore == 2
            assert str(app.query_one(Digits).value) == "2"
            await pilot.click("#azzera")
            assert app.contatore == 0
    esegui(scenario())


def test_avvio_vuoto():
    async def scenario():
        app = GestoreSpeseApp()
        async with app.run_test(size=DIMENSIONE):
            assert app.spese == []
            assert app.query_one(DataTable).row_count == 0
            assert "TOTALE" in str(app.query_one("#riepilogo").render())
    esegui(scenario())


def test_aggiungi_spesa_digitando():
    async def scenario():
        app = GestoreSpeseApp()
        async with app.run_test(size=DIMENSIONE) as pilot:
            await pilot.click("#descrizione")
            await pilot.press(*"pizza")
            await pilot.click("#importo")
            await pilot.press(*"12")
            await pilot.press("enter")            # Invio in un campo = Aggiungi
            await pilot.pause()
            assert len(app.spese) == 1
            assert app.spese[0].descrizione == "pizza"
            assert app.spese[0].importo == 12.0
            assert app.query_one(DataTable).row_count == 1
            assert app.query_one("#descrizione", Input).value == ""   # modulo svuotato
    esegui(scenario())


def test_spesa_non_valida_non_viene_aggiunta():
    async def scenario():
        app = GestoreSpeseApp()
        async with app.run_test(size=DIMENSIONE) as pilot:
            app.query_one("#data", Input).value = "2026-02-30"     # data inesistente
            app.query_one("#descrizione", Input).value = "x"
            app.query_one("#importo", Input).value = "5"
            await pilot.click("#aggiungi")
            await pilot.pause()
            assert app.spese == []
            assert app.query_one("#data", Input).has_class("-invalid")
    esegui(scenario())


def test_elimina_con_conferma_e_annulla(tmp_path):
    file = tmp_path / "spese.json"
    file.write_text(json.dumps([
        {"data": "2026-01-10", "descrizione": "pane", "importo": 2.5, "categoria": "cibo"},
        {"data": "2026-01-11", "descrizione": "cinema", "importo": 9.0, "categoria": "svago"},
    ]))

    async def scenario():
        app = GestoreSpeseApp(file)
        async with app.run_test(size=DIMENSIONE) as pilot:
            assert len(app.spese) == 2
            app.query_one(DataTable).focus()
            await pilot.press("delete")           # apre la finestra di conferma
            await pilot.click("#no")
            assert len(app.spese) == 2
            await pilot.press("delete")
            await pilot.click("#si")
            await pilot.pause()
            # la tabella è ordinata per data decrescente: la prima riga era "cinema"
            assert [s.descrizione for s in app.spese] == ["pane"]
    esegui(scenario())


def test_salva_su_file(tmp_path):
    file = tmp_path / "spese.json"

    async def scenario():
        app = GestoreSpeseApp(file)
        async with app.run_test(size=DIMENSIONE) as pilot:
            app.spese = [Spesa("2026-03-01", "benzina", 50.0, "auto")]
            await pilot.press("ctrl+s")
    esegui(scenario())
    assert json.loads(file.read_text()) == [
        {"data": "2026-03-01", "descrizione": "benzina", "importo": 50.0, "categoria": "auto"}]


def test_riepilogo_per_categoria():
    testo = GestoreSpeseApp.testo_riepilogo([
        Spesa("2026-01-01", "a", 10, "cibo"), Spesa("2026-01-02", "b", 5.5, "cibo"),
        Spesa("2026-01-03", "c", 30, "auto"),
    ]).plain.splitlines()
    assert testo[0].split() == ["auto", "30.00", "€"]          # categoria più costosa per prima
    assert testo[-1].split() == ["TOTALE", "45.50", "€"]
