"""Generate, run, and measure transistor-level signoff cases from extracted SPICE."""
from pathlib import Path
import argparse, json, re, subprocess, os, time, hashlib, shutil
import numpy as np

P=Path(__file__).resolve().parents[1]
Q=P/'verification/signoff';Q.mkdir(exist_ok=True)
TOP='tt_um_jonah_suarez_dac_pex'

def ports(netlist):
    text=re.sub(r'\n\+', ' ',netlist.read_text())
    return next(x.split()[2:] for x in text.splitlines() if x.lower().startswith('.subckt '+TOP+' '))

def header(corner='tt',supply=1.8,temp=27,load=5,netlist=None,seed=None):
    netlist=Path(netlist) if netlist else P/'netlist/tt_um_jonah_suarez_dac.pex.spice'
    pp=ports(netlist)
    cached=P/f'sim/models/sky130_{corner}.spice'
    model=f'.include {cached}' if cached.exists() and not os.getenv('SKY130_FULL_MODELS') else f'.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice {corner}'
    lines=['* Suarez DAC extracted-layout qualification',model,f'.include {netlist}',f'.temp {temp}',f'VDD vdd 0 {supply}','VHI refh 0 .9','VLO refl 0 .2','RHI refh hi 500','RLO refl lo 500','CHI hi 0 5p','CLO lo 0 5p','ROUT out pad 500',f'COUT pad 0 {load}p','RLOAD pad 0 10Meg']
    mp={'VGND':'0','VDPWR':'vdd','ua[0]':'hi','ua[1]':'out','ua[2]':'lo','ui_in[0]':'h','ui_in[1]':'l','ui_in[2]':'s'}
    for n in pp:
        if n not in mp:
            mp[n]='unused_'+re.sub(r'\W','_',n)
            lines.append('Rfixture_'+re.sub(r'\W','_',n)+' '+mp[n]+' 0 1T')
    lines+=['XDUT '+' '.join(mp[n] for n in pp)+' '+TOP,f'.options method={os.getenv("SPICE_METHOD","trap")} reltol=1e-5 abstol=1e-13 vntol=1e-7']
    if seed is not None:lines+=['.param mc_mm_switch=1 mc_pr_switch=0']
    return lines

