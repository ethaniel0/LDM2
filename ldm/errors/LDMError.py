from __future__ import annotations
import sys


def print_error(message: str):
    print(f"Error: {message}", file=sys.stderr)
    exit()


class ParsingTracebackError(Exception):
    def __init__(self, message: str, child: ParsingTracebackError | None = None):
        self.message = message
        self.child = child

    def __str__(self, indent=0):
        if self.child is None:
            return f"{'  ' * indent}{self.message}"
        return f"{'  ' * indent}{self.message}\n{self.child.__str__(indent + 1)}"
