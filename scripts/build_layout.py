from pathlib import Path
import json, re, subprocess

P=Path(__file__).resolve().parents[1];S=json.loads((P/'design.json').read_text());TOP=S['top']
import tempfile, shutil
(P/'build').mkdir(exist_ok=True)
W=Path(tempfile.mkdtemp(prefix='layout_',dir=P/'build'))
RC='/foss/pdks/sky130A/libs.tech/magic/sky130A.magicrc'
cells={}; t=['drc off']
for d in S['devices']:
    key=(d['model'],d['w'],d['l'])
    if key in cells:continue
    cell='dev_'+d['model'].split('__')[1]+'_'+str(d['w']).replace('.','p')+'_'+str(d['l']).replace('.','p')
    cells[key]=cell
    t+=['load '+cell,'box values 0 0 0 0',f"set p [sky130::{d['model']}_defaults]",f"dict set p w {d['w']}",f"dict set p l {d['l']}"]
    if d['kind']=='mos':t+=['dict set p botc 0']
    t+=[f"sky130::{d['model']}_draw $p"]
    if d['kind']=='resistor':
        # The PCell's generated 0.75 um URPM is narrower than the 1.27 um
        # minimum. Expand implant only; keep electrical resistor dimensions.
        half_y=round((d['l']/2+2.28)/.005)
        t += [f'property MASKHINTS_URPM {{-127 -{half_y} 127 {half_y}}}']
    t+=['save '+cell]
t+=['quit -noprompt']
(W/'devices.tcl').write_text('\n'.join(t)+'\n')
with (W/'devices.log').open('w') as log:
    subprocess.run(['magic','-dnull','-noconsole','-rcfile',RC,str(W/'devices.tcl')],cwd=W,stdout=log,stderr=subprocess.STDOUT,check=True)

def info(cell):
    txt=(W/(cell+'.mag')).read_text()
    pins={}
    for line in txt.splitlines():
        m=re.match(r'rlabel (\S+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) \d+ (\S+)',line)
        if m:pins[m[6]]=(m[1],(int(m[2])+int(m[4]))*.0025,(int(m[3])+int(m[5]))*.0025)
    return pins

template=(P/'layout/pin_template.def').read_text()
template=template.replace('DESIGN tt_um_template ;',f'DESIGN {TOP} ;')
(W/'pin_template.def').write_text(template)
t=['drc off',f'def read {W}/pin_template.def',f'load {TOP}','snap internal','box values 0 0 0 0']
def rect(layer,x1,y1,x2,y2):
    x1,x2=sorted([x1,x2]);y1,y2=sorted([y1,y2])
    t.extend([f'box values {x1:.3f}um {y1:.3f}um {x2:.3f}um {y2:.3f}um','paint '+layer])
def trace(layer,a,b,width=.4):
    assert abs(a[0]-b[0])<1e-6 or abs(a[1]-b[1])<1e-6,(a,b)
    rect(layer,min(a[0],b[0])-width/2,min(a[1],b[1])-width/2,max(a[0],b[0])+width/2,max(a[1],b[1])+width/2)
def via(x,y,low):
    # Conservative symmetric landing pads on the 5 nm manufacturing grid.
    size={1:.5,2:.6,3:.8}[low];cut={1:.26,2:.28,3:.32}[low]
    for l in [f'metal{low}',f'metal{low+1}']:rect(l,x-size/2,y-size/2,x+size/2,y+size/2)
    rect('via'+str(low),x-cut/2,y-cut/2,x+cut/2,y+cut/2)
def pinlabel(net,x,y,layer='metal3'):
    t.extend([f'box values {x}um {y}um {x}um {y}um',f'label {{{net}}} center {layer}'])
def place(cell,name,x,y):
    t.extend([f'box values {x}um {y}um {x}um {y}um',f'getcell {cell} child 0 0',f'identify {name}'])
    return {k:(l,x+px,y+py) for k,(l,px,py) in info(cell).items()}

nets=['VGND','VDPWR','ui_in[0]','ui_in[1]','ui_in[2]','H_BAR','L_BAR','S_BAR','ua[0]','ua[2]','SAMPLE','SHIELD','HOLD','BIAS','RBMID','MIRROR','TAIL','AMP','COMP','ua[1]']
lanes={n:201+i*1.0 for i,n in enumerate(nets)}
for n,y in lanes.items():
    # Gate-only controls must not carry unused full-width metal antenna tails.
    left={'ui_in[0]':6,'ui_in[1]':21,'ui_in[2]':36}.get(n,2)
    right=140 if n.startswith('ui_in') else 159
    trace('metal3',(left,y),(right,y),.45)
    if n=='SHIELD':via(2,y,3)
    elif n not in ['VGND','VDPWR']:pinlabel(n,left+2,y)
