from pathlib import Path
import json, shutil

ROOT = Path(__file__).resolve().parents[1]
for d in ['schematic','netlist','layout','gds','lef','src','docs','verification','scripts','sim']:
    (ROOT/d).mkdir(parents=True,exist_ok=True)
TOP='tt_um_jonah_suarez_dac'
dev=[]
def fet(name,typ,d,g,s,w,l):
    dev.append(dict(name='M'+str(1+len(dev)),role=name,kind='mos',model='sky130_fd_pr__'+typ,d=d,g=g,s=s,b='VDPWR' if typ.startswith('p') else 'VGND',w=w,l=l))
for name,signal in [('H','ui_in[0]'),('L','ui_in[1]'),('S','ui_in[2]')]:
    fet('MN_INV_'+name,'nfet_01v8',name+'_BAR',signal,'VGND',1,0.15)
    fet('MP_INV_'+name,'pfet_01v8',name+'_BAR',signal,'VDPWR',2,0.15)
for name,a,b,g in [('H','ua[0]','SAMPLE','ui_in[0]'),('L','ua[2]','SAMPLE','ui_in[1]'),('S','SAMPLE','HOLD','ui_in[2]')]:
    fet('MN_SW_'+name,'nfet_01v8',a,g,b,1,0.15)
    fet('MP_SW_'+name,'pfet_01v8_lvt',a,name+'_BAR',b,2,0.35)
fet('MP_BIAS','pfet_01v8','BIAS','BIAS','VDPWR',4,2)
fet('MP_TAIL','pfet_01v8','TAIL','BIAS','VDPWR',4,2)
fet('MP_INP','pfet_01v8_lvt','AMP','HOLD','TAIL',4,1)
fet('MP_INM','pfet_01v8_lvt','MIRROR','ua[1]','TAIL',4,1)
fet('MN_MIRROR','nfet_01v8','MIRROR','MIRROR','VGND',4,2)
fet('MN_LOAD','nfet_01v8','AMP','MIRROR','VGND',4,2)
fet('MP_OUT','pfet_01v8','ua[1]','BIAS','VDPWR',24,2)
fet('MN_OUT','nfet_01v8','ua[1]','AMP','VGND',20,1)
for i,(a,b) in enumerate([('BIAS','RBMID'),('RBMID','VGND')]):
    dev.append(dict(name=f'R{i+1}',role=f'RB{i+1}',kind='resistor',model='sky130_fd_pr__res_xhigh_po_0p35',a=a,b=b,bulk='VGND',w=.35,l=30))
for role in ['SAMPLE','HOLD']:
    dev.append(dict(name='C1' if role=='SAMPLE' else 'C2',role='C_'+role,kind='capacitor',model='sky130_fd_pr__cap_mim_m3_1',a=role,b='VGND',w=14,l=14,m=16))
dev.append(dict(name='R3',role='RZ',kind='resistor',model='sky130_fd_pr__res_xhigh_po_0p35',a='AMP',b='COMP',bulk='VGND',w=.35,l=14))
dev.append(dict(name='C3',role='C_COMP',kind='capacitor',model='sky130_fd_pr__cap_mim_m3_1',a='COMP',b='ua[1]',w=26,l=26,m=1))
ports=['VGND','VDPWR','clk','ena','rst_n']+[f'{bus}[{i}]' for bus in ['ui_in','uo_out','uio_in','uio_out','uio_oe','ua'] for i in range(8)]
ties=[f'{bus}[{i}]' for bus in ['uo_out','uio_out','uio_oe'] for i in range(8)]
spec={'top':TOP,'ports':ports,'tie_ports':ties,'devices':dev,'target':{'tiles':'1x2','supply_v':1.8,'bits':8,'vref_low_v':.2,'vref_high_v':.9,'load_pf':5,'load_megohm':10,'conversion_us':46},'bulk_policy':'All NMOS bulks VGND; all PMOS bulks VDPWR. Three-terminal visible MOS symbols; bulk ties preserved in silicon and netlists.'}
(ROOT/'design.json').write_text(json.dumps(spec,indent=2)+'\n')
lines=['* Suarez serial two-capacitor DAC; real SKY130 devices',f'.subckt {TOP} '+' '.join(ports)]
for x in dev:
    if x['kind']=='mos':
        lines.append(f"X{x['name']} {x['d']} {x['g']} {x['s']} {x['b']} {x['model']} w={x['w']} l={x['l']} nf=1 m=1")
    elif x['kind']=='resistor':
        # This PDK model has fixed 0.35 um width; only length is a parameter.
        lines.append(f"X{x['name']} {x['a']} {x['b']} {x['bulk']} {x['model']} l={x['l']} m=1")
    else:
        lines.append(f"X{x['name']} {x['a']} {x['b']} {x['model']} w={x['w']} l={x['l']} m={x['m']}")
