from common import *  # noqa: F401,F403  (ints, lines, Grid, bfs, ...)


def solve(text: str):
    """Return the output as a string or an iterable of lines."""
    ls = lines(text)
    n = int(ls[0])
    out = []
    for line in ls[1 : n + 1]:
        nums = ints(line)
        out.append(" ".join(map(str, nums)))
    return out
