"""SAT (satcyc.Model) search for a (K, m) cycle through a FIXED anchor configuration: from (anchor, empty
matter), K ticks, m submissions, the last on tick K exactly at the anchor again. Anchors = submission
configurations of the current best program (they already have a prefix), so the result is spliced directly.
Usage: python3 satanchor.py <name> <idx> <m> <K> [timeout_ms] [maxAnchors]"""
import sys
from harness import LEVEL, cases, load_best, save_best, valid
from retcyc import sim, assemble
import satcyc
import z3sat


def offs(r, e, p):
    return (p - e * r + 3 * r) % (6 * r) - 3 * r


def anchored(r, pat, K, m, anchor, tmo, rad=0, freeact=False, want_cfg=False, freeE=()):
    """rad > 0: the anchor may lie within +-rad rail steps per emitter (freeact: any on/off state)."""
    pos, am = anchor
    md = satcyc.Model(r, pat)
    md.sym = False
    off = [offs(r, e, pos[e]) for e in range(6)]
    if any(abs(off[e]) > r for e in range(6) if e not in freeE):
        return 'skip'
    cs, Ss = satcyc.build_cycle(md, K, m)
    for e in range(6):
        if e in freeE:
            continue
        p, a = cs[-1][e]
        md.add([p[md.offs.index(o)] for o in range(off[e] - rad, off[e] + rad + 1) if -r <= o <= r])
        if not freeact:
            md.add([a if am >> e & 1 else -a])
    res = z3sat.solve(md.nv, md.cl, tmo)
    if res is None or res == 'unknown':
        return res
    cfg = [md.decode(res, c) for c in cs]
    lines = satcyc.lines_between([cfg[-1]] + cfg)
    if want_cfg:
        anc = (tuple((e * r + o) % (6 * r) for e, (o, a) in enumerate(cfg[-1])),
               sum(1 << e for e, (o, a) in enumerate(cfg[-1]) if a))
        return lines, anc
    return lines


def main():
    name, i, m, K = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    tmo = int(sys.argv[5]) if len(sys.argv) > 5 else 60000
    maxa = int(sys.argv[6]) if len(sys.argv) > 6 else 4
    cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
    r, pat, count = cs[i]
    best = load_best(name)
    prog = best[i]
    subs = sim(r, pat, prog)
    seen = []
    for j, (t, pos, am) in enumerate(subs[:count - 1]):
        if (pos, am) in [s[0] for s in seen]:
            continue
        seen.append(((pos, am), t))
    for anchor, t in seen[:maxa]:
        res = anchored(r, pat, K, m, anchor, tmo)
        print('anchor t=%d: %s' % (t, res if isinstance(res, str) else 'UNSAT' if res is None else 'SAT'),
              flush=True)
        if isinstance(res, list):
            cand = assemble(r, pat, count, prog[:t], res)
            print('  assembled', len(cand) if cand else None, 'best', len(prog), flush=True)
            if cand and len(cand) < len(prog) and valid(r, pat, count, cand):
                best = load_best(name)
                best[i] = cand
                save_best(name, best)
                print('pattern %d: %d -> %d' % (i, len(prog), len(cand)), flush=True)
                prog = cand


if __name__ == '__main__':
    main()
