import argparse
import csv
import time
import sys
required_packages = {
    'pyvisa': 'pyvisa',
    'serial': 'pyserial'
}
missing_packages = []
for import_name, install_name in required_packages.items():
    try:
        __import__(import_name)
    except ImportError:
        missing_packages.append(install_name)

if missing_packages:
    print("\n\033[91mError: Missing required dependencies.\033[0m")
    print(f"The following packages are missing: {', '.join(missing_packages)}")
    sys.exit(1)


# Configurable parameters
kChargeComplianceLimit_volts = 4.2
kDischargeCompianceLimit_volts = 2.5
kLeakageCompliantLimit_amps = 1e-3  # 1 mA
kDcirPulseCurrent_amps = 10.0
kDcirPulseDuration_seconds = 0.0025
kDqDvCurrent_amps = 1.0
kDqDvDuration_seconds = 1.0
kLeakageDwellTime_seconds = 1.0

class Keithley2430:
    def __init__(self, resource_name, mock=False):
        self.mock = mock
        if not self.mock:
            rm = pyvisa.ResourceManager()
            self.inst = rm.open_resource(
                resource_name,
                baud_rate=57600,
                data_bits=8,
                parity=pyvisa.constants.Parity.none,
                stop_bits=pyvisa.constants.StopBits.one,
                flow_control=pyvisa.constants.VI_ASRL_FLOW_NONE,
                write_termination="\n",
                read_termination="\n",
                )
            self.inst.write("*RST")
            self.inst.write(":SYST:RSEN ON") # 4-wire mode
        else:
            print(f"Mocking connection to {resource_name}")

    def close(self):
        if not self.mock:
            self.inst.write(":OUTP OFF")
            self.inst.close()

    def output_on(self):
        if not self.mock:
            self.inst.write(":OUTP ON")

    def output_off(self):
        if not self.mock:
            self.inst.write(":OUTP OFF")

    def measure_voltage(self):
        if self.mock: return 3.7
        # :READ? triggers a measurement based on current configuration
        return float(self.inst.query(":MEAS:VOLT?"))

    def measure_current(self):
        if self.mock: return 0.0
        return float(self.inst.query(":MEAS:CURR?"))

    def source_current(self, current, voltage_limit):
        """Sets the source to current mode with a voltage compliance limit."""
        if not self.mock:
            self.inst.write(":SOUR:FUNC CURR")
            self.inst.write(f":SOUR:CURR {current}")
            self.inst.write(f":SENS:VOLT:PROT {voltage_limit}")

    def source_voltage(self, voltage, current_limit):
        """Sets the source to voltage mode with a current compliance limit."""
        if not self.mock:
            self.inst.write(":SOUR:FUNC VOLT")
            self.inst.write(f":SOUR:VOLT {voltage}")
            self.inst.write(f":SENS:CURR:PROT {current_limit}")

    def source_pulse_current(self, current, voltage_limit, width, delay=0):
        """Executes a current pulse and returns the measured voltage."""
        if self.mock:
            return 3.8 if current > 0 else 3.6 # Mock voltage rise/drop
        
        # Configure Pulse Mode
        self.inst.write(":SOUR:FUNC PULS:CURR")
        self.inst.write(f":SOUR:PULS:CURR:LEV {current}")
        self.inst.write(f":SENS:VOLT:PROT {voltage_limit}")
        self.inst.write(f":SOUR:PULS:WIDT {width}")
        self.inst.write(f":SOUR:PULS:DEL {delay}")
        
        # Enable output and trigger measurement
        self.inst.write(":OUTP ON")
        # :READ? initiates the pulse sequence and returns the measurement
        result = float(self.inst.query(":READ?"))
        self.inst.write(":OUTP OFF")
        
        return result