def transient(name,codes,corner='tt',supply=1.8,temp=27,load=5,step_ns=100,seed=None,netlist=None):
    source=Path(netlist) if netlist else P/'netlist/tt_um_jonah_suarez_dac.pex.spice'
    snapshot=Q/(name+'_dut.spice');shutil.copy2(source,snapshot)
    lines=header(corner,supply,temp,load,snapshot,seed);waves={k:[(0,0)] for k in ['h','l','s']};now=0;measures=[]
    def event(t,h,l,s):
        for k,v in zip(waves,[h,l,s]):
            if waves[k][-1][1]!=v:waves[k]+=[(t,waves[k][-1][1]),(t+.005,v)]
    for code in codes:
        event(now+.1,0,supply,supply);now+=8;event(now,0,0,0);now+=.2
        for bit in range(8):
            one=(code>>bit)&1;event(now,supply*one,supply*(1-one),0);now+=2;event(now,0,0,0);now+=.2
            event(now,0,0,supply);now+=2;event(now,0,0,0);now+=.2
        now+=3;measures.append({'code':code,'time_us':now,'ideal_v':.2+.7*code/256});now+=.5
    for k in waves:
        waves[k].append((now,waves[k][-1][1]));lines+=['V'+k+' '+k+' 0 PWL('+' '.join(f'{t:.6f}u {v}' for t,v in waves[k])+')']
    lines+=['.control','set num_threads=1','set wr_vecnames','set wr_singlescale']
    if seed is not None:lines += [f'setseed {seed}','reset']
    lines += [f'tran {step_ns}n {now:.6f}u 0 {step_ns}n',f'wrdata {Q/name}.txt v(XDUT.HOLD) v(out) v(pad) i(VDD) i(VHI) i(VLO)','quit','.endc','.end']
    (Q/(name+'.spice')).write_text('\n'.join(lines)+'\n')
    modelfile=P/f'sim/models/sky130_{corner}.spice'
    modelhash=hashlib.sha256(modelfile.read_bytes()).hexdigest() if modelfile.exists() and not os.getenv('SKY130_FULL_MODELS') else None
    (Q/(name+'_case.json')).write_text(json.dumps({'name':name,'corner':corner,'supply_v':supply,'temp_c':temp,'load_pf':load,'step_ns':step_ns,'mismatch_seed':seed,'netlist':str(source),'netlist_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'gds_sha256':hashlib.sha256((P/'gds/tt_um_jonah_suarez_dac.gds').read_bytes()).hexdigest(),'model_sha256':modelhash,'measurements':measures},indent=2)+'\n')
    return name

def run(name):
    t=time.time()
    (Q/(name+'.txt')).unlink(missing_ok=True)
    (Q/(name+'_result.json')).unlink(missing_ok=True)
    with (Q/(name+'.log')).open('w') as log:
        r=subprocess.run(['ngspice','-b',str(Q/(name+'.spice'))],env={**os.environ,'OMP_NUM_THREADS':'1','OMP_THREAD_LIMIT':'1','OPENBLAS_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT)
    logtext=(Q/(name+'.log')).read_text()
    if r.returncode or not (Q/(name+'.txt')).exists() or 'No. of Data Rows' not in logtext or re.search(r'(?im)^Error|timestep too small|doAnalyses:.*failed',logtext):raise RuntimeError(f'{name} failed; inspect log')
    analyze(name)
    print(name,'done in',round(time.time()-t,1),'s',flush=True)

def analyze(name):
    case=json.loads((Q/(name+'_case.json')).read_text());a=np.loadtxt(Q/(name+'.txt'),skiprows=1);rows=[]
    assert np.isfinite(a).all() and a[-1,0]>=case['measurements'][-1]['time_us']*1e-6, 'Incomplete transient data'
    for m in case['measurements']:
        t=m['time_us']*1e-6;v=float(np.interp(t,a[:,0],a[:,3]));settle=a[(a[:,0]>=t-.5e-6)&(a[:,0]<=t),3]
        rows.append({**m,'output_v':v,'raw_error_lsb':(v-m['ideal_v'])/(.7/256),'last_500ns_ripple_uv':float(np.ptp(settle)*1e6)})
    result=metrics(case,rows,float(np.max(np.abs(a[:,4]))*1e6),float(np.max(np.abs(a[:,5:7]))*1e3))
    (Q/(name+'_result.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2),flush=True)

def metrics(case,rows,supply_current,reference_current):
    v=np.array([r['output_v'] for r in rows]);codes=np.array([r['code'] for r in rows]);full=np.array_equal(codes,np.arange(256));dnl=None;inl=None
    if full:
        slope=(v[-1]-v[0])/255;dnl=np.diff(v)/slope-1;inl=(v-(v[0]+slope*codes))/slope
    result={k:v for k,v in case.items() if k!='measurements'}
    result.update(rows=rows,full_256_codes=full,monotonic=bool(np.all(np.diff(v[np.argsort(codes)])>0)),max_raw_error_lsb=float(max(abs(r['raw_error_lsb']) for r in rows)),max_ripple_uv=float(max(r['last_500ns_ripple_uv'] for r in rows)),max_supply_current_ua=supply_current,max_reference_current_ma=reference_current)
    if full:result.update(max_endpoint_inl_lsb=float(max(abs(inl))),min_dnl_lsb=float(min(dnl)),max_dnl_lsb=float(max(dnl)),endpoint_offset_mv=float((v[0]-.2)*1e3),endpoint_gain_error_pct=float((slope/(.7/256)-1)*100))
    elif codes[0]==0 and codes[-1]==255:
        slope=(v[-1]-v[0])/255;selected_inl=(v-(v[0]+slope*codes))/slope;adjacent=np.diff(codes)==1
        result.update(selected_endpoint_inl_lsb=float(max(abs(selected_inl))),selected_min_dnl_lsb=float(min(np.diff(v)[adjacent]/slope-1)),selected_max_dnl_lsb=float(max(np.diff(v)[adjacent]/slope-1)),endpoint_offset_mv=float((v[0]-.2)*1e3),endpoint_gain_error_pct=float((slope/(.7/256)-1)*100))
    return result

def full_blocks(a):
    parts=[]
    for start in range(0,256,8):
        n=a.name+f'_block{start:03d}'
        transient(n,list(range(start,start+8)),a.corner,a.supply,a.temp,a.load,a.step,a.seed,a.netlist);run(n)
        parts.append(json.loads((Q/(n+'_result.json')).read_text()))
    result=metrics({**parts[0],'name':a.name,'block_count':32,'block_method':'8 ascending codes per independent run; same 8us initialization for every code'},[r for part in parts for r in part['rows']],max(p['max_supply_current_ua'] for p in parts),max(p['max_reference_current_ma'] for p in parts))
    (Q/(a.name+'_result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['probe','full','run','analyze']);ap.add_argument('--name',default='shield_probe');ap.add_argument('--corner',default='tt');ap.add_argument('--temp',type=float,default=27);ap.add_argument('--supply',type=float,default=1.8);ap.add_argument('--load',type=float,default=5);ap.add_argument('--step',type=float,default=100);ap.add_argument('--seed',type=int);ap.add_argument('--netlist');a=ap.parse_args()
    if a.action=='full':full_blocks(a)
    elif a.action=='probe':
        transient(a.name,[0,1,15,63,127,128,129,192,254,255],a.corner,a.supply,a.temp,a.load,a.step,a.seed,a.netlist)
        run(a.name)
    elif a.action=='run':run(a.name)
    else:analyze(a.name)
