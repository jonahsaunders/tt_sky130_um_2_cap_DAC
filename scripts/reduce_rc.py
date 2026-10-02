"""Exactly eliminate capacitance-free internal resistor nodes by star-mesh reduction."""
from pathlib import Path
from collections import defaultdict
import re,json,sys,heapq

source=Path(sys.argv[1]);target=Path(sys.argv[2]);text=re.sub(r'\n\+', ' ',source.read_text());keep=[];protected=set();edges={};graph=defaultdict(dict)
def value(t):
    m=re.fullmatch(r'([+-]?[\d.]+(?:[eE][+-]?\d+)?)([a-zA-Z]*)',t);assert m,t
    return float(m[1])*{'':1,'m':1e-3,'k':1e3,'meg':1e6,'u':1e-6,'n':1e-9}.get(m[2].lower(),1)
def add(a,b,g):
    if a==b:return
    graph[a][b]=graph[a].get(b,0)+g;graph[b][a]=graph[b].get(a,0)+g
for line in text.splitlines():
    t=line.split()
    if t and t[0].startswith('R'):
        assert len(t)==4,t;res=value(t[3]);assert res>0,t;add(t[1],t[2],1/res)
    else:
        keep.append(line)
        if not t:continue
        if t[0].lower()=='.subckt':protected.update(t[2:])
        elif t[0][0].upper()=='C':protected.update(t[1:3])
        elif t[0][0].upper()=='X':
            ix=next(i for i,x in enumerate(t) if x.startswith('sky130_'));protected.update(t[1:ix])
before=sum(len(v) for v in graph.values())//2;eliminated=0
queue=[(len(nb),n) for n,nb in graph.items() if n not in protected];heapq.heapify(queue)
while queue:
    degree,n=heapq.heappop(queue)
    if n not in graph or n in protected or len(graph[n])!=degree:continue
    if degree>8:continue
    nb=list(graph[n].items());total=sum(g for _,g in nb)
    for b,g in nb:del graph[b][n]
    del graph[n];eliminated+=1
    for i,(b,g) in enumerate(nb):
        for c,h in nb[i+1:]:add(b,c,g*h/total)
    for b,_ in nb:
        if b not in protected:heapq.heappush(queue,(len(graph[b]),b))
res=[];seen=set()
for n,nb in graph.items():
    for b,g in nb.items():
        key=tuple(sorted([n,b]))
        if key in seen:continue
        seen.add(key);res.append(f'RRED{len(res)} {n} {b} {1/g:.14g}')
end=next(i for i,line in enumerate(keep) if line.lower().startswith('.ends'))
keep[end:end]=['* Exact static resistor-node elimination; every capacitive/device/port node preserved.']+res
target.write_text('\n'.join(keep)+'\n')
report={'source':str(source),'target':str(target),'resistors_before':before,'resistors_after':len(res),'eliminated_capacitance_free_nodes':eliminated,'protected_nodes':len(protected),'approximation':'none; exact star-mesh at all frequencies for removed nodes without capacitance'}
target.with_suffix('.reduction.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
