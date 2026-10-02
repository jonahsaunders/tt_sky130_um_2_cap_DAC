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
report={'device_count':len(s['devices']),'verified_pin_connections':len(expected),'mismatches':bad,'visible_mos_pin_count':3,'bulk_policy':s['bulk_policy']}
report['schematic_sha256']=hashlib.sha256((P/'schematic/suarez_dac.kicad_sch').read_bytes()).hexdigest()
report['exported_netlist_sha256']=hashlib.sha256((P/'verification/schematic_netlist.xml').read_bytes()).hexdigest()
(P/'verification/schematic_connectivity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
if bad:raise SystemExit(1)
svg=next((P/'schematic/render').glob('*.svg'))
cairosvg.svg2png(url=str(svg),write_to=str(P/'schematic/suarez_dac.png'),output_width=3000)
im=Image.open(P/'schematic/suarez_dac.png')
for name,(x,y,w,h) in {'core':(10,25,255,100),'buffer':(150,129,258,119),'control':(12,129,135,119)}.items():
    box=(x/420*im.width,y/297*im.height,(x+w)/420*im.width,(y+h)/297*im.height)
    im.crop(box).save(P/'schematic/render'/f'{name}.png')
