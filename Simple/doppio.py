"""Utility function to create the double of a number."""

def crea_doppio(n):
    """Return the double of n.

    Parameters:
    n (int|float): number to double

    Returns:
    int|float: doubled value
    """
    try:
        return n * 2
    except TypeError:
        raise TypeError("crea_doppio: input must be a number")
