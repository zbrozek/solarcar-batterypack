## Changes to consider for 1.x to 2.0
* Add e-paper interface for status indication.
* Migrate to STM32H563LI or STM32H573LI for lower power consumption.
* Use hotswap controller instead of diode on DC/DC output.

## Changes to consider for 1.0 --> 1.1
* Put four-wire fan headers directly on the motherboard.
* Reduce slip fit to press fit on Wurth M4 terminals.
* Add 1M resistor across USB2534 oscillator pads.
* Plumb GNSS receiver wake line.

## Changes from 1.0 --> 1.1
* Added P600_VERTICAL to the solid-connect rule.
* Added TO-247-2_VERTICAL to the solid-connect rule.
* Fixed swapped SWDIO and SWCLK on STM32F103.
* Connected TPS79933 GND pin to GND.
* Change VBUS_DET divider upper resistor to 49.9k ohms.
* Removed 33 ohm series resistors on USB-C connector.
* Changed 24 MHz crystal BOM item and matching capacitors due to stocking.
* Added LED to HV_nBLEED signal.
* Added pull-up to SCL in case future chips do clock stretching.
* Moved isoUART to COMH on BQ79600.
* Switched to 15 volt Vicor for DC/DC.
* Used 3P3 for MP6519 EN pull-up because EN gates VCC regulator.
