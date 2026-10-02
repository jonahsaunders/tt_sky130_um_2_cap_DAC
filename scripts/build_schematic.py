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
        props.append(f'(property {q(k)} {q(v)} (at {px} {py} 0) (effects (font (size 1.27 1.27)) (justify left)'+('' if visible else ' (hide yes)')+'))')
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
def mos(role,x,y,tg=False):
    d=dev[role];sym='NMOS3' if 'nfet' in d['model'] else ('PMOS_TG3' if tg else 'PMOS3')
    val=f"{d['w']} / {d['l']} um"+(' LVT' if '_lvt' in d['model'] else '')
    return inst(sym,x,y,d['name'],val,{'Role':role,'PDK_Model':d['model'],'W_um':d['w'],'L_um':d['l'],'Bulk':d['b']})
def passive(role,sym,x,y,value):
    d=dev[role]
    return inst(sym,x,y,d['name'],value,{'Role':role,'PDK_Model':d['model'],'W_um':d['w'],'L_um':d['l'],'Multiplicity':d.get('m',1),'Bulk':d.get('bulk','')})
def stub(pt,net,left=True,n=4):
    e=(round(pt[0]+(-n if left else n),4),pt[1]);wire(pt,e);label(net,e[0],e[1])

text('SUAREZ TWO-CAPACITOR DAC  /  SKY130',15,17,3,True)
text('Tiny Tapeout 1x2 analog macro  |  1.8 V  |  LSB first  |  transistor dimensions shown as W / L',15,23,1.4)
box('01  CHARGE REDISTRIBUTION',15,28,250,94,'30 92 137')
for tag,xx,net in [('H',40,'ua[0]'),('L',115,'ua[2]'),('S',190,'SAMPLE')]:
    text({'H':'CHARGE HIGH','L':'CHARGE LOW','S':'SHARE CHARGE'}[tag],xx-3,42,1.5,True)
    n=mos('MN_SW_'+tag,xx,65)
    p=mos('MP_SW_'+tag,xx+30,65,tg=True)
    up=52;down=79
    for f in [n,p]: wire(f['1'],(f['1'][0],up));wire(f['3'],(f['3'][0],down))
    wire((n['1'][0],up),(p['1'][0],up));wire((n['3'][0],down),(p['3'][0],down))
    label(net,n['1'][0],up)
    outnet='HOLD' if tag=='S' else 'SAMPLE';label(outnet,n['3'][0],down)
    stub(n['2'],dev['MN_SW_'+tag]['g'],n=4)
    stub(p['2'],tag+'_BAR',n=3)
    if tag in ['H','S']:
        cx=(n['3'][0]+p['3'][0])/2
        cap=passive('C_'+outnet,'C_Small',cx,99,'6.454 pF')
        wire((cx,down),cap['1']);junction(cx,down)
        wire(cap['2'],(cx,110));power('VGND',cx,110)
        text('16 x (14 / 14 um) MIM',cx+3,106,1.0)
text('HIGH and LOW must never overlap. SHARE closes only after HIGH / LOW have opened.',20,118,1.12)

box('02  BUFFER COMPENSATION',276,28,129,94,'121 80 131')
r=passive('RZ','R_Small_US_H',310,69,'80 kR nominal')
c=passive('C_COMP','C_Small_H',360,69,'1.373 pF')
wire((289,69),r['1']);label('AMP',289,69)
wire(r['2'],c['1']);label('COMP',334,69);wire(c['2'],(393,69));label('ua[1]',393,69)
text('R3: xhigh poly, 0.35 / 14 um',282,91,1.2)
text('C3 stabilizes the output buffer.',282,101,1.2)
text('C1 and C2 perform the D/A conversion.',282,108,1.2)

box('03  COMPLEMENTARY SWITCH CONTROLS',15,133,130,111,'49 117 103')
for tag,x in [('H',40),('L',78),('S',116)]:
    p=mos('MP_INV_'+tag,x,166);n=mos('MN_INV_'+tag,x,192)
    wire(p['1'],n['1']);oy=179
    wire((p['1'][0],oy),(x+11,oy));junction(p['1'][0],oy);label(tag+'_BAR',x+11,oy)
    gx=x-10
    wire(p['2'],(gx,p['2'][1]));wire(n['2'],(gx,n['2'][1]));wire((gx,p['2'][1]),(gx,n['2'][1]))
    wire((gx,oy),(gx-4,oy));junction(gx,oy);label(dev['MN_INV_'+tag]['g'],gx-4,oy)
    wire(p['3'],(p['3'][0],152));power('VDPWR',p['3'][0],152,flag=tag=='H')
    wire(n['3'],(n['3'][0],215));power('VGND',n['3'][0],215,flag=tag=='H')
