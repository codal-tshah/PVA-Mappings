"""
PVA Workbench Analyzer — Dropdown / Data Validation Extractor
"""
from __future__ import annotations
import re
from dataclasses import dataclass

from xlsb_reader import SheetData
from logger import get_logger

log = get_logger("dropdown_extractor")


@dataclass
class DropdownRecord:
    tab: str
    cell_ref: str
    field_label: str
    validation_type: str   # list | custom | whole | decimal | date | any
    formula1: str          # raw formula or list string
    formula2: str
    options: list[str]     # parsed options if list type
    options_str: str       # pipe-separated for output
    source_range: str      # if options come from a range ref
    notes: str


# ── Known PVA dropdown options (from prior analysis) ──────────────────────────
# Used as fallback when validation is in a separate Lists tab or xlsb
KNOWN_DROPDOWN_OPTIONS: dict[str, list[str]] = {
    "property major type": [
        "Multi-Family", "Retail-Commercial", "Office", "Industrial",
        "Shopping Center", "Health Care", "Senior Housing",
        "Self-Storage", "Lodging & Hospitality", "Mobile/Manufactured Home Park",
    ],
    "what is the pva property type": [
        "Multi-Family", "Retail-Commercial", "Office", "Industrial",
        "Shopping Center", "Health Care", "Senior Housing",
        "Self-Storage", "Lodging & Hospitality", "Mobile/Manufactured Home Park",
    ],
    "existing or proposed": [
        "Existing", "Proposed", "Under Construction", "Vacant Land",
    ],
    "country": ["United States", "Canada"],
    "value type": [
        "Market Value As Is", "Market Value Upon Completion",
        "Market Value As Stabilized", "Prospective Market Value",
        "Investment Value", "Liquidation Value", "Insurable Value",
    ],
    "value perspective": [
        "Retrospective", "Current (as of inspection date)", "Prospective",
    ],
    "interest appraised": [
        "Fee Simple", "Leased Fee", "Leasehold", "Partial Interest", "Easement",
    ],
    "report type": [
        "Appraisal Report", "Restricted Appraisal Report",
        "Evaluation Appraisal Report", "Short Narrative", "Narrative",
    ],
    "what agency": [
        "None", "Freddie Mac", "Fannie Mae", "HUD", "FHA", "CMBS",
    ],
    "hud sub-menu": [
        "HUD 92264", "HUD 92273 Market", "HUD 92273 Affordable",
        "HUD 92273 Section 8", "HUD 92274", "HUD 92264T",
    ],
    "cost approach": ["Yes", "No"],
    "sales comparison approach": ["Yes", "No"],
    "income capitalization approach": ["Yes", "No"],
    "is there multi-family affordable": ["Yes", "No"],
    "is there multi-family renovation": ["Yes", "No"],
    "is this a market study": ["Yes", "No"],
    "is this a proposed property": ["Yes", "No"],
    "is the subject stabilized": ["Yes", "No"],
    "do you need land comps": ["Yes", "No"],
    "has property been sold": ["Yes", "No"],
    "rounding": ["Set Multiple", "Formula"],
    "subject unit of comparison": ["Unit", "SF", "Room", "Bed", "Key"],
    "full cost approach or insurable value": [
        "Full Cost Approach", "Insurable Value Only",
    ],
    "do you need direct cap, dcf, or both": [
        "Direct Cap Only", "DCF Only", "Both",
    ],
    "which dcf software": [
        "Argus Enterprise", "ProCalc", "Excel DCF", "Other",
    ],
    "how many lease grids": ["1", "2", "3"],
    "how does your market quote rental rates": [
        "$/SF/Mo", "$/SF/Yr", "$/Unit/Mo", "$/Unit/Yr", "$/Room/Mo",
    ],
    "topography": [
        "Level", "Gently Sloping", "Moderately Sloping",
        "Steeply Sloping", "Hilly", "Below Street Grade", "Rolling", "Other",
    ],
    "shape": [
        "Regular", "Irregular", "Triangular", "Flag",
        "L-Shaped", "Pie-Shaped", "Rectangular", "Other",
    ],
    "visibility": ["Excellent", "Good", "Average", "Fair", "Poor"],
    "corner location": ["Yes", "No"],
    "quality": [
        "Class A", "Class A-", "Class B+", "Class B",
        "Class B-", "Class C+", "Class C", "Class D",
    ],
    "condition": ["Excellent", "Good", "Average", "Fair", "Poor", "Critical"],
    "conforming": [
        "Conforming", "Legal Non-Conforming", "Non-Conforming", "Unknown",
    ],
    "sprinkler": [
        "Yes — Wet Pipe", "Yes — Dry Pipe", "Yes — Pre-Action", "Partial", "No",
    ],
    "ada compliance": ["Fully Compliant", "Partially Compliant", "Non-Compliant", "Unknown"],
    "type of pgi": ["Contract & Market", "Market Only", "Contract Only"],
    "pgi source": [
        "Option 1: From Rent Roll tab (linked)", "Option 2: Manual Entry",
    ],
    "rent type": [
        "NNN (Triple Net)", "Gross", "Modified Gross",
        "Full Service / Gross", "Base Year Stop", "Industrial Gross",
        "Absolute NNN", "Other",
    ],
    "utility cost burden": [
        "Tenant Paid Directly", "Owner Paid (included in rent)",
        "Tenant Reimburses Owner", "N/A",
    ],
    "confidentiality": ["Confidential", "Non-Confidential"],
    "segmentation": ["National", "Regional", "Market (local)"],
    "value allocation or real estate only": [
        "Real Estate Only", "Value Allocation",
    ],
    "geographies": [
        "National, Regional, Market", "National, Regional",
        "National, Market", "Regional, Market",
        "National Only", "Regional Only", "Market Only",
    ],
    "cap rate pressure": [
        "No Impact", "Strong Upward", "Upward", "Downward", "Strong Downward",
    ],
    "rating": [
        "No Impact", "Strong Upward", "Upward", "Downward", "Strong Downward",
    ],
    "unit name label source": [
        "abc (alphabetical letter)", "123 (sequential number)",
        "Label Prefix (custom prefix text)",
    ],
    "group by": ["Yes", "No"],
    "affordable flag": ["Yes", "No"],
    "inspection": [
        "Interior & Exterior — in person", "Exterior Only — in person",
        "Drive-by", "Desktop/Desk Review", "No Inspection",
        "Virtual/Remote inspection",
    ],
    "intended use": [
        "Mortgage lending — purchase", "Mortgage lending — refinance",
        "Estate planning", "Estate tax", "Litigation support",
        "Internal use/decision making", "Sale/purchase advisory",
        "Portfolio analysis", "Insurance", "Eminent domain", "Other",
    ],
    "approach applicability": ["Not Applicable", "Applicable"],
    "approach utilized": [
        "Not Utilized", "Utilized but Not Reconciled",
        "Utilized and Reconciled",
    ],
    "property rights": ["Fee Simple", "Leased Fee", "Leasehold", "Unknown"],
    "no. of parcels": ["1", "2", "3", "4", "5", "6", "7"],
    "no. of buildings": ["1", "2", "3", "4", "5", "6", "7"],
    "no. of zones": ["1", "2", "3", "4", "5+"],
    "chain scale": [
        "Luxury", "Upper Upscale", "Upscale",
        "Upper Midscale", "Midscale", "Economy", "Independent",
    ],
    "premise": ["As Is", "Upon Completion", "As Stabilized", "Prospective"],
    "show template": ["Front End", "Back End"],
    "mf unit count uom": ["Unit", "SF"],
    "include commercial in unit count": ["Yes", "No"],
}


