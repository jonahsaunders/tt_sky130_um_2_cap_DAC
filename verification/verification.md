# Tiny Tapeout qualification — Suarez serial DAC

The delivered SKY130 macro is ready for an experimental analog submission within the conditions below. Native layout and independently re-imported GDS pass DRC and LVS. Gate antenna checks pass. All 15 official Tiny Tapeout prechecks pass. The editable KiCad schematic has zero ERC violations and all 72 visible device connections match the circuit specification. A fresh build reproduces the circuit and every GDS polygon.

This is a two-capacitor serial charge-sharing converter with an additional buffer compensation capacitor. The two conversion banks are nominally 6.454 pF each, built from 16 MIM units per bank in a common-centroid pattern. Grounded shields limit sample/hold coupling. Low-threshold PMOS transmission-gate devices preserve charge transfer at low supply and cold temperature. The buffer uses approximately 80 kΩ and 1.373 pF compensation. MOS body connections are explicit in silicon and SPICE.

## Qualified use

Nominal supply 1.8 V; modeled supply boundaries 1.62 V and 1.98 V. Temperature samples −40, 27, and 85 °C. Five process corners TT, SS, FF, SF, FS. Fixed references 0.2 V and 0.9 V. Output load 5–20 pF with at least 10 MΩ DC impedance. Every analog-pad model includes 500 Ω series resistance; reference pads also include 5 pF. Control highs track VDPWR.

Initialize each word for 8 µs, then send eight bits LSB first with 2 µs charge, 0.2 µs dead time, 2 µs share, and 0.2 µs dead time. Read 3 µs after the last bit; an additional 0.5 µs gap gives 46.9 µs per word, or about 21.3 kwords/s. The simulator uses a conservative 7.9 µs active reset within the 8 µs initialization slot. The external controller supplies all phases; clk, ena, and rst_n do not sequence this macro. HIGH and LOW must never overlap. LOW and SHARE overlap only during initialization.

## Complete post-layout code measurements

All 256 codes were measured in each of nine conditions: five nominal process corners, the two worst observed PVT points, and the two worst observed mismatch samples. Each code uses the same initialization; eight codes are grouped per independent run to keep input waveform decks manageable. This gives 2,304 final-layout code measurements. All nine curves are strictly monotonic. Endpoint INL removes offset and gain; raw error retains them. Mismatch raw error is therefore larger than linearity error.

| Case | Process | VDD (V) | Temperature (°C) | Load (pF) | Max INL (LSB) | DNL range (LSB) | Max raw error (LSB) |
|---|---|---:|---:|---:|---:|---:|---:|
| full_tt | tt | 1.8 | 27 | 5 | 0.266 | -0.013 to 0.498 | 0.289 |
| full_ss | ss | 1.8 | 27 | 5 | 0.260 | -0.013 to 0.493 | 0.296 |
| full_ff | ff | 1.8 | 27 | 5 | 0.278 | -0.014 to 0.500 | 0.272 |
| full_sf | sf | 1.8 | 27 | 5 | 0.254 | -0.012 to 0.484 | 0.257 |
| full_fs | fs | 1.8 | 27 | 5 | 0.287 | -0.015 to 0.510 | 0.331 |
| full_worst_inl | fs | 1.62 | 85 | 20 | 0.629 | -0.035 to 0.510 | 0.510 |
| full_worst_dnl | fs | 1.98 | 85 | 20 | 0.485 | -0.026 to 0.516 | 0.296 |
| full_mc_1027 | tt | 1.8 | 27 | 5 | 0.338 | -0.017 to 0.603 | 1.922 |
| full_mc_1026 | tt | 1.8 | 27 | 5 | 0.296 | -0.014 to 0.476 | 10.647 |

![All nine final transfer, INL, DNL sweeps and offset distribution](../docs/images/linearity.png)

The figure includes every full-sweep condition, including the two PVT stress cases and two mismatch seeds. The original [nominal-corner qualification plot](qualification.png) is also retained.

An additional 30 PVT points each measure ten selected codes, including 127/128 and both endpoints. All are monotonic at the measured codes; worst raw error is 0.510 LSB. This selected-code grid is not an exhaustive all-code test at every PVT point. Full sweeps target the worst grid points. One nominal LSB is 2.734375 mV. Nominal modeled linearity is assessed against ±1 LSB INL and strictly positive code steps, rather than a claim of eight-bit absolute accuracy.

## Stability, settling, retention, and noise

![All loop-stability cases and standalone-buffer step responses](../docs/images/stability_settling.png)