# Metal-4 power stripes comply with the Tiny Tapeout macro interface.
for n,x in [('VGND',2),('VDPWR',159)]:
    rect('metal4',x-.6,0,x+.6,225.76);via(x,lanes[n],3)
    t.extend([f'box values {x-.6}um 0um {x+.6}um 225.76um',f'label {n} center metal4',f'port {n} make {52 if n=="VGND" else 53}',f'port {n} class input',f'port {n} use '+('ground' if n=='VGND' else 'power')])

# Each MOS terminal escapes locally on metal 1, then rises on metal 2 to
# its metal-3 routing lane. The physical bulk contacts remain explicit.
mos=[d for d in S['devices'] if d['kind']=='mos']
for i,d in enumerate(mos):
    cx,cy=7+7.5*i,184
    f=place(cells[(d['model'],d['w'],d['l'])],d['name'],cx,cy)
    for pin,net in [('D',d['d']),('S',d['s']),('G',d['g']),('B',d['b'])]:
        layer,x,y=f[pin]
        if pin=='B':
            rect('viali',x-.085,y-.085,x+.085,y+.085)
            rect('metal1',x-.25,y-.25,x+.25,y+.25)
            ex=cx+3
        elif pin=='D':ex=cx-(1 if d['l']<.3 else 2)
        elif pin=='S':ex=cx+(1 if d['l']<.3 else 2)
        else:
            ex=cx
            trace('metal1',(x,y),(ex,y+.6),.26)
            y+=.6
        trace('metal1',(x,y),(ex,y),.28)
        via(ex,y,1)
        trace('metal2',(ex,y),(ex,lanes[net]),.4)
        via(ex,lanes[net],2)

# Dedicated metal-1 spines pass through gaps in the MOS escape columns.
spines={'SAMPLE':19,'HOLD':26.5,'ua[0]':34,'ua[1]':41.5,'ua[2]':49,'BIAS':56.5,'RBMID':64,'AMP':71.5,'COMP':79,'VGND':86.5}
for n,x in spines.items():
    trace('metal1',(x,3),(x,lanes[n]),.4)
    via(x,lanes[n],1);via(x,lanes[n],2)

# Two electrically distinct capacitor banks, each sixteen 14x14 um units.
# ABBA / BAAB patterns cancel first-order horizontal and vertical gradients.
roles=['ABBAABBA','BAABBAAB','BAABBAAB','ABBAABBA']
capcell=cells[('sky130_fd_pr__cap_mim_m3_1',14,14)]
cap_positions=[]
for row,pattern in enumerate(roles):
    cy=83+20*row
    for col,letter in enumerate(pattern):
        cx=12.8+18.5*col;net='SAMPLE' if letter=='A' else 'HOLD'
        f=place(capcell,f'C{letter}_{row}_{col}',cx,cy)
        _,x,y=f['C1'];by=cy+(9.0 if letter=='A' else 10.5)
        trace('metal4',(x,y),(x,by),.7)
        via(x,by,3);via(x,by,2)
        cap_positions.append({'bank':net,'x':cx,'y':cy})
    trace('metal3',(2,cy),(151,cy),1.0);via(2,cy,3)
    # Ground stripe between the two long row buses prevents serial-code
    # dependent capacitive feedthrough into the isolated hold bank.
    trace('metal2',(2,cy+9.75),(151,cy+9.75),.4)
    via(spines['VGND'],cy+9.75,1)
    for n,offset in [('SAMPLE',9.0),('HOLD',10.5)]:
        by=cy+offset
        trace('metal2',(11.92,by),(141.42,by),.4)
        via(spines[n],by,1)

# Grounded metal-4 shields occupy the gaps between unit-capacitor columns.
for col in range(7):
    sx=12.8+18.5*col+9.25
    trace('metal4',(sx,80),(sx,152),.6)
    for row in range(4):via(sx,83+20*row,3)

# Lower-area bias resistors and isolated compensation capacitor.
bottom_lanes={'BIAS':68,'RBMID':69.2,'AMP':70.4,'COMP':71.6,'ua[1]':72.8,'VGND':74}
for n,y in bottom_lanes.items():
    trace('metal3',(4,y),(155,y),.45)
    via(spines[n],y,2);via(spines[n],y,1)
