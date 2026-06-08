# PVA Workbench Analyzer

Production-quality Python tool that reads a large `.xlsb` workbook and
populates a documentation spreadsheet (Tab Inventory, Field Inventory,
Dropdown Values, Calculated Fields, Field Mapping, Tab Relationships,
Notes & Findings, Named Ranges).

---

## Project Structure

```
pva_analyzer/
├── main.py                        ← CLI entry point
├── config.py                      ← Target tabs, paths, constants
├── orchestrator.py                ← Main coordinator (resume, error handling)
├── xlsb_reader.py                 ← Workbook reader (xlsb + xlsx)
├── output_writer.py               ← Excel output writer
├── gsheets_writer.py              ← Google Sheets writer (optional)
├── state_manager.py               ← Resume / progress tracking
├── logger.py                      ← Structured logging
├── requirements.txt
├── extractors/
│   ├── field_extractor.py         ← Classifies cells: input/calc/dropdown
│   ├── dropdown_extractor.py      ← Data validation + known dropdown options
│   ├── formula_extractor.py       ← Formula parsing, UDF detection, cross-refs
│   ├── metadata_extractor.py      ← Sheet-level metadata, named ranges
│   └── mapping_extractor.py       ← Cross-tab relationship detection
├── output/                        ← Generated analysis files
├── logs/                          ← Session log files
└── state/                         ← Resume state JSON files
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

### Analyze a workbook (all 28 target tabs)
```bash
python main.py /path/to/workbench.xlsb
```

### Use your own template
```bash
python main.py workbench.xlsb --template my_template.xlsx
```

### Process only specific tabs
```bash
python main.py workbench.xlsb --tabs "File Info" "Settings" "Sales Grid"
```

### Force re-process (ignore saved state)
```bash
python main.py workbench.xlsb --no-resume
```

### Just list all sheet names (quick audit)
```bash
python main.py workbench.xlsb --list-sheets
```

### Generate audit CSVs (sheets + named ranges, no full analysis)
```bash
python main.py workbench.xlsb --audit
```

### Reset saved progress
```bash
python main.py workbench.xlsb --reset
```

### Also write to Google Sheets
```bash
python main.py workbench.xlsb --gsheets
```

---

## Resume Behaviour

State is saved to `state/<workbook_name>_state.json` after every tab.
If the script is interrupted, re-run the same command and it resumes
from where it left off, skipping already-completed tabs.

---

## Output

The script produces `output/<workbook_name>_analysis.xlsx` with 8 sheets:

| Sheet | Contents |
|---|---|
| **Tab Inventory** | One row per tab — visibility, used range, cell counts, table/DV info |
| **Field Inventory** | Every field with type (Input/Calc/Dropdown), data type, required flag, named range, API-seed flag |
| **Dropdown Values** | Every dropdown field with all options (pipe-separated) |
| **Calculated Fields** | Every formula cell with formula text, UDFs, cross-sheet refs, category |
| **Field Mapping** | Source→target data flow across tabs (known patterns + formula-derived) |
| **Tab Relationships** | Simplified inter-tab dependency table |
| **Notes & Findings** | Warnings, gaps, missing tabs, VBA constraints, seeding rules |
| **Named Ranges** | All pva*, N1*, tbl*, LIST_* named ranges with purpose descriptions |

---

## Google Sheets Setup

1. Create a Google Cloud service account and download `credentials.json`
2. Share your Google Sheet with the service account email
3. Set in `config.py`:
   ```python
   GSHEETS_ENABLED        = True
   GSHEETS_CREDENTIALS    = BASE_DIR / "gsheets_credentials.json"
   GSHEETS_SPREADSHEET_ID = "your_spreadsheet_id_here"
   ```
4. Run with `--gsheets` flag

---

## Key Architecture Notes

### Memory management
Sheets are loaded one at a time (`load_sheet`), processed, and then
released. The workbook file is never held open across sheet loads.

### xlsb vs xlsx
- `.xlsb` is read via `pyxlsb` — cell values and formulas extracted
- `.xlsx/.xlsm` is read via `openpyxl` — additionally extracts data
  validation, merged cells, hidden rows/cols, table objects, tab colors
- xlsb files don't expose data validation or tab colors via pyxlsb;
  the dropdown extractor falls back to label-pattern heuristics

### VBA / calculated fields
The workbench uses 5 custom VBA UDFs (`@Spell`, `hideblankorerror`,
`DistanceBetweenLatLongPoints`, `GetDropDownListFormula`, `Spell`).
These are detected in formulas and flagged. They ONLY execute in Excel
with macros enabled — not in Python.

### Named ranges
pva* named ranges are the master control mechanism. The tool extracts
all named ranges from the workbook and cross-references which tabs use
each range in their formulas.