def _best_match_options(label: str) -> list[str]:
    """Find best matching known options by label keyword."""
    ll = label.lower()
    best: list[str] = []
    best_score = 0
    for key, opts in KNOWN_DROPDOWN_OPTIONS.items():
        # Score = number of words from key that appear in label
        words = key.split()
        score = sum(1 for w in words if w in ll)
        if score > 0 and score >= best_score:
            if score > best_score:
                best = opts
                best_score = score
            elif len(opts) > len(best):
                best = opts
    return best


def _parse_list_formula(formula1: str) -> tuple[list[str], str]:
    """Parse inline list like '"Yes,No"' or '"A,B,C"'. Returns (options, source_range)."""
    if not formula1:
        return [], ""

    # If it's a range reference (Sheet!$A$1:$A$10)
    if re.match(r"^['\w\s,]+!\$", formula1) or re.match(r"^\$", formula1):
        return [], formula1

    # Inline list: "Yes,No" or Yes,No
    clean = formula1.strip('"').strip("'")
    if "," in clean:
        parts = [p.strip() for p in clean.split(",") if p.strip()]
        if 1 < len(parts) <= 50:
            return parts, ""

    return [], ""


def extract_dropdowns(tab: str, sheet: SheetData) -> tuple[list[DropdownRecord], dict[str, dict]]:
    """
    Returns:
      records:  list of DropdownRecord for output
      dv_map:   dict of cell_ref -> {type, options} for field_extractor
    """
    records: list[DropdownRecord] = []
    dv_map: dict[str, dict] = {}

    # Process openpyxl-extracted data validations
    for dv in sheet.data_validations:
        sqref = dv.get("sqref", "")
        f1    = dv.get("formula1", "") or ""
        f2    = dv.get("formula2", "") or ""
        vtype = dv.get("type", "any") or "any"

        options, source_range = _parse_list_formula(f1)

        # Build dv_map entry for every cell in sqref
        for ref_block in str(sqref).split():
            dv_map[ref_block] = {"type": vtype, "options": options}

        # Find a label for this validation cell
        label = _guess_label_from_sheet(sqref, sheet)

        # Augment with known options if we parsed none
        if not options and label:
            options = _best_match_options(label)

        records.append(DropdownRecord(
            tab=tab,
            cell_ref=sqref,
            field_label=label,
            validation_type=vtype,
            formula1=f1,
            formula2=f2,
            options=options,
            options_str=" | ".join(options),
            source_range=source_range,
            notes="from data_validation",
        ))

    # Additionally: scan cells for likely dropdown labels not caught by DV
    # (xlsb doesn't expose DV — use label heuristic)
    if not records:
        from config import DROPDOWN_LABEL_PATTERNS
        cell_index = {(c.row, c.col): c for c in sheet.cells}
        for cell in sheet.cells:
            v = str(cell.value or "").strip()
            if not v or len(v) < 4:
                continue
            vl = v.lower()
            if any(vl.startswith(p) for p in DROPDOWN_LABEL_PATTERNS):
                options = _best_match_options(v)
                dv_map[cell.ref] = {"type": "list", "options": options}
                records.append(DropdownRecord(
                    tab=tab,
                    cell_ref=cell.ref,
                    field_label=v,
                    validation_type="list",
                    formula1="",
                    formula2="",
                    options=options,
                    options_str=" | ".join(options),
                    source_range="",
                    notes="inferred from label pattern",
                ))

    log.debug(f"  {tab}: {len(records)} dropdowns found")
    return records, dv_map


def _guess_label_from_sheet(sqref: str, sheet: SheetData) -> str:
    """Try to find a text label near the validation cell."""
    # Take first cell ref from sqref
    first = str(sqref).split()[0].split(":")[0]
    match = re.match(r"([A-Z]+)(\d+)", first.upper())
    if not match:
        return ""
    col_letters, row_str = match.groups()
    row = int(row_str)

    # Convert col letters to index
    col_idx = 0
    for ch in col_letters:
        col_idx = col_idx * 26 + (ord(ch) - ord('A') + 1)

    cell_index = {(c.row, c.col): c for c in sheet.cells}

    # Look left in same row
    for dc in range(1, 8):
        key = (row, col_idx - dc)
        if key in cell_index:
            v = str(cell_index[key].value or "").strip()
            if v and len(v) > 3 and not v.startswith("="):
                return v
    # Look above
    for dr in range(1, 4):
        key = (row - dr, col_idx)
        if key in cell_index:
            v = str(cell_index[key].value or "").strip()
            if v and len(v) > 3 and not v.startswith("="):
                return v
    return ""
