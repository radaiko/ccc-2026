import sys,re
sys.path.insert(0,'/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026')
from levels.level6.candidates.astra import cases
from collections import Counter
for name in ['2-medium','3-large','4-enormous']:
    text=open(f'data/in_level-6_{name}.txt').read()
    out=open(f'runs/best/out_level-6_{name}.txt').read()
    blocks=re.split(r'\n\s*\n',out.strip())
    agg=Counter(); n=Counter(); sz=Counter()
    rows=[]
    for (r,pat,c),b in zip(cases(text),blocks):
        L=len(b.splitlines()); P=sum(row.count('M') for row in pat)
        rows.append((r,P,c,L))
        agg[c]+=L; n[c]+=1; sz[c]+=P
    print(name, 'total',sum(x[3] for x in rows))
    for c in sorted(n): print('  count',c,'n',n[c],'lines',agg[c],'avgP',sz[c]/n[c], 'avgL',agg[c]/n[c])
