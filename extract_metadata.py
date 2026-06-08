"""
PVA Workbench Extractor
-----------------------
Reads a .xlsb file and extracts field-level data for each target tab into CSVs.
Run: python extract_workbench.py --file /path/to/workbench.xlsb --out ./output_csvs
"""

import os
import csv
import argparse
from pyxlsb import open_workbook

TARGET_TABS = [
    "File Info", "Settings", "Dates, Premises", "Contracts, History",
    "Scope", "Site", "Zoning", "Improvements", "Assessment",
    "Land Grid", "Land Valuation", "Land Comp Profiles",
    "Cost Approach Setup", "Sales Grid", "Sale Approach", "Sale Comp Profiles",
    "Income Approach", "Rent Roll Input", "Rent Roll Config", "Lease Grid",
    "Market Rent", "MF Market Rent", "Rent Comp Profiles",
    "Capitalization and Multipliers", "Investor Survey Input",
    "Investor Survey Output", "MF Lease Up", "DirectCapConclusion"
]

MAX_ROWS = 300   # scan first N rows per sheet to find fields
MAX_COLS = 60    # scan first N columns per sheet


def col_letter(n):
    """Convert 0-based column index to Excel letter (A, B, ... Z, AA, ...)."""
    result = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def extract_sheet(wb, sheet_name, out_dir):
    rows_data = []

    try:
        with wb.get_sheet(sheet_name) as sheet:
            for i, row in enumerate(sheet.rows()):
                if i >= MAX_ROWS:
                    break
                for cell in row:
                    if cell.c >= MAX_COLS:
                        continue
                    val = cell.v
                    if val is None or val == "":
                        continue

                    col_ltr = col_letter(cell.c)
                    row_num = cell.r + 1
                    cell_ref = f"{col_ltr}{row_num}"

                    # pyxlsb gives raw values; formulas come as strings starting with '='
                    is_formula = isinstance(val, str) and val.startswith("=")
                    field_type = "calculated" if is_formula else "user_entry"

                    rows_data.append({
                        "tab": sheet_name,
                        "cell": cell_ref,
                        "row": row_num,
                        "col": col_ltr,
                        "value": str(val).strip(),
                        "field_type": field_type,
                        "formula": val if is_formula else "",
                    })
    except Exception as e:
        print(f"  WARNING: Could not read sheet '{sheet_name}': {e}")
        return

    if not rows_data:
        print(f"  INFO: Sheet '{sheet_name}' appears empty or could not be read.")
        return

    safe_name = sheet_name.replace("/", "-").replace("\\", "-").replace(":", "-").replace(" ", "_")
    out_path = os.path.join(out_dir, f"{safe_name}.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["tab", "cell", "row", "col", "value", "field_type", "formula"])
        writer.writeheader()
        writer.writerows(rows_data)
    print(f"  OK: {len(rows_data)} cells written -> {out_path}")


def extract_all_sheet_names(wb):
    """List all sheet names in the workbook."""
    return wb.sheets


def main():
    parser = argparse.ArgumentParser(description="Extract PVA workbench tabs to CSV")
    parser.add_argument("--file", required=True, help="Path to the .xlsb file")
    parser.add_argument("--out", default="./workbench_output", help="Output directory for CSVs")
    parser.add_argument("--list-tabs", action="store_true", help="Just list all tab names and exit")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        return

    os.makedirs(args.out, exist_ok=True)

    print(f"\nOpening: {args.file}")
    with open_workbook(args.file) as wb:
        all_tabs = extract_all_sheet_names(wb)

        # Always write a full tab index
        index_path = os.path.join(args.out, "_all_tabs.txt")
        with open(index_path, "w", encoding="utf-8") as f:
            for t in all_tabs:
                f.write(t + "\n")
        print(f"All tabs ({len(all_tabs)}) written to: {index_path}\n")

        if args.list_tabs:
            for t in all_tabs:
                print(f"  - {t}")
            return

        # Fuzzy match target tabs (case-insensitive)
        all_lower = {t.lower(): t for t in all_tabs}
        for target in TARGET_TABS:
            actual = all_lower.get(target.lower())
            if not actual:
                # Try partial match
                matches = [v for k, v in all_lower.items() if target.lower() in k]
                actual = matches[0] if matches else None

            if actual:
                print(f"Extracting: '{actual}'")
                extract_sheet(wb, actual, args.out)
            else:
                print(f"  MISSING: Tab '{target}' not found in workbook.")

    print(f"\nDone. CSVs saved to: {os.path.abspath(args.out)}")
    print("Zip the output folder and share it back.")


if __name__ == "__main__":
    main()