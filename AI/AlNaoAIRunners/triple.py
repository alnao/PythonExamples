"""Utility: triple a number.

Provides triple(n) which returns 3 * n.
"""
from typing import Union

Number = Union[int, float]

def triple(n: Number) -> Number:
    """Return three times the given numeric value.

    Args:
        n: An integer or float.

    Returns:
        The value 3 * n.
    """
    return 3 * n


if __name__ == "__main__":
    import sys
    try:
        val = float(sys.argv[1])
    except Exception:
        print("Usage: python triple.py <number>")
    else:
        print(triple(val))
