# bms_afe_tester-1_1: second schematic review

> Historical review: the [third review](schematic-review-2026-09-26-round3.md) covers the 12:34 exports and supersedes the status of these findings, including the PHY core supply, DAC reset variant and L2 inductance.

Reviewed the PDF exported September 26 at 11:09:31, the netlist exported at 11:09:29, and the CubeMX file saved at 11:12:30. This supplements and supersedes the status of findings in the [first review](schematic-review-2026-09-26.md). Schematic and netlist changes were inspected; no design files were edited and no bench measurements were made.

**The changes resolve the principal digital wiring errors and the USB power backfeed path. The principal remaining startup issue is the approximately 5 V cell command at DAC reset. The isolated rail's estimated 5.5 V idle level merits prototype qualification; the estimate does not establish an absolute-maximum violation.**

The acceptance case remains one tester, 2.0-4.4 V per cell, a 15-ohm load on one cell at a time, logic/comms operating from ordinary 5 V USB, and cell operation after a suitable PD contract. Independent 3P3/1P2 startup with a Schottky clamp and MCU-controlled PHY reset are intentional design choices.

## Confirmed fixes and improvements

| Item | Current implementation | Review status |
|---|---|---|
| Ethernet MDC | SMI.MDC_1 now reaches U1 pin 9 / PC1 | Closed. Matches ETH_MDC and the .ioc. |
| I2C SCL pull-ups | R21 and R49 add 1.5 kohm pull-ups to I2C1.SCL and I2C3.SCL | Closed. Both clock nets now have defined external pull-ups. |
| Ethernet center tap | J2 pin 7 now connects directly to ETH_VDDA, with C36 bypassing it | Closed. Matches the vendor bias arrangement. |
| USB data termination | R128/R129 removed; D+/D- connect through the protection network without extra 33-ohm termination | Closed. Appropriate for the H563's integrated matching. |
| Data-port power backfeed | D2 and D6 diode-OR 5P0 and VBUS_DATA into 4P7 for the logic bucks | Closed for the previously identified conducting path. Data-port power no longer feeds the cell 5P0 rail or U8's output. |
| Host taking over cell loads after PD removal | Logic-only diode-OR separates the data feed from cell power | Closed for this former power-transfer path. Firmware should still stop/reset cell operation on PD loss. |
| Negative cell voltage without a bypass | D8A-P connect anode to VOUT_N, cathode to VOUT_P | Close the missing-clamp finding. Actual negative excursion is now governed by diode current, temperature and wiring. |
| Main buck inductor current margin | L2 is SRP1265A-4R7M, rated 13.5 A RMS / 28 A saturation at the manufacturer's stated conditions | Close the previous undersized-inductor finding. Inductance-value qualification remains below. |
| HSE configuration | .ioc now specifies 16 MHz, matching X1 | Closed. |
| DAC SPI configuration | 7.5 Mbit/s, 24-bit, MSB first, CPOL low / second-edge capture | The previous excessive clock/incomplete format concerns are resolved in the saved configuration. |
| Output discharge | R17/R19 changed from 10k/10k to 1k/1k, both 0.1% | Ten times stronger bleed and faster passive downward settling; compensation also changed. |

Connectivity examples in the current netlist: MDC at line 803; I2C3 SCL at 2491; I2C1 SCL at 2503; ETH_VDDA at 2731; VBUS_DATA_1 at 688. These line numbers describe this export only.

The new power tree is electrically consistent: D2 passes 5P0 toward 4P7; D6 passes data VBUS toward 4P7. Their cathodes meet on 4P7. Reverse isolation between the two feeds follows from this orientation. The data host can power the logic bucks without energizing the cell supplies.

## Remaining analog findings

### 1. Qualify the isolated rail's operating margin on the prototype

U6 remains DC21-V0505SLF and still directly powers U3, U4's secondary side, and U5. Extrapolating HALO's green 5 V-input trace in the 2 W / 5 V-output plot is useful: approximately 5.45 V at 40 mA and 4.95 V at 400 mA give Vraw ~= 5.51 V - (1.4 ohms)*Iout. This predicts approximately **5.5 V at zero load**, at nominal 5 V input. The round-two circuit itself draws roughly 5-7 mA while idle (DAC, isolator, LED and 2 kohm feedback divider), giving essentially the same **5.50 V with no external cell load**. These are approximate plot-based estimates, not measured values or guaranteed limits.

