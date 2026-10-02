"""Verify deterministic circuit and polygon geometry reproduction in a fresh tree."""
from pathlib import Path
import tempfile,shutil,subprocess,json
import klayout.db as db
P=Path(__file__).resolve().parents[1]
W=Path(tempfile.mkdtemp(prefix='rebuild_',dir=P/'build'));(W/'layout').mkdir()
shutil.copytree(P/'scripts',W/'scripts');shutil.copy2(P/'layout/pin_template.def',W/'layout/pin_template.def')
for script in ['build_circuit.py','build_layout.py']:
    with (W/(script+'.log')).open('w') as log:subprocess.run(['python3',str(W/'scripts'/script)],stdout=log,stderr=subprocess.STDOUT,check=True)
assert (W/'netlist/tt_um_jonah_suarez_dac.spice').read_bytes()==(P/'netlist/tt_um_jonah_suarez_dac.spice').read_bytes()
designs=[]
for root in [P,W]:
    ly=db.Layout();ly.read(str(root/'gds/tt_um_jonah_suarez_dac.gds'));designs.append(ly)
layers=set((li.layer,li.datatype) for ly in designs for li in ly.layer_infos())
for layer in layers:
    regions=[db.Region(ly.top_cell().begin_shapes_rec(ly.layer(*layer))) for ly in designs]
    assert (regions[0]^regions[1]).is_empty(),layer
report={'netlist_identical':True,'gds_polygon_geometry_identical':True,'layer_count':len(layers),'scripts_executed':['build_circuit.py','build_layout.py']}
(P/'verification/rebuild.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
