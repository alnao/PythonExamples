def doppio(n):
    """Return the double of n."""
    return n * 2


def triplo(n):
    """Return the triple of n."""
    return n * 3


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python matematica.py <number>")
        sys.exit(1)

    try:
        val = float(sys.argv[1])
    except ValueError:
        print("Input must be a number")
        sys.exit(1)

    result = doppio(val)
    # Print as int when whole number for cleaner output
    if isinstance(result, float) and result.is_integer():
        print(int(result))
    else:
        print(result)
