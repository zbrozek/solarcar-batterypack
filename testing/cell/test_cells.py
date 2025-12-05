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
kLeakageCompliantLimit_amps = 1e-3
kR0PulseCurrent_amps = 10.0
kR0PulseDuration_seconds = 0.0025
kDcirCurrent_amps = 3.0
kDcirDuration_seconds = 10.0
kLeakageDwellTime_seconds = 1.0
kVoltageSenseDwell_seconds = 0.1

class Keithley2430:
    def __init__(self, resource_name, mock=False, terminals='front'):
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
            
            # Select terminals
            if terminals.lower() == 'rear':
                self.inst.write(":ROUT:TERM REAR")
            else:
                self.inst.write(":ROUT:TERM FRONT")
        else:
            print(f"Mocking connection to {resource_name}")

    def test_connection(self):
        """Tests the connection to the instrument by querying its ID."""
        if self.mock:
            print("Mock connection successful.")
            return True
        
        try:
            idn = self.inst.query("*IDN?")
            print(f"Connection successful. Instrument ID: {idn.strip()}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

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
        
        # Configure pulse mode
        self.inst.write(":SOUR:FUNC:SHAP PULS")
        self.inst.write(":SOUR:FUNC:MODE CURR")
        self.inst.write(f":SOUR:CURR:LEV {current}")
        self.inst.write(f":SENS:VOLT:PROT {voltage_limit}")
        self.inst.write("SENS:FUNC \"VOLT\"")
        self.inst.write(f":SOUR:PULS:WIDT {width}")
        self.inst.write(f":SOUR:PULS:DEL {delay}")

        # Configure for one pulse
        self.inst.write(":TRIG:CLE")
        self.inst.write(":ARM:COUN 1")
        self.inst.write(":TRIG:COUN 1")
        
        # :READ? initiates the pulse sequence and returns the measurement.
        # Pulse mode automatically turns the output on and off.
        result = float(self.inst.query(":READ?"))
        
        return result

def run_tests(inst, serial_number):
    print(f"Testing cell {serial_number}...")
    
    # 1. Open Circuit Voltage
    print("  Measuring OCV...")
    inst.source_current(0.0, kChargeComplianceLimit_volts)
    inst.output_on()
    time.sleep(kVoltageSenseDwell_seconds)
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

    # 3. R0 Estimate
    print("  Measuring R0...")
    # Measure idle voltage for charge
    v_idle_charge = inst.measure_voltage()
    
    # Charge Pulse
    print(f"  Pulsing {kR0PulseCurrent_amps}A for {kR0PulseDuration_seconds}s...")
    v_load_charge = inst.source_pulse_current(kR0PulseCurrent_amps, kChargeComplianceLimit_volts, kR0PulseDuration_seconds)
    
    # Measure idle voltage for discharge
    v_idle_discharge = inst.measure_voltage()

    # Discharge Pulse
    print(f"  Pulsing {-kR0PulseCurrent_amps}A for {kR0PulseDuration_seconds}s...")
    v_load_discharge = inst.source_pulse_current(-kR0PulseCurrent_amps, kChargeComplianceLimit_volts, kR0PulseDuration_seconds)

    r_charge = (v_load_charge - v_idle_charge) / kR0PulseCurrent_amps
    r_discharge = (v_idle_discharge - v_load_discharge) / kR0PulseCurrent_amps # Delta V / Delta I. Delta I is positive magnitude here.
    r0 = (r_charge + r_discharge) / 2.0
    print(f"  R0: {r0:.4f} Ohm")

    # 4. DCIR Test
    print("  Measuring DCIR...")
    # Measure idle voltage for charge
    v_idle_charge_dcir = inst.measure_voltage()
    
    # Charge
    print(f"  Sourcing {kDcirCurrent_amps}A for {kDcirDuration_seconds} seconds...")
    inst.source_current(kDcirCurrent_amps, kChargeComplianceLimit_volts)
    inst.output_on()
    time.sleep(kDcirDuration_seconds)
    v_load_charge_dcir = inst.measure_voltage()
    inst.output_off()

    # Measure idle voltage for discharge
    v_idle_discharge_dcir = inst.measure_voltage()

    # Discharge
    print(f"  Sourcing {-kDcirCurrent_amps}A for {kDcirDuration_seconds} seconds...")
    inst.source_current(-kDcirCurrent_amps, kChargeComplianceLimit_volts)
    inst.output_on()
    time.sleep(kDcirDuration_seconds)
    v_load_discharge_dcir = inst.measure_voltage()
    inst.output_off()

    r_charge_dcir = (v_load_charge_dcir - v_idle_charge_dcir) / kDcirCurrent_amps
    r_discharge_dcir = (v_idle_discharge_dcir - v_load_discharge_dcir) / kDcirCurrent_amps
    dcir = (r_charge_dcir + r_discharge_dcir) / 2.0
    print(f"  DCIR: {dcir:.4f} Ohm")

    results = {
        "Serial Number": serial_number,
        "OCV (V)": ocv,
        "Leakage (A)": leakage,
        "R0 (Ohm)": r0,
        "DCIR (Ohm)": dcir
    }
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Battery Cell Testing Script")
    parser.add_argument("output_csv", help="Path to the output CSV file")
    parser.add_argument("--resource", default="GPIB0::24::INSTR", help="VISA resource string for Keithley 2430")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without hardware")
    parser.add_argument("--terminals", choices=['front', 'rear'], default='front', help="Select front or rear terminals (default: front)")
    parser.add_argument("--test-connection", action="store_true", help="Test connection to the instrument and exit")
    args = parser.parse_args()

    # Initialize CSV
    fieldnames = ["Serial Number", "OCV (V)", "Leakage (A)", "R0 (Ohm)", "DCIR (Ohm)"]
    
    # Check if file exists to decide whether to write header
    try:
        with open(args.output_csv, 'x', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    except FileExistsError:
        pass # Append to existing file

    try:
        inst = Keithley2430(args.resource, mock=args.mock, terminals=args.terminals)
        
        if args.test_connection:
            success = inst.test_connection()
            sys.exit(0 if success else 1)

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
