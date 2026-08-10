## Changes to consider for 1.x to 2.0
* Add e-paper interface for status indication.

## Changes from 1.0 --> 1.1
* Added P600_VERTICAL to the solid-connect rule.
* Added TO-247-2_VERTICAL to the solid-connect rule.
* Fixed swapped SWDIO and SWCLK on STM32F103.
* Connected TPS79933 GND pin to GND.
* Changed VBUS_DET divider upper resistor to 49.9k ohms.
* Removed 33 ohm series resistors on USB-C connector.
* Changed 24 MHz crystal BOM item and matching capacitors due to stocking.
* Added LED to HV_nBLEED signal.
* Added pull-up to SCL in case future chips do clock stretching.
* Switched to 15 volt Vicor for DC/DC.
* Used 3P3 for MP6519 EN pull-up because EN gates VCC regulator.
* Connected GNSS receiver wake line.
* Removed blocking diode and pull up resistor on GNSS nRST.
* Reduced slip fit to press fit on Wurth M4 terminals.
* Updated BOM to switch from MCP3913 to MCP3913B.
* Eliminated "shunt filter" on voltage sense channel.
* Harmonized -3dB corner for voltage and current sensing.
* Nudged MP6519 circuits to avoid contactor fill ports.
* Added switched and buffered LVB divider to STM32 ADC input on PC0, ADCx_IN10.
* Changed PPS LED to red due to low VIO rail on LC29HEU GNSS receiver.
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
* Changed VDDA/VREF to 2.5 volt precision regulator.
* Changed analog input dividers to 1:2 for 5 volt range on 2.5 volt reference.

* Move GNSS receiver UART/USART to avoid DMA conflict with BQ79616.
* Migrate to STM32H5F5LJH7Q to improve power consumption and performance.
* Use BQ25690 for LV battery charging to improve efficiency.
* Move LV_PWM to a regular timer.