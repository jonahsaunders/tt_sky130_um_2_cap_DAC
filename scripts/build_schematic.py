from pathlib import Path
import json, uuid, math

P=Path(__file__).resolve().parents[1]
spec=json.loads((P/'design.json').read_text())
dev={x['role']:x for x in spec['devices']}
uid=lambda:str(uuid.uuid4())
root=uid(); pieces=[]; instances=[]; lib=[]; sympins={}
def snap(v): return round(round(v/1.27)*1.27,3)
def q(s): return json.dumps(str(s),ensure_ascii=False)
def text(s,x,y,size=1.27,bold=False):
    pieces.append(f'(text {q(s)} (at {x} {y} 0) (effects (font (size {size} {size})'+(' (bold yes)' if bold else '')+f') (justify left)) (uuid {q(uid())}))')
def wire(a,b):
    a=tuple(snap(v) for v in a);b=tuple(snap(v) for v in b)
    if a==b: return
    pieces.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid {q(uid())}))')
def label(s,x,y,angle=0):
    x,y=snap(x),snap(y)
    pieces.append(f'(label {q(s)} (at {x} {y} {angle}) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {q(uid())}))')
def junction(x,y): pieces.append(f'(junction (at {snap(x)} {snap(y)}) (diameter 0) (color 0 0 0 0) (uuid {q(uid())}))')
def box(title,x,y,w,h,color):
    pieces.append(f'(rectangle (start {x} {y}) (end {x+w} {y+h}) (stroke (width .3) (type default) (color {color} 1)) (fill (type none)) (uuid {q(uid())}))')
    text(title,x+3,y+5,1.8,True)

def make_symbol(name,pins,draw,ref='M',power=False):
    sympins[name]={num:(x,y) for num,nm,x,y,ang,kind in pins}
    pp=[]
    for num,nm,x,y,ang,kind in pins:
        pp.append(f'(pin {kind} line (at {x} {y} {ang}) (length 2.54) (name {q(nm)} (effects (font (size 1.0 1.0)))) (number {q(num)} (effects (font (size 1.0 1.0)))))')
    power_tag='(power)' if power else ''
    s=f'''(symbol "Sky130:{name}" {power_tag} (pin_names (offset 0) hide) (pin_numbers hide)
    (exclude_from_sim no) (in_bom no) (on_board no)
    (property "Reference" "{ref}" (at 5.08 3.81 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{name}" (at 5.08 -7.62 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "https://skywater-pdk.readthedocs.io/" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (symbol "{name}_0_1" {draw}) (symbol "{name}_1_1" {' '.join(pp)}))'''
    lib.append(s)

def line(coords):return '(polyline (pts '+' '.join(f'(xy {x} {y})' for x,y in coords)+') (stroke (width .254) (type default)) (fill (type none)))'
fetdraw=''.join([line([(-2.54,0),(-1.27,0)]),line([(-1.27,-2.54),(-1.27,2.54)]),line([(0,-2.54),(0,2.54)]),line([(0,2.54),(2.54,2.54)]),line([(0,-2.54),(2.54,-2.54)])])
for name,p,down in [('NMOS3',False,False),('PMOS3',True,False),('PMOS_TG3',True,True)]:
    d_y=5.08 if (not p or down) else -5.08
    s_y=-d_y
    draw=fetdraw+('(circle (center -2.1 0) (radius .55) (stroke (width .254) (type default)) (fill (type background)))' if p else '')
    make_symbol(name,[('1','D',2.54,d_y,270 if d_y>0 else 90,'passive'),('2','G',-5.08,0,0,'passive'),('3','S',2.54,s_y,270 if s_y>0 else 90,'passive')],draw)