def run_tests(inst, serial_number):
    print(f"Testing cell {serial_number}...")
    
    # 1. Open Circuit Voltage
    print("  Measuring OCV...")
    inst.source_current(0.0, kChargeComplianceLimit_volts)
    inst.output_on()
    time.sleep(0.5) # Settle
    ocv = inst.measure_voltage()
    inst.output_off()
    print(f"  OCV: {ocv:.4f} V")

    # 2. Leakage Current
    print("  Measuring Leakage...")
    inst.source_voltage(ocv, kLeakageCompliantLimit_amps)
    inst.output_on()
    time.sleep(kLeakageDwellTime_seconds)
    leakage = inst.measure_current()
    inst.output_off()
    print(f"  Leakage: {leakage:.4e} A")

    # 3. DC Impedance Estimate
    print("  Measuring DC Impedance...")
    # Measure idle voltage for charge
    inst.source_current(0.0, kChargeComplianceLimit_volts)
    inst.output_on()
    time.sleep(0.5)
    v_idle_charge = inst.measure_voltage()
    inst.output_off()
    
    # Charge Pulse
    print(f"  Pulsing {kDcirPulseCurrent_amps}A for {kDcirPulseDuration_seconds}s...")
    v_load_charge = inst.source_pulse_current(kDcirPulseCurrent_amps, kChargeComplianceLimit_volts, kDcirPulseDuration_seconds)
    
    # Measure idle voltage for discharge
    inst.source_current(0.0, kChargeComplianceLimit_volts)
    inst.output_on()
    time.sleep(0.5)
    v_idle_discharge = inst.measure_voltage()
    inst.output_off()

    # Discharge Pulse
    print(f"  Pulsing {-kDcirPulseCurrent_amps}A for {kDcirPulseDuration_seconds}s...")
    v_load_discharge = inst.source_pulse_current(-kDcirPulseCurrent_amps, kChargeComplianceLimit_volts, kDcirPulseDuration_seconds)

    r_charge = (v_load_charge - v_idle_charge) / kDcirPulseCurrent_amps
    r_discharge = (v_idle_discharge - v_load_discharge) / kDcirPulseCurrent_amps # Delta V / Delta I. Delta I is positive magnitude here.
    dc_impedance = (r_charge + r_discharge) / 2.0
    print(f"  DC Impedance: {dc_impedance:.4f} Ohm")

    # 4. dQ/dV Capacity Estimate
    print("  Measuring dQ/dV...")
    # Charge
    inst.source_current(kDqDvCurrent_amps, kChargeComplianceLimit_volts)
    inst.output_on()
    v_start_charge = inst.measure_voltage()
    time.sleep(kDqDvDuration_seconds)
    v_end_charge = inst.measure_voltage()
    
    dq_charge = kDqDvCurrent_amps * kDqDvDuration_seconds
    dv_charge = v_end_charge - v_start_charge
    dqdv_charge = dv_charge / dq_charge if dq_charge != 0 else 0

    # Discharge
    inst.source_current(-kDqDvCurrent_amps, kChargeComplianceLimit_volts)
    v_start_discharge = inst.measure_voltage()
    time.sleep(kDqDvDuration_seconds)
    v_end_discharge = inst.measure_voltage()
    inst.output_off()

    dq_discharge = kDqDvCurrent_amps * kDqDvDuration_seconds # Magnitude
    dv_discharge = v_start_discharge - v_end_discharge # Magnitude of drop
    dqdv_discharge = dv_discharge / dq_discharge if dq_discharge != 0 else 0
    
    print(f"  dQ/dV Charge: {dqdv_charge:.4f} V/C")
    print(f"  dQ/dV Discharge: {dqdv_discharge:.4f} V/C")

    results = {
        "Serial Number": serial_number,
        "OCV (V)": ocv,
        "Leakage (A)": leakage,
        "DC Impedance (Ohm)": dc_impedance,
        "Charging dV/dQ (V/C)": dqdv_charge,
        "Discharging dV/dQ (V/C)": dqdv_discharge
    }
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Battery Cell Testing Script")
    parser.add_argument("output_csv", help="Path to the output CSV file")
    parser.add_argument("--resource", default="GPIB0::24::INSTR", help="VISA resource string for Keithley 2430")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without hardware")
    args = parser.parse_args()

    # Initialize CSV
    fieldnames = ["Serial Number", "OCV (V)", "Leakage (A)", "DC Impedance (Ohm)", "Charging dV/dQ (V/C)", "Discharging dV/dQ (V/C)"]
    
    # Check if file exists to decide whether to write header
    try:
        with open(args.output_csv, 'x', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    except FileExistsError:
        pass # Append to existing file

    try:
        inst = Keithley2430(args.resource, mock=args.mock)
        
        while True:
            try:
                serial_number = input("Scan barcode (or 'q' to quit): ").strip()
                if serial_number.lower() == 'q':
                    break
                if not serial_number:
                    continue

                results = run_tests(inst, serial_number)
                
                with open(args.output_csv, 'a', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerow(results)
                
                print(f"Test complete for {serial_number}. Results saved.")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error testing cell: {e}")

    except Exception as e:
        print(f"Failed to initialize instrument: {e}")
    finally:
        if 'inst' in locals():
            inst.close()

if __name__ == "__main__":
    main()
