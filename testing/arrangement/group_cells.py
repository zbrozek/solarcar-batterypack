import csv
import argparse
import sys
from dataclasses import dataclass, field
from typing import List

@dataclass
class Cell:
    serial_number: str
    dcir: float
    conductance: float
    original_index: int

@dataclass
class Module:
    id: int
    cells: List[Cell] = field(default_factory=list)
    total_conductance: float = 0.0

    @property
    def resistance(self) -> float:
        if self.total_conductance == 0:
            return 0.0
        return 1.0 / self.total_conductance

def read_cells(file_path: str) -> List[Cell]:
    cells = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader, None) # Skip header
            for i, row in enumerate(reader):
                if not row or len(row) < 6:
                    continue
                
                serial = row[0]
                try:
                    dcir = float(row[5])
                    if dcir <= 0:
                        print(f"Warning: skipping row {i+2}, non-positive DCIR: {dcir}")
                        continue
                    
                    cells.append(Cell(serial, dcir, 1.0 / dcir, i))
                except ValueError:
                    print(f"Warning: skipping row {i+2}, invalid DCIR: {row[5]}")
                    continue
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
        
    return cells

def write_output(file_path: str, modules: List[Module], sort_input: bool):
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Module ID", "Serial Number", "Cell DCIR (Ohm)", "Module Parallel DCIR (Ohm)"])
            
            # Collect all rows first
            rows = []
            for mod in modules:
                mod_res = mod.resistance
                for cell in mod.cells:
                    rows.append({
                        "row": [mod.id, cell.serial_number, f"{cell.dcir:.6f}", f"{mod_res:.6f}"],
                        "original_index": cell.original_index
                    })
            
            # Sort if requested
            if sort_input:
                rows.sort(key=lambda x: x["original_index"])
            
            # Write rows
            for item in rows:
                writer.writerow(item["row"])

    except Exception as e:
        print(f"Error writing output: {e}")
        sys.exit(1)

def print_stats(modules: List[Module]):
    resistances = [m.resistance for m in modules]
    min_res = min(resistances)
    max_res = max(resistances)
    avg_res = sum(resistances) / len(resistances)
    diff = max_res - min_res
    percent_diff = (diff / avg_res) * 100 if avg_res > 0 else 0

    print("\n--- Module Statistics ---")
    print(f"Min Resistance: {min_res:.6f} Ohm")
    print(f"Max Resistance: {max_res:.6f} Ohm")
    print(f"Avg Resistance: {avg_res:.6f} Ohm")
    print(f"Spread:         {diff:.6f} Ohm ({percent_diff:.4f}%)")

def main():
    parser = argparse.ArgumentParser(description="Group battery cells into modules with balanced parallel resistance.")
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--series", type=int, required=True, help="Number of cells in series (number of modules)")
    parser.add_argument("--parallel", type=int, required=True, help="Number of cells in parallel per module")
    parser.add_argument("--output", default="modules.csv", help="Path to output CSV file")
    parser.add_argument("--sort-input", action="store_true", help="Sort output by original input order instead of by module")
    
    args = parser.parse_args()

    # 1. Read CSV
    cells = read_cells(args.input)
    
    total_needed = args.series * args.parallel
    if len(cells) < total_needed:
        print(f"Error: Not enough cells! Have {len(cells)}, need {total_needed}")
        sys.exit(1)

    # 2. Filter and Sort Cells
    # Sort by DCIR and pick the middle chunk to avoid outliers.
    cells.sort(key=lambda c: c.dcir)
    
    excess = len(cells) - total_needed
    start_index = excess // 2
    selected_cells = cells[start_index : start_index + total_needed]
    
    print(f"Selected {len(selected_cells)} cells from {len(cells)} available (skipped {start_index} low and {excess - start_index} high outliers)")

    # 3. Grouping Algorithm (Greedy Best-Fit)
    # Sort selected cells by Conductance descending (highest current capability first)
    selected_cells.sort(key=lambda c: c.conductance, reverse=True)

    modules = [Module(id=i+1) for i in range(args.series)]

    # Distribute cells
    for cell in selected_cells:
        # Find the module with the lowest total conductance that isn't full
        # We filter for non-full modules, then find min by total_conductance
        eligible_modules = [m for m in modules if len(m.cells) < args.parallel]
        
        if not eligible_modules:
             print(f"Error: Algorithm error, no eligible modules for cell {cell.serial_number}")
             sys.exit(1)

        best_module = min(eligible_modules, key=lambda m: m.total_conductance)
        
        best_module.cells.append(cell)
        best_module.total_conductance += cell.conductance

    # 4. Write Output
    write_output(args.output, modules, args.sort_input)
    
    # Print stats
    print_stats(modules)

if __name__ == "__main__":
    main()
