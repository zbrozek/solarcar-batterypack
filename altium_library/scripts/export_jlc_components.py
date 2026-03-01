import sqlite3
import json
import csv
import re
import sys

def sanitize_string(val):
    if not isinstance(val, str):
        val = str(val) if val is not None else ""
    # Strip commas, apostrophes, backticks, graves, quotation marks
    return re.sub(r'[,`\'"’‘“”]', '', val)

def parse_resistance(val_str):
    if not val_str:
        return None
    match = re.match(r'^([\d\.]+)\s*([mkMGTμu]?)[ΩOohms]*$', val_str.strip(), re.IGNORECASE)
    if not match:
        return None
    val, mult = match.groups()
    val = float(val)
    multiplier = 1.0
    mult_lower = mult.lower()
    if mult_lower == 'm' and mult != 'M':
        multiplier = 1e-3
    elif mult_lower == 'k':
        multiplier = 1e3
    elif mult == 'M':
        multiplier = 1e6
    elif mult == 'G':
        multiplier = 1e9
    return val * multiplier

def format_resistance(val):
    if val >= 1e6:
        return f"{val/1e6:g}M"
    elif val >= 1e3:
        return f"{val/1e3:g}k"
    elif val >= 1:
        return f"{val:g}"
    else:
        return f"{val*1e3:g}m"

def parse_capacitance(val_str):
    if not val_str:
        return None
    match = re.match(r'^([\d\.]+)\s*([pnumkMμ]?)[Ff]*$', val_str.strip(), re.IGNORECASE)
    if not match:
        return None
    val, mult = match.groups()
    val = float(val)
    multiplier = 1.0
    mult = mult.lower()
    if mult == 'p':
        multiplier = 1e-12
    elif mult == 'n':
        multiplier = 1e-9
    elif mult in ('u', 'μ'):
        multiplier = 1e-6
    elif mult == 'm':
        multiplier = 1e-3
    return val * multiplier

def format_capacitance(val):
    if val < 1e-9:
        return f"{val*1e12:g}p"
    elif val < 1e-6:
        return f"{val*1e9:g}n"
    elif val < 1e-3:
        return f"{val*1e6:g}u"
    else:
        return f"{val*1e3:g}m"

def parse_power_mw(val_str):
    if not val_str:
        return None
    val_str = val_str.strip().lower()
    
    # Handle fractions like "1/10W"
    fraction_match = re.match(r'^(\d+)/(\d+)\s*w$', val_str)
    if fraction_match:
        num, den = fraction_match.groups()
        return (float(num) / float(den)) * 1000.0

    match = re.search(r'([\d\.]+)\s*(m?)(w)', val_str)
    if not match:
        return None
    val = float(match.group(1))
    is_milli = match.group(2) == 'm'
    return val if is_milli else val * 1000.0

def parse_tolerance(val_str):
    if not val_str:
        return None
    match = re.search(r'([\d\.]+)%', val_str)
    if not match:
        return None
    return float(match.group(1))

def parse_tcr(val_str):
    if not val_str:
        return None
    # Looking for max absolute value
    matches = re.findall(r'-?[\d\.]+', val_str.replace('~', ' '))
    if not matches:
        return None
    return max([abs(float(m)) for m in matches])
    
def parse_voltage(val_str):
    if not val_str:
        return None
    val_str = val_str.strip().lower()
    match = re.match(r'^([\d\.]+)\s*([k]?)[v]$', val_str)
    if not match:
        return None
    val, mult = match.groups()
    val = float(val)
    if mult == 'k':
        val *= 1000.0
    return val

