## Changes to consider for next revision
* Add e-paper interface for status indication.

## Changes completed from 1.0 --> 1.1
* Added P600_VERTICAL to the solid-connect rule.
* Added TO-247-2_VERTICAL to the solid-connect rule.
* Fixed swapped SWDIO and SWCLK on STM32F103.
* Connected TPS79933 GND pin to GND.
* Removed 33 ohm series resistors on USB-C connector.
* Changed 24 MHz crystal BOM item and matching capacitors due to stocking.
* Added LED to HV_nBLEED signal.
* Added pull-up to SCL in case future chips do clock stretching.
* Used 3P3 for MP6519 EN pull-up because EN gates VCC regulator.
* Connected GNSS receiver wake line.
* Removed blocking diode and pull up resistor on GNSS nRST.
* Reduced slip fit to press fit on Wurth M4 terminals.
* Updated BOM to switch from MCP3913 to MCP3914B.
* Eliminated "shunt filter" on voltage sense channel.
* Harmonized -3dB corner for voltage and current sensing.
* Nudged MP6519 circuits to avoid contactor fill ports.
* Added switched and buffered LVB divider to STM32 ADC input.
* Added PPS test point.
* Reversed DIP switch net numbering to match printed label on DIP switch.
* Adjusted RGB LED resistors to get better color intensity matching.
* Fixed LED4_1 and LED3_1 polarity on Ethernet switch.
* Added a reverse-polarity fuse-blowing schottky diode to LVB/GND.
* Added bus switch to onboard SWD and debug buses to avoid STM32F1 backfeed.
* Changed HV BLEED resistor to 1k to reduce NC SSR self-heating.
* Fixed mistake where pack shunt override went to the array channel.
* Switched to non-waterproof USB-C connector (external cover required).
* Transformer-coupled isoUART from BQ79600.
* Changed isoUART to 2-pin connector.
* Added second isoUART interface to implement fault-tolerant ring.
* Changed VREF to 2.5 volt precision regulator.
* Changed analog input dividers to 1:2 for 5 volt range on 2.5 volt reference.
* Migrated to STM32H5F5LJH7Q to improve power consumption and performance.
* Moved LV_PWM to a regular timer.
* Changed D12 (LV TVS) to 15 volt standoff.
* Changed D13 (HV TVS) to 132 volt standoff.
* Eliminated the HV-present indicator. In practice it turned out not-useful.
* Eliminated FPC fan header and breakout. Used PC-industry 4-pin fan header.
* Add SD card bypass cap and pull-ups.
* Switch from 25 MHz crystal to 16 MHz crystal on STM32H5.
* Use BQ25690 for LV battery charging.
* Switch Vicor Micro to Cincon 40 watt ECLB for improved efficiency.
* Adjusted optical SSR LED drive strengths upwards to cover more edge cases.
* Added TAS5720ATDAPRQ1 audio amplifier; powered from LV2.
* Fixed top sheet note about PWM fractions for precharge relay current targets.
* Added RTL8152B and connected it to port 5 on the Ethernet switch.
* Added diode-OR on GNSS receiver V_BCKP domain from coin cell and VCC.
* Reduced capacitance of GNSS receiver TVS.
* Increased base drive resistance on antenna bias switch.
* Separated center taps on Ethernet switch magnetic center taps.
* Reduce VN9E30F supply resistor to 150 ohms to match 3.3v recommendation.
* Fixed missing pull-up resistor for Ethernet switch interrupt pin.
* Increased package size for digital input current-limiting resistor.
* Added VN9E30F direct input GPIO connections.
* Updated triple-buck ENx divider to account for EN pin leakage.
* Added insulation monitoring circuit.
* Added unity gain buffers to MCP3914B voltage inputs to mitigate leakage.
* Updated LAN8670 to D0 stepping to resolve errata.
