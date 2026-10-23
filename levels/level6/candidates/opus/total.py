"""Print the merged best total over the four upload inputs and update levels/level6/output/ when better.
Every program is re-verified by simulation before an output file is replaced."""
import re
from harness import LEVEL, cases, load_best, save_best, valid

OUT = LEVEL / 'output'
tot = 0
for n in ['1-small', '2-medium', '3-large', '4-enormous']:
    b = load_best(n)
    save_best(n, b)
    s = sum(map(len, b))
    tot += s
    f = OUT / ('out_level-6_%s.txt' % n)
    cur = None
    if f.exists():
        cur = sum(len(x.splitlines()) for x in re.split(r'\n\s*\n', f.read_text().strip()))
    if cur is None or s < cur:
        cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % n)).read_text()))
        assert len(cs) == len(b)
        assert all(valid(r, p, c, prog) for (r, p, c), prog in zip(cs, b)), n
        f.write_text('\n\n'.join('\n'.join(p) for p in b) + '\n')
        print(n, s, '(output updated from %s)' % cur)
    else:
        print(n, s, '(output has %s)' % cur)
print('TOTAL', tot)
