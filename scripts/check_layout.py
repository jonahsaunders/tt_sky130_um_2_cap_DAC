from pathlib import Path
import json, re, hashlib
import klayout.db as db
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

p=Path(__file__).resolve().parents[1];w=p/'layout'
ly=db.Layout();ly.read(str(p/'gds/tt_um_jonah_suarez_dac.gds'));top=ly.top_cell()
print('bbox',top.dbbox(),'dbu',ly.dbu)
fig,ax=plt.subplots(figsize=(8,11),facecolor='#111b2b');ax.set_facecolor('#111b2b')
layers=[(64,20,'#397d80',.6),(65,20,'#cf826c',.7),(66,20,'#eda64c',.8),(67,20,'#b4b4b4',.9),(68,20,'#73c7e8',.6),(69,20,'#e7849c',.7),(70,20,'#9e87d7',.8),(89,44,'#cfb571',.85),(71,20,'#78c8b3',.7)]
for num,dt,col,alpha in layers:
    idx=ly.find_layer(num,dt)
    if idx is None:continue
    polygons=[]
    for s in db.Region(top.begin_shapes_rec(idx)).each_merged():
        polygons.append([(q.x*ly.dbu,q.y*ly.dbu) for q in s.each_point_hull()])
    ax.add_collection(PolyCollection(polygons,facecolors=col,edgecolors=col,linewidths=.12,alpha=alpha))
ax.set_xlim(-2,163);ax.set_ylim(-2,228);ax.set_aspect('equal');ax.tick_params(colors='#b4c1d3',labelsize=9)
for spine in ax.spines.values():spine.set_color('#5b6d83')
ax.set_xlabel('µm',color='#b4c1d3');ax.set_ylabel('µm',color='#b4c1d3')
ax.set_title('Suarez two-capacitor DAC · SKY130 · 1 × 2 tiles',color='white',pad=15)
fig.tight_layout();fig.savefig(p/'layout/suarez_dac_layout.png',dpi=220)
pl=json.loads((w/'placement.json').read_text());banks={}
for n in ['SAMPLE','HOLD']:
    pts=np.array([[d['x'],d['y']] for d in pl['capacitors'] if d['bank']==n]);banks[n]={'units':len(pts),'centroid_um':pts.mean(0).tolist()}
urpm=[]
for c in ly.each_cell():
    if not c.name.startswith('dev_res'):continue
    r=db.Region(c.begin_shapes_rec(ly.layer(79,20)))
    urpm.append({'cell':c.name,'width_um':r.bbox().width()*ly.dbu,'height_um':r.bbox().height()*ly.dbu})
print('URPM',urpm)
present_m5=not db.Region(top.begin_shapes_rec(ly.layer(72,20)) ).is_empty()
geometry={'macro_um':[161,225.76],'bbox_um':[top.dbbox().left,top.dbbox().bottom,top.dbbox().right,top.dbbox().top],'metal5_present':present_m5,'capacitor_banks':banks,'resistor_implants':urpm,'gds_sha256':hashlib.sha256((p/'gds/tt_um_jonah_suarez_dac.gds').read_bytes()).hexdigest()}
assert not present_m5
assert banks['SAMPLE']['centroid_um']==banks['HOLD']['centroid_um']
assert all(r['width_um']>=1.27 for r in urpm)
(p/'verification/layout_geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
pex=p/'netlist/tt_um_jonah_suarez_dac.pex.spice'
if not pex.exists():
    print('PEX files',list(pex.parent.glob('*')));raise SystemExit()
txt=pex.read_text();join=re.sub(r'\n\+', ' ',txt)
line=next(x for x in join.splitlines() if x.lower().startswith('.subckt tt_um_jonah_suarez_dac_pex '))
ports=line.split()[2:]
tb=(p/'sim/transfer_tt.spice').read_text()
tb=tb.replace(str(p/'netlist/tt_um_jonah_suarez_dac.spice'),str(pex))
map={'VGND':'0','VDPWR':'vdd','ua[0]':'hi','ua[1]':'out','ua[2]':'lo','ui_in[0]':'h','ui_in[1]':'l','ui_in[2]':'s'}
tb=re.sub(r'^XDUT .+$','XDUT '+' '.join(map.get(n,'0') for n in ports)+' tt_um_jonah_suarez_dac_pex',tb,flags=re.M)
tb=tb.replace('verification/transfer_tt.txt','verification/transfer_pex_tt.txt')
(p/'sim/transfer_pex_tt.spice').write_text(tb)
print('PEX ports',ports)
