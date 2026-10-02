"""Keep current evidence, preserve development history, and build a compact release ZIP."""
from pathlib import Path
import json,hashlib,re,shutil,zipfile,datetime
P=Path(__file__).resolve().parents[1];V=P/'verification';Q=V/'signoff';BASE=Path('/foss/designs')
assert P.is_relative_to(BASE/'outputs')
sha=hashlib.sha256((P/'gds/tt_um_jonah_suarez_dac.gds').read_bytes()).hexdigest()
summary=json.loads((V/'summary.json').read_text());assert summary['gds_sha256']==sha and summary['full_code_sweeps']==9
H=BASE/'work'/('release_history_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));H.mkdir()
def archive(path):
    assert path.is_relative_to(P) and path!=P
    dest=H/path.relative_to(P);dest.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(path),str(dest))
allowed=set()
def companions(name,suffixes):
    for s in suffixes:allowed.add(name+s)
for f in Q.glob('*_case.json'):
    d=json.loads(f.read_text())
    if d.get('gds_sha256')==sha:companions(f.name[:-10],['.spice','.log','.txt','_case.json','_dut.spice','_result.json'])
for f in Q.glob('*_result.json'):
    d=json.loads(f.read_text())
    if d.get('gds_sha256')!=sha:continue
    allowed.add(f.name)
    if f.name.startswith('ac_'):companions(f.name[:-12],['.spice','.log','.txt','_op.txt','_loop.spice','_result.json'])
for d in json.loads((Q/'special_results.json').read_text()):
    if d['name'].startswith(('step_','hold_')):companions(d['name'],['.spice','.log','.txt'])
for d in json.loads((Q/'noise_results.json').read_text()):
    companions(f"noise_{d['corner']}_{d['temp_c']}",['.spice','.log','.txt','_spectrum.txt'])
allowed.update(['special_results.json','noise_results.json','ac_suite.json','pvt_suite.json','mc_suite.json','full_suite.json'])
for f in list(Q.iterdir()):
    if f.name not in allowed:archive(f)
keep={'signoff','precheck','layout_build.log','layout_geometry.json','lvs.log','gds_lvs.log','gds_drc.log','physical_checks.json','antenna.txt','model_cache.json','pex2.log','pex3.log','pex2_console.log','pex3_console.log','precheck_console.log','provenance.json','rebuild.json','schematic_connectivity.json','schematic_erc.rpt','schematic_netlist.xml','summary.json','verification.md','qualification.png','all_code_results.csv'}
for f in list(V.iterdir()):
    if f.name not in keep:archive(f)
# Preserve only the masters referenced by the delivered native top cell.
used={'tt_um_jonah_suarez_dac'};pending=list(used)
while pending:
    cell=pending.pop();text=(P/'layout'/(cell+'.mag')).read_text()
    for child in re.findall(r'^use\s+(\S+)',text,re.M):
        if child not in used:used.add(child);pending.append(child)
for f in (P/'layout').glob('*.mag'):
    if f.stem not in used:archive(f)
if (P/'build').exists():archive(P/'build')
for directory in [P/'scripts',P/'examples']:
    if (directory/'__pycache__').exists():archive(directory/'__pycache__')
paths=[]
for f in sorted(P.rglob('*')):
    if not f.is_file() or f.name=='manifest.json':continue
    rel=f.relative_to(P)
    if '__pycache__' in rel.parts or 'build' in rel.parts:continue
    # Code result JSON/CSV and logs retain measurements; raw vectors are local.
    if rel.parts[:2]==('verification','signoff'):
        if f.name.endswith('_dut.spice'):continue
        if f.suffix=='.txt' and not f.name.startswith(('step_','powerup','noise_','hold_')):continue
    paths.append(f)
manifest={'gds_sha256':sha,'status':summary['status'],'files':[{'path':str(f.relative_to(P)).replace('\\','/'),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in paths],'excluded':'development build trees, stale evidence, per-run DUT duplicates, and redundant raw waveform vectors; current raw vectors remain locally and scripts regenerate them'}
(P/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
zip_path=P.parent/'suarez_dac_sky130.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in paths+[P/'manifest.json']:z.write(f,arcname='suarez_dac/'+str(f.relative_to(P)).replace('\\','/'))
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    for record in manifest['files']:
        assert hashlib.sha256(z.read('suarez_dac/'+record['path'])).hexdigest()==record['sha256']
print(json.dumps({'zip':str(zip_path),'bytes':zip_path.stat().st_size,'files':len(paths)+1,'gds_sha256':sha,'zip_integrity':'all member hashes verified','development_history':str(H)},indent=2))
