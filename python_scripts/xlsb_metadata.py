import os
import re
import pandas as pd
from pyxlsb import open_workbook

# ============================================================
# CONFIG
# ============================================================

XLSB_FILE = r"Mixed Use v1.300.xlsb"  # path to your XLSB file
OUTPUT_DIR = "excel_metadata"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# SHEET INVENTORY
# ============================================================

sheet_inventory = []

with open_workbook(XLSB_FILE) as wb:
    for sheet_name in wb.sheets:
        sheet_inventory.append({
            "sheet_name": sheet_name
        })

pd.DataFrame(sheet_inventory).to_csv(
    os.path.join(OUTPUT_DIR, "sheet_inventory.csv"),
    index=False
)

print("Sheet inventory exported")

# ============================================================
# FORMULA INVENTORY
# ============================================================

formula_rows = []

with open_workbook(XLSB_FILE) as wb:

    for sheet_name in wb.sheets:

        try:
            sheet = wb.get_sheet(sheet_name)

            for row_idx, row in enumerate(sheet.rows(), start=1):

                for col_idx, cell in enumerate(row, start=1):

                    value = cell.v

                    if isinstance(value, str):

                        if value.startswith("="):

                            formula_rows.append({
                                "sheet": sheet_name,
                                "row": row_idx,
                                "column": col_idx,
                                "formula": value
                            })

        except Exception as e:
            print(f"Error reading {sheet_name}: {e}")

pd.DataFrame(formula_rows).to_csv(
    os.path.join(OUTPUT_DIR, "formula_inventory.csv"),
    index=False
)

print("Formula inventory exported")

# ============================================================
# SHEET DEPENDENCIES
# ============================================================

dependency_rows = []

sheet_names = set([s["sheet_name"] for s in sheet_inventory])

for row in formula_rows:

    formula = row["formula"]

    referenced_sheets = []

    for s in sheet_names:

        pattern = rf"'{re.escape(s)}'!"
        pattern2 = rf"{re.escape(s)}!"

        if re.search(pattern, formula, re.IGNORECASE):
            referenced_sheets.append(s)

        elif re.search(pattern2, formula, re.IGNORECASE):
            referenced_sheets.append(s)

    for ref in referenced_sheets:

        dependency_rows.append({
            "source_sheet": row["sheet"],
            "depends_on_sheet": ref
        })

pd.DataFrame(dependency_rows).drop_duplicates().to_csv(
    os.path.join(OUTPUT_DIR, "sheet_dependencies.csv"),
    index=False
)

print("Dependencies exported")

print("\nDone.")
print(f"Output folder: {OUTPUT_DIR}")