def main():
    db_path = r'cache.sqlite3'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    STANDARD_RESISTOR_PACKAGES = {"0201", "0402", "0603", "0805", "1206", "1210", "1812", "2010", "2512", "4527"}
    STANDARD_CAPACITOR_PACKAGES = {"0201", "0402", "0603", "0805", "1206", "1210", "1812", "2220"}

    # --- Resistors ---
    print("Processing Resistors...")
    cursor.execute("""
        SELECT c.extra, m.name as manufacturer_name, c.package, c.lcsc as lcsc_number, c.stock, c.datasheet
        FROM components c
        JOIN categories cat ON c.category_id = cat.id
        LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
        WHERE cat.subcategory = 'Chip Resistor - Surface Mount'
          AND c.extra != '{}'
          AND c.stock > 10
    """)
    
    resistors_dict = {}
    for row in cursor:
        try:
            extra = json.loads(row['extra'])
            attrs = extra.get('attributes', {})
            
            res_val = parse_resistance(attrs.get('Resistance', ''))
            power_mw = parse_power_mw(attrs.get('Power(Watts)', ''))
            tol = parse_tolerance(attrs.get('Tolerance', ''))
            tcr_str = attrs.get('Temperature Coefficient', '')
            tcr = parse_tcr(tcr_str)
            
            if res_val is None or power_mw is None or tol is None or tcr is None:
                continue
                
            # Filters
            if tol > 1.0:
                continue
            if tcr > 100.0:
                continue
                
            package = extra.get('package', row['package'])
            if package not in STANDARD_RESISTOR_PACKAGES:
                continue
                
            datasheet = extra.get('datasheet', {}).get('pdf', row['datasheet'])
            if not datasheet:
                continue
                
            mpn = extra.get('mpn', '')
            lcsc_pn = extra.get('number', f"C{row['lcsc_number']}")
            stock = row['stock']
            
            item = {
                'mpn': mpn,
                'manufacturer': row['manufacturer_name'] or '',
                'footprint': f"R{package}",
                'package': package,
                'power_mw': power_mw,
                'datasheet': datasheet,
                'value_ohms': res_val,
                'value_formatted': format_resistance(res_val),
                'tolerance_percent': tol,
                'tcr_ppm': tcr,
                'tcr_str': tcr_str,
                'lcsc': lcsc_pn,
                'stock': stock
            }
            
            # Dedup: highest stock for identical (resistance, power, package, tolerance)
            key = (res_val, power_mw, package, tol)
            if key not in resistors_dict or stock > resistors_dict[key]['stock']:
                resistors_dict[key] = item
                
        except Exception as e:
            continue
            
    resistors = list(resistors_dict.values())
    # Sort: value -> package -> power -> tolerance
    resistors.sort(key=lambda x: (x['value_ohms'], x['package'], x['power_mw'], x['tolerance_percent']))
    
    with open('resistors.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            'Manufacturer Part Number', 'Manufacturer', 'SymbolName', 'SymbolLibrary', 
            'FootprintName', 'FootprintLibrary', 'Package', 'Power Rating (mW)', 'Value', 
            'Tolerance', 'Temperature Coefficient', 'Supplier 1', 'Supplier Part Number 1', 
            'Supplier 2', 'Supplier Part Number 2', 'ComponentLink1Description', 'ComponentLink1URL'
        ])
        for r in resistors:
            writer.writerow([
                sanitize_string(r['mpn']),
                sanitize_string(r['manufacturer']),
                '__template_resistor',
                'symbols/resistor.SchLib',
                sanitize_string(r['footprint']),
                'footprints/resistor.PcbLib',
                sanitize_string(r['package']),
                f"{round(r['power_mw'], 1):g}",
                sanitize_string(r['value_formatted']),
                f"{r['tolerance_percent']:g}%",
                sanitize_string(r['tcr_str']),
                '',
                '',
                'LCSC',
                sanitize_string(r['lcsc']),
                'Datasheet',
                sanitize_string(r['datasheet'])
            ])
            
    # --- Capacitors ---
    print("Processing Capacitors...")
    cursor.execute("""
        SELECT c.extra, m.name as manufacturer_name, c.package, c.lcsc as lcsc_number, c.stock, c.datasheet
        FROM components c
        JOIN categories cat ON c.category_id = cat.id
        LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
        WHERE cat.subcategory LIKE 'Multilayer Ceramic Capacitors MLCC - SMD/SMT%'
          AND c.extra != '{}'
          AND c.stock > 10
    """)
    
    capacitors_dict = {}
    for row in cursor:
        try:
            extra = json.loads(row['extra'])
            attrs = extra.get('attributes', {})
            
            cap_val = parse_capacitance(attrs.get('Capacitance', ''))
            voltage_str = attrs.get('Voltage Rated', '')
            voltage = parse_voltage(voltage_str)
            dielectric = attrs.get('Temperature Coefficient', '')
            
            if cap_val is None or voltage is None:
                continue
                
            if not dielectric or dielectric.strip().lower() in ('null', 'none', '-', 'unspecified', ''):
                continue
                
            package = extra.get('package', row['package'])
            if package not in STANDARD_CAPACITOR_PACKAGES:
                continue
                
            datasheet = extra.get('datasheet', {}).get('pdf', row['datasheet'])
            if not datasheet:
                continue
                
            mpn = extra.get('mpn', '')
            lcsc_pn = extra.get('number', f"C{row['lcsc_number']}")
            stock = row['stock']
            
            item = {
                'mpn': mpn,
                'manufacturer': row['manufacturer_name'] or '',
                'footprint': f"C{package}",
                'package': package,
                'voltage': voltage,
                'voltage_str': voltage_str,
                'dielectric': dielectric,
                'cap_farads': cap_val,
                'cap_formatted': format_capacitance(cap_val),
                'datasheet': datasheet,
                'lcsc': lcsc_pn,
                'stock': stock
            }
            
            # Dedup: highest stock for identical (value, package, dielectric, voltage)
            key = (cap_val, package, dielectric, voltage)
            if key not in capacitors_dict or stock > capacitors_dict[key]['stock']:
                capacitors_dict[key] = item
                
        except Exception as e:
            continue
            
    capacitors = list(capacitors_dict.values())
    # Sort: value -> voltage -> dielectric -> voltage_str
    capacitors.sort(key=lambda x: (x['cap_farads'], x['voltage'], x['dielectric'] or '', x['voltage']))
    
    with open('capacitors.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            'Manufacturer Part Number', 'Manufacturer', 'SymbolName', 'SymbolLibrary', 
            'FootprintName', 'FootprintLibrary', 'Package', 'Voltage Rating', 'Dielectric', 
            'Capacitance', 'Supplier 1', 'Supplier Part Number 1', 'Supplier 2', 'Supplier Part Number 2', 
            'ComponentLink1Description', 'ComponentLink1URL'
        ])
        for c in capacitors:
            writer.writerow([
                sanitize_string(c['mpn']),
                sanitize_string(c['manufacturer']),
                '__template_capacitor',
                'symbols/capacitor.SchLib',
                sanitize_string(c['footprint']),
                'footprints/capacitor.PcbLib',
                sanitize_string(c['package']),
                sanitize_string(c['voltage_str']),
                sanitize_string(c['dielectric']),
                sanitize_string(c['cap_formatted']),
                '',
                '',
                'LCSC',
                sanitize_string(c['lcsc']),
                'Datasheet',
                sanitize_string(c['datasheet'])
            ])

    print(f"Exported {len(resistors)} resistors to resistors.csv")
    print(f"Exported {len(capacitors)} capacitors to capacitors.csv")

if __name__ == "__main__":
    main()
