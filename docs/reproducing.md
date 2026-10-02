# Rebuilding and reviewing the design

[Back to the README](../README.md) · [Circuit guide](architecture.md) · [Test coverage](testing.md)

## Tools and paths

The verified environment is IIC OSIC Tools release 2026.07, image `hpretl/iic-osic-tools@sha256:5d6adf1f437cd0f2f8f8614488ec3c247ba8c768f4663a25d5e997b30ccb13b0`, with Magic 8.3.678, ngspice 46, netgen 1.5.323, and the bundled SKY130A PDK. The schematic exports use native KiCad 10.0.6. See [provenance](../verification/provenance.json) for reference repository revisions.

Mount the repository at `/foss/designs` and run commands in the IIC OSIC login shell, which initializes the tool paths. Use `PDK=sky130A`, `PDK_ROOT=/foss/pdks`, and `PDKPATH=/foss/pdks/sky130A`. Clone `TinyTapeout/tt-support-tools` and set `TT_SUPPORT_TOOLS` to that clone's path. The verification runner sets the SKY130 environment explicitly.

Saved decks contain the original verification mount paths. Regenerate cases through the provided scripts before running them in a different checkout. The shared cached PDK models, measured results, and important special-test waveforms are included; most redundant raw vectors and per-run DUT copies are regenerated.

## Edit and export the schematic

Open `schematic/suarez_dac.kicad_pro` in KiCad. The schematic contains embedded symbols and a local `Sky130.kicad_sym`, so it is self-contained. All MOS symbols retain D/G/S pin numbers 1/2/3. Body ties remain explicit in SPICE and silicon.

The generator reproduces the drawing from `design.json`. Running it overwrites manual schematic edits; keep manual changes or update the generator deliberately.

```sh
python3 scripts/build_schematic.py
```

On Windows, export ERC, the XML netlist, SVG, and PDF through the included script:

```powershell
.\scripts\export_schematic.ps1
```

Then, in the IIC OSIC environment:

```sh
python3 scripts/check_schematic.py
```

This compares all 72 visible device connections to `design.json`, records hashes, and generates the full-page PNG, three detail crops, and documentation overview. Review the images as well as ERC and the connectivity report after a drawing change.

## Rebuild silicon and run qualification

```sh
python3 scripts/build_circuit.py
python3 scripts/build_layout.py
bash scripts/verify.sh
```

The circuit generator updates the SPICE source and baseline testbenches. The layout generator builds in a fresh directory under `build/`, checks native DRC, and updates Magic cells, GDS, LEF, and the circuit extraction. Keep adjacent device `.mag` files with the top cell.

The verification runner performs native and re-imported GDS DRC/LVS, antenna checks, exact rebuild comparison, full RC extraction, geometry and schematic checks, official prechecks, and project-document checks. It then runs AC, PVT, mismatch, full-code, startup, settling, retention, noise, and numerical-equivalence checks before producing the qualification report. Full simulation qualification takes substantially longer than regenerating the documentation images.

Rerun physical and simulation qualification after an electrical or silicon-layout change. A drawing-only schematic change must still pass ERC and the exported-netlist comparison. Editing prose or rendering existing evidence does not require repeating unchanged analog simulations.

## Regenerate the documentation figures

```sh
python3 scripts/render_docs.py
```

This requires NumPy, Matplotlib, and the KLayout Python module supplied by the verified image. Schematic rendering additionally uses CairoSVG and Pillow. The figure generator rejects result files with a different GDS or RC hash and creates:

| Image | Source |
|---|---|
| `docs/images/layout_overview.png` | Actual GDS polygons and `layout/placement.json` |
| `docs/images/linearity.png` | Nine complete sweeps and 32 local-mismatch result files |
| `docs/images/stability_settling.png` | 120 AC results and saved buffer-step waveforms |
| `docs/images/timing.png` | Documented phase schedule; labeled as an illustration |
| `docs/images/schematic_overview.png` | Native KiCad SVG export, via `check_schematic.py` |

## GitHub integration checks

The `gds` workflow packages the supplied custom GDS/LEF/Verilog, runs the official precheck, and publishes the viewer. The `docs` workflow builds the Tiny Tapeout project documentation. They do not rerun the full analog simulation suite; the local qualification evidence is delivered separately.

For the viewer, enable **Settings → Pages → GitHub Actions**. The setting is already enabled in the main repository. If rerunning a failed viewer attempt creates duplicate artifacts named `github-pages`, start a fresh `gds` run with **Run workflow**. The chip remains unsubmitted to a shuttle until a separate submission is made.