# Horizontal switch symbols and inward-facing amplifier symbols retain D/G/S
# pin numbers 1/2/3. Only their drawing and pin positions change.
for name,p in [('NMOS_H3',False),('PMOS_H3',True)]:
    gy=7.62 if p else -7.62
    side=1 if p else -1
    draw=line([(-2.54,0),(-2.54,side*2.54),(2.54,side*2.54),(2.54,0)])+line([(-2.54,side*3.81),(2.54,side*3.81)])+line([(0,side*3.81),(0,side*5.08)])
    if p:draw+='(circle (center 0 4.65) (radius .55) (stroke (width .254) (type default)) (fill (type background)))'
    make_symbol(name,[('1','D',-5.08,0,0,'passive'),('2','G',0,gy,270 if p else 90,'passive'),('3','S',5.08,0,180,'passive')],draw)
mirror_draw=''.join([line([(2.54,0),(1.27,0)]),line([(1.27,-2.54),(1.27,2.54)]),line([(0,-2.54),(0,2.54)]),line([(0,2.54),(-2.54,2.54)]),line([(0,-2.54),(-2.54,-2.54)])])
for name,p in [('NMOS_R3',False),('PMOS_R3',True)]:
    dy=-5.08 if p else 5.08
    draw=mirror_draw+('(circle (center 2.1 0) (radius .55) (stroke (width .254) (type default)) (fill (type background)))' if p else '')
    make_symbol(name,[('1','D',-2.54,dy,90 if p else 270,'passive'),('2','G',5.08,0,180,'passive'),('3','S',-2.54,-dy,270 if p else 90,'passive')],draw)
capdraw=line([(-1.27,.635),(1.27,.635)])+line([(-1.27,-.635),(1.27,-.635)])+line([(0,.635),(0,1.27)])+line([(0,-.635),(0,-1.27)])
make_symbol('C_Small',[('1','1',0,3.81,270,'passive'),('2','2',0,-3.81,90,'passive')],capdraw,ref='C')
cap_h=line([(-.635,-1.27),(-.635,1.27)])+line([(.635,-1.27),(.635,1.27)])+line([(-1.27,0),(-.635,0)])+line([(.635,0),(1.27,0)])
make_symbol('C_Small_H',[('1','1',-3.81,0,0,'passive'),('2','2',3.81,0,180,'passive')],cap_h,ref='C')
rdraw=line([(0,1.27),(.635,1.016),(-.635,.508),(.635,0),(-.635,-.508),(.635,-1.016),(0,-1.27)])
make_symbol('R_Small_US',[('1','1',0,3.81,270,'passive'),('2','2',0,-3.81,90,'passive')],rdraw,ref='R')
rdraw_h=line([(-1.27,0),(-1.016,.635),(-.508,-.635),(0,.635),(.508,-.635),(1.016,.635),(1.27,0)])
make_symbol('R_Small_US_H',[('1','1',-3.81,0,0,'passive'),('2','2',3.81,0,180,'passive')],rdraw_h,ref='R')
make_symbol('VGND',[('1','VGND',0,0,90,'power_in')],line([(0,0),(0,-1.27)])+line([(-1.27,-1.27),(1.27,-1.27)])+line([(-.889,-1.778),(.889,-1.778)])+line([(-.508,-2.286),(.508,-2.286)]),ref='#PWR',power=True)
make_symbol('VDPWR',[('1','VDPWR',0,0,270,'power_in')],line([(0,0),(0,1.27)])+line([(-.762,1.27),(0,2.54),(.762,1.27),(-.762,1.27)]),ref='#PWR',power=True)
make_symbol('PWR_FLAG',[('1','pwr',0,0,90,'power_out')],line([(0,0),(0,1.27),(-.762,1.778),(0,2.286),(.762,1.778),(0,1.27)]),ref='#FLG',power=True)

