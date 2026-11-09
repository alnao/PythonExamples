"""Test di expense_manager.py: approx, tmp_path, monkeypatch, capsys, mock."""
import json
from datetime import date
from unittest.mock import patch

import pytest

import expense_manager
from expense_manager import GestoreSpese, Spesa, formatta_elenco, main


# --- validazione della dataclass ---

def test_spesa_valida(crea_spesa):
    spesa = crea_spesa(3.5, "cornetto")
    assert spesa.importo == 3.5
    assert spesa.categoria == "varie"


@pytest.mark.parametrize(("importo", "descrizione"), [(0, "x"), (-5, "x"), (5, ""), (5, "   ")])
def test_spesa_non_valida(importo, descrizione):
    with pytest.raises(ValueError):
        Spesa(date(2026, 1, 1), descrizione, importo)


def test_spesa_immutabile(crea_spesa):
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        crea_spesa().importo = 0


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [("12.5", 12.5), ("12,5", 12.5), (" 7 ", 7.0)],
)
def test_da_testo_importo(testo, atteso):
    assert Spesa.da_testo("2026-03-01", "x", testo).importo == atteso


def test_da_testo_importo_non_numerico():
    with pytest.raises(ValueError, match="non numerico"):
        Spesa.da_testo("2026-03-01", "x", "dieci")


def test_da_testo_data_non_valida():
    with pytest.raises(ValueError):
        Spesa.da_testo("2026-02-30", "x", "1")


def test_da_testo_data_vuota_usa_oggi(monkeypatch):
    # monkeypatch sostituisce la funzione solo per la durata di questo test
    monkeypatch.setattr(expense_manager, "oggi", lambda: date(2030, 12, 25))
    assert Spesa.da_testo("", "regali", "100").data == date(2030, 12, 25)


def test_da_testo_data_vuota_con_mock():
    # stessa cosa con unittest.mock.patch, che in più registra le chiamate
    with patch("expense_manager.oggi", return_value=date(2031, 1, 1)) as finto_oggi:
        spesa = Spesa.da_testo("", "x", "1")
    assert spesa.data == date(2031, 1, 1)
    finto_oggi.assert_called_once()


# --- gestore ---

def test_gestore_vuoto():
    gestore = GestoreSpese()
    assert len(gestore) == 0
    assert gestore.totale() == 0
    assert gestore.totale_per_categoria() == {}


def test_totale(gestore_con_spese):
    assert gestore_con_spese.totale() == pytest.approx(124.80)


def test_totale_con_float_problematici(crea_spesa):
    gestore = GestoreSpese([crea_spesa(0.1), crea_spesa(0.2)])
    # pytest.approx confronta i float con una tolleranza
    assert gestore.totale() == pytest.approx(0.3)


def test_totale_per_categoria(gestore_con_spese):
    assert gestore_con_spese.totale_per_categoria() == {"auto": 105.0, "cibo": 19.8}


@pytest.mark.parametrize(("anno", "mese", "quante"), [(2026, 1, 2), (2026, 2, 2), (2026, 3, 0), (2025, 1, 0)])
def test_filtra_mese(gestore_con_spese, anno, mese, quante):
    assert len(gestore_con_spese.filtra_mese(anno, mese)) == quante


@pytest.mark.parametrize("mese", [0, 13])
def test_filtra_mese_non_valido(gestore_con_spese, mese):
    with pytest.raises(ValueError):
        gestore_con_spese.filtra_mese(2026, mese)


def test_rimuovi(gestore_con_spese):
    rimossa = gestore_con_spese.rimuovi(1)
    assert rimossa.descrizione == "benzina"
    assert len(gestore_con_spese) == 3


@pytest.mark.parametrize("indice", [-1, 4, 100])
def test_rimuovi_indice_non_valido(gestore_con_spese, indice):
    with pytest.raises(IndexError):
        gestore_con_spese.rimuovi(indice)
    assert len(gestore_con_spese) == 4


def test_elenco_e_una_copia(gestore_con_spese):
    gestore_con_spese.elenco().clear()
    assert len(gestore_con_spese) == 4


def test_formatta_elenco(gestore_con_spese):
    righe = formatta_elenco(gestore_con_spese.elenco()).splitlines()
    assert righe[0] == "1 2026-01-10 pizza [cibo] 12.50 €"
    assert len(righe) == 4
    assert formatta_elenco([]) == "Nessuna spesa presente"


# --- tmp_path: cartella temporanea diversa per ogni test, cancellata da pytest ---

def test_salva_e_carica_json(gestore_con_spese, tmp_path):
    file = tmp_path / "spese.json"
    gestore_con_spese.salva_json(file)
    assert json.loads(file.read_text(encoding="utf-8"))[0]["data"] == "2026-01-10"
    ricaricato = GestoreSpese.carica_json(file)
    assert ricaricato.elenco() == gestore_con_spese.elenco()


def test_carica_file_inesistente(tmp_path):
    assert len(GestoreSpese.carica_json(tmp_path / "manca.json")) == 0


# --- main(): input simulato con monkeypatch, output catturato con capsys ---

def simula_input(monkeypatch, *risposte):
    risposte_iter = iter(risposte)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(risposte_iter))


def test_main_aggiungi_totale_esci(monkeypatch, capsys, tmp_path):
    file = tmp_path / "spese.json"
    simula_input(monkeypatch,
                 "3", "2026-05-01", "libro", "18,90", "cultura",   # aggiungi
                 "2",                                             # totale
                 "5")                                             # esci
    main(file)
    uscita = capsys.readouterr().out
    assert "Spesa aggiunta" in uscita
    assert "Totale spese 18.90 €" in uscita
    assert GestoreSpese.carica_json(file).totale_per_categoria() == {"cultura": 18.9}


def test_main_gestisce_input_sbagliati(monkeypatch, capsys):
    simula_input(monkeypatch,
                 "9",                                  # comando inesistente
                 "3", "ieri", "x", "1", "",            # data non valida
                 "4", "abc",                           # numero non valido
                 "4", "7",                             # indice fuori intervallo
                 "5")
    main()
    uscita = capsys.readouterr().out
    assert "Comando non valido" in uscita
    assert "Spesa non valida" in uscita
    assert uscita.count("Numero non valido") == 2
    assert uscita.rstrip().endswith("Ciao ciao")
