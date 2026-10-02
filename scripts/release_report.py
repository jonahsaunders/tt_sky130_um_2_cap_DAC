"""Audit current-revision evidence and produce the qualification report and plots."""
from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET,csv,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from qualify import P,Q,metrics
V=P/'verification';TOP='tt_um_jonah_suarez_dac'
sha=hashlib.sha256((P/f'gds/{TOP}.gds').read_bytes()).hexdigest()
rcsha=hashlib.sha256((P/f'netlist/{TOP}.rc.spice').read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def current(path):
    d=read(path);assert d['gds_sha256']==sha,(path,'wrong GDS')
    return d
names=['full_'+c for c in ['tt','ss','ff','sf','fs']]+['full_worst_inl','full_worst_dnl','full_mc_1027','full_mc_1026']
full=[current(Q/(n+'_result.json')) for n in names]
for r in full:
    assert r['netlist_sha256']==rcsha and r['full_256_codes'] and [x['code'] for x in r['rows']]==list(range(256))
    assert r['monotonic'] and r['min_dnl_lsb']>-1 and r['max_endpoint_inl_lsb']<1,(r['name'],'linearity failure')
pvt=[current(Q/f'pvt_{i:02d}_result.json') for i in range(30)]
mc=[current(Q/f'mc_{i}_result.json') for i in range(1001,1033)]
for r in pvt+mc:
    assert r['netlist_sha256']==rcsha and r['monotonic']
    updated=metrics(r,r['rows'],r['max_supply_current_ua'],r['max_reference_current_ma']);r.update(updated)
ac=[read(f) for f in Q.glob('ac_*_result.json')];ac=[r for r in ac if r.get('gds_sha256')==sha]
assert len(ac)==120 and all(r['phase_margin_deg']>=60 and r['netlist_sha256']==rcsha for r in ac)
special=read(Q/'special_results.json');noise=read(Q/'noise_results.json')
assert all(r['gds_sha256']==sha and r['netlist_sha256']==rcsha for r in special+noise)
assert special[0]['passes_0p5lsb'] and special[-1]['passes']
steps=[r for r in special if r['name'].startswith('step_')]
assert max(s['settling_0p5lsb_us'] for r in steps for s in r['steps'])<=8
hold=[r for r in special if r['name'].startswith('hold_')]
assert all(abs(r['hold_drift_50us_lsb'])<.1 for r in hold)
physical=current(V/'physical_checks.json');geometry=current(V/'layout_geometry.json')
assert physical['antenna_feedback_count']==0 and physical['full_gds_drc_errors']==0
tests=list(ET.parse(V/'precheck/results.xml').getroot().iter('testcase'))
assert len(tests)==15 and all(not list(t) for t in tests)
assert re.search(r'\*\* ERC messages: 0\s+Errors 0\s+Warnings 0', (V/'schematic_erc.rpt').read_text())
schematic=read(V/'schematic_connectivity.json');assert schematic['verified_pin_connections']==72 and not schematic['mismatches']
rebuild=read(V/'rebuild.json');assert rebuild['netlist_identical'] and rebuild['gds_polygon_geometry_identical']
allcases=full+pvt+mc
assert max(r['max_reference_current_ma'] for r in allcases)<4 and max(r['max_supply_current_ua'] for r in allcases)<4000
summary={'status':'qualified experimental Tiny Tapeout analog macro','gds_sha256':sha,'rc_sha256':rcsha,'official_prechecks_passed':15,'native_and_gds_lvs':'unique match without property errors','gds_drc_errors':0,'antenna_feedback_count':0,'schematic_erc_errors':0,'schematic_connections_checked':72,'full_code_sweeps':len(full),'full_code_measurements':len(full)*256,'pvt_probe_points':30,'mismatch_seeds':32,'stability_cases':120,'min_phase_margin_deg':min(r['phase_margin_deg'] for r in ac),'worst_full_endpoint_inl_lsb':max(r['max_endpoint_inl_lsb'] for r in full),'min_full_dnl_lsb':min(r['min_dnl_lsb'] for r in full),'max_full_dnl_lsb':max(r['max_dnl_lsb'] for r in full),'max_pvt_probe_raw_error_lsb':max(r['max_raw_error_lsb'] for r in pvt),'mc_offset_range_mv':[min(r['endpoint_offset_mv'] for r in mc),max(r['endpoint_offset_mv'] for r in mc)],'mc_gain_error_range_pct':[min(r['endpoint_gain_error_pct'] for r in mc),max(r['endpoint_gain_error_pct'] for r in mc)],'max_supply_current_ua':max(r['max_supply_current_ua'] for r in allcases),'max_reference_current_ma':max(r['max_reference_current_ma'] for r in allcases),'limitations':['Offset/gain calibration required for precise absolute voltage','Discrete modeled PVT points and 32 mismatch seeds do not establish silicon yield','Full 0.7V buffer step can take about 6.4us at the cold/slow corner; actual DAC protocol is verified separately','References fixed at 0.2V and 0.9V; arbitrary reference range and clock-rate scaling unqualified','Continuous-time noise and kT/C estimate do not establish measured ENOB']}
(V/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with (V/'all_code_results.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['case','corner','supply_v','temp_c','load_pf','seed','code','output_v','raw_error_lsb','block'])
    for r in full:
        for row in r['rows']:writer.writerow([r['name'],r['corner'],r['supply_v'],r['temp_c'],r['load_pf'],r['mismatch_seed'],row['code'],row['output_v'],row['raw_error_lsb'],row.get('block','')])
fig,axs=plt.subplots(2,2,figsize=(12,9));colors=['#007d81','#d68128','#6e53a3','#438241','#bc4772']
for r,col in zip(full[:5],colors):
    codes=np.arange(256);volts=np.array([x['output_v'] for x in r['rows']]);slope=(volts[-1]-volts[0])/255;inl=(volts-(volts[0]+slope*codes))/slope;dnl=np.diff(volts)/slope-1
    axs[0,0].plot(codes,volts,color=col,label=r['corner'].upper());axs[0,1].plot(codes,inl,color=col);axs[1,0].plot(codes[1:],dnl,color=col)
axs[0,0].plot(np.arange(256),.2+.7*np.arange(256)/256,'k--',linewidth=.8,label='Ideal');axs[0,0].set(title='Full RC extracted transfer',ylabel='Output (V)');axs[0,0].legend()
axs[0,1].set(title='Endpoint INL · nominal supply and temperature',ylabel='LSB');axs[1,0].set(title='DNL · every adjacent code',ylabel='LSB')
axs[1,1].hist([r['endpoint_offset_mv'] for r in mc],bins=10,color='#007d81',edgecolor='white');axs[1,1].set(title='32 PDK mismatch seeds',xlabel='Buffer + DAC endpoint offset (mV)',ylabel='Samples')
for ax in axs.flat:
    ax.grid(alpha=.2)
for ax in [axs[0,0],axs[0,1],axs[1,0]]:ax.set_xlabel('Code')
fig.suptitle('Suarez DAC · SKY130 · final GDS qualification',fontsize=15);fig.tight_layout();fig.savefig(V/'qualification.png',dpi=180);plt.close(fig)
table='\n'.join(f"| {r['name']} | {r['corner']} | {r['supply_v']} | {r['temp_c']} | {r['load_pf']} | {r['max_endpoint_inl_lsb']:.3f} | {r['min_dnl_lsb']:.3f} to {r['max_dnl_lsb']:.3f} | {r['max_raw_error_lsb']:.3f} |" for r in full)
worst=max(s['settling_0p5lsb_us'] for r in steps for s in r['steps']);kick=max(abs(r['opposite_sample_kick_lsb']) for r in hold)
report=f'''# Tiny Tapeout qualification — Suarez serial DAC

The delivered SKY130 macro is ready for an experimental analog submission within the conditions below. Native layout and independently re-imported GDS pass DRC and LVS. Gate antenna checks pass. All 15 official Tiny Tapeout prechecks pass. The editable KiCad schematic has zero ERC violations and all 72 visible device connections match the circuit specification. A fresh build reproduces the circuit and every GDS polygon.

This is a two-capacitor serial charge-sharing converter with an additional buffer compensation capacitor. The two conversion banks are nominally 6.454 pF each, built from 16 MIM units per bank in a common-centroid pattern. Grounded shields limit sample/hold coupling. Low-threshold PMOS transmission-gate devices preserve charge transfer at low supply and cold temperature. The buffer uses approximately 80 kΩ and 1.373 pF compensation. MOS body connections are explicit in silicon and SPICE.

## Qualified use

Nominal supply 1.8 V; modeled supply boundaries 1.62 V and 1.98 V. Temperature samples −40, 27, and 85 °C. Five process corners TT, SS, FF, SF, FS. Fixed references 0.2 V and 0.9 V. Output load 5–20 pF with at least 10 MΩ DC impedance. Every analog-pad model includes 500 Ω series resistance; reference pads also include 5 pF. Control highs track VDPWR.

Initialize each word for 8 µs, then send eight bits LSB first with 2 µs charge, 0.2 µs dead time, 2 µs share, and 0.2 µs dead time. Read 3 µs after the last bit; an additional 0.5 µs gap gives 46.9 µs per word, or about 21.3 kwords/s. The simulator uses a conservative 7.9 µs active reset within the 8 µs initialization slot. The external controller supplies all phases; clk, ena, and rst_n do not sequence this macro. HIGH and LOW must never overlap. LOW and SHARE overlap only during initialization.

## Complete post-layout code measurements

All 256 codes were measured in each of nine conditions: five nominal process corners, the two worst observed PVT points, and the two worst observed mismatch samples. Each code uses the same initialization; eight codes are grouped per independent run to keep input waveform decks manageable. This gives 2,304 final-layout code measurements. All nine curves are strictly monotonic. Endpoint INL removes offset and gain; raw error retains them. Mismatch raw error is therefore larger than linearity error.

| Case | Process | VDD (V) | Temperature (°C) | Load (pF) | Max INL (LSB) | DNL range (LSB) | Max raw error (LSB) |
|---|---|---:|---:|---:|---:|---:|---:|
{table}

![Final transfer, INL, DNL, and offset distribution](qualification.png)

An additional 30 PVT points each measure ten selected codes, including 127/128 and both endpoints. All are monotonic at the measured codes; worst raw error is {summary['max_pvt_probe_raw_error_lsb']:.3f} LSB. This selected-code grid is not an exhaustive all-code test at every PVT point. Full sweeps target the worst grid points. One nominal LSB is 2.734375 mV. Nominal modeled linearity is assessed against ±1 LSB INL and strictly positive code steps, rather than a claim of eight-bit absolute accuracy.

## Stability, settling, retention, and noise

The actual extracted RC circuit was tested with Middlebrook voltage injection at the buffer feedback gate. 120 combinations cover five process corners, both supply boundaries, both temperature boundaries, three input voltages, and both load boundaries. Every case exceeds 60° phase margin; the minimum is {summary['min_phase_margin_deg']:.2f}°. Small-signal margins do not by themselves establish large-signal settling.

Power-up from zero stored voltages, a 10 µs supply ramp, and references established by 15 µs passes; conversion starts at 20 µs. The standalone buffer's worst measured full 0.7 V upward step settles within half an LSB in {worst:.2f} µs at SS/1.62 V/−40 °C/20 pF and can overshoot by about 248 mV. Allow 8 µs for such a full-range buffer step. The DAC's actual sequence produces smaller charge-sharing steps and is separately verified at the stated 3 µs read delay. Arbitrary rapid changes to the reference voltages are outside the qualified protocol.

At 85 °C, hold tests last almost 100 µs while the sample bank is driven to the opposite reference. This deliberately adversarial action produces up to {kick:.3f} LSB of immediate feedthrough; subsequent 50 µs leakage drift stays below {max(abs(r['hold_drift_50us_lsb']) for r in hold):.4f} LSB. Refresh periodically and do not alter the sample bank while expecting an unchanged held output.

Continuous-time buffer noise is integrated separately from sampled switch noise. The modeled buffer noise from 0.1 Hz to the 10.66 kHz conversion Nyquist frequency is {min(r['integrated_buffer_noise_0p1hz_to_nyquist_uv_rms'] for r in noise):.1f}–{max(r['integrated_buffer_noise_0p1hz_to_nyquist_uv_rms'] for r in noise):.1f} µV RMS in the three tested cases. The kT/C estimate for a 6.454 pF hold bank at 85 °C is about 27.7 µV RMS. These results do not establish measured ENOB, distortion, or dynamic silicon performance.

## Mismatch and calibration

32 PDK local-mismatch seeds were simulated with process mismatch disabled; process corners are tested separately. All selected-code curves are monotonic. Endpoint offset spans {summary['mc_offset_range_mv'][0]:.2f} to {summary['mc_offset_range_mv'][1]:.2f} mV. The input pair is small and untrimmed, so accurate absolute voltage requires calibration. Measure codes 0 and 255, fit voltage versus code, and map requested voltages into that measured range. The supplied controller example includes this mapping. Calibration cannot extend the measured endpoint range or remove all code-dependent nonlinearity.

Seeds 1027 (worst selected INL) and 1026 (worst offset/gain) additionally receive complete 256-code sweeps. Repeating the same seed reproduces the same outputs. These 32 samples characterize modeled sensitivity; they do not prove manufacturing yield or include wafer-scale capacitor gradients, package variation, or an exhaustive process distribution.

## Extraction and evidence integrity

Full RC extraction uses the installed SKY130 Magic technology and IIC OSIC extraction flow, with 1 Ω resistance gating/minimum resistance and zero delay cutoff. Raw extraction and reduced RC are both delivered. Reduction exactly eliminates only internal resistor nodes having no capacitance, device terminal, or external port. Every capacitive and device node is preserved. Measured differences between raw and reduced RC, cached and complete PDK models, and 100 ns and 25 ns maximum time steps are recorded in `signoff/special_results.json`; each is below 10 µV. The model cache preserves all geometry bins and global parameters of every used model family.

Peak supply current across the conversion qualification is {summary['max_supply_current_ua']:.1f} µA; peak reference-pad current is {summary['max_reference_current_ma']:.3f} mA, below the 4 mA analog-pad limit. Full-height metal-4 power stripes are 1.2 µm wide. The macro has exact 161 × 225.76 µm bounds, the official pin geometry, grounded unused digital outputs, isolated unallocated analog pads, and no metal 5.

Final GDS SHA-256: `{sha}`. Final reduced RC SHA-256: `{rcsha}`. Every qualification case records these hashes. `all_code_results.csv` contains all final full-sweep measurements. JSON results, decks, logs, model hashes, native layout, and generators make the checks auditable. Raw waveform vectors remain in the local results folder; the compact ZIP omits redundant per-run vectors and DUT snapshots, which the scripts regenerate.

The GitHub custom-GDS workflow and metadata follow the current official analog template. The package has not been uploaded, submitted, purchased, fabricated, or measured. Chip integration and silicon measurements remain the final confirmation of performance.

Sources: [Tiny Tapeout analog specifications](https://tinytapeout.com/specs/analog/), [official analog template](https://github.com/TinyTapeout/ttsky-analog-template), [official support tools](https://github.com/TinyTapeout/tt-support-tools), [IIC OSIC Tools](https://github.com/iic-jku/IIC-OSIC-TOOLS). Exact tool and repository versions are recorded in `provenance.json`.
'''
(V/'verification.md').write_text(report,encoding='utf-8')
print(json.dumps(summary,indent=2))
