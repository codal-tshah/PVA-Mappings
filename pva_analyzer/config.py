"""
PVA Workbench Analyzer — Configuration
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
OUTPUT_DIR  = BASE_DIR / "output"
LOG_DIR     = BASE_DIR / "logs"
STATE_DIR   = BASE_DIR / "state"

for d in [OUTPUT_DIR, LOG_DIR, STATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Target tabs (Jira ticket scope) ───────────────────────────────────────────
TARGET_TABS = [
    "File Info",
    "Settings",
    "Dates, Premises",
    "Contracts, History",
    "Scope",
    "Site",
    "Zoning",
    "Improvements",
    "Assessment",
    "Land Grid",
    "Land Valuation",
    "Land Comp Profiles",
    "Cost Approach Setup",
    "Sales Grid",
    "Sale Approach",
    "Sale Comp Profiles",
    "Income Approach",
    "Rent Roll Input",
    "Rent Roll Config",
    "Lease Grid",
    "Market Rent",
    "MF Market Rent",
    "Rent Comp Profiles",
    "Capitalization and Multipliers",
    "Investor Survey Input",
    "Investor Survey Output",
    "MF Lease Up",
    "DirectCapConclusion",
]

# ── Values to skip (workbench internal markers) ───────────────────────────────
SKIP_VALUES = {
    "VeryHidden", "?", "REPORT WRITER", "This column hidden by default",
    "Hide", "Show", "Auto", "Navigate", "True", "False",
    "Back End", "Front End", "tu", "q", "pp", "tq",
}
SKIP_PREFIXES = ("0x",)

# ── Field type heuristics ──────────────────────────────────────────────────────
FORMULA_INDICATORS = ("=", "@Spell", "=IF", "=SUM", "=INDEX", "=IFERROR")
INPUT_KEYWORDS = [
    "hand enter", "← hand enter", "enter", "type", "input",
    "your name", "your firm",
]
DROPDOWN_LABEL_PATTERNS = [
    "what is", "is there", "is this", "how many", "which", "do you",
    "are you", "does", "what agency", "choose", "select",
]

# ── Named range prefixes of interest ──────────────────────────────────────────
NAMED_RANGE_PREFIXES = ("pva", "N1", "tbl", "LIST_", "data_", "lucro_", "pvaMktSur")

# ── Output template sheet names ───────────────────────────────────────────────
TEMPLATE_SHEETS = [
    "Tab Inventory",
    "Field Inventory",
    "Field Mapping",
    "Dropdown Values",
    "Calculated Fields",
    "Tab Relationships",
    "Notes & Findings",
]

# ── Styling constants ──────────────────────────────────────────────────────────
COLORS = {
    "header_bg":    "0D2137",
    "section_bg":   "1A5276",
    "input_bg":     "DBEAFE",
    "calc_bg":      "FEF3C7",
    "dropdown_bg":  "D1FAE5",
    "gap_bg":       "FEF9C3",
    "alt_bg":       "F1F5F9",
    "white":        "FFFFFF",
    "border":       "CBD5E1",
    "req_bg":       "FEE2E2",
    "opt_bg":       "F0FDF4",
    "cond_bg":      "FFF7ED",
    "teal":         "0E6655",
}

# ── Google Sheets (optional) ──────────────────────────────────────────────────
GSHEETS_ENABLED        = False   # set True to enable
GSHEETS_CREDENTIALS    = BASE_DIR / "gsheets_credentials.json"
GSHEETS_SPREADSHEET_ID = ""      # paste your Google Sheets ID here
