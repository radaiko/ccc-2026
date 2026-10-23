import sys
sys.path.insert(0,'/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026/levels/level6/candidates/opus')
from harness import load_best, cases, LEVEL
from levels.level6.candidates.astra import board, ring, DIRS, NB
name=sys.argv[1]; idxs=[int(x) for x in sys.argv[2].split(',')]; PF=sys.argv[3] if len(sys.argv)>3 else None
cs=list(cases((LEVEL/'data'/('in_level-6_%s.txt'%name)).read_text())); b=load_best(name)
for i in idxs:
    r,pat,c=cs[i]; prog=[l.split() for l in (open(PF).read().split(chr(10)) if PF else b[i]) if l.strip()]
    g=board(r);h,w=2*r+1,4*r+1;rg=ring(r);m=len(rg)
    pc=[(y,x) for y in range(h) for x in range(w) if pat[y][x]=='M'];ps=set(pc)
    halo={(y+dy,x+dx) for y,x in pc for dy,dx in NB if (y+dy,x+dx) not in ps and 0<=y+dy<h and 0<=x+dx<w and g[y+dy][x+dx] in 'OM'}
    pos=[0,r,2*r,3*r,4*r,5*r];act=[False]*6;out=[]
    for line in prog:
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
        pm=sum(g[y][x]=='M' for y,x in pc);hm=sum(g[y][x]=='M' for y,x in halo)
        sub=pm==len(pc) and hm==0
        out.append('%d/%d%s'%(pm,hm,'*' if sub else ''))
        if sub:
            for y,x in pc:g[y][x]='O'
    print(i,'r',r,'P',len(pc),'c',c,'L',len(prog)); print(' '.join(out))
