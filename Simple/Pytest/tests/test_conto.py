"""Test di conto.py: fixture, parametrize, pytest.raises e Decimal."""
from decimal import Decimal

import pytest

from conto import (ContoCorrente, Gestore, ImportoNonValidoError,
                   SaldoInsufficienteError, a_decimal)


# --- test semplici con le fixture di conftest.py ---

def test_saldo_iniziale(alberto):
    assert alberto.saldo == Decimal("40000")


def test_deposita_restituisce_nuovo_saldo(valentina):
    assert valentina.deposita(500) == Decimal("3500")
    assert valentina.saldo == Decimal("3500")


def test_preleva_fino_a_zero(valentina):
    # nell'originale "return 0" era indistinguibile da un prelievo rifiutato
    assert valentina.preleva(3000) == Decimal("0")


def test_saldo_in_sola_lettura(alberto):
    with pytest.raises(AttributeError):
        alberto.saldo = 1_000_000


def test_descrizione(alberto):
    assert alberto.descrizione() == "Conto corrente Alberto n.1 saldo 40000.00"


# --- eccezioni: pytest.raises con match (regex sul messaggio) ---

def test_preleva_oltre_il_saldo(valentina):
    with pytest.raises(SaldoInsufficienteError, match="disponibili 3000"):
        valentina.preleva(3000.01)
    assert valentina.saldo == Decimal("3000"), "un prelievo rifiutato non deve toccare il saldo"


@pytest.mark.parametrize("importo", [0, -1, -0.01, "abc", None, True, float("nan"), float("inf")])
def test_importi_non_validi(valentina, importo):
    with pytest.raises(ImportoNonValidoError):
        valentina.deposita(importo)


@pytest.mark.parametrize("nome", ["", "   "])
def test_nome_obbligatorio(nome):
    with pytest.raises(ValueError, match="nome"):
        ContoCorrente(nome, 3, 100)


def test_saldo_iniziale_negativo():
    with pytest.raises(ImportoNonValidoError):
        ContoCorrente("Mario", 3, -50)


# --- parametrize con id leggibili nel report (pytest -v) ---

@pytest.mark.parametrize(
    ("valore", "atteso"),
    [
        (10, Decimal("10")),
        ("12.50", Decimal("12.50")),
        (0.1, Decimal("0.1")),
        (Decimal("3.333"), Decimal("3.333")),
    ],
    ids=["int", "stringa", "float", "decimal"],
)
def test_a_decimal(valore, atteso):
    assert a_decimal(valore) == atteso


def test_decimal_evita_errori_di_arrotondamento():
    conto = ContoCorrente("Test", 9)
    for _ in range(3):
        conto.deposita(0.1)
    assert 0.1 + 0.1 + 0.1 != 0.3            # con i float il risultato è 0.30000000000000004
    assert conto.saldo == Decimal("0.3")      # con Decimal è esatto


# --- bonifico ---

def test_bonifico(alberto, valentina):
    Gestore.bonifico(alberto, valentina, 200)
    assert (alberto.saldo, valentina.saldo) == (Decimal("39800"), Decimal("3200"))


def test_bonifico_senza_copertura_e_atomico(alberto, valentina):
    totale_prima = alberto.saldo + valentina.saldo
    with pytest.raises(SaldoInsufficienteError):
        Gestore.bonifico(valentina, alberto, 5000)
    assert alberto.saldo + valentina.saldo == totale_prima
    assert valentina.saldo == Decimal("3000")


def test_bonifico_verso_se_stesso(alberto):
    with pytest.raises(ValueError, match="diversi"):
        Gestore.bonifico(alberto, alberto, 10)


@pytest.mark.lento
def test_tanti_bonifici_conservano_il_totale(alberto, valentina):
    """Marcato "lento": si esclude con  pytest -m "not lento"."""
    totale = alberto.saldo + valentina.saldo
    for i in range(20_000):
        sorgente, destinazione = (alberto, valentina) if i % 2 else (valentina, alberto)
        Gestore.bonifico(sorgente, destinazione, "0.01")
    assert alberto.saldo + valentina.saldo == totale


# --- capsys: cattura quello che il codice stampa ---

def test_demo_stampa(capsys):
    import runpy
    from pathlib import Path
    runpy.run_path(str(Path(__file__).parent.parent / "conto.py"), run_name="__main__")
    uscita = capsys.readouterr().out
    assert "Conto corrente Alberto n.1 saldo 39800.00" in uscita
    assert "Bonifico rifiutato" in uscita