The actual extracted RC circuit was tested with Middlebrook voltage injection at the buffer feedback gate. 120 combinations cover five process corners, both supply boundaries, both temperature boundaries, three input voltages, and both load boundaries. Every case exceeds 60° phase margin; the minimum is 71.74°. Small-signal margins do not by themselves establish large-signal settling.

Power-up from zero stored voltages, a 10 µs supply ramp, and references established by 15 µs passes; conversion starts at 20 µs. The standalone buffer's worst measured full 0.7 V upward step settles within half an LSB in 6.36 µs at SS/1.62 V/−40 °C/20 pF and can overshoot by about 248 mV. Allow 8 µs for such a full-range buffer step. The DAC's actual sequence produces smaller charge-sharing steps and is separately verified at the stated 3 µs read delay. Arbitrary rapid changes to the reference voltages are outside the qualified protocol.

At 85 °C, hold tests last almost 100 µs while the sample bank is driven to the opposite reference. This deliberately adversarial action produces up to 0.335 LSB of immediate feedthrough; subsequent 50 µs leakage drift stays below 0.0031 LSB. Refresh periodically and do not alter the sample bank while expecting an unchanged held output.

Continuous-time buffer noise is integrated separately from sampled switch noise. The modeled buffer noise from 0.1 Hz to the 10.66 kHz conversion Nyquist frequency is 57.4–58.3 µV RMS in the three tested cases. The kT/C estimate for a 6.454 pF hold bank at 85 °C is about 27.7 µV RMS. These results do not establish measured ENOB, distortion, or dynamic silicon performance.

## Mismatch and calibration

32 PDK local-mismatch seeds were simulated with process mismatch disabled; process corners are tested separately. All selected-code curves are monotonic. Endpoint offset spans -28.94 to 25.24 mV. The input pair is small and untrimmed, so accurate absolute voltage requires calibration. Measure codes 0 and 255, fit voltage versus code, and map requested voltages into that measured range. The supplied controller example includes this mapping. Calibration cannot extend the measured endpoint range or remove all code-dependent nonlinearity.

Seeds 1027 (worst selected INL) and 1026 (worst offset/gain) additionally receive complete 256-code sweeps. Repeating the same seed reproduces the same outputs. These 32 samples characterize modeled sensitivity; they do not prove manufacturing yield or include wafer-scale capacitor gradients, package variation, or an exhaustive process distribution.

## Extraction and evidence integrity

Full RC extraction uses the installed SKY130 Magic technology and IIC OSIC extraction flow, with 1 Ω resistance gating/minimum resistance and zero delay cutoff. Raw extraction and reduced RC are both delivered. Reduction exactly eliminates only internal resistor nodes having no capacitance, device terminal, or external port. Every capacitive and device node is preserved. Measured differences between raw and reduced RC, cached and complete PDK models, and 100 ns and 25 ns maximum time steps are recorded in `signoff/special_results.json`; each is below 10 µV. The model cache preserves all geometry bins and global parameters of every used model family.

Peak supply current across the conversion qualification is 281.4 µA; peak reference-pad current is 0.312 mA, below the 4 mA analog-pad limit. Full-height metal-4 power stripes are 1.2 µm wide. The macro has exact 161 × 225.76 µm bounds, the official pin geometry, grounded unused digital outputs, isolated unallocated analog pads, and no metal 5.

Final GDS SHA-256: `efce3b66b1ce380e21becc94a6c70523c7269990198254b27dcbe6d7e679d306`. Final reduced RC SHA-256: `37552ff61c2aa6ffbdae603dc7450a877b3ab69719ba779948dca93ffadc16df`. Every qualification case records these hashes. `all_code_results.csv` contains all final full-sweep measurements. JSON results, decks, logs, model hashes, native layout, and generators make the checks auditable. Raw waveform vectors remain in the local results folder; the compact ZIP omits redundant per-run vectors and DUT snapshots, which the scripts regenerate.

The GitHub custom-GDS workflow and metadata follow the current official analog template. The design is published in its GitHub repository; it has not been submitted to a shuttle, purchased, fabricated, or measured. Chip integration and silicon measurements remain the final confirmation of performance.

Sources: [Tiny Tapeout analog specifications](https://tinytapeout.com/specs/analog/), [official analog template](https://github.com/TinyTapeout/ttsky-analog-template), [official support tools](https://github.com/TinyTapeout/tt-support-tools), [IIC OSIC Tools](https://github.com/iic-jku/IIC-OSIC-TOOLS). Exact tool and repository versions are recorded in `provenance.json`.