pwr_count=0
def inst(sym,x,y,ref,value,extra=None,visval=True):
    x,y=snap(x),snap(y)
    iid=uid(); props=[]
    for k,v,px,py,visible in [('Reference',ref,x+5,y-3.8,not ref.startswith('#')),('Value',value,x+5,y+7.6,visval),('Footprint','',x,y,False),('Datasheet','https://skywater-pdk.readthedocs.io/',x,y,False)]+[(k,v,x,y,False) for k,v in (extra or {}).items()]:
        if sym in ['C_Small','R_Small_US'] and k=='Reference': px,py=x+3,y-2
        if sym in ['C_Small','R_Small_US'] and k=='Value': px,py=x+3,y+2
        if sym in ['C_Small_H','R_Small_US_H'] and k=='Reference': px,py=x-2,y-5
        if sym in ['C_Small_H','R_Small_US_H'] and k=='Value': px,py=x-4,y+4
        if sym=='VGND' and k=='Value':px,py=x+2,y+3
        if sym=='VDPWR' and k=='Value':px,py=x+2,y-3
        if sym.endswith('_H3') and k=='Reference':px,py=x+7,y-3
        if sym.endswith('_R3') and k=='Reference':px,py=x-12,y-3.8
        if sym.endswith('_R3') and k=='Value':px,py=x-18,y+7.6
        fs=1.05 if sym.endswith('3') and k=='Value' else 1.27
        props.append(f'(property {q(k)} {q(v)} (at {px} {py} 0) (effects (font (size {fs} {fs})) (justify left)'+('' if visible else ' (hide yes)')+'))')
    pieces.append(f'''(symbol (lib_id "Sky130:{sym}") (at {x} {y} 0) (unit 1)
      (exclude_from_sim no) (in_bom no) (on_board no) (dnp no) (uuid {q(iid)})
      {' '.join(props)} {' '.join(f'(pin {q(n)} (uuid {q(uid())}))' for n in sympins[sym])}
      (instances (project "suarez_dac" (path {q('/'+root)} (reference {q(ref)}) (unit 1)))))''')
    return {n:(round(x+px,4),round(y-py,4)) for n,(px,py) in sympins[sym].items()}
def power(net,x,y,flag=False):
    global pwr_count
    pwr_count+=1
    inst(net,x,y,f'#PWR{pwr_count:03}',net,visval=True)
    if flag:
        pwr_count+=1
        inst('PWR_FLAG',x,y,f'#FLG{pwr_count:03}','PWR_FLAG',visval=False)
def mos(role,x,y,tg=False,horizontal=False,mirror=False):
    d=dev[role];sym='NMOS3' if 'nfet' in d['model'] else ('PMOS_TG3' if tg else 'PMOS3')
    if horizontal:sym='NMOS_H3' if 'nfet' in d['model'] else 'PMOS_H3'
    if mirror:sym='NMOS_R3' if 'nfet' in d['model'] else 'PMOS_R3'
    val=f"{d['w']} / {d['l']} um"+(' LVT' if '_lvt' in d['model'] else '')
    return inst(sym,x,y,d['name'],val,{'Role':role,'PDK_Model':d['model'],'W_um':d['w'],'L_um':d['l'],'Bulk':d['b']},visval=not horizontal)
def passive(role,sym,x,y,value):
    d=dev[role]
    return inst(sym,x,y,d['name'],value,{'Role':role,'PDK_Model':d['model'],'W_um':d['w'],'L_um':d['l'],'Multiplicity':d.get('m',1),'Bulk':d.get('bulk','')})
def stub(pt,net,left=True,n=4):
    e=(round(pt[0]+(-n if left else n),4),pt[1]);wire(pt,e);label(net,e[0],e[1])

def path(*points):
    for a,b in zip(points,points[1:]):wire(a,b)

def tap(x,y):junction(x,y)

def tg(tag,x,y):
    p=mos('MP_SW_'+tag,x,y-6.35,horizontal=True)
    n=mos('MN_SW_'+tag,x,y+6.35,horizontal=True)
    xl,xr=snap(x-10.16),snap(x+10.16)
    for f in [p,n]:
        path(f['1'],(xl,f['1'][1]),(xl,y))
        path(f['3'],(xr,f['3'][1]),(xr,y))
    tap(xl,y);tap(xr,y)
    path(p['2'],(x,y-16.51));label(tag+'_BAR',x,y-16.51)
    path(n['2'],(x,y+16.51));label(dev['MN_SW_'+tag]['g'],x,y+16.51)
    return (xl,snap(y)),(xr,snap(y))

