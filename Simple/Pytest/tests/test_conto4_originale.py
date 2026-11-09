"""Test di caratterizzazione su Simple/conto4.py (il codice originale, non modificato).

Prima di riscrivere del codice si scrivono test che ne fotografano il comportamento:
così si vede cosa funziona e dove sono i bug. Qui il bug del bonifico è segnato
con xfail(strict=True): il test "deve fallire" e se un giorno passasse
(cioè il bug viene corretto) pytest lo segnala come errore, così ci si ricorda di togliere il marker.
"""
import importlib.util
from pathlib import Path

import pytest

PERCORSO_ORIGINALE = Path(__file__).resolve().parents[2] / "conto4.py"


@pytest.fixture(scope="module")
def conto4():
    """Importa il file originale. scope="module": viene eseguito una sola volta per questo file."""
    if not PERCORSO_ORIGINALE.exists():
        pytest.skip(f"file originale non trovato: {PERCORSO_ORIGINALE}")
    spec = importlib.util.spec_from_file_location("conto4_originale", PERCORSO_ORIGINALE)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)   # l'originale stampa a video quando viene importato
    return modulo


def test_bonifico_con_copertura(conto4):
    a = conto4.ContoCorrente("A", 1, 100)
    b = conto4.ContoCorrente("B", 2, 0)
    conto4.Gestore.bonifico(a, b, 30)
    assert a._ContoCorrente__saldo == 70    # name mangling: __saldo diventa _ContoCorrente__saldo
    assert b._ContoCorrente__saldo == 30


def test_preleva_rifiutato_restituisce_zero(conto4):
    a = conto4.ContoCorrente("A", 1, 100)
    assert a.preleva(500) == 0
    assert a._ContoCorrente__saldo == 100


@pytest.mark.xfail(strict=True, reason="bug noto: senza copertura il destinatario riceve comunque i soldi")
def test_bonifico_senza_copertura_non_crea_denaro(conto4):
    a = conto4.ContoCorrente("A", 1, 10)
    b = conto4.ContoCorrente("B", 2, 0)
    conto4.Gestore.bonifico(a, b, 1000)
    totale = a._ContoCorrente__saldo + b._ContoCorrente__saldo
    assert totale == 10   # in realtà vale 1010: mille euro creati dal nulla
