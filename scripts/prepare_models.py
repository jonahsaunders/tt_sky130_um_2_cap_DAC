"""Cache exact PDK model families used by this circuit; retain all bins and globals."""
from pathlib import Path
import subprocess,re,hashlib,json,os
P=Path(__file__).resolve().parents[1];W=P/'build/model_cache';W.mkdir(parents=True,exist_ok=True);OUT=P/'sim/models';OUT.mkdir(exist_ok=True)
source=Path('/foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice')
alias=W/'pdk'
if not alias.exists():alias.symlink_to('/foss/pdks/sky130A',target_is_directory=True)
alias_parent=alias/'libs.tech/ngspice'
main=source.read_text()
main=re.sub(r'(?m)^(\.include)\s+"([^"]+)"',lambda m:f'{m[1]} "{os.path.normpath(alias_parent/m[2])}"',main)
(W/'sky130.lib.spice').write_text(main)
wanted={'sky130_fd_pr__nfet_01v8','sky130_fd_pr__pfet_01v8','sky130_fd_pr__pfet_01v8_lvt','sky130_fd_pr__cap_mim_m3_1','sky130_fd_pr__res_xhigh_po_0p35','sky130_fd_pr__res_xhigh_po__base'}
report=[]
for corner in ['tt','ss','ff','sf','fs']:
    with (W/(corner+'.log')).open('w') as log:subprocess.run(['python3','/foss/tools/sak/sak-spice-model-red.py',str(W/'sky130.lib.spice'),corner],cwd=W,stdout=log,stderr=subprocess.STDOUT,check=True)
    text=(W/f'sky130.lib.spice.{corner}.red').read_text();lines=[];depth=0;active=True;found=set()
    for line in text.splitlines():
        t=line.lower().split()
        if t and t[0]=='.subckt':
            if depth==0:active=t[1] in wanted
            depth+=1
            if active:found.add(t[1])
        if t and t[0]=='.endl':continue
        if active:lines.append(line)
        if t and t[0]=='.ends':
            depth-=1
            if depth==0:active=True
    assert wanted<=found and depth==0,(found,depth)
    preamble='* Derived from the unmodified SkyWater SKY130 PDK, Copyright 2020 The SkyWater PDK Authors.\n* Licensed under Apache License 2.0, https://www.apache.org/licenses/LICENSE-2.0\n* All parameter expressions and all geometry bins of each used model retained.\n'
    f=OUT/f'sky130_{corner}.spice';f.write_text(preamble+'\n'.join(lines)+'\n')
    report.append({'corner':corner,'flat_bytes':len(text),'cached_bytes':f.stat().st_size,'families':sorted(wanted),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(P/'verification/model_cache.json').write_text(json.dumps({'pdk_source':str(source),'pdk_library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'method':'IIC OSIC sak-spice-model-red flattening, then remove unused subcircuit families; all global parameters and used-family bins preserved','corners':report},indent=2)+'\n')
print(json.dumps(report,indent=2))
