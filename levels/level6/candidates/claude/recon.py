"""Reconstruct level-6 inputs (pattern + count) from output programs.

At the first submission tick the pattern is exactly one connected M component.
For each radius candidate and each (tick, component) before any submission,
simulate the whole program with P = component; keep candidates whose last tick
submits. Report ambiguity.
"""
import sys
sys.path.insert(0, '/home/user/ccc-2026/levels/level6')
from validator import _Geom, FIRE_OV

def parse_out(text):
    progs, cur = [], None
    for line in text.replace('\r', '').split('\n'):
        if not line.strip():
            cur = None
            continue
        if cur is None:
            cur = []
            progs.append(cur)
        cur.append(line.split())
    return progs

GEOMS = {}
def geom(R):
    if R not in GEOMS:
        GEOMS[R] = _Geom(R)
    return GEOMS[R]

def sim(g, prog, pset, halo, stop_first=False):
    """Returns (list of submission ticks, boards per tick (before clearing) if pset None)."""
    grid = set()
    plen = len(g.perimeter)
    idx = [t * g.edge for t in range(6)]
    active = [False] * 6
    subs = []
    boards = []
    for ti, line in enumerate(prog):
        for t in range(6):
            ins = line[t]
            if ins == 'F':
                idx[t] = (idx[t] + 1) % plen
            elif ins == 'B':
                idx[t] = (idx[t] - 1) % plen
            elif ins == 'T':
                active[t] = not active[t]
        cnt = {}
        for t in range(6):
            if active[t]:
                for k in g.ray[idx[t]][t]:
                    cnt[k] = cnt.get(k, 0) + 1
        for k, n in cnt.items():
            if n == 2:
                grid.add(k)
            elif n >= 3:
                grid.discard(k)
        if pset is None:
            boards.append(frozenset(grid))
            continue
        if pset <= grid and not (halo & grid):
            grid -= pset
            subs.append(ti)
    return subs, boards

def comps(g, cells):
    cols = g.cols
    cells = set(cells)
    out = []
    while cells:
        s = cells.pop()
        comp = {s}
        st = [s]
        while st:
            k = st.pop()
            r, c = divmod(k, cols)
            for dc, dr in FIRE_OV:
                kk = (r + dr) * cols + (c + dc)
                if kk in cells:
                    cells.remove(kk)
                    comp.add(kk)
                    st.append(kk)
        out.append(frozenset(comp))
    return out

def halo_of(g, pset):
    cols = g.cols
    h = set()
    for k in pset:
        r, c = divmod(k, cols)
        for dc, dr in FIRE_OV:
            rr, cc = r + dr, c + dc
            if 0 <= rr < g.rows and 0 <= cc < cols and g.playable[rr * cols + cc]:
                kk = rr * cols + cc
                if kk not in pset:
                    h.add(kk)
    return frozenset(h)

def candidates(prog, radii):
    res = []
    for R in radii:
        g = geom(R)
        # first submission state is independent of P; simulate without submissions
        _, boards = sim(g, prog, None, None)
        seen = set()
        for t, b in enumerate(boards):
            for C in comps(g, b):
                if len(C) < 2 or C in seen:
                    continue
                seen.add(C)
                h = halo_of(g, C)
                subs, _ = sim(g, prog, C, h)
                if subs and subs[0] == t and subs[-1] == len(prog) - 1:
                    res.append((R, C, len(subs), t))
    return res

def render(g, R, pset):
    lines = []
    for i in range(2 * R + 1):
        row = []
        for c in range(g.cols):
            k = i * g.cols + c
            if g.playable[k]:
                row.append('M' if k in pset else 'O')
            else:
                row.append('?')
        lines.append(row)
    # border cells: per RULES formula
    out = []
    for i in range(2 * R + 1):
        kk = abs(i - R)
        s = ['-'] * (4 * R + 1)
        for j in range(2 * R + 1 - kk):
            c = kk + 2 * j
            k = i * g.cols + c
            if g.playable[k]:
                s[c] = 'M' if k in pset else 'O'
            else:
                s[c] = '*'
        out.append(''.join(s))
    return out

RADII = {'0-example': range(3, 6), '1-small': [3], '2-medium': range(3, 6), '3-large': range(6, 9),
         '4-enormous': range(9, 13)}

if __name__ == '__main__':
    name, outpath, inpath = sys.argv[1], sys.argv[2], sys.argv[3]
    progs = parse_out(open(outpath).read())
    blocks = []
    amb = 0
    for pi, prog in enumerate(progs):
        cs = candidates(prog, RADII[name])
        if len(cs) != 1:
            amb += 1
            print('program', pi, 'candidates', [(R, len(C), n, t) for R, C, n, t in cs], file=sys.stderr)
        if not cs:
            raise SystemExit('no candidate for program %d' % pi)
        # prefer earliest first submission, then largest pattern
        cs.sort(key=lambda x: (x[3], -len(x[1])))
        R, C, n, t = cs[0]
        g = geom(R)
        blocks.append('%d %d %d %d\n' % (R, 2 * R + 1, 4 * R + 1, n) + '\n'.join(render(g, R, C)))
    open(inpath, 'w').write('%d\n' % len(progs) + '\n\n'.join(blocks) + '\n')
    print(name, len(progs), 'programs, ambiguous', amb, file=sys.stderr)
