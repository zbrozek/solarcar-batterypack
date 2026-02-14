## bms_mainboard

Overall, this is a complicated and excessive kitchen sink of functionality. Its primary function is managing the battery pack state machine and driving the contactors accordingly. Beyond that, however, it is effectively a full central vehicle computer. There are some choices that seasoned solar car teams might find unusual.

The contactors are provided onboard. Most solar cars use dramatically bigger wires and contactors than they actually need. By right-sizing these devices, they can fit onto a PCBA. Current sensing is done via onboard shunt resistors in order to avoid more interconnects. This simplifies the wiring of the battery pack tremendously, reducing opportunities for errors and failures. There is also an automatic high voltage bus discharge when the system is powered down. All three contactors are driven with current regulators, enabling fine-grained control of coil currents in order to reduce system power consumption.

An onboard Ethernet switch provides Ethernet connectivity from the onboard STM32 microcontroller both to other on-vehicle devices as well as to an uncommitted RJ-45 receptacle intended for easy debugging. Some - maybe most - teams won't utilize this feature, preferring to stick to the more-familiar CAN (also provided). Beyond being simply much faster, Ethernet also offers point-to-point links which make the network (mostly) topology insensitive. There is no worrying about whether or not the bus remains terminated as the system topology changes.

The exception to the above is the speculative inclusion of a 10BASE-T1S PHY on the topshell-facing (blue Ampseal 35-position) connector. This is the IEEE 802.3 committee's answer to CAN. It is a 10 mbps multi-drop physical layer for Ethernet that carries traditional Ethernet frames. I will very-likely design MPPTs that use this bus. 

There are also some affordances for improved data gathering about the vehicle. An onboard IMU (3-axis acceleromter plus 3-axis gyroscope) can be used to capture information about vehicle dynamics or to try and estimate incline. An onboard GNSS receiver can be used to provide system time and capture vehicle location or to calibrate wheel odometry. An onboard MicroSD slot allows teams to log telemetry data locally in order to be independent of wireless telemetry systems.

An isolated DC/DC converter produces the low voltage power for the vehicle. It is permanently connected to a low voltage (nominally "12 volt") battery. That battery floats the low voltage bus, absorbing transient loads, but providing net-zero energy to the system. Hypercompetitive teams will probably be annoyed that the system does not afford a battery for allowed off-the-books loads. This is an opinionated choice on my part; I think reliability is more important and this reduces the amount of system state that needs to be tracked and babysat.

There is a current-loop called "EDISC" that must be completed in order for the BMS to receive power. This is intended to be sent to any number of series-connected on/off switches to turn the car on and off. A potentially-controversial feature is the ability for the main microcontroller tor read that loop and force-keepalive the system. This is intended to enable software-driven soft-shutdown procedures.

Finally, there are some protected high-side switches that can be used to drive lights or horns or other loads, as well as some analog and digital inputs for things like throttle sensors and switches.

## bms_afe

The mainboard does *not* sense battery voltages. The "analog front end" board does. It is mounted directly to the battery module to minimize pack wiring and opportunities for failure. This is admittedly annoying to assemble, but since that is a one-time procedure I consider it to be tolerable.

It is built around a TI BQ79616 cell monitoring chip and follows the provided application schematic closely. The board uses the eight remaining GPIO pins (which can be multiplexed to the on-chip ADC) to read NTC thermistors.

These boards can be connected to the mainboard or daisy-chained via twisted pair cables.

## bms_afe_tester

This is a development and test tool. It mates to the AFE board and has sixteen adjustable-output isolated flyback converters to drive the cell tap inputs. It's powered from USB-C PD at 12 volts and can communicate via a second USB-C port or via Ethernet. Hopefully teams use this for scripted automatic testing of their BMS software.

Another use for this is during scrutineering. I hope that teams will bring spare AFE boards and an AFE tester board so that they can easily demonstrate BMS behavior to scrutineers. Clip points are provided in case a team wants to override a flyback's output with an external supply. If doing that, set that channel's output to its lowest-possible voltage and then externally drive to a higher voltage.

## bms_fan_breakout

This is a simple board to break out from an 8-pin FPC cable to two PC-compatible 4-pin fan headers.