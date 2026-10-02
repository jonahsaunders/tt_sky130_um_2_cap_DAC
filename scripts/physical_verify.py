"""Independent GDS re-import, full Magic DRC, and transistor-level LVS."""
from pathlib import Path
import os,subprocess,hashlib,json
P=Path(__file__).resolve().parents[1];TOP='tt_um_jonah_suarez_dac'
W=P/'build/gds_check';W.mkdir(parents=True,exist_ok=True);V=P/'verification'
rc='/foss/pdks/sky130A/libs.tech/magic/sky130A.magicrc'
tcl=f'''gds maskhints yes
gds read {P}/gds/{TOP}.gds
load {TOP}
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "GDS_DRC_COUNT [drc list count total]"
puts "GDS_DRC_DETAILS [drc listall why]"
flatten {TOP}_flat
load {TOP}_flat
extract all
feedback clear
antennacheck debug
antennacheck
puts "ANTENNA_COUNT [feedback count]"
feedback save {P}/verification/antenna.txt
ext2spice lvs
ext2spice short resistor
ext2spice subcircuit on
ext2spice -o {P}/netlist/gds_lvs.spice
quit -noprompt
'''
(W/'check.tcl').write_text(tcl)
with (V/'gds_drc.log').open('w') as log:subprocess.run(['magic','-dnull','-noconsole','-rcfile',rc,str(W/'check.tcl')],cwd=W,stdout=log,stderr=subprocess.STDOUT,check=True)
assert 'GDS_DRC_COUNT 0' in (V/'gds_drc.log').read_text()
assert 'ANTENNA_COUNT 0' in (V/'gds_drc.log').read_text(), 'Antenna violations; inspect antenna.txt'
for source,out in [('extracted_lvs.spice','lvs.log'),('gds_lvs.spice','gds_lvs.log')]:
    extracted_top=TOP+'_flat' if source=='gds_lvs.spice' else TOP
    with (W/(out+'.console')).open('w') as log:subprocess.run(['netgen','-batch','lvs',f'{P}/netlist/{source} {extracted_top}',f'{P}/netlist/{TOP}.spice {TOP}','/foss/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl',str(V/out)],stdout=log,stderr=subprocess.STDOUT,check=True)
    text=(V/out).read_text();assert 'Final result: Circuits match uniquely.' in text and 'Property errors were found' not in text
report={'gds_sha256':hashlib.sha256((P/f'gds/{TOP}.gds').read_bytes()).hexdigest(),'full_gds_drc_errors':0,'antenna_feedback_count':0,'native_lvs':'unique match, no property errors','gds_lvs':'unique match, no property errors','maskhints':True}
(V/'physical_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