for d,cx,cy in [(d,90 if d['name']=='R1' else 110 if d['name']=='R2' else 66,42 if d['name']!='R3' else 60) for d in S['devices'] if d['kind']=='resistor']:
    f=place(cells[(d['model'],d['w'],d['l'])],d['name'],cx,cy)
    for pin,net,dx in [('R1',d['a'],-1),('R2',d['b'],1),('B',d['bulk'],2.5)]:
        layer,x,y=f[pin]
        if pin=='B':
            rect('viali',x-.085,y-.085,x+.085,y+.085);rect('metal1',x-.25,y-.25,x+.25,y+.25)
        trace('metal1',(x,y),(cx+dx,y),.28);via(cx+dx,y,1)
        trace('metal2',(cx+dx,y),(cx+dx,bottom_lanes[net]),.4);via(cx+dx,bottom_lanes[net],2)
d=next(x for x in S['devices'] if x['role']=='C_COMP')
f=place(cells[(d['model'],d['w'],d['l'])],d['name'],32,38)
for pin,n,exit_y in [('C1','COMP',56),('C2','ua[1]',21)]:
    _,x,y=f[pin]
    trace('metal4',(x,y),(x,exit_y),.7);via(x,exit_y,3);via(x,exit_y,2)
    trace('metal2',(x,exit_y),(x,bottom_lanes[n]),.4);via(x,bottom_lanes[n],2)

# Original DEF pin rectangles are preserved exactly. Only routing is added.
pins=[]
for m in re.finditer(r'- (\S+) \+ NET .*?\+ LAYER met4 \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \).*?\+ PLACED \( (\d+) (\d+) \)',template,re.S):
    n=m[1];px,py=int(m[6])/1000,int(m[7])/1000;pins.append((n,px,py))
    # Unused digital outputs are grounded. Unallocated analog pads stay isolated.
    ground=n.startswith(('uo_out','uio_out','uio_oe'))
    if n in ['ui_in[0]','ui_in[1]','ui_in[2]']:
        via(px,225,3)
        ex=px+.6 if n=='ui_in[2]' else px
        trace('metal3',(px,225),(ex,225),.4);via(ex,225,2)
        trace('metal2',(ex,225),(ex,lanes[n]),.4);via(ex,lanes[n],2)
    elif n in ['ua[0]','ua[1]','ua[2]']:
        via(px,.75,3);via(px,.75,2)
        by={'ua[0]':4,'ua[1]':6,'ua[2]':8}[n]
        trace('metal2',(px,.75),(px,by),.4);via(px,by,2)
        trace('metal3',(px,by),(spines[n],by),.45);via(spines[n],by,2);via(spines[n],by,1)
    elif ground:
        if py>200:
            via(px,225,3);trace('metal3',(px,225),(px,223.5),.45)
        else:
            via(px,.75,3);trace('metal3',(px,.75),(px,1.8),.45)
trace('metal3',(2,223.5),(153,223.5),.45);via(2,223.5,3)
trace('metal3',(2,1.8),(100,1.8),.45);via(2,1.8,3)

t+=['box values 0 0 161um 225.76um',f'property FIXED_BBOX {{0 0 32200 45152}}',f'save {TOP}','drc on','drc check','drc catchup',f'puts "DRC_COUNT [drc list count total]"',f'puts "DRC_DETAILS [drc listall why]"','extract all','ext2spice lvs','ext2spice short resistor','ext2spice subcircuit on','ext2spice -o extracted.spice',f'gds write {TOP}.gds',f'lef write {TOP}.lef -pinonly','quit -noprompt']
(W/'build.tcl').write_text('\n'.join(t)+'\n')
(W/'placement.json').write_text(json.dumps({'capacitors':cap_positions,'spines':spines,'lanes':lanes,'pins':pins},indent=2)+'\n')
with (W/'build.log').open('w') as log:
    r=subprocess.run(['magic','-dnull','-noconsole','-rcfile',RC,str(W/'build.tcl')],cwd=W,stdout=log,stderr=subprocess.STDOUT)
print('Magic exit',r.returncode)
txt=(W/'build.log').read_text()
print(txt[-5000:])

if 'DRC_COUNT 0' not in txt: raise RuntimeError('Native Magic DRC failed')
for f in W.glob('*.mag'):shutil.copy2(f,P/'layout'/f.name)
for suffix,folder in [('gds','gds'),('lef','lef')]:shutil.copy2(W/f'{TOP}.{suffix}',P/folder/f'{TOP}.{suffix}')
shutil.copy2(W/'extracted.spice',P/'netlist/extracted_lvs.spice')
shutil.copy2(W/'build.log',P/'verification/layout_build.log')
shutil.copy2(W/'placement.json',P/'layout/placement.json')
print('Build products:',W)
