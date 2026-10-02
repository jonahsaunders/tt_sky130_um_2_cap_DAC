"""Power-up, numerical/model equivalence, retention, and buffer step checks."""
from pathlib import Path
import concurrent.futures,hashlib,json,os,re,subprocess,time
import numpy as np
from qualify import P,Q,TOP,header,transient,run
RC=P/'netlist/tt_um_jonah_suarez_dac.rc.spice'
def simulate(name,lines):
    lines=[l.replace('.control','.control\nset num_threads=1') for l in lines]
    (Q/(name+'.spice')).write_text('\n'.join(lines)+'\n');(Q/(name+'.txt')).unlink(missing_ok=True)
    with (Q/(name+'.log')).open('w') as log:
        subprocess.run(['ngspice','-b',str(Q/(name+'.spice'))],env={**os.environ,'OMP_NUM_THREADS':'1','OMP_THREAD_LIMIT':'1'},stdout=log,stderr=subprocess.STDOUT,check=True)
    a=np.loadtxt(Q/(name+'.txt'),skiprows=1);assert np.isfinite(a).all()
    return a
def steps(corner,supply,temp,load):
    name=f'step_{corner}_{supply}_{temp}_{load}';lines=header(corner,supply,temp,load,RC)
    lines+=['VH h 0 0','VL l 0 0','VS s 0 0','VFORCE XDUT.HOLD 0 PWL(0 .2 2u .2 2.001u .9 12u .9 12.001u .2)','.control','set wr_vecnames','set wr_singlescale','tran 25n 22u 0 25n',f'wrdata {Q/name}.txt v(pad) i(VDD)','quit','.endc','.end']
    a=simulate(name,lines);assert a[-1,0]>=22e-6;results=[]
    for start,end,up in [(2e-6,12e-6,True),(12e-6,22e-6,False)]:
        seg=a[(a[:,0]>=start+.001e-6)&(a[:,0]<=end)]
        final=float(np.mean(seg[-20:,1]));outside=np.where(abs(seg[:,1]-final)>.7/512)[0]
        settle=float((seg[outside[-1],0]-start)*1e6) if len(outside) else 0
        overshoot=float((max(seg[:,1])-final if up else final-min(seg[:,1]))*1e3)
        results.append({'direction':'up' if up else 'down','settling_0p5lsb_us':settle,'overshoot_mv':overshoot,'final_v':final})
    return {**meta(name),'corner':corner,'supply_v':supply,'temp_c':temp,'load_pf':load,'steps':results,'passes_3us':all(r['settling_0p5lsb_us']<=3 for r in results)}
def meta(name):return {'name':name,'gds_sha256':hashlib.sha256((P/'gds/tt_um_jonah_suarez_dac.gds').read_bytes()).hexdigest(),'netlist_sha256':hashlib.sha256(RC.read_bytes()).hexdigest()}
def startup():
    name='powerup';transient(name,[255],netlist=RC,step_ns=25)
    f=Q/(name+'.spice');text=f.read_text()
    for key in ['h','l','s']:
        text=re.sub(r'^V'+key+r' .+$',lambda m:re.sub(r'([\d.]+)u',lambda n:f'{float(n[1])+20:.6f}u',m[0]).replace('PWL(','PWL(0 0 '),text,flags=re.M)
    text=text.replace('VDD vdd 0 1.8','VDD vdd 0 PWL(0 0 10u 1.8)').replace('VHI refh 0 .9','VHI refh 0 PWL(0 0 10u 0 15u .9)').replace('VLO refl 0 .2','VLO refl 0 PWL(0 0 10u 0 15u .2)')
    text=text.replace('tran 25n 46.900000u 0 25n','tran 25n 66.900000u 0 25n uic')
    f.write_text(text);case=json.loads((Q/(name+'_case.json')).read_text());case['measurements'][0]['time_us']+=20;(Q/(name+'_case.json')).write_text(json.dumps(case,indent=2))
    run(name);r=json.loads((Q/(name+'_result.json')).read_text());return {**meta(name),'raw_error_lsb':r['max_raw_error_lsb'],'passes_0p5lsb':r['max_raw_error_lsb']<=.5,'supply_ramp_us':10,'reference_ramp_end_us':15,'sequence_start_us':20,'initial_state':'UIC zero stored voltages'}
def retention(corner,temp,code):
    name=f'hold_{corner}_{temp}_{code}';transient(name,[code],corner=corner,temp=temp,netlist=RC)
    f=Q/(name+'.spice');text=f.read_text().replace('tran 100n 46.900000u 0 100n','tran 100n 146.900000u 0 100n')
    # Keep the sample bank at the opposite reference during retention.
    key='l' if code==255 else 'h';text=re.sub(r'^V'+key+r' (.+)PWL\((.+)\)$',lambda m:'V'+key+' '+m[1]+'PWL('+m[2]+' 47u 0 47.005u 1.8)',text,flags=re.M)
    a=simulate(name,text.splitlines());assert a[-1,0]>=146.9e-6
    v0=float(np.interp(48e-6,a[:,0],a[:,1]));v50=float(np.interp(98e-6,a[:,0],a[:,1]));v100=float(np.interp(146.9e-6,a[:,0],a[:,1]));coupling=float((np.interp(48e-6,a[:,0],a[:,1])-np.interp(46.4e-6,a[:,0],a[:,1]))/(.7/256))
    return {**meta(name),'corner':corner,'temp_c':temp,'code':code,'opposite_sample_kick_lsb':coupling,'hold_drift_50us_lsb':(v50-v0)/(.7/256),'hold_drift_98p9us_lsb':(v100-v0)/(.7/256)}
def numerical():
    cases=[('numeric_100',100,None,False),('numeric_25',25,None,False),('model_full',100,None,True),('rc_unreduced',100,P/'netlist/tt_um_jonah_suarez_dac.rc_raw.spice',False),('seed_repeat_a',100,None,False),('seed_repeat_b',100,None,False)]
    for n,step,net,full in cases:
        if full:os.environ['SKY130_FULL_MODELS']='1'
        else:os.environ.pop('SKY130_FULL_MODELS',None)
        transient(n,[0,127,128,255],step_ns=step,netlist=net or RC,seed=1001 if n.startswith('seed_repeat') else None);run(n)
    r={n:json.loads((Q/(n+'_result.json')).read_text()) for n,*_ in cases};baseline=np.array([x['output_v'] for x in r['numeric_100']['rows']]);diff={n:float(np.max(abs(np.array([x['output_v'] for x in r[n]['rows']])-baseline))*1e6) for n in ['numeric_25','model_full','rc_unreduced']}
    repeat=float(max(abs(x['output_v']-y['output_v']) for x,y in zip(r['seed_repeat_a']['rows'],r['seed_repeat_b']['rows']))*1e6)
    return {**meta('equivalence'),'max_output_difference_uv':diff,'same_seed_repeat_difference_uv':repeat,'passes':all(v<10 for v in diff.values()) and repeat==0}
result=[startup(),*[steps(*c) for c in [('tt',1.8,27,5),('ss',1.62,-40,20),('ff',1.98,-40,5)]],*[retention(c,85,k) for c in ['tt','ff'] for k in [0,255]],numerical()]
(Q/'special_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