text('SUAREZ SERIAL CHARGE-SHARING DAC',15,17,3,True)
text('SKY130  |  1.8 V  |  8 bits, LSB first  |  161 x 225.76 um  |  W / L dimensions in um',15,24,1.35)
box('01  REFERENCE SELECTION AND CHARGE SHARING',15,32,194,148,'30 92 137')
box('02  UNITY-GAIN BUFFER  /  BIAS, FEEDBACK AND COMPENSATION',219,32,186,220,'121 80 131')
box('03  COMPLEMENTARY PHASE DRIVERS',15,188,194,64,'49 117 103')

hi_in,hi_out=tg('H',65,77)
lo_in,lo_out=tg('L',65,127)
s_in,s_out=tg('S',165,102)
path((23,77),hi_in);label('ua[0]',23,77)
path((23,127),lo_in);label('ua[2]',23,127)
text('VREFH = 0.9 V',23,70,1.15)
text('VREFL = 0.2 V',23,120,1.15)
text('HIGH',51,49,1.35,True)
text('LOW',52,106,1.35,True)
text('SHARE',155,73,1.35,True)
path(hi_out,(128,77),(128,127),lo_out)
path((128,102),s_in);tap(128,102);label('SAMPLE',128,102)
path(s_out,(196,102),(217,102),(217,141))
label('HOLD',184,102)
for role,x in [('C_SAMPLE',128),('C_HOLD',196)]:
    c=passive(role,'C_Small',x,150,'6.454 pF')
    path((x,102),c['1']);tap(x,102)
    path(c['2'],(x,171));power('VGND',x,171)
text('C1 / C2: 16 MIM units per bank',23,161,1.05)
text('Switches: N 1 / 0.15; P 2 / 0.35 LVT',23,171,1.05)

# Bias reference, current source and output load share an actual bias wire.
b=mos('MP_BIAS',238,82)
t=mos('MP_TAIL',270,82)
po=mos('MP_OUT',350,82)
for f in [b,t,po]:path(f['3'],(f['3'][0],55))
path((b['3'][0],55),(po['3'][0],55));tap(t['3'][0],55)
power('VDPWR',323,55,flag=True);tap(323,55)
path(b['1'],(b['1'][0],94),(224,94),(224,82),b['2'])
tap(b['1'][0],94);tap(224,82)
path((224,94),(336,94),(336,82),po['2'])
path(t['2'],(259,t['2'][1]),(259,94));tap(259,94)
label('BIAS',305,94)
r1=passive('RB1','R_Small_US_H',248,46,'171 kR')
r2=passive('RB2','R_Small_US_H',286,46,'171 kR')
path((224,94),(224,46),r1['1']);tap(224,94)
path(r1['2'],r2['1']);label('RBMID',264,46)
path(r2['2'],(303,46));power('VGND',303,46)

# Inward-facing differential pair; HOLD enters from the conversion core.
pp=mos('MP_INP',244,141)
pm=mos('MP_INM',286,141,mirror=True)
path((217,141),pp['2'])
path(t['1'],(t['1'][0],117))
path(pp['3'],(pp['3'][0],117),(pm['3'][0],117),pm['3'])
tap(t['1'][0],117);label('TAIL',253,117)
nl=mos('MN_LOAD',244,174)
nm=mos('MN_MIRROR',286,174,mirror=True)
path(pp['1'],nl['1']);path(pm['1'],nm['1'])
label('AMP',pp['1'][0],153);label('MIRROR',pm['1'][0],153)
path((pm['1'][0],155),(299,155),(299,188),(231,188),(231,174),nl['2'])
path(nm['2'],(299,174));tap(299,174);tap(pm['1'][0],155)
for f in [nl,nm]:path(f['3'],(f['3'][0],197))
path((nl['3'][0],197),(nm['3'][0],197));power('VGND',265,197);tap(265,197)

