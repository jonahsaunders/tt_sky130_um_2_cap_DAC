from pathlib import Path
import xml.etree.ElementTree as ET
import json,hashlib
import cairosvg
from PIL import Image

P=Path(__file__).resolve().parents[1]
s=json.loads((P/'design.json').read_text())
t=ET.parse(P/'verification/schematic_netlist.xml').getroot()
actual={}
for net in t.findall('nets/net'):
    name=net.attrib['name'].lstrip('/')
    for node in net.findall('node'):
        actual[(node.attrib['ref'],node.attrib['pin'])]=name
expected={}
for d in s['devices']:
    if d['kind']=='mos':pins={'1':d['d'],'2':d['g'],'3':d['s']}
    else:pins={'1':d['a'],'2':d['b']}
    for n,v in pins.items():expected[(d['name'],n)]=v
bad=[dict(ref=k[0],pin=k[1],expected=v,actual=actual.get(k)) for k,v in expected.items() if actual.get(k)!=v]
components={c.attrib['ref']:c for c in t.findall('components/comp')}
parts={(p.attrib['lib'],p.attrib['part']):p for p in t.findall('libparts/libpart')}
property_bad=[];symbol_bad=[]
for d in s['devices']:
    c=components[d['name']]
    fields={f.attrib['name']:f.text or '' for f in c.findall('fields/field')}
    values={'Role':d['role'],'PDK_Model':d['model'],'W_um':str(d['w']),'L_um':str(d['l']),
            'Bulk':d['b'] if d['kind']=='mos' else d.get('bulk','')}
    if d['kind']!='mos':values['Multiplicity']=str(d.get('m',1))
    for key,value in values.items():
        if fields.get(key)!=value:property_bad.append({'ref':d['name'],'field':key,'expected':value,'actual':fields.get(key)})
    source=c.find('libsource')
    pins={p.attrib['num']:p.attrib['name'] for p in parts[(source.attrib['lib'],source.attrib['part'])].findall('pins/pin')}
    wanted={'1':'D','2':'G','3':'S'} if d['kind']=='mos' else {'1':'1','2':'2'}
    if pins!=wanted:symbol_bad.append({'ref':d['name'],'expected':wanted,'actual':pins})
report={'device_count':len(s['devices']),'verified_pin_connections':len(expected),'mismatches':bad,'visible_mos_pin_count':3,'bulk_policy':s['bulk_policy']}
report.update(verified_device_properties=len(s['devices']),property_mismatches=property_bad,symbol_pin_mismatches=symbol_bad)
report['schematic_sha256']=hashlib.sha256((P/'schematic/suarez_dac.kicad_sch').read_bytes()).hexdigest()
report['exported_netlist_sha256']=hashlib.sha256((P/'verification/schematic_netlist.xml').read_bytes()).hexdigest()
(P/'verification/schematic_connectivity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
if bad or property_bad or symbol_bad:raise SystemExit(1)
svg=next((P/'schematic/render').glob('*.svg'))
cairosvg.svg2png(url=str(svg),write_to=str(P/'schematic/suarez_dac.png'),output_width=3000)
im=Image.open(P/'schematic/suarez_dac.png')
for name,(x,y,w,h) in {'core':(12,29,201,155),'buffer':(216,29,192,226),'control':(12,185,201,70)}.items():
    box=(x/420*im.width,y/297*im.height,(x+w)/420*im.width,(y+h)/297*im.height)
    im.crop(box).save(P/'schematic/render'/f'{name}.png')
out=P/'docs/images';out.mkdir(parents=True,exist_ok=True)
im.crop((12/420*im.width,29/297*im.height,408/420*im.width,255/297*im.height)).save(out/'schematic_overview.png')
