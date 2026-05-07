#!/usr/bin/env python3
"""Calcola area di un rombo.

Supporta due modalità di input:
 - diagonali: --d1 <val> --d2 <val>
 - lato + angolo (gradi): --side <val> --angle <deg>

Esempi:
    python area_rombo.py --d1 10 --d2 8
    python area_rombo.py --side 5 --angle 60
"""

import argparse
import math
import sys


def area_from_diagonals(d1: float, d2: float) -> float:
    """Area = (d1 * d2) / 2"""
    return (d1 * d2) / 2.0


def area_from_side_angle(side: float, angle_deg: float) -> float:
    """Area = side^2 * sin(angle)
    angle in degrees
    """
    return side * side * math.sin(math.radians(angle_deg))


def main():
    p = argparse.ArgumentParser(description="Calcola area di un rombo.")
    p.add_argument('--d1', type=float, help='diagonale 1')
    p.add_argument('--d2', type=float, help='diagonale 2')
    p.add_argument('--side', type=float, help='lunghezza lato')
    p.add_argument('--angle', type=float, help='angolo interno in gradi (tra 0 e 180)')
    args = p.parse_args()

    if args.d1 is not None or args.d2 is not None:
        if args.d1 is None or args.d2 is None:
            p.error('Se si usa --d1 occorre anche --d2')
        area = area_from_diagonals(args.d1, args.d2)
    else:
        if args.side is None or args.angle is None:
            p.error('Usa o --d1 e --d2, oppure --side e --angle')
        if not (0 < args.angle < 180):
            p.error('--angle deve essere compreso tra 0 e 180 (gradi)')
        area = area_from_side_angle(args.side, args.angle)

    # Stampa risultato con 6 decimali
    print(f"{area:.6f}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'Errore: {e}', file=sys.stderr)
        sys.exit(1)
