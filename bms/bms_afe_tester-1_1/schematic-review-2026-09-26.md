# bms_afe_tester-1_1 schematic review

**Historical first pass:** the subsequent [second review](schematic-review-2026-09-26-round2.md) records fixes and the current remaining findings against the 11:09 export.

Reviewed 2026-09-26. **I would correct the issues below before releasing this revision for fabrication.** The isolated DAC/pass-transistor architecture can plausibly meet the stated load, but the secondary supply bounds, reset voltage, and several control/communications connections need attention.

## Scope and acceptance case

This review uses the eight-sheet schematic in [the current output PDF](outputs/bms_afe_tester-1_1.PDF), the expanded [WireList netlist](outputs/bms_afe_tester-1_1.NET) generated at 09:52 on September 26, the project variant, component database, and CubeMX configuration. The May 16 PDF in the project root is older and was not used as the current design. The README's programmable-flyback/12 V description is also obsolete for this revision.

The clarified requirement is 2.0-4.4 V per cell, a minimum load resistance of 15 ohms, and one balancing load at a time. Sixteen simultaneous loads are optional. MCU and communications must operate from ordinary 5 V USB; cell supplies may require a negotiated PD profile, probably 20 V / 3 A. One standalone tester is the intended use. External supply override and series-connected testers are evaluated separately below.

All eight schematic pages were inspected visually and connections were checked against the expanded netlist. Manufacturer documents were checked for the principal active parts. This was a schematic review, not an Altium ERC run, PCB creepage/thermal/layout signoff, circuit simulation, or bench test. No design files were changed. References such as U3/Q1/R17 refer to the repeated cell sheet; physical channel instances have suffixes A-P.

Sheet map: 1 top level; 2 STM32H563; 3 cell simulator; 4 USB-C connector; 5 LAN8742A; 6 TCAL9539; 7 MT3406; 8 TPS51386.

## Findings to address before fabrication

### 1. P1 - The isolated rail is not bounded within the downstream IC supply ratings

**Location:** sheet 3, U6, U3/U4/U5, Q1; example net NetC20A_1, netlist line 2338.

DC21-V0505SLF is unregulated. Its output directly powers the TLV379, DAC80501, and secondary side of CA-IS3741. Their maximum recommended supply is 5.5 V. HALO's typical 2 W / 5 V load curve is already approximately 5.45 V at 40 mA; it does not specify the lower-load region where this circuit normally operates without balancing. The DAC, isolator, divider, and LED draw only a few milliamps at idle. Input tolerance, line regulation, and load removal leave no demonstrated upper-rail margin.

