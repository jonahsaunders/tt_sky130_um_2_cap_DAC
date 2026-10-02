from pathlib import Path
import json, numpy as np
p=Path(__file__).resolve().parents[1]
meas=json.loads((p/'sim/measurements.json').read_text())
for corner in ['tt','ss','ff','pex_tt']:
    f=p/f'verification/transfer_{corner}.txt'
    if not f.exists():continue
    a=np.loadtxt(f,skiprows=1)
    rows=[]
    for m in meas:
        hold=float(np.interp(m['time_us']*1e-6,a[:,0],a[:,2]))
        out=float(np.interp(m['time_us']*1e-6,a[:,0],a[:,4]))
        rows.append({**m,'hold_v':hold,'output_v':out,'error_mv':1000*(out-m['ideal_v']),'error_lsb':(out-m['ideal_v'])/(.7/256)})
    res={'corner':corner,'rows':rows,'max_abs_error_mv':max(abs(r['error_mv']) for r in rows),'selected_codes_monotonic':bool(np.all(np.diff([r['output_v'] for r in rows])>0))}
    (p/f'verification/transfer_{corner}_summary.json').write_text(json.dumps(res,indent=2)+'\n')
    print(json.dumps(res,indent=2))
