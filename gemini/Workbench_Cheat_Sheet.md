# Workbook Workbench Cheat Sheet

## Purpose
This workbook is a generated mapping layer for reverse-engineering the Excel file. It turns workbook structure, formulas, dropdowns, named ranges, and dependencies into CSV tabs that are easier to review, clean, and present.

## Overall Flow
1. `script_4_gpt.py` scans the source workbook and exports analysis CSVs.
2. `csv_cleaning.py` filters and deduplicates those CSVs for cleaner review.
3. `dumpdata_in_gspread.py` uploads the cleaned CSVs into Google Sheets with color-coded tabs.

## Main Output Tabs and What They Mean

### `00_Index`
- Landing page for the Google Sheet.
- Gives a quick list of all tabs and opens links to each one.

### `Tab Inventory.csv`
- One row per workbook sheet.
- Shows the sheet name, sheet state, sheet role, and tab color.
- Good for seeing the workbook at a high level.

### `Field Inventory.csv`
- One row per visible/input/formula/dropdown field found in a sheet.
- Shows the field label, data type, required status, formula flag, dropdown flag, and cell reference.
- Best tab for understanding what the workbook captures in each sheet.

### `Field Mapping.csv`
- Shows source fields and where they are used.
- Useful for tracing where data flows from one sheet to another.
- This is the main source-to-target mapping tab.

### `Dropdown Values.csv`
- Lists dropdown cells and their resolved options when possible.
- Includes the named range source, formula source, referenced cells, and resolution status.
- Best for understanding validation lists and user input constraints.

### `Calculated Fields.csv`
- Lists formula cells and their dependency breakdown.
- `Depends On (Source Fields)` shows the field-level inputs behind the formula.
- `Named Range Dependencies` shows any named ranges used in the formula.

### `Named Ranges.csv`
- Catalog of all named ranges found in the workbook.
- Shows the sheet, start and end cells, cell count, preview values, and where the named range is used.
- Good for finding reusable workbook logic and lookup sources.

### `Tab Relationships.csv`
- Sheet-to-sheet relationship summary.
- Shows which tabs feed or reference other tabs and the relationship type.
- Helpful for migration planning and dependency review.

### `WorkbookGraph.csv`
- Full dependency edge list for the workbook.
- Shows `Source Tab`, `Target Tab`, `Dependency Type`, and `Dependency Source`.
- Best tab for graph analysis and tooling like NetworkX.

### `ShowHide Usage.csv`
- Captures formulas related to show/hide logic.
- Useful for conditional visibility and form behavior analysis.

### `Notes Findings.csv`
- Place for manual observations, open questions, and review notes.
- Good for presenting issues or follow-up items.

## How the Tabs Map Together
- `Tab Inventory.csv` tells you what each sheet is.
- `Field Inventory.csv` tells you what fields exist on each sheet.
- `Dropdown Values.csv` tells you which fields are dropdowns and what choices they allow.
- `Calculated Fields.csv` tells you what formulas depend on what source fields or named ranges.
- `Field Mapping.csv` tells you which source tab/field feeds another tab.
- `Named Ranges.csv` tells you where reusable workbook ranges live and where they are used.
- `Tab Relationships.csv` and `WorkbookGraph.csv` summarize dependencies across sheets.

## Clean-Up Workflow
- Use `csv_cleaning.py` to trim noisy rows and remove duplicates.
- The cleaned files are then uploaded with `dumpdata_in_gspread.py`.
- The Google Sheet gets a styled tab per CSV plus the `00_Index` landing page.

## Useful Editing Tips
- In `script_4_gpt.py`, `TARGET_TABS` controls which workbook sheets get scanned.
- In `script_4_gpt.py`, `SELECTED_OUTPUT_CSVS` controls which CSVs are produced.
- In `csv_cleaning.py`, `TARGET_CSV_FILES` controls which CSVs are cleaned.
- In `dumpdata_in_gspread.py`, tab colors and the index sheet legend control how the final Google Sheet looks.

## Best Short Summary
This workbook is a mapped view of the source Excel file:
- **tabs** = workbook structure
- **fields** = data entry and formula locations
- **dropdowns** = allowed input values
- **named ranges** = reusable logic/data sources
- **calculated fields** = formula dependencies
- **relationships/graph** = sheet-to-sheet dependency map
