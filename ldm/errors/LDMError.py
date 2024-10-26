import sys


def error(message: str):
    print(f"Error: {message}", file=sys.stderr)
    exit()