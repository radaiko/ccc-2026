from common import *


def board(r):
    rows = []
    for i in range(2 * r + 1):
        k = abs(i - r)
        n = 2 * r + 1 - k
        if k == r:
            cells = ['*'] * n
        else:
            cells = ['*'] + ['O'] * (n - 2) + ['*']
        rows.append('-' * k + '-'.join(cells) + '-' * k)
    return rows


def solve(text):
    v = ints(text)
    n = v[0]
    out = []
    for idx, r in enumerate(v[1:1 + n]):
        if idx:
            out.append('')
        out.extend(board(r))
    return out