text('External phases provide dead time.',21,232,1.2)
text('No on-chip word counter is required.',21,239,1.2)

box('04  INPUT AMPLIFIER AND BIAS',155,133,155,111,'121 80 131')
b=mos('MP_BIAS',175,166);wire(b['3'],(b['3'][0],151));power('VDPWR',b['3'][0],151)
wire(b['2'],(165,b['2'][1]));wire((165,166),(165,177));wire((165,177),(b['1'][0],177));wire(b['1'],(b['1'][0],177));junction(b['1'][0],177);label('BIAS',165,177)
r1=passive('RB1','R_Small_US',177.54,195,'171 kR nominal');r2=passive('RB2','R_Small_US',177.54,215,'171 kR nominal')
wire((177.54,177),r1['1']);wire(r1['2'],r2['1']);label('RBMID',177.54,205)
wire(r2['2'],(177.54,228));power('VGND',177.54,228)
t=mos('MP_TAIL',239,151);wire(t['3'],(t['3'][0],144));power('VDPWR',t['3'][0],144);stub(t['2'],'BIAS')
pp=mos('MP_INP',220,179);pm=mos('MP_INM',263,179)
wire(t['1'],(t['1'][0],166));wire((pp['3'][0],166),(pm['3'][0],166));junction(t['1'][0],166);label('TAIL',246,166)
for f in [pp,pm]:wire(f['3'],(f['3'][0],166))
stub(pp['2'],'HOLD');stub(pm['2'],'ua[1]')
nl=mos('MN_LOAD',220,216);nm=mos('MN_MIRROR',263,216)
wire(pp['1'],nl['1']);label('AMP',pp['1'][0],199)
wire(pm['1'],nm['1']);label('MIRROR',pm['1'][0],199)
stub(nl['2'],'MIRROR')
wire(nm['2'],(253,216));wire((253,216),(253,199));wire((253,199),(nm['1'][0],199));junction(nm['1'][0],199)
wire(nl['3'],(nl['3'][0],235));wire(nm['3'],(nm['3'][0],235));wire((nl['3'][0],235),(nm['3'][0],235));power('VGND',242,235);junction(242,235)

box('05  OUTPUT DRIVER',320,133,85,111,'121 80 131')
po=mos('MP_OUT',351,166);no=mos('MN_OUT',351,211)
wire(po['3'],(po['3'][0],151));power('VDPWR',po['3'][0],151)
wire(po['1'],no['1']);wire((po['1'][0],189),(390,189));junction(po['1'][0],189);label('ua[1]',390,189)
stub(po['2'],'BIAS');stub(no['2'],'AMP')
wire(no['3'],(no['3'][0],229));power('VGND',no['3'][0],229)
text('Buffered analog output',326,239,1.2)

text('PORTS',15,255,1.6,True)
text('ui_in[0] = HIGH    ui_in[1] = LOW    ui_in[2] = SHARE    ua[0] = VREFH    ua[1] = VOUT    ua[2] = VREFL',15,261,1.27)
text('Initialize: HIGH=0, LOW=1, SHARE=1 for 8 us. Then 8 bits, LSB first: charge 2 us, dead 0.2 us, share 2 us, dead 0.2 us.',15,268,1.27)
text('Bulk ties: every NMOS -> VGND; every PMOS -> VDPWR. Bulk pins are implicit in this drawing and explicit in the silicon netlist.',15,275,1.27)
text('Unused digital outputs are tied to VGND; ua[3:7] are isolated. Supply bypassing is provided by the Tiny Tapeout chip / board.',15,282,1.15)

sch=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(root)})
(paper "A3") (title_block (title "Suarez two-capacitor DAC") (rev "0.1") (company "SKY130 / Tiny Tapeout"))
(lib_symbols {' '.join(lib)}) {' '.join(pieces)} (sheet_instances (path "/" (page "1"))))'''
(P/'schematic/suarez_dac.kicad_sch').write_text(sch+'\n')
library='(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+ ' '.join(s.replace('"Sky130:','"') for s in lib)+')'
(P/'schematic/Sky130.kicad_sym').write_text(library+'\n')
(P/'schematic/sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Sky130") (type "KiCad") (uri "${KIPRJMOD}/Sky130.kicad_sym") (options "") (descr "SKY130 three-terminal circuit symbols")))\n')
(P/'schematic/suarez_dac.kicad_pro').write_text(json.dumps({'meta':{'filename':'suarez_dac.kicad_pro','version':1}},indent=2)+'\n')
print('Created KiCad schematic with',len(spec['devices']),'PDK devices')