# Second gain stage and the two visible paths around it: feedback above,
# AMP drive and R3-C3 Miller compensation below.
no=mos('MN_OUT',350,174)
path(po['1'],no['1'])
path((po['1'][0],151),(392,151));tap(po['1'][0],151);label('ua[1]',392,151)
text('VOUT',379,144,1.4,True)
path((389,151),(389,125),(315,125),(315,141),pm['2']);tap(389,151)
text('unity-gain feedback',318,119,1.1)
path(no['3'],(no['3'][0],197));power('VGND',no['3'][0],197)
path((pp['1'][0],156),(225,156),(225,230));tap(pp['1'][0],156)
path((225,213),(336,213),(336,174),no['2']);tap(225,213)
label('AMP',306,213)
r=passive('RZ','R_Small_US_H',260,230,'80 kR')
c=passive('C_COMP','C_Small_H',314,230,'1.373 pF')
path((225,230),r['1']);path(r['2'],c['1']);label('COMP',285,230)
path(c['2'],(375,230),(375,151));tap(375,151)
text('R3-C3 compensation belongs to the buffer',230,246,1.1)

for tag,x in [('H',40),('L',97),('S',154)]:
    p=mos('MP_INV_'+tag,x,207);n=mos('MN_INV_'+tag,x,232)
    oy=snap(220)
    path(p['1'],n['1']);tap(p['1'][0],oy)
    path((p['1'][0],oy),(x+12,oy));label(tag+'_BAR',x+12,oy)
    gx=snap(x-11)
    path(p['2'],(gx,p['2'][1]),(gx,n['2'][1]),n['2'])
    path((gx,oy),(gx-8,oy));tap(gx,oy);label(dev['MN_INV_'+tag]['g'],gx-8,oy)
    path(p['3'],(p['3'][0],199));power('VDPWR',p['3'][0],199)
    path(n['3'],(n['3'][0],244));power('VGND',n['3'][0],244,flag=tag=='H')

text('OPERATING SEQUENCE',15,259,1.5,True)
text('Initialize: HIGH=0, LOW=1, SHARE=1 for 8 us. Then all phases off for 0.2 us.',15,265,1.12)
text('8 bits, LSB first: charge 2 us; dead 0.2 us; share 2 us; dead 0.2 us. Read 3 us after bit 7.',15,271,1.12)
text('HIGH / LOW never overlap. LOW / SHARE overlap only during initialization. External controller supplies dead time.',15,277,1.02)
text('Bodies: all NMOS -> VGND; all PMOS -> VDPWR. Body ties are explicit in SPICE / silicon.',15,283,1.02)

sch=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(root)})
(paper "A3") (title_block (title "Suarez two-capacitor DAC") (rev "0.2") (company "SKY130 / Tiny Tapeout"))
(lib_symbols {' '.join(lib)}) {' '.join(pieces)} (sheet_instances (path "/" (page "1"))))'''
(P/'schematic/suarez_dac.kicad_sch').write_text(sch+'\n')
library='(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+ ' '.join(s.replace('"Sky130:','"') for s in lib)+')'
(P/'schematic/Sky130.kicad_sym').write_text(library+'\n')
(P/'schematic/sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Sky130") (type "KiCad") (uri "${KIPRJMOD}/Sky130.kicad_sym") (options "") (descr "SKY130 three-terminal circuit symbols")))\n')
(P/'schematic/suarez_dac.kicad_pro').write_text(json.dumps({'meta':{'filename':'suarez_dac.kicad_pro','version':1}},indent=2)+'\n')
print('Created KiCad schematic with',len(spec['devices']),'PDK devices')