This establishes a missing design guarantee, not a measured claim that every unit exceeds 6 V or fails. Use a regulated isolated supply with specified startup/light-load limits, or redesign the secondary rails to protect the ICs while preserving 4.4 V loaded output headroom. A nominal 5 V LDO behind a nominal 5 V unregulated converter does not automatically solve both high- and low-rail limits. [HALO datasheet](https://www.haloelectronics.com/pdf/dc-converter-1w2w.pdf), [DAC80501](https://www.ti.com/lit/ds/symlink/dac80501.pdf), [TLV379](https://www.ti.com/lit/ds/symlink/tlv379.pdf), [CA-IS374x](https://e.chipanalog.com/Public/Uploads/uploadfile/files/20240611/CAIS374xdatasheetVersion1.06en.pdf).

### 2. P1 - Cell enable initially commands approximately 5 V

**Location:** sheet 3, U5 DAC80501MDGSR, R17/R19, Q2/Q3.

The M DAC variant resets to midscale. With its default 2.5 V reference, gain of two, and reference divisor of one, DAC output is 2.5 V. The external loop multiplies that by two, requesting 5.0 V at the simulated cell. That exceeds the intended 4.4 V test range. Actual output can be limited by supply headroom, but this is not a controlled voltage ceiling.

PWR_EN powers the entire secondary; firmware cannot initialize the DAC while holding this output stage independently disconnected. Choose a safe power-on state, or add an independently controlled output clamp/disconnect so initialization happens before connecting the cell. Changing to a zero-scale DAC is useful but still requires a defined startup sequence and transient verification. [DAC80501 device comparison and reset/register behavior](https://www.ti.com/lit/ds/symlink/dac80501.pdf).

### 3. P1 - Both I2C clock lines lack external pull-ups

**Location:** sheet 2, I2C1.SCL and I2C3.SCL; sheet 6, U9A/U9B pin 22. Netlist lines 2491 and 2502.

R54 and R34 pull up SDA only. Neither SCL net has a pull-up in the MCU sheet, expander sheet, or expanded connectivity. Normal open-drain I2C operation therefore has no defined external mechanism to return SCL high. These buses control every channel's power and DAC chip select.

Add one suitably sized SCL pull-up to 3P3 on each bus, choosing resistance for bus capacitance, speed, and sink current. Weak MCU internal pull-ups may enable a slow workaround; they should not be the implicit production design. [TCAL9539 pin descriptions and I2C interface](https://www.ti.com/lit/gpn/tcal9539).

### 4. P1 - Ethernet MDC is on the wrong MCU pin

**Location:** sheet 2, U1 pin 8 PC0; SMI.MDC_1, netlist lines 779-781.

The schematic routes MDC to PC0. STM32H563 assigns ETH_MDC to PC1, pin 9, alternate function 11. PC1 is currently unused, and the CubeMX file already selects PC1. Consequently the hardware Ethernet management interface cannot reach the PHY as drawn.

Move MDC to PC1. Bit-banging management through PC0 is a possible workaround, but it needlessly departs from the configured hardware interface. [STM32H563 datasheet, alternate-function table](https://www.st.com/resource/en/datasheet/stm32h563rg.pdf).

### 5. P2 - The two USB power inputs are not fully isolated from each other

**Location:** sheet 1 D2; sheet 8 U8/L2; J11A data port and J11B PD port.

D2's orientation is correct for feeding 5P0 from the data port while blocking 5P0 from feeding that same port. However, data-only power can travel from 5P0 through L2 and the synchronous buck's high-side body diode to U8 VIN and the PD connector's VBUS. There is no separate reverse-blocking element in that path. Thus the unpowered PD port can acquire voltage, and later attachment/discharge behavior is not controlled.

Provide a reverse-blocking power path and explicitly handle the cases of either cable alone, both connected, and either removed first. This is inferred from the schematic and U8's integrated MOSFET topology; measure the backfeed voltage/current rather than assuming a specific value. [TI's explanation of buck reverse-current paths](https://www.ti.com/lit/an/slyt689/slyt689.pdf).

### 6. P2 - USB input charging bypasses the intended soft start

**Location:** J11A/C80A/D2, C32/C33, C17A/B/C18A/B; J11B/C80B/C29/C30.

The data port directly charges approximately 98 uF nominal across its connector capacitor, 66 uF main output bank, and 22 uF downstream buck input banks, before smaller capacitors and voltage-dependent capacitance are considered. D2 does not limit this charging slew. U8's soft-start capacitor C39 does not control charging through D2. The PD port also sees approximately 20.1 uF directly before downstream startup.

Add controlled inrush on the data feed and qualify both attachment paths against the intended USB sources. Cable/source impedance must not be the only current-control mechanism. Treat connector capacitance and pre-contract current as explicit USB design constraints; the capacitance estimates alone are not a measured compliance result. [USB-IF electrical/inrush test requirements](https://compliance.usb.org/index.asp?UpdateFile=Electrical).

### 7. P2 - Ethernet external-core supply sequencing is not guaranteed

**Location:** sheet 5 U7 VDDCR and R95; sheet 7 U2A/U2B.

The PHY's internal core regulator is disabled, and separate 1P2 and 3P3 bucks start from the same 5P0 rail without a sequencing dependency. LAN8742A requires VDDIO to reach at least 80% before external VDDCR is applied. These independent starts do not establish that ordering.

Use the PHY internal regulator, or sequence external 1P2 from valid 3P3. Also implement the required PHY reset after supplies are valid; R83/C51 is only a 10 kohm / 27 pF filter, not a millisecond reset delay. The reset signal reaches PA3, but the current CubeMX file does not configure it. Allow at least 25 ms after valid supplies before reset deassertion, and meet the 100 us minimum reset assertion. [LAN8742A datasheet, sections 3.7.3.1 and 5.6.3](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/DS_LAN8742_00001989A.pdf).

### 8. P2 - Ethernet transformer center-tap bias differs from the vendor circuit

**Location:** sheet 5, J2 pin 7 CT and C36.

The PHY-side center tap is connected only to a 100 nF capacitor to ground. Microchip's checklist calls for the transmit center tap to connect directly to VDDA and the common receive center tap. The four 49.9-ohm pull-ups provide another bias path, but do not make this the specified center-tap connection.

Restore the manufacturer's center-tap bias arrangement, or establish an approved alternative with waveform/link testing. This is a concrete reference-design discrepancy; it does not by itself prove that every link partner will fail. The official evaluation schematic confirms a 0-ohm connection from the analog rail to the shared PHY-side center tap. [LAN8742A checklist](https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/SupportingCollateral/LAN8742AQFNRevASchematicChecklist.pdf), [EVB8742 schematic, sheet 2](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/BoardDesignFiles/evb8742_sch.pdf).

### 9. P2 - USB data series resistance is excessive for this MCU's integrated termination

**Location:** sheet 4, data-port R128A/R129A, each 33 ohms.

STM32H563 already integrates USB matching resistance; ST specifies no additional series termination. Adding 33 ohms to each line changes source impedance substantially. Fit 0-ohm links in these footprints as the baseline, then validate USB signal quality with the actual routing, protection, connector, and cable. This is a signal-integrity risk, not a claim that enumeration is impossible. [STM32H563 USB electrical characteristics, Table 119 note 3](https://www.st.com/resource/en/datasheet/stm32h563rg.pdf).

### 10. P2 - Disabled cells need a defined behavior inside the DUT's series string

**Location:** sheet 3, VOUT_P/VOUT_N, Q1, R17/R19, U3 IN+.

There is no explicit antiparallel clamp across a cell. Even one tester can form a series string through its attached BMS. If the BMS draws end-to-end supply current while one channel is disabled or starts late, that current flows from the disabled cell's negative terminal toward its positive terminal. Its 20 kohm divider alone would imply Vcell = -Istring * 20 kohm: only 50 uA corresponds to -1 V before protection/parasitic paths intervene. Q1's body diode does not provide the needed negative-voltage bypass.

Provide a bounded reverse-cell path appropriate to the DUT's allowed negative voltage and string current, and define startup, shutdown, and single-channel-disable sequencing. Test this with the DUT drawing stack power. Severity becomes P1 if independent channel shutdown under stack load is an intended normal operation. This concern also exists without an external bench supply or a second tester.

### 11. P2 - Data-port VBUS cannot be detected independently

**Location:** sheet 1 J11A/D2; sheet 2 R5/R24 and U1 PB1.

The data connector's VBUS net connects only to D2 and C80A. The MCU divider measures the separate PD connector's VBUS. When PD powers the board, firmware therefore lacks a direct indication of whether the data host's VBUS is present. Add a data-port VBUS sense input and use it to control the USB attach pull-up. Otherwise attachment behavior can remain asserted into an unpowered data host. This is an attachment/compliance defect, not a claim that normal enumeration always fails. [ST AN4879, sections 2.6 and 3.1.1](https://www.st.com/resource/en/application_note/an4879-introduction-to-usb-hardware-and-pcb-guidelines-using-stm32-mcus-stmicroelectronics.pdf).

### 12. P2 - L2 does not cover the main buck's current-limit envelope

**Location:** sheet 8 L2 FTC404030S1R5MGCA and U8.

The inductor specification lists 6.5 A typical / 6.0 A lower-limit RMS capability and 12.5 A typical / 11 A lower-limit saturation current. At 20-to-5 V, 1.5 uH and 600 kHz, nominal ripple is approximately 4.17 A peak-to-peak. A 6 A load therefore produces about 6.12 A RMS and an 8.08 A peak, leaving little thermal margin at that optional aggregate load.

More importantly, U8 limits valley current at up to 12.5 A. Adding one full nominal ripple excursion gives an approximately 16.7 A peak design envelope, exceeding L2's saturation rating. Actual fault waveforms depend on switching behavior and saturation. Choose the inductor/current limit together and qualify load steps and faults; the normal single-channel load does not create this peak by itself. [Inductor manufacturer specification, p.16](https://atta.szlcsc.com/upload/public/pdf/source/20231019/B5E0F432965A5C2228E278E158E2A8B1.pdf), [TPS51386 current limiting and inductor selection](https://www.ti.com/lit/ds/symlink/tps51386.pdf).

## Analog behavior requiring qualification

**Loop stability is unproven.** U3 drives Q1's gate directly. The amplifier, pass-FET transconductance, output load, and DUT capacitance form a composite feedback loop. C21 across R17 changes feedback around 7.2-14.5 kHz; it is not evidence of adequate phase margin. TLV379's 90 kHz bandwidth and Q1's roughly 1 nF gate load justify careful characterization. Check setpoint steps and 15-ohm balancing turn-on/off at all relevant output capacitances. Do not label this circuit unstable without simulation or measurements. [TLV379 stability guidance](https://www.ti.com/lit/ds/symlink/tlv379.pdf), [FDC638P characteristics](https://www.onsemi.com/download/data-sheet/pdf/fdc638p-d.pdf).

**Q1 needs a linear thermal/SOA budget.** Using a 5.0 V raw rail and a 15-ohm load:

| Cell voltage | Load current | Load power | Q1 dissipation |
|---|---:|---:|---:|
| 2.0 V | 133 mA | 0.267 W | 0.400 W |
| 2.5 V | 167 mA | 0.417 W | 0.417 W |
| 3.3 V | 220 mA | 0.726 W | 0.374 W |
| 4.4 V | 293 mA | 1.291 W | 0.176 W |

The maximum is near half the raw supply voltage, not at maximum cell voltage. At a 5.5 V raw rail it becomes 0.504 W near 2.75 V. FDC638P's minimum-pad thermal resistance of 156 C/W gives approximately 65-79 C rise for those two peak cases; substantially more copper improves this. These estimates do not predict a certain room-temperature failure, but the displayed 4.5 A switching rating does not qualify linear operation. Validate copper area, ambient, enclosure, and DC SOA. No dedicated per-cell current limit defines Q1's fault envelope. [FDC638P ratings and thermal notes](https://www.onsemi.com/download/data-sheet/pdf/fdc638p-d.pdf).

**Accuracy needs a budget and calibration target.** R17/R19 are the 0.1%, 25 ppm/C RT0402BRD0710KL parts, not the common 1% 10 kohm resistors elsewhere. Their worst opposing tolerance gives about 4.4 mV cell error at 4.4 V. U3's maximum 2.5 mV offset contributes another 5 mV after the external gain, before DAC, drift, contact, and noise errors. Sixteen-bit resolution does not establish millivolt absolute accuracy. A two-point per-channel calibration is useful; tighter offset and ratio tracking may be needed for stringent threshold tests. There is no independent cell-voltage readback in this design. [Local resistor database](../../altium_library/tables/resistor.csv), [TLV379 electrical specifications](https://www.ti.com/lit/ds/symlink/tlv379.pdf).

**The output sources current but cannot actively sink it.** This is compatible with the required passive balancing load. With the DUT essentially unloaded, the intentional discharge path is 20 kohms, only 100-220 uA over the intended range. Downward steps therefore depend on DUT loading and capacitance: 1 uF gives a roughly 20 ms time constant, 10 uF about 200 ms. Active sinking is not required for the stated use, but scripted tests must allow measured settling time.

## Primary power and firmware checks

- **5 V cold boot needs measurement, not rejection by inspection.** The PD port feeds a buck set to 5.0 V from an initial nominal 5.0 V input. U8 supports large-duty operation, so its output can be below 5 V yet still run the 3.318 V logic buck. Verify power-port-only boot at minimum source voltage and cable drop, and recovery through PD negotiation/reset. The cell enables must remain low until a sufficient contract is valid. Data-port-only boot takes the D2 path instead. [TPS51386](https://www.ti.com/lit/ds/symlink/tps51386.pdf).
- **Regulator values:** R8A/R10A = 10k/10k produces 1.2 V. The active project variant changes R8B to 45.3k, giving 3.318 V with R10B = 10k. The repeated unexpanded sheet showing two 10k resistors is not proof of a 3P3 error. Keep this override explicit in manufacturing outputs; encoding a required rail voltage as an assembly variant is easy to lose.
- **One balancing channel fits the nominal converter rating.** At 4.4 V / 15 ohms, approximately 293 mA plus local electronics is below U6's 400 mA rating. With all sixteen loaded, secondary rail power is approximately 23.5 W for 5 V rails; at 85% efficiency this approaches 5.5 A from 5P0 before logic/other losses. Thus the nominal 6 A design has limited aggregate margin. Do not reject the required single-load use because 16 fully rated 2 W converters could overload it; conversely, do not promise sixteen balancing loads from the 60 W PD input alone.
- **Reconcile CubeMX with the hardware before generating firmware.** X1 is a 16 MHz part while the .ioc specifies 25 MHz HSE. The saved SPI2 calculation is 129 Mbit/s, above the DAC's 50 MHz limit. Recalculate clocks, select the correct SPI mode and 24-bit transaction format, configure PA3 PHY reset, and choose a conservative initial SPI speed for sixteen isolator loads. These are configuration findings, not claims about running firmware; no tester application source was present. [DAC80501 interface limits](https://www.ti.com/lit/ds/symlink/dac80501.pdf).
- **Initialize output states before directions.** Write expander output latches with all PWR_EN low and all nCS high before changing pins to outputs. Use channel power sequencing consistent with the reverse-cell finding. Do not clock SPI while chip selects are undefined. Review MCU-only reset: expanders and powered DACs can retain previous states.
- **DAC range:** with the external gain of two, configure a 0-2.5 V DAC range for a nominal 0-5 V cell range. REF-DIV=1 also avoids relying on an undivided 2.5 V reference when the DAC supply is slightly below 5 V. Clamp commands to the calibrated 2.0-4.4 V range.
- **USB-C termination and attachment:** account for the external 5.1k CC pull-downs when configuring internal UCPD pull-down/dead-battery behavior; two enabled terminations in parallel would be approximately 2.55k. Explicitly establish the H563 dead-battery handoff before repurposing PC9 for I2C3. Confirm both connector orientations and source types. [ST AN5225](https://www.st.com/resource/en/application_note/an5225-usb-typec-power-delivery-using-stm32-mcus-and-mpus-stmicroelectronics.pdf).
- **PD loss must remove the high-power load.** All cells share the same 5P0 rail that D2 can feed from the data host. If PD is unplugged while the data cable remains, enabled cell loads can transfer to the ordinary USB source. Disable them on contract loss and consider a hardware gate/current limit so that reset or slow firmware cannot defeat the power budget.

## Optional connection cases

| Case | Assessment |
|---|---|
| One tester with its 16 channels joined into a stack by the DUT/harness | Intended architecture is reasonable. Apply the fixes and qualification above, especially power transitions while the DUT draws stack current. |
| Two testers driving electrically separate BMS modules | Essentially two independent instances of the same acceptance case. Shared USB/computer ground is on the primary side; ensure DUT/debug wiring does not bridge isolated output references unexpectedly. |
| Bench supply across a simulated cell | Unsupported as a general operation in this revision. Q1's body diode can feed VOUT_P into the raw secondary rail, especially with PWR_EN off. Turning off the converter is not disconnecting the output. The stage also cannot absorb significant injected current. Add defined reverse-current blocking/output isolation and a sink strategy if this feature is wanted. The README's previous instruction to lower the setpoint and override externally should be removed or rewritten for this topology. |
| Two complete cell strings wired in series | No obvious schematic ground tie prevents it. At 4.4 V/cell, 16 cells produce 70.4 V and 32 produce 140.8 V. Qualification must cover continuous working voltage, PCB clearances, connectors, fixtures, and every external instrument path. A converter's 1.5 kV isolation test rating alone is not a continuous working-voltage signoff. This optional case was not layout-qualified. |

Do not parallel two actively regulated tester outputs without a specific current-sharing design.

## Checks that passed

The cell-sheet amplifier polarity and Q1 source/drain assignment are correct for a P-channel pass regulator. Q2/Q3 and R14/R23 give a default-off converter enable. The netlist preserves separate secondary references and does not accidentally tie them to primary ground. DAC interface selection, reference bypass, and isolator direction are consistent with write-only SPI; the unused reverse isolator input is grounded. There is no multiple-driver MISO bus.

The MCU's LQFP64 power/reset/boot pin assignments and two 2.2 uF VCAP capacitors match the H563 package. This package has no separate externally accessible VDDUSB pin. Expander address straps are consistent with 0x74/0x75 and the two separate I2C buses. Ethernet TX polarity reversal is explicitly intentional in the drawing; it was not treated as an accidental crossed pair. U8's 20 V operating input and the 50 V primary input capacitors are compatible with the proposed nominal PD voltage.

## Focused validation plan

1. Correct the definite connectivity and supply/startup issues. Regenerate the expanded schematic, BOM and netlist with the intended rail variant, and run ERC with useful pin electrical types.
2. With no DUT, test data-only, PD-port-only at 5 V, both cables, either removal order, PD transition, and PD reset. Scope VBUS, 5P0, 3P3, 1P2 and PHY reset. Check unpowered-connector backfeed and inrush.
3. On one cell, measure raw isolated supply and output during enable, reset, disable, idle, and load removal. Establish that the secondary IC rails and DUT output limits are met before attaching the AFE.
4. Sweep 2.0-4.4 V into 15 ohms; dwell near 2.5-2.75 V for thermal testing. Record output error, Q1 temperature and raw-rail voltage. Pulse the load and test representative DUT/cable capacitances for settling and ringing.
5. Attach the full DUT string and test one channel disabled, slow startup, cable unplug, and MCU reset while the DUT draws stack power. Measure each differential cell voltage, not only the total string.
6. Validate reliable I2C/SPI operation, USB attachment/removal, Ethernet cold starts/link negotiation, and two-point cell calibration. Only then increase simultaneous balancing loads and establish an enforced aggregate limit.

Remaining product decisions are the required cell-voltage accuracy and settling time, whether a disabled channel should represent an open circuit or a near-zero-volt cell, and whether external supply override is to become a supported feature.
