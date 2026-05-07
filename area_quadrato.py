"""Calcolo area quadrato

Funzione semplice e CLI minimale.
"""

def area_quadrato(lato):
    """Ritorna area del quadrato dato il lato. Accetta int/float."""
    try:
        v = float(lato)
    except (TypeError, ValueError):
        raise ValueError("lato deve essere numerico")
    return v * v


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        try:
            lato = float(sys.argv[1])
        except ValueError:
            print("Errore: lato non numerico")
            sys.exit(1)
    else:
        try:
            lato = float(input("Lato: "))
        except Exception:
            print("Errore: lato non numerico")
            sys.exit(1)
    print(area_quadrato(lato))
