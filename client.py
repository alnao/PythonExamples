#!/usr/bin/env python3
"""
client.py - semplice client che ritorna il doppio di un numero
Usage:
  python client.py 5
  echo 5 | python client.py
"""
import sys


def double(x):
    """Ritorna doppio di x. Accetta stringa, int, float."""
    try:
        if isinstance(x, (int, float)):
            return x * 2
        s = str(x).strip()
        # supporta numeri con punto decimale
        if s == '':
            raise ValueError
        if any(c in s for c in ('.', 'e', 'E')):
            return float(s) * 2
        return int(s) * 2
    except Exception:
        raise ValueError("Input non numerico")


def triple(x):
    """Ritorna triplo di x. Accetta stringa, int, float."""
    try:
        if isinstance(x, (int, float)):
            return x * 3
        s = str(x).strip()
        # supporta numeri con punto decimale
        if s == '':
            raise ValueError
        if any(c in s for c in ('.', 'e', 'E')):
            return float(s) * 3
        return int(s) * 3
    except Exception:
        raise ValueError("Input non numerico")


def main():

    if len(sys.argv) > 1:
        val = sys.argv[1]
    else:
        data = sys.stdin.read().strip()
        if not data:
            print("Usage: python client.py <numero>", file=sys.stderr)
            sys.exit(2)
        val = data.split()[0]
    try:
        res = double(val)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    # stampa risultato senza extra
    if isinstance(res, float) and res.is_integer():
        # mostra come intero quando appropriato
        print(int(res))
    else:
        print(res)


if __name__ == "__main__":
    main()
