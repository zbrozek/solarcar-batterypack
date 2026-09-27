# bms_afe_tester-1_1: third schematic review

> Historical review: the [fourth review](schematic-review-2026-09-26-round4.md) covers the 20:34 exports and supersedes these findings. The user has accepted the single VDDCR capacitor; it is no longer a correction request. The load requirement is now clarified as 15 ohms through 4.25 V and 4.4 V unloaded.

Reviewed the September 26 PDF export at 12:34:55, matching netlist at 12:34:53, both BOMs, assembly variant 0, and the saved CubeMX configuration. All eight schematic pages were visually inspected, with connectivity compared against round two. This report supersedes the status of findings in [round two](schematic-review-2026-09-26-round2.md). No design files were changed in this pass. PCB layout and bench behavior were not evaluated.

**The LAN8742A is correctly configured to use its internal core regulator.** The external-core sequencing concern is closed. The zero-scale DAC substitution and recommended-value main-buck inductor also close their earlier findings. Three modest corrections or qualification items remain below; no new P1 circuit defect was found.

## PHY regulator and straps

| Connection | Current implementation | Result |
|---|---|---|
| REGOFF, U7 pin 3 | R95 = 10 kohm to GND | Low enables the internal regulator. |
| LED1 | U7 through R96 to J2 pin 15 anode; pin 14 cathode to GND | Active-high LED wiring agrees with the low strap. |
| VDDCR, U7 pin 6 | Only C50 = 1 uF to GND | External 1P2 and D7 are removed; no external load remains. Add the small bypass below. |
| VDDIO, U7 pin 9 | 3P3 | Correct. |
| VDD1A/VDD2A, U7 pins 19/1 | Filtered ETH_VDDA | Correct, including the regulator input supply. |
| nINTSEL, U7 pin 2 | R98 = 10 kohm to GND | Selects REFCLKO; LED2 remains active high. |

These connections agree with the [LAN8742A datasheet, sections 3.7.3 and 3.8.1](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/DS_LAN8742_00001989A.pdf). The symbol's `nREGOFF` spelling is misleading: Microchip calls the signal `REGOFF`. The implemented polarity is nevertheless correct.

MCU-controlled PHY reset remains the accepted approach. R83/C51 can remain an RFI filter; firmware supplies the reset timing. The prior MDC, center-tap, MDIO and I2C corrections remain intact.

## Remaining findings

### P2: add the specified 470 pF VDDCR bypass

C50 is the only capacitor on U7 pin 6. Add **470 pF in parallel with the existing 1 uF**, placed close to the pin with a short ground return. Microchip specifies both, with the bulk capacitor at least 1 uF and ESR no greater than 1 ohm. This is a documented decoupling omission, not evidence that the present circuit must fail. [Microchip schematic checklist, VDDCR section, page 7](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/SupportingCollateral/LAN8742AQFNRevASchematicChecklist.pdf).

### P2: change R50 from 33 kohm to 47 kohm

The new sense connection is correct: data-port VBUS before D6 feeds R50, and the R50/R51 junction reaches **PB2, U1 pin 28**. The IOC correctly configures PB2 as `GPIO_Input`, `GPIO_NOPULL`, with label `USB_VBUS_SENSE`.

The fitted values are 33 kohm over 82 kohm. Their calculated output is:

| VBUS | Nominal PB2 voltage | Maximum with 1% resistor tolerances |
|---|---:|---:|
| 5.00 V | 3.565 V | 3.586 V |
| 5.25 V | 3.743 V | 3.765 V |
| 5.50 V | 3.922 V | 3.944 V |

