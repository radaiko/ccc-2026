import sys,re
sys.path.insert(0,'/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026')
from levels.level6.candidates.astra import cases, board, ring, DIRS, NB
from collections import Counter
def sim_ticks(r,pat,prog):
    g=board(r);h,w=2*r+1,4*r+1;rg=ring(r);m=len(rg)
    pc=[(y,x) for y in range(h) for x in range(w) if pat[y][x]=='M'];ps=set(pc)
    halo={(y+dy,x+dx) for y,x in pc for dy,dx in NB if (y+dy,x+dx) not in ps and 0<=y+dy<h and 0<=x+dx<w}
    pos=[0,r,2*r,3*r,4*r,5*r];act=[False]*6;ticks=[]
    for t,line in enumerate(prog):
        for e,ins in enumerate(line):
            if ins=='F':pos[e]=(pos[e]+1)%m
            elif ins=='B':pos[e]=(pos[e]-1)%m
            elif ins=='T':act[e]=not act[e]
        cnt={}
        for e in range(6):
            if not act[e]:continue
            dy,dx=DIRS[e];y,x=rg[pos[e]];y+=dy;x+=dx
            while 0<=y<h and 0<=x<w and g[y][x] in 'OM':
                cnt[(y,x)]=cnt.get((y,x),0)+1;y+=dy;x+=dx
        for (y,x),k in cnt.items():
            if k==2:g[y][x]='M'
            elif k>=3:g[y][x]='O'
        if all(g[y][x]=='M' for y,x in pc) and not any(g[y][x]=='M' for y,x in halo):
            for y,x in pc:g[y][x]='O'
            ticks.append(t+1)
    return ticks
name=sys.argv[1]
text=open(f'data/in_level-6_{name}.txt').read()
out=open(f'runs/opus/out_level-6_{name}.txt').read()
blocks=re.split(r'\n\s*\n',out.strip())
tot_first=0;tot_rest=0;tot_tail=0;kc=Counter()
for i,((r,pat,c),b) in enumerate(zip(cases(text),blocks)):
    prog=[l.split() for l in b.splitlines()]
    t=sim_ticks(r,pat,prog)
    P=sum(row.count('M') for row in pat)
    gaps=[b-a for a,b in zip(t,t[1:])]
    tot_first+=t[0]; tot_rest+=t[c-1]-t[0]; tot_tail+=len(prog)-t[c-1]
    if c>1: kc[round((t[c-1]-t[0])/(c-1),1)]+=1
    if len(sys.argv)>2: print(i,r,P,c,len(prog),t[0],gaps)
print(name,'first',tot_first,'rest',tot_rest,'tail',tot_tail)
print(sorted(kc.items()))
