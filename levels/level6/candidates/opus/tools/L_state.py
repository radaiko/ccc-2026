import sys
sys.path.insert(0,'/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026/levels/level6/candidates/opus')
from harness import cases, LEVEL
from levels.level6.candidates.astra import board, ring, DIRS, NB
name,i,pf,T=sys.argv[1],int(sys.argv[2]),sys.argv[3],int(sys.argv[4])
r,pat,c=list(cases((LEVEL/'data'/('in_level-6_%s.txt'%name)).read_text()))[i]
prog=[l.split() for l in open(pf) if l.strip()]
g=board(r);h,w=2*r+1,4*r+1;rg=ring(r);m=len(rg)
pc=[(y,x) for y in range(h) for x in range(w) if pat[y][x]=='M'];ps=set(pc)
halo={(y+dy,x+dx) for y,x in pc for dy,dx in NB if (y+dy,x+dx) not in ps and 0<=y+dy<h and 0<=x+dx<w and g[y+dy][x+dx] in 'OM'}
pos=[0,r,2*r,3*r,4*r,5*r];act=[False]*6
def cells(e,p):
    dy,dx=DIRS[e];y,x=rg[p];y+=dy;x+=dx;out=[]
    while 0<=y<h and 0<=x<w and g[y][x] in 'OM': out.append((y,x));y+=dy;x+=dx
    return out
for t,line in enumerate(prog[:T]):
    for e,ins in enumerate(line):
        if ins=='F':pos[e]=(pos[e]+1)%m
        elif ins=='B':pos[e]=(pos[e]-1)%m
        elif ins=='T':act[e]=not act[e]
    cnt={}
    for e in range(6):
        if not act[e]:continue
        for q in cells(e,pos[e]): cnt[q]=cnt.get(q,0)+1
    for q,k in cnt.items():
        if k==2:g[q[0]][q[1]]='M'
        elif k>=3:g[q[0]][q[1]]='O'
    if all(g[y][x]=='M' for y,x in pc) and not any(g[y][x]=='M' for y,x in halo):
        for y,x in pc:g[y][x]='O'
print('pos',pos,'act',act)
miss=[q for q in pc if g[q[0]][q[1]]!='M']
for y in range(h):
    row=''
    for x in range(w):
        ch=g[y][x]
        if (y,x) in ps: row+= 'M' if ch=='M' else '?'
        elif (y,x) in halo: row+= 'h' if ch!='M' else '!'
        else: row+= {'O':'.','M':'m'}.get(ch,ch)
    print(row)
for q in miss:
    ds=[]
    for e in range(6):
        best=None
        for p in range(m):
            if q in cells(e,p):
                d=min(abs(p-pos[e]),m-abs(p-pos[e]))+(0 if act[e] else 1); best=(d,p)
        ds.append(best)
    print('missing',q,ds)