The H563 FT input's recommended ceiling is **3.6 V with its supply at zero**, so this lacks margin during the beginning of power-up. This is an operating-range issue; these values do not establish an absolute-maximum violation. With **R50 = 47 kohm and R51 = 82 kohm**, the maximum at 5.5 V becomes **3.522 V**, including resistor tolerance. The high level is adequate for this board's approximately 3.3 V supply and a valid 5 V port. Keep HSLV disabled and internal pulls off. [STM32H563 datasheet, Tables 14, 17 and 20](https://www.st.com/resource/en/datasheet/stm32h563rg.pdf).

The 33k/82k divider appears in [AN4879 section 2.6](https://www.st.com/resource/en/application_note/an4879-introduction-to-usb-hardware-and-pcb-guidelines-using-stm32-mcus-stmicroelectronics.pdf); its suitability still depends on the selected MCU's limits. The proposed 47k/82k pair is for this board, not a claim of covering every supply voltage and detection threshold considered by that generic application note.

### P2: X3 needs a compatible specification or oscillator qualification

This is **pre-existing**, newly identified during this pass. X3 remains **XRCGB25M000F3A00R0**, with R85 = 330 ohm and C52/C53 = 6 pF.

| Parameter | Selected Murata crystal | LAN8742A requirement/reference |
|---|---|---|
| Maximum ESR | 100 ohm | 50 ohm for the 300 uW circuit; 80 ohm for the 100 uW circuit |
| Frequency budget | +/-30 ppm initial, +/-35 ppm over -40 to +125 C, plus aging | +/-50 ppm total |

The crystal's guaranteed limits therefore do not establish compatibility. Its initial and full-range temperature tolerances alone can add to +/-65 ppm. A laboratory temperature range may perform better, but that needs supporting data. Select a suitable crystal/circuit combination, or obtain vendor approval and qualify startup, drive and frequency over the intended conditions. Recalculate load capacitors including PCB capacitance; changing R85 alone is not a complete fix. [Murata exact-part catalog, page 2](https://www.murata.com/-/media/webrenewal/support/library/catalog/products/timingdevice/crystalu/vppt-hcrj126-d.ashx?cvid=20200814082906000000&la=en-sg), [LAN8742A section 5.7](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/DS_LAN8742_00001989A.pdf).

## Other changes verified

| Change | Review result |
|---|---|
| U5A-P changed to DAC80501ZDGSR | All 16 confirmed in the expanded netlist and both BOMs. Closes the former approximately 5 V reset-command finding. |
| L2 changed to SRP1265A-2R2M | 2.2 uH is a recommended value for the 5 V TPS51386 application. Closes the previous out-of-table inductance concern. |
| External 1P2 buck removed | The remaining MT3406 has R8 = 45.3 kohm in variant 0 and R10 = 10 kohm, producing nominally 3.318 V. The base sheet's 10 kohm annotation is overridden correctly. |
| Logic power OR | D2/D6 retain the correct orientation. Data USB still cannot feed the cell 5P0 rail through this path. |
| PD CC resistor population | R12B/R13B are not fitted in variant 0; their presence on the base PDF does not establish parallel populated Rd resistors. |
| Cell clamps and feedback | No changed pin-to-net mappings across 432 cell-sheet components. D8A-P orientation, 1 kohm feedback resistors and 2.2 nF compensation are unchanged. |

TI specifies zero-scale reset for the Z DAC, but the suffix does **not** change the default reference/gain settings. Configure `REF-DIV=1` and `BUFF-GAIN=1` before nonzero codes for the intended nominal cell command `Vcell = 5 V * code / 65536` with external gain two. Zero-scale POR removes the high settled reset command; full-circuit startup transients still require measurement. [DAC80501 datasheet, device comparison and GAIN register](https://www.ti.com/lit/ds/symlink/dac80501.pdf).

The new inductor is rated 22 A RMS and 40 A saturation. At 20-to-5 V and 600 kHz, calculated ripple is 2.84 A peak-to-peak; the peak corresponding to the maximum 12.5 A valley-current limit is approximately 15.34 A. Current margin is ample. [TPS51386 Table 8-2 and electrical characteristics](https://www.ti.com/lit/ds/symlink/tps51386.pdf), [Bourns SRP1265A data](https://www.bourns.com/docs/product-datasheets/srp1265a.pdf).

## Prototype and release notes

The previously accepted isolated-rail qualification remains: the plot-based idle estimate is about 5.5 V, with about 0.5 V to the DAC's 6 V absolute maximum. Measure enable, idle and load-release peaks and cell accuracy. Include the new zero-code startup state, where the output divider supplies essentially no preload. No mandatory converter redesign is inferred from the nominal estimate. [HALO converter data](https://www.haloelectronics.com/pdf/dc-converter-1w2w.pdf).

Removing one logic buck reduces nominal data-port input capacitance from about 32 uF to **21 uF**; PD input remains about 20.1 uF. Hot-plug inrush and PD-only cold-start at the lowest intended input remain prototype checks. Cell-loop transient response, pass-FET temperature and source-only behavior retain the qualifications documented in round two.

The placement exports still describe the older PCB: L2 has the old `SMD-4.1x4.1x3.0` footprint, and R8A/R8B/U2A/U2B still appear despite the current single-buck schematic. Synchronize the PCB and regenerate assembly outputs before release. This is an export-consistency note, not a new schematic circuit finding.

Evidence locations refer to this export: netlist lines 679-689 for PB2/VBUS, 1799-1801 for VDDCR, 619-634 for all DACs, and variant BOM row 34 for R8. The PDF and netlist were confirmed unchanged from the frozen review snapshots at completion.
