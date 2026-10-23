import sys
sys.path.insert(0,'/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026/levels/level6/candidates/opus')
from harness import load_best, cases, LEVEL
from levels.level6.candidates.astra import board, ring, DIRS, NB
for name in ['2-medium','3-large','4-enormous']:
    cs=list(cases((LEVEL/'data'/('in_level-6_%s.txt'%name)).read_text())); b=load_best(name)
    tot=travel=zero=one=tail=0; cells=0; copies=0
    for (r,pat,c),prog in zip(cs,b):
        prog=[l.split() for l in prog]
        g=board(r);h,w=2*r+1,4*r+1;rg=ring(r);m=len(rg)
        pc=[(y,x) for y in range(h) for x in range(w) if pat[y][x]=='M'];ps=set(pc)
        pos=[0,r,2*r,3*r,4*r,5*r];act=[False]*6;pm_prev=0;started=False
        cells+=len(pc)*c; copies+=c
        segment=[]
        for line in prog:
            tot+=1
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
            pm=sum(g[y][x]=='M' for y,x in pc)
            gain=pm-pm_prev
            if not started and gain<=0: travel+=1
            else:
                started=True
                if gain<=0: zero+=1
                elif gain==1: one+=1
            segment.append(gain)
            pm_prev=pm
            if pm==len(pc):
                # tail = ticks spent on the last 10% of cells of this copy
                need=len(pc)*0.9;s=0;k=0
                for k,gv in enumerate(segment):
                    s+=gv
                    if s>=need: break
                tail+=len(segment)-1-k; segment=[]
                for y,x in pc:g[y][x]='O'
                pm_prev=0
    print('%-10s lines %5d | start travel %4d | zero-gain %4d | one-cell %4d | last-10%%-of-cells ticks %4d | avg cells/tick %.1f'%(name,tot,travel,zero,one,tail,cells/tot))
