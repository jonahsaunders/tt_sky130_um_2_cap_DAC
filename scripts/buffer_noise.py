"""Closed-loop continuous-time buffer noise; sampled kT/C is reported separately."""
from pathlib import Path
import json,os,subprocess,hashlib
import numpy as np
from qualify import P,Q,header
RC=P/'netlist/tt_um_jonah_suarez_dac.rc.spice';results=[]
for corner,temp in [('tt',27),('ff',85),('ss',-40)]:
    name=f'noise_{corner}_{temp}';lines=header(corner,temp=temp,netlist=RC)
    lines+=['VH h 0 0','VL l 0 0','VS s 0 0','VFORCE XDUT.HOLD 0 .55 AC 1','.control','set num_threads=1','set wr_vecnames','set wr_singlescale','noise v(pad) VFORCE dec 100 .1 100Meg',f'wrdata {Q/name}.txt onoise_total inoise_total','setplot noise1',f'wrdata {Q/name}_spectrum.txt onoise_spectrum','quit','.endc','.end']
    (Q/(name+'.spice')).write_text('\n'.join(lines)+'\n');(Q/(name+'.txt')).unlink(missing_ok=True);(Q/(name+'_spectrum.txt')).unlink(missing_ok=True)
    with (Q/(name+'.log')).open('w') as log:subprocess.run(['ngspice','-b',str(Q/(name+'.spice'))],env={**os.environ,'OMP_THREAD_LIMIT':'1'},stdout=log,stderr=subprocess.STDOUT,check=True)
    d=np.loadtxt(Q/(name+'_spectrum.txt'),skiprows=1);assert np.isfinite(d).all() and d[-1,0]>=1e8
    mask=d[:,0]<=1/(2*46.9e-6);band=float(np.sqrt(np.trapezoid(d[mask,1]**2,d[mask,0]))*1e6)
    total=np.loadtxt(Q/(name+'.txt'),skiprows=1).reshape(-1);results.append({'corner':corner,'temp_c':temp,'integrated_buffer_noise_0p1hz_to_nyquist_uv_rms':band,'nyquist_hz':1/(2*46.9e-6),'wideband_noise_0p1hz_to_100mhz_uv_rms':float(total[1]*1e6),'gds_sha256':hashlib.sha256((P/'gds/tt_um_jonah_suarez_dac.gds').read_bytes()).hexdigest(),'netlist_sha256':hashlib.sha256(RC.read_bytes()).hexdigest()})
(Q/'noise_results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
