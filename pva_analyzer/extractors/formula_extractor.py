"""
PVA Workbench Analyzer — Formula / Calculated Field Extractor
"""
from __future__ import annotations
import re
from dataclasses import dataclass

from xlsb_reader import SheetData, CellData
from config import NAMED_RANGE_PREFIXES
from logger import get_logger

log = get_logger("formula_extractor")

# Custom VBA UDFs present in the workbench
KNOWN_UDFS = {
    "@Spell": "Converts dollar value to written English words for report narrative",
    "Spell":  "Non-@ variant of @Spell — same function",
    "hideblankorerror": "Returns blank instead of Excel error (#N/A, #REF!) or zero",
    "DistanceBetweenLatLongPoints": "Calculates miles between two lat/lon coordinate pairs",
    "GetDropDownListFormula": "Dynamically builds data validation list formula",
}

BUILTIN_FUNCS = {
    "IF","IFS","IFERROR","AND","OR","NOT","SWITCH","CHOOSE",
    "SUM","SUMIF","SUMIFS","AVERAGE","AVERAGEIF","MIN","MAX","MEDIAN",
    "COUNT","COUNTA","COUNTIF","COUNTIFS","ROUND","ROUNDUP","ROUNDDOWN",
    "INDEX","MATCH","VLOOKUP","HLOOKUP","XLOOKUP","OFFSET","INDIRECT",
    "TEXT","VALUE","LEFT","RIGHT","MID","LEN","TRIM","UPPER","LOWER",
    "TEXTJOIN","CONCAT","CONCATENATE","SUBSTITUTE","SEARCH","FIND",
    "TODAY","NOW","DATE","YEAR","MONTH","DAY","DATEVALUE","DAYS",
    "LET","LAMBDA","MAP","FILTER","SORT","UNIQUE","SEQUENCE",
    "NPV","PV","FV","PMT","RATE","IRR","XNPV","XIRR",
    "ABS","INT","MOD","CEILING","FLOOR","POWER","SQRT",
    "ISNUMBER","ISTEXT","ISBLANK","ISFORMULA","ISERROR","ISNA",
}


@dataclass
class FormulaRecord:
    tab: str
    cell_ref: str
    row: int
    col: int
    label: str
    formula: str
    computed_value: str
    functions_used: list[str]
    udfs_used: list[str]
    named_ranges_used: list[str]
    cross_sheet_refs: list[str]      # other sheets referenced
    depends_on_tabs: list[str]
    formula_category: str            # arithmetic | lookup | text | date | financial | udf | aggregate
    notes: str


def _extract_functions(formula: str) -> tuple[list[str], list[str]]:
    """Returns (builtin_funcs, custom_udfs)."""
    raw = re.findall(r"@?([A-Za-z_][A-Za-z0-9_]*)\s*\(", formula)
    builtins, udfs = [], []
    for fn in raw:
        clean = fn.lstrip("@")
        if clean.upper() in BUILTIN_FUNCS:
            builtins.append(clean.upper())
        elif clean in KNOWN_UDFS or fn.startswith("@"):
            udfs.append(fn)
    return list(set(builtins)), list(set(udfs))


def _extract_named_ranges(formula: str) -> list[str]:
    found = []
    for prefix in NAMED_RANGE_PREFIXES:
        pattern = rf"\b{re.escape(prefix)}[A-Za-z0-9_]+"
        found.extend(re.findall(pattern, formula, re.IGNORECASE))
    return list(set(found))


def _extract_cross_sheet_refs(formula: str) -> list[str]:
    """Find 'SheetName'!CellRef or SheetName!CellRef patterns."""
    # Quoted sheet names
    refs = re.findall(r"'([^']+)'!", formula)
    # Unquoted
    refs += re.findall(r"\b([A-Za-z][A-Za-z0-9 _\-,]+)!", formula)
    return list(set(r.strip() for r in refs if len(r) > 1))


def _categorize(formula: str, funcs: list[str]) -> str:
    if any(u in formula for u in KNOWN_UDFS):
        return "udf"
    if any(f in funcs for f in ["VLOOKUP","HLOOKUP","INDEX","MATCH","XLOOKUP","OFFSET","INDIRECT"]):
        return "lookup"
    if any(f in funcs for f in ["SUM","SUMIF","SUMIFS","AVERAGE","COUNT","COUNTA"]):
        return "aggregate"
    if any(f in funcs for f in ["NPV","PV","FV","IRR","XIRR","XNPV","PMT"]):
        return "financial"
    if any(f in funcs for f in ["TEXT","LEFT","RIGHT","MID","TEXTJOIN","CONCAT","SUBSTITUTE"]):
        return "text"
    if any(f in funcs for f in ["DATE","YEAR","MONTH","DAY","TODAY","NOW","DATEVALUE"]):
        return "date"
    if any(f in funcs for f in ["IF","IFS","IFERROR","AND","OR","SWITCH"]):
        return "conditional"
    if re.search(r"[+\-\*/]", formula):
        return "arithmetic"
    return "other"


def _find_label(cell: CellData, cell_index: dict) -> str:
    for dc in range(1, 8):
        key = (cell.row, cell.col - dc)
        if key in cell_index:
            v = str(cell_index[key].value or "").strip()
            if v and len(v) > 2 and not v.startswith("="):
                return v
    for dr in range(1, 4):
        key = (cell.row - dr, cell.col)
        if key in cell_index:
            v = str(cell_index[key].value or "").strip()
            if v and len(v) > 2 and not v.startswith("="):
                return v
    return ""


def extract_formulas(tab: str, sheet: SheetData) -> list[FormulaRecord]:
    cell_index = {(c.row, c.col): c for c in sheet.cells}
    records: list[FormulaRecord] = []

    for cell in sheet.cells:
        if not cell.formula:
            continue

        formula = cell.formula.strip()
        if not formula.startswith("=") and not any(formula.startswith(u) for u in KNOWN_UDFS):
            continue

        funcs, udfs        = _extract_functions(formula)
        named_ranges       = _extract_named_ranges(formula)
        cross_refs         = _extract_cross_sheet_refs(formula)
        category           = _categorize(formula, funcs)
        label              = _find_label(cell, cell_index)

        notes = []
        if udfs:
            notes.append(f"UDF: {', '.join(udfs)}")
        if named_ranges:
            notes.append(f"named: {', '.join(named_ranges[:5])}")

        records.append(FormulaRecord(
            tab=tab,
            cell_ref=cell.ref,
            row=cell.row,
            col=cell.col,
            label=label[:150],
            formula=formula[:400],
            computed_value=str(cell.value or ""),
            functions_used=funcs,
            udfs_used=udfs,
            named_ranges_used=named_ranges,
            cross_sheet_refs=cross_refs,
            depends_on_tabs=cross_refs,
            formula_category=category,
            notes="; ".join(notes),
        ))

    log.debug(f"  {tab}: {len(records)} formula cells")
    return records
