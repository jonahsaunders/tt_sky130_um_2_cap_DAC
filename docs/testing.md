# Test results and their limits

[Back to the README](../README.md) · [Circuit guide](architecture.md) · [Reproduce the checks](reproducing.md)

These results come from the delivered GDS and its extracted resistance/capacitance netlist. They are model-based tests; no fabricated silicon has been measured. The [complete qualification report](../verification/verification.md) contains the per-case table, exact hashes, extraction checks, and operating limits.

## Physical and schematic correctness

| Test | Recorded result | Report |
|---|---|---|
| Native Magic DRC and LVS | Zero DRC errors; unique LVS match without property errors | [Native LVS log](../verification/lvs.log) |
| Independently re-imported GDS | Zero full DRC errors; unique LVS match | [Physical checks](../verification/physical_checks.json), [GDS LVS log](../verification/gds_lvs.log) |
| Gate antenna check | Zero feedback entries | [Antenna report](../verification/antenna.txt) |
| Official Tiny Tapeout precheck | 15 / 15 tests pass | [Precheck report](../verification/precheck/results.md) |
| Editable schematic | Zero ERC violations; all 72 visible device-pin connections match `design.json` | [ERC](../verification/schematic_erc.rpt), [connectivity](../verification/schematic_connectivity.json) |
| Rebuild | Same circuit netlist and all GDS polygon geometry | [Rebuild report](../verification/rebuild.json) |

The schematic revision changes drawing geometry and connections shown on paper. The exported netlist is checked against the existing circuit specification; the qualified GDS and RC netlist remain unchanged.

## Transfer, INL, DNL, and mismatch

![All nine complete code sweeps and the distribution of modeled endpoint offset](images/linearity.png)

Nine complete sweeps measure all 256 codes: five nominal process corners (TT, SS, FF, SF, FS), two selected PVT stress conditions, and two selected mismatch seeds. This gives 2,304 measurements. All nine sweeps are strictly monotonic.

| Metric | Worst recorded value |
|---|---:|
| Endpoint INL magnitude | 0.6294 LSB |
| DNL minimum | −0.0350 LSB |
| DNL maximum | +0.6028 LSB |
| Untrimmed endpoint offset, 32 seeds | −28.94 to +25.24 mV |
| Minimum phase margin, 120 cases | 71.74° |
| Peak supply current | 281.4 µA |
| Peak reference-pad current | 0.312 mA |

One nominal LSB is 0.7 V / 256 = 2.734375 mV. Endpoint INL and DNL use the line fitted to measured codes 0 and 255; they remove offset and gain. The upper-left transfer plot uses raw output voltage and therefore still shows offset. A small endpoint INL does not imply the same absolute voltage accuracy.

An additional 30 PVT conditions measure ten selected codes each, including both endpoints and the 127/128 transition. The 32 PDK local-mismatch seeds also measure ten selected codes each; seeds 1027 and 1026 additionally receive full sweeps. The selected-code grid is not an exhaustive 256-code sweep at every operating condition.

[Download every full-sweep measurement](../verification/all_code_results.csv). The [recorded cases and results](../verification/signoff/) include conditions, model hashes, extracted-netlist hashes, simulation decks, and logs.

## Stability and settling

![All 120 loop-stability measurements and three full-range standalone-buffer step responses](images/stability_settling.png)

The loop-stability cases cover five process corners, both supply boundaries, both temperature boundaries, three input voltages, and both load boundaries. All 120 cases pass the 60° phase-margin criterion; the minimum is 71.74°. These small-signal results are separate from the large-signal step tests.

The plot on the right is an actual **standalone buffer** test that forces HOLD from 0.2 to 0.9 V. At SS / 1.62 V / −40°C / 20 pF, the upward response overshoots by about 248 mV and settles within half a nominal LSB in 6.36 µs. Allow 8 µs for this full-range step. The DAC's ordinary conversion sequence is separately verified with a 3 µs read delay after the last bit; it does not apply this same forced step.

Startup uses zero initial stored voltages, a 10 µs supply ramp, references established by 15 µs, and conversion beginning at 20 µs. Retention tests drive SAMPLE toward the opposite reference after conversion: immediate feedthrough can reach 0.335 LSB, while subsequent 50 µs leakage drift remains below 0.0031 LSB. These tests explain why the held output must be refreshed and SAMPLE should not be changed while expecting a constant output.

See [special-test results](../verification/signoff/special_results.json), [step-test data](../verification/signoff/step_ss_1.62_-40_20.txt), and the [test generator](../scripts/special.py).

## Calibration and limits

Measure the outputs at codes 0 and 255. Fit `VOUT = V0 + code × (V255 − V0) / 255`, then map requested voltages into the measured endpoint range. The [controller example](../examples/phase_driver.py) implements this mapping. Calibration corrects offset and gain within that range; it cannot extend the range or eliminate code-dependent nonlinearity.

Qualified references remain fixed at 0.2 and 0.9 V. Loads are 5–20 pF with at least 10 MΩ DC impedance. Analog-pad models include 500 Ω series resistance, with an additional 5 pF on reference pads. Control highs follow VDPWR. Temperature samples are −40, 27, and 85°C, with supply boundaries of 1.62 and 1.98 V.

The modeled continuous-time buffer noise is 57.4–58.3 µV RMS from 0.1 Hz to the 10.66 kHz conversion Nyquist frequency. The separate kT/C estimate for C2 at 85°C is about 27.7 µV RMS. These values do not establish measured ENOB or distortion. The 32 mismatch seeds do not establish manufacturing yield or cover every wafer gradient, package effect, or process distribution.

## Evidence integrity and figure generation

The GDS SHA-256 is `efce3b66b1ce380e21becc94a6c70523c7269990198254b27dcbe6d7e679d306`. The reduced RC SHA-256 is `37552ff61c2aa6ffbdae603dc7450a877b3ab69719ba779948dca93ffadc16df`. The result files and figure generator check those identities before accepting data.

[`render_docs.py`](../scripts/render_docs.py) renders layout polygons from the GDS and plots saved full-sweep, mismatch, AC, and step-response data. The timing diagram is explicitly a protocol illustration. [`check_schematic.py`](../scripts/check_schematic.py) creates schematic images from native KiCad SVG export after verifying connectivity. Neither figure-generation step reruns or alters the circuit simulations.

Raw/full RC and reduced RC outputs, complete/cached PDK models, repeated seeds, and different transient time steps were compared during qualification. The recorded differences are in the [special-test results](../verification/signoff/special_results.json). The [manifest](../manifest.json) lists the byte count and SHA-256 of every delivered file.
