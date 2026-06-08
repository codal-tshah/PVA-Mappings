"""
PVA Workbench Analyzer — Field Extractor
Classifies each cell as: label | input | calculated | dropdown | unknown
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any

from xlsb_reader import SheetData, CellData
from config import (
    FORMULA_INDICATORS, INPUT_KEYWORDS,
    DROPDOWN_LABEL_PATTERNS, NAMED_RANGE_PREFIXES,
)
from logger import get_logger

log = get_logger("field_extractor")


@dataclass
class FieldRecord:
    tab: str
    cell_ref: str
    row: int
    col: int
    label: str
    field_type: str        # input | calculated | dropdown | label | unknown
    value: Any
    formula: str
    data_type: str         # Text | Currency | Percentage | Date | Integer | Decimal | Mixed | Image
    is_required: str       # Required | Conditional | Optional
    is_hidden: bool
    is_merged: bool
    named_ranges_used: list[str]
    notes: str


# ── Heuristic classifiers ──────────────────────────────────────────────────────

def _is_formula(cell: CellData) -> bool:
    if cell.is_formula:
        return True
    f = str(cell.formula or "")
    return any(f.startswith(ind) for ind in FORMULA_INDICATORS)


def _is_likely_dropdown_label(text: str) -> bool:
    t = text.lower().strip()
    return any(t.startswith(p) for p in DROPDOWN_LABEL_PATTERNS)


def _is_likely_input_label(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in INPUT_KEYWORDS)


def _infer_data_type(cell: CellData, label: str) -> str:
    v = cell.value
    label_lower = label.lower()

    if any(kw in label_lower for kw in ["date", "day", "month", "year", "effective", "report date",
                                          "inspection", "due date", "invoice date"]):
        return "Date"
    if any(kw in label_lower for kw in ["price", "fee", "cost", "value", "income", "rent",
                                          "expense", "taxes", "assessment", "noi", "pgi", "egi"]):
        return "Currency"
    if any(kw in label_lower for kw in ["%", "percent", "ratio", "rate", "vacancy", "factor"]):
        return "Percentage"
    if any(kw in label_lower for kw in ["sf", "area", "acres", "gba", "nra", "units", "count",
                                          "number of", "# of", "stories", "age"]):
        if "%" in label_lower:
            return "Percentage"
        return "Integer"
    if v is not None:
        if isinstance(v, float) and not str(v).replace(".", "").replace("-", "").isdigit():
            return "Decimal"
        if isinstance(v, int):
            return "Integer"
    return "Text"


def _infer_required(label: str, field_type: str, tab: str) -> str:
    ll = label.lower()
    # Always required
    if any(kw in ll for kw in ["subject id", "property name", "report date", "inspection date",
                                  "address", "city", "state", "property type", "value type",
                                  "interest appraised"]):
        return "Required"
    # Conditional
    if any(kw in ll for kw in ["if", "when", "only if", "required if", "agency", "hud",
                                  "freddie", "fannie", "cmbs", "proposed", "mf", "multi-family",
                                  "renovation", "affordable", "lodging", "senior"]):
        return "Conditional"
    # Dropdowns are usually required
    if field_type == "dropdown":
        return "Required"
    # Calculated never required from user
    if field_type == "calculated":
        return "Calculated"
    return "Optional"


def _extract_named_ranges(formula: str) -> list[str]:
    if not formula:
        return []
    found = []
    for prefix in NAMED_RANGE_PREFIXES:
        pattern = rf"\b{re.escape(prefix)}[A-Za-z0-9_]+"
        found.extend(re.findall(pattern, formula))
    return list(set(found))


def _find_nearby_label(cell: CellData, all_cells: dict[tuple, CellData],
                        max_lookback: int = 5) -> str:
    """Look left and above for a text label cell."""
    # Check same row, columns to the left
    for dc in range(1, max_lookback + 1):
        key = (cell.row, cell.col - dc)
        if key in all_cells:
            v = str(all_cells[key].value or "").strip()
            if v and len(v) > 2 and not v.startswith("="):
                return v
    # Check rows above, same column
    for dr in range(1, 4):
        key = (cell.row - dr, cell.col)
        if key in all_cells:
            v = str(all_cells[key].value or "").strip()
            if v and len(v) > 2 and not v.startswith("="):
                return v
    return ""


# ── Main extractor ─────────────────────────────────────────────────────────────

def extract_fields(tab: str, sheet: SheetData,
                   dv_map: dict[str, dict] | None = None) -> list[FieldRecord]:
    """
    Extract all meaningful fields from a sheet.
    dv_map: optional dict of cell_ref -> validation info (from extract_dropdowns)
    """
    if dv_map is None:
        dv_map = {}

    # Build cell lookup
    cell_index: dict[tuple, CellData] = {
        (c.row, c.col): c for c in sheet.cells
    }

    records: list[FieldRecord] = []
    seen_refs: set[str] = set()

    for cell in sheet.cells:
        if cell.ref in seen_refs:
            continue
        seen_refs.add(cell.ref)

        raw_val = str(cell.value or "").strip()
        formula = cell.formula or ""

        # Skip internal markers
        if not raw_val and not formula:
            continue
        if raw_val in {"", "?", "VeryHidden", "REPORT WRITER"}:
            continue
        if raw_val.startswith("0x"):
            continue

        # Classify
        if _is_formula(cell):
            field_type = "calculated"
            label = _find_nearby_label(cell, cell_index)
        elif cell.ref in dv_map:
            field_type = "dropdown"
            label = raw_val if len(raw_val) > 3 else _find_nearby_label(cell, cell_index)
        elif _is_likely_dropdown_label(raw_val):
            field_type = "dropdown"
            label = raw_val
        elif raw_val and not cell.is_formula:
            # Distinguish label vs input
            if (len(raw_val) > 3
                    and not str(raw_val).replace(".", "").replace("-", "").replace(",", "").isdigit()):
                field_type = "input"
                label = raw_val
            else:
                field_type = "input"
                label = _find_nearby_label(cell, cell_index) or raw_val
        else:
            field_type = "unknown"
            label = raw_val

        named_ranges = _extract_named_ranges(formula)
        data_type    = _infer_data_type(cell, label)
        required     = _infer_required(label, field_type, tab)

        notes = ""
        if cell.is_hidden_row:
            notes += "hidden-row; "
        if cell.is_hidden_col:
            notes += "hidden-col; "
        if cell.is_merged:
            notes += "merged; "

        records.append(FieldRecord(
            tab=tab,
            cell_ref=cell.ref,
            row=cell.row,
            col=cell.col,
            label=label[:200],
            field_type=field_type,
            value=cell.value,
            formula=formula[:300],
            data_type=data_type,
            is_required=required,
            is_hidden=cell.is_hidden_row or cell.is_hidden_col,
            is_merged=cell.is_merged,
            named_ranges_used=named_ranges,
            notes=notes.strip("; "),
        ))

    log.debug(f"  {tab}: {len(records)} fields "
              f"({sum(1 for r in records if r.field_type=='input')} input, "
              f"{sum(1 for r in records if r.field_type=='calculated')} calc, "
              f"{sum(1 for r in records if r.field_type=='dropdown')} dropdown)")
    return records
