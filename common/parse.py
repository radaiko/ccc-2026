import re

_INT = re.compile(r"-?\d+")
_FLOAT = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def lines(text: str) -> list:
    """Lines without trailing whitespace; trailing newlines dropped."""
    return [l.rstrip() for l in text.rstrip("\n").split("\n")]


def ints(s: str) -> list:
    return [int(x) for x in _INT.findall(s)]


def floats(s: str) -> list:
    return [float(x) for x in _FLOAT.findall(s)]


def tokens(text: str) -> list:
    """All whitespace-separated tokens; use iter(tokens(text)) + next() for stream parsing."""
    return text.split()


def blocks(text: str) -> list:
    """Split on blank lines into lists of lines."""
    return [b.split("\n") for b in text.strip().split("\n\n")]