The concrete concern is therefore essentially zero nominal margin to the downstream ICs' 5.5 V operating ceiling. HALO's line-regulation specification permits up to about 1.2% output change per 1% input change, so a 1% high input can add roughly 60-65 mV. Check actual idle voltage, input tolerance, turn-on and load removal before choosing a remedy. The extrapolation does not establish destructive voltage or require replacing the converter automatically; it also does not bound unit variation, temperature or transients. If measurements/vendor data show inadequate margin, provide a bounded supply or protection while preserving headroom at 4.4 V and 293 mA. [HALO converter data](https://www.haloelectronics.com/pdf/dc-converter-1w2w.pdf), [DAC80501 ratings](https://www.ti.com/lit/ds/symlink/dac80501.pdf), [TLV379 ratings](https://www.ti.com/lit/ds/symlink/tlv379.pdf).

The DAC's supply absolute maximum is 6 V, leaving approximately 0.5 V between the nominal idle estimate and that stress limit. The TLV379 and CA-IS3741 supply absolute maxima are both 7 V. Accordingly, classify this as a prototype qualification item rather than a demonstrated damage mechanism or mandatory converter replacement. Operation above 5.5 V would still fall outside the specified operating range; being below absolute maximum does not establish specified accuracy, functionality or lifetime. Check rail peaks and cell accuracy before accepting that tradeoff. [DAC80501 absolute maximum and operating ratings](https://www.ti.com/lit/ds/symlink/dac80501.pdf), [TLV379 ratings](https://www.ti.com/lit/ds/symlink/tlv379.pdf), [CA-IS3741 ratings](https://e.chipanalog.com/Public/Uploads/uploadfile/files/20250123/CAIS374xdatasheetVersion1.08en20241217.pdf).

### 2. The selected DAC still requests approximately 5 V on cell enable/reset

U5 remains DAC80501MDGSR. Its reset DAC output is 2.5 V with the default gain/reference settings. Equal R17/R19 still give an external gain of two, so the initial cell command remains 5 V. Changing their absolute resistance does not change this ratio.

If startup must remain inside 2.0-4.4 V, this still needs a safe reset/output-isolation strategy. Firmware can change the voltage after power-up but cannot initialize an unpowered DAC before its directly connected output stage begins operating. A zero-scale-reset variant would remove the 5 V default but does not by itself supply a defined 2 V startup or qualify analog startup transients. [DAC80501 reset and gain behavior](https://www.ti.com/lit/ds/symlink/dac80501.pdf).

## The new clamps and the reset decision

**D7 is correctly oriented for the intended rail clamp:** anode on 1P2, cathode on 3P3. It diverts current when 1P2 exceeds 3P3 by a forward diode drop, reducing the differential stress that otherwise falls on downstream internal structures.

It does not establish the LAN8742A's documented startup relationship: section 3.7.3.1 calls for VDDIO to reach 80% of its final voltage before external VDDCR is applied. A clamp can bring an otherwise-low 3P3 rail to approximately 1.2 V minus a diode drop; it cannot make that rail reach approximately 2.65 V first. Accordingly, record this as an intentional departure from the specified sequence with a protective clamp, not as proof that latch-up or all startup failures are impossible. I am not proposing another sequencing circuit contrary to your stated decision. Qualify fast/slow ramps, interrupted ramps, brownouts, and repeated power cycles. [LAN8742A datasheet, section 3.7.3.1](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/DS_LAN8742_00001989A.pdf).

**The short PHY reset RC is fine with MCU-controlled reset.** R83/C51 can serve as an RFI filter; it does not need to generate the startup delay. This is removed from the hardware correction list. Firmware should perform a real reset after valid supplies: allow at least 25 ms from valid supplies to deassertion and at least 100 us assertion. PA3 remains physically connected to ETH_nRST; its final firmware configuration still needs to implement that intent. Reset timing and supply clamping address different mechanisms. [LAN8742A reset timing](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/DS_LAN8742_00001989A.pdf).

**D8A-P solve the missing negative-current path.** Their orientation is correct and their 20 V reverse rating exceeds the intended 4.4 V positive cell voltage. They permit an unpowered cell to bypass end-to-end string current instead of relying on op-amp protection or MOSFET breakdown. They clamp the cell to approximately minus their forward voltage, not exactly zero. Verify that excursion against the DUT's allowed differential voltage at the expected string current and minimum temperature. This is now a clamp-qualification check rather than a missing-component finding.

The clamps do not isolate an externally driven positive cell output or add active sinking. The bench-supply-override limits from the first review therefore remain.

## Changes that need transient qualification

**Cell feedback:** the total intentional bleed is now 2 kohms. It draws 1 mA at 2 V and 2.2 mA at 4.4 V. With negligible DUT load, its first-order discharge time constant is about 2 ms per microfarad, down from 20 ms per microfarad.

C21 remains 2.2 nF. Reducing both feedback resistors tenfold moves the feedback-network zero/pole from approximately 7.23/14.47 kHz to 72.3/144.7 kHz. These are the feedback-network frequencies, not a prediction of the complete loop's crossover or stability. If the intent was to retain the previous feedback transfer function while increasing bleed, C21 would scale to 22 nF. Neither value can be declared correct without qualifying the complete TLV379/Q1/DUT loop. Measure setpoint steps and balancing turn-on/off at minimum and maximum relevant output capacitance.

**Main buck inductance:** at 20-to-5 V and 600 kHz, the new 4.7 uH L2 gives approximately 1.33 A peak-to-peak ripple. Using the maximum 12.5 A valley current limit gives a nominal peak envelope of about 13.83 A, comfortably below this part's 28 A saturation rating. Its 13.5 A RMS rating also clears the 6 A design target. [Bourns SRP1265A table](https://www.bourns.com/docs/product-datasheets/srp1265a.pdf).

The value change is separate from that current-rating improvement. TI's 5 V application table recommends 1.5 or 2.2 uH; 4.7 uH with unchanged C32/C33 changes the filter and internally compensated regulator response. This is a qualification item, not evidence of oscillation. Either retain the stronger inductor family with a recommended inductance, or verify the 4.7 uH choice through startup and load-step testing. [TPS51386 Table 8-2](https://www.ti.com/lit/ds/symlink/tps51386.pdf).

**Ordinary 5 V startup:** data-port-only logic power now takes D6 directly into 4P7 and then the MT3406 bucks. PD-port-only 5 V startup takes U8 in dropout followed by the added D2 drop before the logic bucks. Check the latter with low source voltage, cable drop, MCU activity and Ethernet startup. The schematic does not prove it fails; it has less headroom than the first version on that path.

## Other open items, with updated scope

- **Data-port VBUS sensing is still absent.** VBUS_DATA_1 contains C80A, D6 and the connector VBUS pins, with no MCU sense input. U1 PB1 still measures the PD connector. Its purpose is to enable the USB D+ attachment pull-up only while the data host supplies VBUS, and remove it when that supply disappears. The separate PD connector can keep the MCU alive after the host port loses power, so board power alone cannot provide that indication. This concerns USB attachment and host power-state behavior; it requires no PD negotiation on the data port and does not imply enumeration will fail during ordinary powered use. A suitable GPIO detector with firmware control of USB attachment is sufficient. [ST AN4879, sections 2.6 and 3.1.1](https://www.st.com/resource/en/application_note/an4879-introduction-to-usb-hardware-and-pcb-guidelines-using-stm32-mcus-stmicroelectronics.pdf).
- **Data-port inrush is reduced, not eliminated.** The former 66 uF cell-rail capacitor bank is now isolated from the data feed. Nominal directly reachable input capacitance is about 32 uF: C80A plus the two 11 uF MT3406 input networks, before other charging effects. PD-port direct capacitance remains about 20.1 uF. A measured current/charge test or controlled-slew input is still needed for predictable USB compatibility; the previous 98 uF estimate no longer applies.
- **CC termination coordination is unchanged.** The PD connector still has external 5.1k Rd resistors, while the MCU UCPD also supplies selectable terminations. Confirm the chosen firmware/dead-battery configuration leaves one intended effective Rd, and handles PC9's use for I2C3. The data-only connector's fixed Rd resistors are appropriate to that role. [ST AN5225](https://www.st.com/resource/en/application_note/an5225-usb-typec-power-delivery-using-stm32-mcus-and-mpus-stmicroelectronics.pdf).
- **Thermal and accuracy qualification remain.** At 15 ohms, Q1 still dissipates roughly 0.42 W near 2.5 V for a 5 V raw rail. The smaller divider contributes only a few additional milliwatts. The gain ratio remains two and resistor tolerance remains 0.1%, so lowering resistance does not remove the divider-ratio or amplifier-offset errors. Calibration, load-step behavior and adequate pass-FET copper remain part of acceptance.

## Next measurements to prioritize

1. Raw isolated rail and cell output during first enable, reset, idle and 15-ohm load removal. These address the two outstanding high-priority analog issues directly.
2. One cell's setpoint/load-step response with the new feedback values; Q1 temperature at approximately 2.5-2.75 V into 15 ohms.
3. 5 V boot through each connector separately, both cable orders, and PD removal with a data cable present. Check logic continuity, connector backfeed and inrush.
4. 3P3/1P2 ramp differences and reliable PHY recovery with D7 and the intended firmware reset. Include brownouts and interrupted power cycles.
5. A disabled cell in the full DUT string: measure D8's actual negative clamp voltage under end-to-end load.
6. Main 5P0 transient response with the new L2, especially if supporting multiple balancing loads.

No new definite connectivity error was found in the changed cell or primary-power circuitry. This review closes the identified fixes without treating unmeasured startup, stability or thermal behavior as proven.
