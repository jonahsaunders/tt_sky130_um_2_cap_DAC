from pathlib import Path
import argparse,re,json,subprocess,os,hashlib
import numpy as np
from qualify import P,Q,header,TOP
ap=argparse.ArgumentParser();ap.add_argument('--corner',default='tt');ap.add_argument('--supply',type=float,default=1.8);ap.add_argument('--temp',type=float,default=27);ap.add_argument('--load',type=float,default=5);ap.add_argument('--vin',type=float,default=.55);ap.add_argument('--rz-l',type=float);ap.add_argument('--cc-size',type=float);ap.add_argument('--netlist');a=ap.parse_args()
actual_l=next(d['l'] for d in json.loads((P/'design.json').read_text())['devices'] if d['role']=='RZ')
if a.rz_l is None:a.rz_l=actual_l
actual_cc=next(d['l'] for d in json.loads((P/'design.json').read_text())['devices'] if d['role']=='C_COMP')
if a.cc_size is None:a.cc_size=actual_cc
name=f'ac_{a.corner}_{a.supply}_{a.temp}_{a.load}_{a.vin}_rz{a.rz_l}_cc{a.cc_size}'
source=Path(a.netlist) if a.netlist else P/'netlist/tt_um_jonah_suarez_dac.rc.spice'
text=source.read_text();new=[];changes=0
for line in text.splitlines():
    tok=line.split()
    if tok and tok[0].startswith('X') and len(tok)>5 and tok[2].startswith('ua[1]') and 'sky130_fd_pr__pfet_01v8_lvt' in tok:
        gate=tok[2];tok[2]='FBX';line=' '.join(tok);changes+=1
    if 'sky130_fd_pr__res_xhigh_po_0p35' in line and re.search(r'\bl='+str(actual_l)+r'\b',line):line=re.sub(r'\bl='+str(actual_l)+r'\b',f'l={a.rz_l}',line)
    if 'sky130_fd_pr__cap_mim_m3_1' in line and f'l={actual_cc} w={actual_cc}' in line:line=line.replace(f'l={actual_cc} w={actual_cc}',f'l={a.cc_size} w={a.cc_size}')
    new.append(line)
assert changes==1
net=Q/(name+'_loop.spice');net.write_text('\n'.join(new)+'\n')
lines=header(a.corner,a.supply,a.temp,a.load,net)
lines+=['VH h 0 0','VL l 0 0','VS s 0 0',f'VFORCE XDUT.HOLD 0 {a.vin}',f'VINJECT XDUT.FBX XDUT.{gate} 0 AC 1',f'EOBS return 0 XDUT.{gate} 0 1','.control','set wr_vecnames','set wr_singlescale','op',f'wrdata {Q/name}_op.txt v(out) i(VDD)','ac dec 100 1 1G',f'wrdata {Q/name}.txt v(return) v(XDUT.FBX)','quit','.endc','.end']
(Q/(name+'.spice')).write_text('\n'.join(lines)+'\n')
(Q/(name+'.txt')).unlink(missing_ok=True)
(Q/(name+'_op.txt')).unlink(missing_ok=True)
with (Q/(name+'.log')).open('w') as log:subprocess.run(['ngspice','-b',str(Q/(name+'.spice'))],env={**os.environ,'OMP_NUM_THREADS':'1','OMP_THREAD_LIMIT':'1','OPENBLAS_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,check=True)
d=np.loadtxt(Q/(name+'.txt'),skiprows=1);freq=d[:,0];out=d[:,1]+1j*d[:,2];fb=d[:,3]+1j*d[:,4];loop=-out/fb;gain=20*np.log10(abs(loop));phase=np.unwrap(np.angle(loop))*180/np.pi
assert np.isfinite(d).all() and freq[-1]>=1e9 and len(freq)>=900, 'Incomplete AC data'
cross=np.where((gain[:-1]>=0)&(gain[1:]<0))[0];pm=None;ugf=None
if len(cross):
    i=cross[0];alpha=gain[i]/(gain[i]-gain[i+1]);ugf=float(np.exp(np.log(freq[i])*(1-alpha)+np.log(freq[i+1])*alpha));pm=float(180+phase[i]*(1-alpha)+phase[i+1]*alpha)
res={'name':name,**vars(a),'netlist_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'gds_sha256':hashlib.sha256((P/'gds/tt_um_jonah_suarez_dac.gds').read_bytes()).hexdigest(),'dc_gain_db':float(gain[0]),'unity_gain_hz':ugf,'phase_margin_deg':pm,'passes_60deg':pm is not None and pm>=60}
(Q/(name+'_result.json')).write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
