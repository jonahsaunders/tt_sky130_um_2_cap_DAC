# Suarez serial two-capacitor DAC

[![GDS and precheck](https://github.com/jonahsaunders/tt_sky130_um_2_cap_DAC/actions/workflows/gds.yaml/badge.svg)](https://github.com/jonahsaunders/tt_sky130_um_2_cap_DAC/actions/workflows/gds.yaml)
[![Documentation](https://github.com/jonahsaunders/tt_sky130_um_2_cap_DAC/actions/workflows/docs.yaml/badge.svg)](https://github.com/jonahsaunders/tt_sky130_um_2_cap_DAC/actions/workflows/docs.yaml)

An editable, physically verified SKY130 analog macro prepared for an experimental Tiny Tapeout submission. Built with IIC OSIC Tools and drawn using KiStack's schematic workflow. The conversion core contains two equal capacitor banks; its output buffer adds a separate compensation capacitor. The final qualification report records the exact GDS, all-code linearity, operating corners, mismatch, stability, startup, noise, and limits. Precise absolute voltage requires offset/gain calibration.

[Open the published layout viewer](https://jonahsaunders.github.io/tt_sky130_um_2_cap_DAC/). The viewer workflow requires GitHub Pages to be enabled under **Settings → Pages**, with **GitHub Actions** as its publishing source. For a fork, enable that setting and start a fresh `gds` workflow run. If a retry reports multiple artifacts named `github-pages`, start a new run with **Run workflow** instead of rerunning the failed attempt.

## Open the design

* `schematic/suarez_dac.kicad_pro` — KiCad project; open the schematic within it.
* `schematic/suarez_dac.kicad_sch` — native editable A3 schematic with three-terminal visible MOS symbols.
* `schematic/suarez_dac.pdf` — printable schematic.
* `layout/tt_um_jonah_suarez_dac.mag` — hierarchical Magic layout; retain all adjacent device `.mag` files.
* `gds/tt_um_jonah_suarez_dac.gds` — fabricated geometry for the complete 161 × 225.76 µm macro.
* `lef/tt_um_jonah_suarez_dac.lef` — integration pin geometry.
* `netlist/tt_um_jonah_suarez_dac.spice` — transistor-level circuit with explicit body connections.
* `netlist/tt_um_jonah_suarez_dac.rc.spice` — GDS-extracted devices, coupled capacitances, and interconnect resistance used for qualification.
* `netlist/tt_um_jonah_suarez_dac.rc_raw.spice` — unreduced full RC extraction for fidelity checks.
* `netlist/tt_um_jonah_suarez_dac.pex.spice` — coupled-capacitance extraction.
* `docs/info.md` — operation, timing, pinout, and external hardware.
* `verification/verification.md` — qualification results and limitations.
* `verification/all_code_results.csv` — every measured code in every full sweep.
* `verification/qualification.png` — transfer, INL, DNL, and mismatch plots.
* `examples/phase_driver.py` — controller callback interface and two-point calibration.

## Interface

| Pin | Function |
|---|---|
| VDPWR / VGND | 1.8 V supply / ground |
| ui_in[0] | CHARGE_HIGH |
| ui_in[1] | CHARGE_LOW |
| ui_in[2] | SHARE |
| ua[0] | VREFH, nominal 0.9 V |
| ua[1] | Buffered DAC output |
| ua[2] | VREFL, nominal 0.2 V |

Initialize both banks before each word, then send bits LSB first with separate charge and share phases. The supplied timing uses 2 µs per active phase and 0.2 µs dead time; one word repeats every 46.9 µs. See `docs/info.md` for the initialization exception and complete timing. There is no internal sequencer or reset circuit.

## Rebuild and verify

Mount this directory at `/foss/designs` in the IIC OSIC Tools image. Invoke scripts through its login shell so the EDA tool paths are initialized. The supplied SPICE testbenches use the image's `/foss/pdks/sky130A` models.

```
python3 scripts/build_circuit.py
python3 scripts/build_layout.py
bash scripts/verify.sh
```

Set `TT_SUPPORT_TOOLS` to the support-tool clone before running verification. The verified container image is `hpretl/iic-osic-tools@sha256:5d6adf1f437cd0f2f8f8614488ec3c247ba8c768f4663a25d5e997b30ccb13b0` (release 2026.07). `scripts/export_schematic.ps1` performs the KiCad 10 exports on Windows.

The layout generator creates a fresh directory under `build/` each run and updates native layout, GDS, LEF, the extracted LVS netlist, and build log. The verification runner checks native/GDS LVS, full DRC, gate antenna ratios, exact rebuildability, full RC extraction, and the complete simulation suite. It also runs the official precheck and project metadata checks; pass the cloned support-tool directory through `TT_SUPPORT_TOOLS`. The circuit generator updates design.json, SPICE, and baseline testbenches. Baseline selected-code testbenches are development aids; final qualification uses `scripts/qualify.py` and `scripts/qualify_suite.py`.

To rebuild the schematic after editing circuit parameters, run `python3 scripts/build_schematic.py`, export PDF/SVG and KiCad XML with KiCad 10, then run `python3 scripts/check_schematic.py`. Existing decks record the original verification mount path. Regenerate them with these scripts when mounting the package at a different path. The compact ZIP keeps cases, logs, measured code results, and shared extracted models; redundant per-run DUT copies and raw waveform vectors are regenerated by the scripts. Full raw vectors also remain in the local output folder.

The existing schematic is fully self-contained through its embedded symbols and local library. There are deliberately no PCB footprints: these are on-chip devices. The visible symbols show D/G/S, while all NMOS bodies connect to VGND and all PMOS bodies to VDPWR in SPICE and layout.

For the official submission checks, clone `TinyTapeout/tt-support-tools`, enter its `precheck/` directory, set `PDK_ROOT=/foss/pdks` and `PDK=sky130A`, and run `python3 precheck.py --gds /foss/designs/gds/tt_um_jonah_suarez_dac.gds --tech sky130A`. The complete reports from the current run are included under `verification/precheck/`.

The top Verilog file is the analog integration black box. It is supplied in both `src/` and beside the GDS as required by the precheck. `info.yaml`, `docs/info.md`, and GitHub custom-GDS workflows follow the current analog template. Nothing has been submitted to a shuttle. Model-based qualification does not establish measured silicon yield or ENOB.
