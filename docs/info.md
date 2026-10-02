# How it works

![Connected transistor-level schematic with charge sharing, feedback, and compensation](images/schematic_overview.png)

The schematic follows **reference selection → SAMPLE → SHARE → HOLD → buffer → VOUT**. The amplifier is drawn as one circuit with its bias, output stage, feedback loop, and compensation connected visibly. The phase inverters sit beneath the conversion core. The [circuit guide](architecture.md) explains each device group and node.

This SKY130 implementation uses the serial charge-sharing method associated with Suarez, Gray, and Hodges. Two equal 6.454 pF nominal MIM banks repeatedly average a held voltage with the next bit's reference. Bits arrive least significant first. A unity-gain amplifier isolates the hold bank from the analog pad. The amplifier has a separate 1.373 pF compensation capacitor and an approximately 80 kilohm compensation resistor, so there are two conversion capacitors plus one compensation capacitor. Low-threshold PMOS switches preserve charge transfer at low supply and cold temperature.

The macro occupies one by two Tiny Tapeout analog tiles (161 by 225.76 micrometres), uses the 1.8 V VDPWR supply, and needs three analog pads. Each conversion bank contains sixteen 14 by 14 micrometre MIM units. Their common-centroid pattern is ABBAABBA / BAABBAAB / BAABBAAB / ABBAABBA.

![Final GDS geometry and the assignment of the two matched banks](images/layout_overview.png)

The layout image is rendered from the delivered GDS. A denotes C1/SAMPLE and B denotes C2/HOLD. Both bank centroids are (77.55, 113.00) micrometres. An [interactive layout viewer](https://jonahsaunders.github.io/tt_sky130_um_2_cap_DAC/) is also available.

For an eight-bit word, ideal output is VREFL + (VREFH - VREFL) * code / 256. The nominal reference range is 0.2 V to 0.9 V. This is an externally sequenced analog macro: clk, ena, and rst_n do not control the circuit. There is no on-chip word counter or automatic reset. Unused digital outputs and bidirectional enables are grounded; unallocated analog pins are isolated.

# How to test

Use digital control highs equal to VDPWR, nominally 1.8 V. Drive ua[0] with a low-impedance 0.9 V reference, drive ua[2] with 0.2 V, and observe ua[1] with a high-impedance instrument. Modeled output loads are 5 to 20 pF with at least 10 megohms, including 500 ohms pad series resistance. Supply boundaries 1.62 and 1.98 V and temperatures -40, 27, and 85 degrees Celsius are tested. Keep both references fixed during conversion. Do not attach a 50 ohm terminated scope input.

Initialize each word by setting CHARGE_HIGH=0, CHARGE_LOW=1, SHARE=1 for 8 microseconds. Then set all controls low for 0.2 microseconds. This deliberate initialization is the only phase during which CHARGE_LOW and SHARE overlap.

For each bit, least significant first: assert either CHARGE_HIGH for a one or CHARGE_LOW for a zero for 2 microseconds; deassert both and wait 0.2 microseconds; assert SHARE for 2 microseconds; deassert SHARE and wait 0.2 microseconds. After eight bits, wait another 3 microseconds and read the output. The supplied simulation repeats words every 46.9 microseconds (approximately 21.3 kwords/s).

![Phase timing for an example 0xA5 word, including initialization and the read point](images/timing.png)

CHARGE_HIGH and CHARGE_LOW must never overlap. During conversion, SHARE must be low while charging. The complement-generating inverters do not provide dead time; the external controller must do so. Refresh the word periodically because the hold voltage is stored charge.

The qualification report includes native/GDS DRC and LVS, gate antenna checks, all 15 official Tiny Tapeout prechecks, nine full 256-code RC-extracted sweeps, a 30-point PVT grid, 32 mismatch seeds, and 120 stability cases. See `verification/verification.md` for exact measured linearity and operating limits. The output buffer is always powered. A standalone full 0.7 V upward buffer step can take about 6.4 microseconds at the cold/slow boundary and can overshoot; allow 8 microseconds for such a step. The actual DAC protocol is separately verified with the stated 3 microsecond read delay.

![Nine complete extracted code sweeps and local-mismatch results](images/linearity.png)

All nine complete sweeps are monotonic, totaling 2,304 measurements. Worst endpoint INL is 0.63 LSB; DNL ranges from -0.035 to +0.603 LSB. Endpoint linearity removes offset and gain. Raw transfer and the mismatch histogram retain the untrimmed offset. See the [test guide](testing.md) and [measurement CSV](../verification/all_code_results.csv) for coverage and data.

![Loop stability and standalone-buffer large-signal settling](images/stability_settling.png)

All 120 stability cases exceed 60 degrees phase margin, with a minimum of 71.74 degrees. The step response is a separate forced full-range buffer test and shows the cold/slow overshoot; it is not the ordinary DAC word waveform.

For precise absolute voltage, measure outputs at codes 0 and 255 and fit voltage versus code. Use the measured endpoint range when mapping target voltages. PDK mismatch simulations show substantial untrimmed buffer offset; calibration corrects offset and gain within the measured range, but cannot extend that range or remove all nonlinearity. Physical samples have not been fabricated or measured. Modeled linearity, noise, and 32 samples do not establish measured ENOB or manufacturing yield.

# External hardware

Two low-impedance reference sources, a controller providing three nonoverlapping 1.8 V phase signals, and a high-impedance voltage measurement input are required. A level translator may be needed for a 3.3 V controller.
