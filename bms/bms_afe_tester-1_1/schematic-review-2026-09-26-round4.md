# bms_afe_tester-1_1: fourth schematic review

Reviewed the September 26 PDF exported at 20:34:51, matching netlist at 20:34:40, variant-0 BOM, project variant configuration, and saved IOC. Inspected all eight schematic pages, compared the compiled connectivity and parts with round three, and checked all sixteen cell channels. No design files were changed. This report supersedes the status of findings in [round three](schematic-review-2026-09-26-round3.md).

**The revised cell circuit is consistent with the clarified operating requirements. No new definite analog or primary-power wiring defect was found. The remaining schematic correction is the drive arrangement for the new PHY crystal.**

## Requirements and accepted choices

- Generate 2.0-4.4 V per cell. A 15-ohm discharge load is required only through 4.25 V, on one channel at a time; 4.4 V is required without an external load.
- Active sinking is for discharging DUT capacitance, not absorbing continuous externally supplied current.
- Only small parasitic capacitance is directly across an output. Substantial DUT capacitors are behind series resistors.
- Logic/comms operate from ordinary 5 V USB. Cell simulation may require a suitable PD contract, nominally 20 V / 3 A.
- **Keep the existing single 1 uF capacitor on VDDCR.** This is an accepted user decision and is removed from the correction list. MCU-controlled PHY reset remains accepted.
- The unregulated isolated rail remains an accepted architecture with prototype voltage/accuracy qualification. This review does not reopen a mandatory converter redesign.

## Remaining schematic finding

### P2: restore the drive-limiting provision for the 100 uW PHY crystal

X3 is now **ABM11W-25.0000MHZ-8-D1X-T3**. Its 50-ohm maximum ESR and +/-10 ppm initial, +/-20 ppm temperature, and +/-2 ppm first-year aging specifications resolve the old crystal's ESR/frequency-budget mismatch. However, this replacement is rated **100 uW maximum drive**, and R85 has been removed: XTAL2 now connects directly to the crystal.

