"""Fixture condivise: pytest le trova da solo e le passa ai test che le chiedono per nome."""
from datetime import date

import pytest

from conto import ContoCorrente
from expense_manager import GestoreSpese, Spesa


@pytest.fixture
def alberto() -> ContoCorrente:
    # ogni test riceve un conto nuovo: nessuno stato condiviso tra i test
    return ContoCorrente("Alberto", 1, 40000)


@pytest.fixture
def valentina() -> ContoCorrente:
    return ContoCorrente("Valentina", 2, 3000)


@pytest.fixture
def crea_spesa():
    """Fixture "factory": restituisce una funzione con valori di default sensati."""
    def _crea(importo=10.0, descrizione="caffè", giorno=date(2026, 1, 15), categoria="varie"):
        return Spesa(giorno, descrizione, importo, categoria)
    return _crea


@pytest.fixture
def gestore_con_spese(crea_spesa) -> GestoreSpese:
    # una fixture può usarne un'altra
    return GestoreSpese([
        crea_spesa(12.50, "pizza", date(2026, 1, 10), "cibo"),
        crea_spesa(45.00, "benzina", date(2026, 1, 20), "auto"),
        crea_spesa(7.30, "pane", date(2026, 2, 3), "cibo"),
        crea_spesa(60.00, "tagliando", date(2026, 2, 28), "auto"),
    ])
