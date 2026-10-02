"""Render documentation figures from the delivered GDS and existing evidence.

No circuit simulation or layout modification is performed. Every result JSON
must identify the current GDS and extracted RC netlist before it is plotted.
"""
from pathlib import Path
import hashlib
import json

import klayout.db as db
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle
import numpy as np

P = Path(__file__).resolve().parents[1]
Q = P / "verification/signoff"
OUT = P / "docs/images"
OUT.mkdir(parents=True, exist_ok=True)
GDS = P / "gds/tt_um_jonah_suarez_dac.gds"
gds_sha = hashlib.sha256(GDS.read_bytes()).hexdigest()
rc_sha = hashlib.sha256((P / "netlist/tt_um_jonah_suarez_dac.rc.spice").read_bytes()).hexdigest()
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def evidence(path):
    data = json.loads(path.read_text())
    for item in data if isinstance(data, list) else [data]:
        assert item["gds_sha256"] == gds_sha, (path, "GDS mismatch")
        assert item["netlist_sha256"] == rc_sha, (path, "RC mismatch")
    return data


def save(fig, name):
    fig.savefig(OUT / name, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


# Actual merged mask polygons, with bank identity from generator placement.
ly = db.Layout()
ly.read(str(GDS))
top = ly.top_cell()
placement = json.loads((P / "layout/placement.json").read_text())
fig = plt.figure(figsize=(12, 9), facecolor="white")
ax = fig.add_axes((.055, .11, .49, .79), facecolor="#111b2b")
layers = [(64,20,"#397d80",.6),(65,20,"#cf826c",.7),(66,20,"#eda64c",.8),
          (67,20,"#b4b4b4",.9),(68,20,"#73c7e8",.6),(69,20,"#e7849c",.7),
          (70,20,"#9e87d7",.8),(89,44,"#cfb571",.85),(71,20,"#78c8b3",.7)]
for num, dt, color, alpha in layers:
    idx = ly.find_layer(num, dt)
    if idx is None:
        continue
    polygons = [[(v.x*ly.dbu, v.y*ly.dbu) for v in s.each_point_hull()]
                for s in db.Region(top.begin_shapes_rec(idx)).each_merged()]
    ax.add_collection(PolyCollection(polygons, facecolors=color, edgecolors=color, linewidths=.1, alpha=alpha))
for cap in placement["capacitors"]:
    ax.text(cap["x"], cap["y"], "A" if cap["bank"] == "SAMPLE" else "B",
            ha="center", va="center", fontsize=9, color="#102c35", weight="bold")
ax.set(xlim=(-2,163), ylim=(-2,228), xlabel="µm", ylabel="µm")
ax.set_aspect("equal")
ax.tick_params(colors="#58677a")
for y, title in [(184,"1"),(113,"2"),(39,"3")]:
    ax.text(153, y, title, ha="center", va="center", color="#111b2b", weight="bold",
            bbox={"boxstyle":"circle,pad=.25", "fc":"white", "ec":"none"})
note = fig.add_axes((.59,.56,.37,.32));note.axis("off")
note.text(0, .98, "1   TRANSISTORS AND ROUTING", weight="bold", fontsize=12, va="top")
note.text(0, .83, "M1–M6: phase inverters\nM7–M12: reference and share switches\nM13–M20: bias and output buffer", va="top", linespacing=1.7)
note.text(0, .50, "2   MATCHED CONVERSION BANKS", weight="bold", fontsize=12, va="top")
note.text(0, .35, "A = C1 / SAMPLE    B = C2 / HOLD\n16 × (14 × 14 µm) MIM units per bank\n6.454 pF nominal per bank", va="top", linespacing=1.7)
note.text(0, .02, "3   BIAS AND COMPENSATION\nR1–R3 and the separate C3 capacitor", va="top", linespacing=1.7)
grid = fig.add_axes((.60,.18,.36,.25))
xs = sorted({c["x"] for c in placement["capacitors"]})
ys = sorted({c["y"] for c in placement["capacitors"]})
for c in placement["capacitors"]:
    x, y = xs.index(c["x"]), ys.index(c["y"])
    a = c["bank"] == "SAMPLE"
    grid.add_patch(Rectangle((x+.04,y+.04),.92,.92,facecolor="#247a91" if a else "#be7552"))
    grid.text(x+.5,y+.5,"A" if a else "B",color="white",ha="center",va="center",weight="bold",fontsize=13)
grid.set(xlim=(0,8),ylim=(0,4));grid.set_aspect("equal");grid.axis("off")
grid.set_title("Common-centroid placement",loc="left",fontsize=12,pad=10)
fig.text(.60,.125,"Both bank centroids: (77.55, 113.00) µm",fontsize=10)
fig.suptitle("Final SKY130 GDS  |  161 × 225.76 µm",fontsize=18,y=.97)
fig.text(.055,.025,f"Mask geometry from {GDS.name}  ·  SHA-256 {gds_sha[:16]}…",fontsize=9,color="#58677a")
save(fig,"layout_overview.png")


names = ["full_"+c for c in ["tt","ss","ff","sf","fs"]] + ["full_worst_inl","full_worst_dnl","full_mc_1027","full_mc_1026"]
full = [evidence(Q / (n+"_result.json")) for n in names]
assert all(r["full_256_codes"] and len(r["rows"]) == 256 and r["monotonic"] for r in full)
mc = [evidence(Q / f"mc_{seed}_result.json") for seed in range(1001,1033)]
fig, axs = plt.subplots(2,2,figsize=(12,8.5))
colors = ["#007d81","#d68128","#6e53a3","#438241","#bc4772","#153b71","#86640d","#286fa2","#bd5143"]
labels = ["TT · nominal","SS · nominal","FF · nominal","SF · nominal","FS · nominal",
          "FS · 1.62 V / 85°C / 20 pF","FS · 1.98 V / 85°C / 20 pF","TT · mismatch seed 1027","TT · mismatch seed 1026"]
handles = []
for r, color, label in zip(full,colors,labels):
    codes = np.arange(256)
    volts = np.array([row["output_v"] for row in r["rows"]])
    slope = (volts[-1]-volts[0])/255
    style = "-" if r["name"] in names[:5] else "--"
    line, = axs[0,0].plot(codes,volts,color=color,ls=style,lw=1.1,label=label)
    handles.append(line)
    axs[0,1].plot(codes,(volts-volts[0]-slope*codes)/slope,color=color,ls=style,lw=1.1)
    axs[1,0].plot(codes[1:],np.diff(volts)/slope-1,color=color,ls=style,lw=1.1)
axs[0,0].set(title="Transfer · raw output, including offset",ylabel="Output (V)")
axs[0,1].set(title="Endpoint INL · all nine sweeps",ylabel="LSB")
axs[1,0].set(title="DNL · all nine sweeps",ylabel="LSB")
axs[1,1].hist([r["endpoint_offset_mv"] for r in mc],bins=10,color="#247a91",edgecolor="white")
axs[1,1].set(title="Local mismatch · 32 PDK seeds",xlabel="Endpoint offset (mV)",ylabel="Samples")
for ax in axs.flat:ax.grid(alpha=.2)
for ax in axs.flat[:3]:ax.set_xlabel("Code")
fig.suptitle("Post-layout results from the final RC extraction",fontsize=17,y=.98)
worst_inl = max(r['max_endpoint_inl_lsb'] for r in full)
fig.text(.5,.932,f"{len(full)*256:,} code measurements · nine monotonic sweeps · worst endpoint INL {worst_inl:.2f} LSB",ha="center",fontsize=11)
fig.legend(handles,labels,loc="lower center",ncol=3,fontsize=8.5,frameon=False,bbox_to_anchor=(.5,.005))
fig.subplots_adjust(top=.86,bottom=.18,hspace=.38,wspace=.24)
save(fig,"linearity.png")


ac = [evidence(f) for f in sorted(Q.glob("ac_*_result.json"))]
assert len(ac) == 120
special = evidence(Q / "special_results.json")
fig, axs = plt.subplots(1,2,figsize=(12,4.7))
for i, corner in enumerate(["tt","ss","ff","sf","fs"]):
    points = [r["phase_margin_deg"] for r in ac if r["corner"] == corner]
    axs[0].scatter(i+np.linspace(-.18,.18,len(points)),points,s=24,color=colors[i],alpha=.75)
axs[0].axhline(60,color="#bd5143",ls="--",lw=1,label="60° acceptance criterion")
axs[0].set(xticks=range(5),xticklabels=["TT","SS","FF","SF","FS"],ylabel="Phase margin (degrees)",
           title="Loop stability · all 120 cases",ylim=(55,max(r["phase_margin_deg"] for r in ac)+4))
axs[0].legend(fontsize=8,loc="lower right")
axs[0].text(.03,.95,f"Minimum: {min(r['phase_margin_deg'] for r in ac):.2f}°",transform=axs[0].transAxes,va="top",weight="bold")
for name, color, label in [("step_tt_1.8_27_5","#007d81","TT / 1.8 V / 27°C / 5 pF"),
                           ("step_ss_1.62_-40_20","#bd5143","SS / 1.62 V / −40°C / 20 pF"),
                           ("step_ff_1.98_-40_5","#6e53a3","FF / 1.98 V / −40°C / 5 pF")]:
    data = np.loadtxt(Q / (name+".txt"),skiprows=1)
    mask = (data[:,0]>=2e-6) & (data[:,0]<=12e-6)
    axs[1].plot((data[mask,0]-2e-6)*1e6,data[mask,1],color=color,label=label,lw=1.5)
axs[1].axhline(.9,color="#738295",ls=":",lw=1)
axs[1].axvline(8,color="#738295",ls=":",lw=1)
axs[1].set(title="Standalone buffer · full 0.7 V step",xlabel="Time after upward step (µs)",ylabel="Output (V)",xlim=(0,10))
axs[1].legend(fontsize=8,loc="lower right")
for ax in axs:ax.grid(alpha=.2)
fig.suptitle("Stability and large-signal settling are separate checks",fontsize=16,y=.99)
worst_step = max(s['settling_0p5lsb_us'] for r in special if r['name'].startswith('step_') for s in r['steps'] if s['direction']=='up')
fig.text(.5,.025,f"Worst standalone upward step: {worst_step:.2f} µs to ±½ LSB; allow 8 µs. The DAC protocol is verified separately.",ha="center",fontsize=9.5)
fig.subplots_adjust(top=.82,bottom=.18,wspace=.25)
save(fig,"stability_settling.png")


# Hardware protocol illustration, deliberately distinct from SPICE waveforms.
intervals = [(0,8,(0,1,1)),(8,8.2,(0,0,0))]
t = 8.2
for bit in range(8):
    one = bool(0xA5 & (1<<bit))
    intervals.extend([(t,t+2,(int(one),int(not one),0)),(t+2,t+2.2,(0,0,0)),
                      (t+2.2,t+4.2,(0,0,1)),(t+4.2,t+4.4,(0,0,0))])
    t += 4.4
intervals.append((t,46.9,(0,0,0)))
fig, axs = plt.subplots(3,1,figsize=(12,4.5),sharex=True)
for i, ax in enumerate(axs):
    x,y=[],[]
    for a,b,state in intervals:x.extend([a,b]);y.extend([state[i],state[i]])
    ax.plot(x,y,color=["#247a91","#be7552","#6e53a3"][i],lw=1.7)
    ax.set(ylim=(-.15,1.3),yticks=[0,1],ylabel=["HIGH","LOW","SHARE"][i])
    ax.axvspan(0,8,color="#eaf1f5")
    ax.axvline(46.4,color="#738295",ls="--",lw=.9)
    ax.grid(axis="x",alpha=.2)
for bit in range(8):
    start = 8.2+bit*4.4
    axs[0].text(start+2.2,1.14,f"b{bit}={int(bool(0xA5 & (1<<bit)))}",ha="center",fontsize=8)
axs[-1].set(xlim=(0,46.9),xlabel="Time from word initialization (µs)")
axs[0].text(4,1.14,"initialize",ha="center",fontsize=8)
fig.suptitle("Phase timing example · code 0xA5, LSB first",fontsize=16)
fig.text(.5,.025,"Protocol illustration, not a simulated waveform. Read at 46.4 µs; 0.5 µs gap gives 46.9 µs/word.",ha="center",fontsize=9)
fig.subplots_adjust(top=.84,bottom=.18,hspace=.18,left=.09,right=.98)
save(fig,"timing.png")

print(f"Rendered four documentation figures; GDS {gds_sha}; RC {rc_sha}")
