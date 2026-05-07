def double(n):
    """
    Return double of n.
    Works for numbers that support multiplication by 2.
    """
    return n * 2


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        try:
            x = float(sys.argv[1])
        except ValueError:
            print("Invalid number")
        else:
            print(double(x))
    else:
        print("Usage: python double.py <number>")
