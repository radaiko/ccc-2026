"""Count>=2 patterns: build the next copy by running the first copy's emitter configurations backwards
(enormous agent).  Moves are reversible (F<->B, T<->T); when no relevant cell is ever hit 3 times and no halo
matter appears, the matter painted is order independent, so the reversed run rebuilds the pattern and the
leading travel ticks of copy 1 become unnecessary at the end of copy 2.
Usage: python3 rev_e.py <input-name> [--only i,j]"""
import sys

from harness import LEVEL, cases, load_best, save_best, valid
from resuf_e import sub_ticks

INV = {'F': 'B', 'B': 'F', 'T': 'T', '-': '-'}


def inv(line):
    return ' '.join(INV[c] for c in line.split())


def candidates(prog, t1):
    rev = [inv(prog[k]) for k in range(t1 - 1, 0, -1)]  # configs C_{t1-1} .. C_1
    yield prog[:t1] + rev
    yield prog[:t1] + ['- - - - - -'] + rev


def main():
    args = sys.argv[1:]
    only = None
    if '--only' in args:
        i = args.index('--only')
        only = [int(x) for x in args[i + 1].split(',')]
        del args[i:i + 2]
    name = args[0]
    cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    for i in (only if only is not None else range(len(cs))):
        r, pat, count = cs[i]
        if count < 2:
            continue
        st = sub_ticks(r, pat, best[i])
        t1 = st[0]
        bestc = None
        for cand in candidates(best[i], t1):
            # copies beyond 2: keep appending reversed / forward segments alternately
            st2 = sub_ticks(r, pat, cand)
            if len(st2) >= count:
                c = cand[:st2[count - 1]]
                if bestc is None or len(c) < len(bestc):
                    bestc = c
        if bestc and len(bestc) < len(best[i]) and valid(r, pat, count, bestc):
            print('pattern %d: %d -> %d (copy1 %d)' % (i, len(best[i]), len(bestc), t1), flush=True)
            best[i] = bestc
            save_best(name, best)
        else:
            print('pattern %d: %d, reverse %s (copy1 %d)' % (i, len(best[i]), len(bestc) if bestc else 'FAIL', t1),
                  flush=True)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))))


if __name__ == '__main__':
    main()
