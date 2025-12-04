# Motivation
Cells have varying incoming quality and we want to reject weak or bad cells. The pass/fail criteria will be left to the battery pack builder, but this script seeks to capture the data in time-efficient, semi-automated manner.

# Requirements
You will need:
* Pulse-capable Keithley source meter connected to your computer. I use a [Keithley 2430](https://www.tek.com/en/products/keithley/source-measure-units/2400-graphical-series-sourcemeter).
* 4-terminal battery chuck. I use [these, 15 amp flavor](https://a2delectronics.ca/shop/battery-testing/4-wire-cell-holder/).
* Barcode scanner
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
## Leakage current
The meter is set to source the cell's open circuit voltage and with a small current limit. The actual current consumed by the cell will be its leakage current.
## DC impedance estimate
The cell voltage is measured with the cell idle (identical to the open circuit voltage test), and then again while sourcing a short high-current pulse. The dV/dI is the charging resistance. The tool then does this again, but discharging. This yields the discharging resistance. The average of the two is used as an estimate of the DC impedance of the cell at the current state of charge.
## dQ/dV capacity estimate
This test runs longer than the pulse test above, and captures the change in voltage produced  by the injection of a certain amount of charge. Another data point is captured by discharging the cell of the same amount of charge. The slope of voltage with charge is a proxy for capacity.

# Configurable parameters
Some constants defined at the top of the script can be tweaked to suit your particular cell parameters:
* _kChargeComplianceLimit_volts_ sets the upper voltage limit when sourcing current into the cell.
* _kDischargeCompianceLimit_volts_ sets the lower voltage limit when sinking current out of the cell.
* _kLeakageCompliantLimit_amps_ sets the maximum current used for measuring cell leakage.
* _kDcirPulseCurrent_amps_ sets the pulse current used when estimating the DC impedance of the cell at the current state of charge.
* _kDcirPulseDuration_seconds_ sets the length of the pulse when testing the DC impedance of the cell.
* _kDqDvCurrent_amps_ sets the steady state current used when charging or discharging the cell to estimate the capacity relative to other cells of the same design.
* _kDqDvDuration_seconds_ sets the time that the steady state current will be applied. Its product with _kDqDvCurrent_amps_ sets the amount of charge sourced into our sunk out of the cell.
* _kLeakageDwellTime_seconds_ sets the time that the instrument will wait for the current to settle to determine the leakage of the cell.

# Handy links
* (Keithley 2400-series user's manual, including SCPI programming)[https://download.tek.com/manual/2400S-900-01_K-Sep2011_User.pdf]
* (PyVisa, for connecting to the instrument)[https://pyvisa.readthedocs.io/en/latest/]