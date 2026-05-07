"""Modulo matematica
Fornisce le funzioni `doppio(n)` e `triplo(n)` che ritornano il doppio e il triplo di un numero.
Esempio CLI: python matematica.py 3  -> stampa 6
"""

def doppio(n):
    """Restituisce il doppio di n. Accetta int o float o valori convertibili a float.

    Raises:
        TypeError: se n non è un numero o non è convertibile a float.
    """
    if isinstance(n, (int, float)):
        return n * 2
    try:
        val = float(n)
    except Exception:
        raise TypeError("doppio: valore non numerico")
    return val * 2


def triplo(n):
    """Restituisce il triplo di n. Accetta int o float o valori convertibili a float.

    Raises:
        TypeError: se n non è un numero o non è convertibile a float.
    """
    if isinstance(n, (int, float)):
        return n * 3
    try:
        val = float(n)
    except Exception:
        raise TypeError("triplo: valore non numerico")
    return val * 3


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calcola il doppio di un numero.")
    parser.add_argument("number", nargs="?", help="Numero da raddoppiare", type=float)
    args = parser.parse_args()

    if args.number is None:
        try:
            s = input("Inserisci un numero: ")
            num = float(s)
        except Exception:
            print("Input non valido")
            raise SystemExit(1)
    else:
        num = args.number

    res = doppio(num)
    # Stampa come intero se il risultato è intero
    if isinstance(res, float) and res.is_integer():
        print(int(res))
    else:
        print(res)
