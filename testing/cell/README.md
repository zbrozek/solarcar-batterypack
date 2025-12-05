# Motivation
Cells have varying incoming quality and we want to reject weak or bad cells. The pass/fail criteria will be left to the battery pack builder, but this script seeks to capture the data in time-efficient, semi-automated manner.

# Requirements
You will need:
* Pulse-capable Keithley source meter connected to your computer. I use a [Keithley 2430](https://www.tek.com/en/products/keithley/source-measure-units/2400-graphical-series-sourcemeter).
* 4-terminal battery chuck. I use [these, 15 amp flavor](https://a2delectronics.ca/shop/battery-testing/4-wire-cell-holder/).
* Barcode scanner. I have [this thing](https://www.amazon.com/dp/B01M264K5L).
* Serialized batteries
* Python 

# Workflow
All of the cells should be in thermal steady state in a temperature-controlled room prior to starting the test.
1. Launch the script.
2. Place a cell into the chuck.
3. Scan the barcode on the cell when prompted.
4. Wait for the tests to complete.
5. Place a new cell into the chuck and repeat until finished.

# Tests performed
The instrument is in four wire sensing mode. If the wires are shielded, the shield should be driven by the guard output of the instrument.
## Open circuit voltage
This is a very simple test. The source meter is placed in current-source mode with a zero current target, and the voltage at the terminals is measured over a short interval.
## R0 estimate
The cell voltage is measured with the cell idle (identical to the open circuit voltage test), and then again while sourcing a short high-current pulse. The dV/dI is the charging resistance. The tool then does this again, but discharging. This yields the discharging resistance. The average of the two is used as an estimate of the R0 impedance of the cell at the current state of charge. This should mostly be a measurement of the simple mechanical resistances and have little to do with the chemistry.
## DC impedance estimate
This test is similar to the R0 estimate, but uses a much longer pulse in order to try and get an estimate of the DC impedance. 

# Configurable parameters
Some constants defined at the top of the script can be tweaked to suit your particular cell parameters:
* _kChargeComplianceLimit_volts_ sets the upper voltage limit when sourcing current into the cell.
* _kDischargeCompianceLimit_volts_ sets the lower voltage limit when sinking current out of the cell.
* _kR0PulseCurrent_amps_ sets the pulse current used when estimating the R0 impedance of the cell.
* _kR0PulseDuration_seconds_ sets the length of the pulse when testing the R0 impedance of the cell.
* _kDcirPulseCurrent_amps_ sets the pulse current used when estimating the DC impedance of the cell.
* _kDcirPulseDuration_seconds_ sets the length of the pulse when testing the DC impedance of the cell.
* _kLeakageDwellTime_seconds_ sets the time that the instrument will wait for the current to settle to determine the leakage of the cell.

# Handy links
* [Keithley 2400-series user's manual, including SCPI programming](https://download.tek.com/manual/2400S-900-01_K-Sep2011_User.pdf)
* [PyVisa, for connecting to the instrument](https://pyvisa.readthedocs.io/en/latest/)