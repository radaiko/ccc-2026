"""Row sweeps: emitters a and a+3 on the same line paint it whole (2 hits) one line per tick; the beam
search only controls the four other emitters (punching halo cells with a third hit) and finishes freely.
Usage: python3 sweep.py <input-name> <width> [--only i,j] [beam weights...]"""
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid
sys.path.insert(0, str(LEVEL.parents[1]))
from levels.level6.candidates.astra import DIRS, ring  # noqa: E402


def covering_position(r, e, cell, ring_index):
    y, x = cell
    dy, dx = DIRS[e]
    while (y, x) not in ring_index:
        y -= dy
        x -= dx
    return ring_index[y, x]


def offset(r, e, p):
    return (p - e * r + 3 * r) % (6 * r) - 3 * r


def schedules(r, pat, count):
    cells = [(y, x) for y, row in enumerate(pat) for x, ch in enumerate(row) if ch == 'M']
    ri = {c: i for i, c in enumerate(ring(r))}
    out = []
    for a in range(3):
        b = a + 3
        rows = sorted({(offset(r, a, covering_position(r, a, c, ri)), offset(r, b, covering_position(r, b, c, ri)))
                       for c in cells})
        for order in (rows, rows[::-1]):
            sched = []
            da, db = order[0]
            for t in range(max(abs(da), abs(db))):
                line = ['?'] * 6
                line[a] = ('F' if da > 0 else 'B') if t < abs(da) else '-'
                line[b] = ('F' if db > 0 else 'B') if t < abs(db) else '-'
                sched.append(line)
            line = ['?'] * 6
            line[a] = line[b] = 'T'
            sched.append(line)
            seq = order
            for copy in range(count):
                if copy:
                    line = ['?'] * 6
                    line[a] = line[b] = '-'
                    sched.append(line)
                for (pa, pb), (qa, qb) in zip(seq, seq[1:]):
                    line = ['?'] * 6
                    line[a] = 'F' if qa > pa else 'B' if qa < pa else '-'
                    line[b] = 'F' if qb > pb else 'B' if qb < pb else '-'
                    sched.append(line)
                seq = seq[::-1]
            out.append(['' .join(l) for l in sched])
    return out


def main():
    args = sys.argv[1:]
    only = None
    if '--only' in args:
        i = args.index('--only')
        only = [int(x) for x in args[i + 1].split(',')]
        del args[i:i + 2]
    name, width = args[0], args[1]
    weights = args[2:] or ['3', '1', '0.3', '0.5']
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    tmp = tempfile.mkdtemp()
    jobs = []
    for i in (only if only is not None else range(len(cs))):
        r, pat, count = cs[i]
        for j, s in enumerate(schedules(r, pat, count)):
            path = os.path.join(tmp, '%d_%d.txt' % (i, j))
            with open(path, 'w') as f:
                f.write('\n'.join(s) + '\n')
            jobs.append((i, path))

    def job(arg):
        i, path = arg
        out = subprocess.run([str(HERE / 'beam'), str(inp), str(i), width, '1'] + weights + ['400', path],
                             capture_output=True, text=True).stdout.split('\n')
        return i, [l for l in out if l.strip() and l != 'NONE']

    with ThreadPoolExecutor(os.cpu_count()) as ex:
        for i, prog in ex.map(job, jobs):
            r, pat, count = cs[i]
            if prog and len(prog) < len(best[i]) and valid(r, pat, count, prog):
                print('pattern %d: %d -> %d' % (i, len(best[i]), len(prog)), flush=True)
                best[i] = prog
                save_best(name, best)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))))


if __name__ == '__main__':
    main()
