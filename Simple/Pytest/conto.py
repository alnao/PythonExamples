"""Conti correnti e bonifici: versione testabile di Simple/conto4.py.

Differenze rispetto all'originale, pensate per rendere il codice verificabile:
- i metodi restituiscono valori invece di stampare (la stampa resta solo nella demo);
- gli errori sono eccezioni esplicite invece di "return 0" (che era ambiguo:
  0 poteva voler dire "saldo azzerato" oppure "prelievo rifiutato");
- gli importi sono Decimal, così 0.1 + 0.2 fa davvero 0.3;
- il bonifico è atomico: se il prelievo fallisce, il deposito non avviene
  (nell'originale il destinatario riceveva i soldi anche senza copertura).
"""
from decimal import Decimal, InvalidOperation


class ImportoNonValidoError(ValueError):
    """Importo negativo, nullo o non numerico."""


class SaldoInsufficienteError(Exception):
    """Il conto non ha abbastanza soldi per l'operazione."""


def a_decimal(valore: int | float | str | Decimal) -> Decimal:
    """Converte un importo in Decimal. I float passano da str per evitare 0.1000000000000000055..."""
    if isinstance(valore, bool):
        raise ImportoNonValidoError(f"Importo non valido: {valore!r}")
    try:
        importo = Decimal(str(valore)) if isinstance(valore, float) else Decimal(valore)
    except (InvalidOperation, TypeError) as errore:
        raise ImportoNonValidoError(f"Importo non valido: {valore!r}") from errore
    if not importo.is_finite():
        raise ImportoNonValidoError(f"Importo non valido: {valore!r}")
    return importo


class Conto:
    def __init__(self, nome: str, numero: int):
        if not nome or not nome.strip():
            raise ValueError("Il nome dell'intestatario è obbligatorio")
        self.nome = nome
        self.numero = numero

    def descrizione(self) -> str:
        return f"Conto {self.nome} n.{self.numero}"


class ContoCorrente(Conto):
    def __init__(self, nome: str, numero: int, saldo_iniziale: int | float | str | Decimal = 0):
        super().__init__(nome, numero)
        saldo = a_decimal(saldo_iniziale)
        if saldo < 0:
            raise ImportoNonValidoError("Il saldo iniziale non può essere negativo")
        self._saldo = saldo

    @property
    def saldo(self) -> Decimal:
        """Sola lettura: il saldo cambia solo con preleva/deposita."""
        return self._saldo

    @staticmethod
    def _importo_positivo(importo) -> Decimal:
        valore = a_decimal(importo)
        if valore <= 0:
            raise ImportoNonValidoError(f"L'importo deve essere positivo, ricevuto {valore}")
        return valore

    def preleva(self, importo) -> Decimal:
        valore = self._importo_positivo(importo)
        if valore > self._saldo:
            raise SaldoInsufficienteError(
                f"Saldo insufficiente su {self.nome}: disponibili {self._saldo}, richiesti {valore}"
            )
        self._saldo -= valore
        return self._saldo

    def deposita(self, importo) -> Decimal:
        self._saldo += self._importo_positivo(importo)
        return self._saldo

    def descrizione(self) -> str:
        return f"Conto corrente {self.nome} n.{self.numero} saldo {self._saldo:.2f}"


class Gestore:
    @staticmethod
    def bonifico(sorgente: ContoCorrente, destinazione: ContoCorrente, importo) -> Decimal:
        """Sposta l'importo da un conto all'altro e restituisce il saldo finale della sorgente."""
        if sorgente is destinazione:
            raise ValueError("Sorgente e destinazione devono essere conti diversi")
        valore = ContoCorrente._importo_positivo(importo)
        # prima il prelievo: se fallisce solleva l'eccezione e il deposito non parte
        saldo_sorgente = sorgente.preleva(valore)
        destinazione.deposita(valore)
        return saldo_sorgente


if __name__ == "__main__":
    c1 = ContoCorrente("Alberto", 1, 40000)
    c2 = ContoCorrente("Valentina", 2, 3000)
    print(c1.descrizione())
    print(c2.descrizione())
    Gestore.bonifico(c1, c2, 200)
    print("Bonifico da", c1.nome, "a", c2.nome, "di importo 200")
    print(c1.descrizione())
    print(c2.descrizione())
    try:
        Gestore.bonifico(c2, c1, 1_000_000)
    except SaldoInsufficienteError as errore:
        print("Bonifico rifiutato:", errore)