lines.append('* Zero-ohm elements below represent metal shorts of interface ports, not fabricated resistors.')
for i,n in enumerate(ties):lines.append(f'R_TIE_{i} {n} VGND 0')
lines.append(f'.ends {TOP}')
(ROOT/'netlist'/f'{TOP}.spice').write_text('\n'.join(lines)+'\n')
v='''`default_nettype none
// Integration black box. The physical implementation is in gds/ and lef/.
module TOP(input wire VGND, input wire VDPWR,
 input wire [7:0] ui_in, output wire [7:0] uo_out,
 input wire [7:0] uio_in, output wire [7:0] uio_out,
 output wire [7:0] uio_oe, inout wire [7:0] ua,
 input wire ena, input wire clk, input wire rst_n);
endmodule
'''.replace('TOP',TOP)
(ROOT/'src/project.v').write_text(v)

def testbench(codes,corner='tt',buffer_only=False):
    header=['* SKY130 transistor-level simulation',f'.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice {corner}',f'.include {ROOT}/netlist/{TOP}.spice','VDD vdd 0 1.8','VHI refh 0 .9','VLO refl 0 .2','RHI refh hi 500','RLO refl lo 500','CHI hi 0 5p','CLO lo 0 5p','ROUT out pad 500','COUT pad 0 5p','RLOAD pad 0 10Meg']
    nets={'VGND':'0','VDPWR':'vdd','ua[0]':'hi','ua[1]':'out','ua[2]':'lo','ui_in[0]':'h','ui_in[1]':'l','ui_in[2]':'s'}
    header.append('XDUT '+' '.join(nets.get(p,'0') for p in ports)+' '+TOP)
    if buffer_only:
        # Force just the hold node to study the unity-gain buffer independently.
        header+=['VFORCE XDUT.HOLD 0 .2','VH h 0 0','VL l 0 0','VS s 0 0','.control','set wr_vecnames','set wr_singlescale','dc VFORCE .15 1.0 .005',f'wrdata {ROOT}/verification/buffer_dc.txt v(out) v(pad) v(XDUT.BIAS) v(XDUT.TAIL)','quit','.endc','.end']
        return '\n'.join(header)+'\n',[]
    waves={k:[(0,0)] for k in ['h','l','s']}
    def event(t,h,l,s):
        for k,v in zip(['h','l','s'],[h,l,s]):
            if waves[k][-1][1]!=v:
                waves[k]+=[(t, waves[k][-1][1]),(t+.005, v)]
    measures=[]
    time=0
    for code in codes:
        event(time+.1,0,1.8,1.8) # Initialization: both capacitors charged to VREFL.
        time+=8
        event(time,0,0,0)
        time+=.2
        for b in range(8):
            one=(code>>b)&1
            event(time,1.8*one,1.8*(1-one),0)
            time+=2
            event(time,0,0,0)
            time+=.2
            event(time,0,0,1.8)
            time+=2
            event(time,0,0,0)
            time+=.2
        time+=3
        measures.append(dict(code=code,time_us=time,ideal_v=.2+.7*code/256))
        time+=.5
    for k in waves:
        waves[k].append((time, waves[k][-1][1]))
        header.append('V'+k.upper()+' '+k+' 0 PWL('+' '.join(f'{t:.6f}u {v}' for t,v in waves[k])+')')
    header+=['.options method=gear reltol=1e-5 abstol=1e-13','.control','set wr_vecnames','set wr_singlescale',f'tran 20n {time}u',f'wrdata {ROOT}/verification/transfer_{corner}.txt v(XDUT.SAMPLE) v(XDUT.HOLD) v(out) v(pad) v(h) v(l) v(s)','quit','.endc','.end']
    return '\n'.join(header)+'\n',measures

for cor in ['tt','ss','ff']:
    tb,meas=testbench([0,1,2,15,63,127,128,129,192,254,255],cor)
    (ROOT/'sim'/f'transfer_{cor}.spice').write_text(tb)
(ROOT/'sim/measurements.json').write_text(json.dumps(meas,indent=2)+'\n')
tb,_=testbench([],buffer_only=True)
(ROOT/'sim/buffer_dc.spice').write_text(tb)
print(ROOT)