Microchip specifies a **500-ohm series resistor, 495-505 ohms**, in its 100 uW circuit. Restore that provision on XTAL2, following Figure 5-8, or use a vendor-qualified alternative. The direct connection does not follow that circuit; this is not a claim that actual overdrive or failure has been measured. [Abracon ABM11W electrical specifications and ordering codes](https://abracon.com/Resonators/ABM11W.pdf), [LAN8742A section 5.7.2, Figure 5-8 and Table 5-17](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/DS_LAN8742_00001989A.pdf).

Also recalculate C52/C53 for the replacement's **8 pF load specification**. Both remain 6 pF, as used with the previous 6 pF crystal. Equal 6 pF external capacitors contribute 3 pF effective series capacitance before pin/PCB parasitics. Include those parasitics and verify frequency, drive and startup. The schematic alone does not establish the final capacitor values; changing the resistor alone does not finish oscillator qualification.

Evidence: netlist lines 717 and 723-731; PDF sheet 5; variant BOM confirms X3 and the absence of R85.

## Cell output redesign

The new **TLV9051 + complementary 2SCR572D3/2SAR572D3 emitter followers** has the correct topology. The DAC now drives IN+, the divider drives IN-, Q1 sources from the isolated supply, and Q4 sinks to cell negative. Separate 22-ohm base resistors and the 10-kohm drive-to-output resistor are consistently connected. Explicit checks across all sixteen channels found no mismatched topology or component selection.

The local TO-252-3 footprint contains pads 1, 3 and 4; pad 4 is the large collector land. This agrees with the symbol convention even though ROHM calls the collector terminal 2. No symbol/footprint numbering defect was found.

### Range and headroom

The upper emitter follower needs:

`Vraw > Vcell + VBE + 22 ohms * IB + op-amp output headroom`

Low VCE(sat) does not eliminate VBE. Nevertheless, the clarified endpoints are supported by the nominal model evidence:

| Existing saved DC case | Command/load | Calculated output | Calculated raw rail |
|---|---|---:|---:|
| Loaded case | 4.3 V / 15 ohms | 4.30065 V | 5.04513 V |
| Unloaded case | 4.4 V / no external load | 4.40065 V | 5.44646 V |

These saved runs use the TI TLV905x family model, LTspice-distributed ROHM transistor models, and a 5.45 V source with 1.4-ohm series resistance. Their circuit agrees with the new buffer topology. The loaded case is slightly above the required 4.25 V endpoint. These are typical-model results, not measured limits or production-corner guarantees; the supply model also omits some auxiliary converter loading.

ROHM's typical VBE near 0.28 A is approximately 0.69 V at room temperature and rises when cold. Verify **4.25 V into 15 ohms at the lowest actual isolated rail and intended temperature**. A loaded 4.4 V failure is outside the clarified requirements and is not a finding. [ROHM NPN data](https://fscdn.rohm.com/en/products/databook/datasheet/discrete/transistor/bipolar/2scr572d3tl1-e.pdf).

### Compensation and capacitive loads

C21 is now **68 pF from the op-amp output to the feedback midpoint**, rather than 2.2 nF across the upper feedback resistor. The old compensation frequency calculation therefore no longer applies. This capacitor provides local high-frequency feedback while the DC loop senses the cell output.

Existing 68 pF model results show about 60 degrees or more phase margin for their tested small-parasitic cases, including a DUT filter represented by **100 ohms / 470 nF / 100 ohms**. This supports the intended filtered-load arrangement, but does not qualify every DUT filter. Check balancing edges, voltage steps and settling with the real harness and input network.

The saved sweep also predicts much lower margin with 10 nF directly across the output and instability in some 100 nF direct-load cases. Those loads are outside the clarified intent, so this is a **load-envelope limit**, not a requirement to redesign for a large direct capacitor.

Q4 supplies active downward correction and supersedes the earlier source-only/passive-discharge limitation. Its relevant check is the discharge transient. Continuous externally driven sinking is not part of this review's acceptance case.

### Dissipation and accuracy

Q1's calculated dissipation peaks around **0.45-0.46 W near 2.5 V output into 15 ohms**, using the existing 5.45-5.51 V / 1.4-ohm source approximation. ROHM's 125 C/W junction-to-ambient figure on its stated test PCB corresponds to roughly 57 C rise at 0.46 W; actual copper changes this. Provide suitable collector copper and measure the temperature. Its 10 W case-temperature rating is not a free-air allowance. [ROHM thermal data](https://fscdn.rohm.com/en/techdata_basic/transistor/thermal_resistance/2scr572d3_thermal_resistance-e.pdf).

The TLV9051 improves speed and offset relative to TLV379. Its maximum 25 C input offset contributes approximately 3.2 mV at gain two; the two 0.1% feedback resistors permit approximately 4.4 mV gain error at a 4.4 V output. DAC errors and wiring drops add separately. Calibration remains relevant if millivolt accuracy is required. [TI TLV9051 specifications](https://www.ti.com/lit/ds/symlink/tlv9051.pdf).

All sixteen DACs remain zero-scale-reset **DAC80501Z**. Configure REF-DIV/BUFF-GAIN before nonzero commands; the reset suffix alone does not choose the desired range. Negative Schottky clamps remain correctly oriented. Startup transients, rail peaks, output faults and actual DUT settling remain prototype checks, rather than newly established schematic failures. [DAC80501 data](https://www.ti.com/lit/ds/symlink/dac80501.pdf).

## Other changes checked

| Item | Current result |
|---|---|
| PB2 data-VBUS sense | R50 is now 47 kohm, R51 82 kohm, correctly tapped before D6. IOC remains GPIO input with no pulls. Previous divider finding closed. |
| Internal PHY regulator | REGOFF remains low with matching LED polarity; VDDCR has no external source or load. Previous sequencing finding stays closed. |
| Main buck L2 | Now SRP7030CA-2R2M: 2.2 uH, 13 A RMS, 19 A typical saturation. Smaller than the previous part but reasonable for the intended load. |
| Logic buck R8 | Now 45.3 kohm in the base sheet, netlist and BOM, giving nominally 3.318 V with R10 = 10 kohm. No variant ambiguity remains. |
| Power paths | D2/D6 OR and both regulator connections remain correct. Data USB cannot forward-feed the cell supply through this path. |
| PD CC population | Variant 0 omits R12B/R13B; the data-port termination resistors remain populated. |
| Digital interfaces | MCU pin assignments, both expanders and all sixteen isolators checked; no new connectivity defect found. Earlier MDC, Ethernet bias, USB termination and I2C fixes remain intact. |
| MCU crystal | Removal of the former zero-ohm series R42 is electrically neutral at schematic level. This is separate from removing the nonzero PHY drive resistor. |

For the smaller L2, nominal 20-to-5 V operation at 600 kHz gives 2.84 A peak-to-peak ripple: about **7.42 A peak / 6.06 A RMS at 6 A load**. Maximum-DCR winding loss is approximately 0.50 W before temperature/core-loss effects. The nominal peak corresponding to the regulator's maximum valley-current limit is about 15.34 A. The new part retains useful margin, but the old 40 A saturation figure no longer applies. [Bourns SRP7030CA data](https://www.bourns.com/docs/product-datasheets/SRP7030CA.pdf), [TPS51386 data](https://www.ti.com/lit/ds/symlink/tps51386.pdf).

The 47k/82k divider's calculated worst-case input is 3.522 V at 5.5 V VBUS with 1% resistors, within the unpowered FT input operating ceiling. Keep internal pulls and HSLV disabled. [STM32H563 input ratings](https://www.st.com/resource/en/datasheet/stm32h563rg.pdf).

## Review limits and next validation

Prior firmware integration checks remain: actively reset the PHY, initialize all chip selects before SPI activity, define behavior after MCU-only reset, and use PB2 to gate USB attachment. No firmware application was reviewed.

The most useful hardware checks are: 4.25 V / 15-ohm regulation at supply/temperature extremes; Q1 temperature near 2.5 V under that load; voltage/load steps with the actual DUT filters; and PHY oscillator frequency/drive/startup. Existing USB inrush and PD-only 5 V cold-start checks remain unchanged.

Simulation figures above were read from saved local decks, raw results and completion logs, which showed no failure or relaxed-convergence warning. A new batch launch did not produce usable verification output, so no fresh simulation pass is claimed. No bench measurements or PCB-layout review were performed. The accepted VDDCR and isolated-supply choices are not reopening correction requests.
