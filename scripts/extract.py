"""Extract coupled capacitance and full RC from the delivered GDS."""
from pathlib import Path
import subprocess,os,shutil
P=Path(__file__).resolve().parents[1];TOP='tt_um_jonah_suarez_dac'
env={**os.environ,'PDK':'sky130A','PDK_ROOT':'/foss/pdks','PDKPATH':'/foss/pdks/sky130A'}
for mode in [2,3]:
    w=P/f'build/pex{mode}';w.mkdir(parents=True,exist_ok=True)
    cmd=['sak-pex.sh','-m',str(mode),'-n',TOP+'_pex','-w',str(w)]
    if mode==3:cmd+=['-t','1000','-r','1000','-y','0']
    cmd+=[str(P/f'gds/{TOP}.gds')]
    with (P/f'verification/pex{mode}_console.log').open('w') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    dst=P/f'netlist/{TOP}.{"pex" if mode==2 else "rc_raw"}.spice'
    shutil.copy2(w/f'{TOP}.pex.spice',dst)
    shutil.copy2(w/f'{TOP}.pex.log',P/f'verification/pex{mode}.log')
subprocess.run(['python3',str(P/'scripts/reduce_rc.py'),str(P/f'netlist/{TOP}.rc_raw.spice'),str(P/f'netlist/{TOP}.rc.spice')],check=True)
print('Extracted coupled C, raw RC, and exact reduced RC')
