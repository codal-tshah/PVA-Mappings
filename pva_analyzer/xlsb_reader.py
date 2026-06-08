"""
PVA Workbench Analyzer — XLSB Reader
Handles xlsb via pyxlsb; falls back to openpyxl for xlsx/xlsm.
Returns a unified WorkbookData object consumed by all extractors.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from logger import get_logger
from config import SKIP_VALUES, SKIP_PREFIXES

log = get_logger("xlsb_reader")


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class CellData:
    row: int
    col: int
    col_letter: str
    ref: str          # e.g. "B5"
    value: Any
    formula: str
    is_formula: bool
    is_merged: bool
    is_hidden_row: bool
    is_hidden_col: bool


@dataclass
class SheetMeta:
    name: str
    visible: str      # "Visible" | "Hidden" | "VeryHidden"
    tab_color: str
    used_range: str
    max_row: int
    max_col: int


@dataclass
class WorkbookData:
    path: str
    format: str                          # "xlsb" | "xlsx"
    all_sheet_names: list[str]
    sheet_visibility: dict[str, str]     # name -> Visible/Hidden/VeryHidden
    named_ranges: dict[str, str]         # name -> refers_to
    sheets: dict[str, "SheetData"] = field(default_factory=dict)


@dataclass
class SheetData:
    meta: SheetMeta
    cells: list[CellData]
    merged_ranges: list[str]
    hidden_rows: set[int]
    hidden_cols: set[int]
    col_widths: dict[int, float]
    row_heights: dict[int, float]
    tables: list[dict]
    data_validations: list[dict]


# ── Column letter helper ───────────────────────────────────────────────────────

def col_letter(n: int) -> str:
    """0-based column index → Excel letter."""
    result = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def is_skip(v: Any) -> bool:
    if v is None:
        return True
    s = str(v).strip()
    if not s:
        return True
    if s in SKIP_VALUES:
        return True
    for p in SKIP_PREFIXES:
        if s.startswith(p):
            return True
    return False


# ── XLSB reader (pyxlsb) ──────────────────────────────────────────────────────

def _read_xlsb_sheet(wb_path: str, sheet_name: str,
                     hidden_rows: set, hidden_cols: set) -> list[CellData]:
    from pyxlsb import open_workbook
    cells: list[CellData] = []
    try:
        with open_workbook(wb_path) as wb:
            with wb.get_sheet(sheet_name) as ws:
                for row_obj in ws.rows():
                    for cell in row_obj:
                        if cell.v is None:
                            continue
                        v = cell.v
                        is_form = isinstance(v, str) and v.strip().startswith("=")
                        cl = col_letter(cell.c)
                        cells.append(CellData(
                            row=cell.r + 1,
                            col=cell.c + 1,
                            col_letter=cl,
                            ref=f"{cl}{cell.r + 1}",
                            value=v if not is_form else None,
                            formula=v if is_form else "",
                            is_formula=is_form,
                            is_merged=False,
                            is_hidden_row=(cell.r + 1) in hidden_rows,
                            is_hidden_col=(cell.c + 1) in hidden_cols,
                        ))
    except Exception as e:
        log.warning(f"pyxlsb read error on '{sheet_name}': {e}")
    return cells


def _xlsb_sheet_names(wb_path: str) -> tuple[list[str], dict[str, str]]:
    """Returns (sheet_names, visibility_dict). xlsb doesn't expose visibility directly."""
    from pyxlsb import open_workbook
    with open_workbook(wb_path) as wb:
        names = wb.sheets
    visibility = {n: "Visible" for n in names}
    return names, visibility


def _xlsb_named_ranges(wb_path: str) -> dict[str, str]:
    """Best-effort named range extraction from xlsb."""
    from pyxlsb import open_workbook
    ranges: dict[str, str] = {}
    try:
        with open_workbook(wb_path) as wb:
            if hasattr(wb, "defined_names"):
                for dn in wb.defined_names:
                    ranges[dn.name] = dn.formula or ""
    except Exception as e:
        log.debug(f"Named range extraction (xlsb): {e}")
    return ranges


# ── XLSX/XLSM reader (openpyxl) ───────────────────────────────────────────────

def _xlsx_visibility(wb_path: str) -> dict[str, str]:
    import openpyxl
    wb = openpyxl.load_workbook(wb_path, read_only=True)
    result = {}
    for ws in wb.worksheets:
        sv = getattr(ws, "sheet_state", "visible")
        if sv == "hidden":
            result[ws.title] = "Hidden"
        elif sv == "veryHidden":
            result[ws.title] = "VeryHidden"
        else:
            result[ws.title] = "Visible"
    wb.close()
    return result


def _xlsx_sheet_names(wb_path: str) -> list[str]:
    import openpyxl
    wb = openpyxl.load_workbook(wb_path, read_only=True)
    names = wb.sheetnames
    wb.close()
    return names


def _xlsx_named_ranges(wb_path: str) -> dict[str, str]:
    import openpyxl
    wb = openpyxl.load_workbook(wb_path, read_only=False)
    ranges = {}
    for dn in wb.defined_names:
        try:
            ranges[dn.name] = dn.attr_text or ""
        except Exception:
            pass
    wb.close()
    return ranges


def _xlsx_read_sheet(wb_path: str, sheet_name: str) -> SheetData:
    import openpyxl
    from openpyxl.utils import get_column_letter as gcl

    # Load twice: once for formulas, once for values
    wb_f = openpyxl.load_workbook(wb_path, read_only=False, data_only=False)
    wb_v = openpyxl.load_workbook(wb_path, read_only=False, data_only=True)

    ws_f = wb_f[sheet_name]
    ws_v = wb_v[sheet_name]

    # Visibility
    sv = getattr(ws_f, "sheet_state", "visible")
    vis = "VeryHidden" if sv == "veryHidden" else ("Hidden" if sv == "hidden" else "Visible")

    # Tab color
    tab_color = ""
    try:
        if ws_f.sheet_properties.tabColor:
            tab_color = ws_f.sheet_properties.tabColor.rgb or ""
    except Exception:
        pass

    # Hidden rows/cols
    hidden_rows: set[int] = set()
    hidden_cols: set[int] = set()
    col_widths: dict[int, float] = {}
    row_heights: dict[int, float] = {}

    for rn, rd in (ws_f.row_dimensions or {}).items():
        if rd.hidden:
            hidden_rows.add(int(rn))
        if rd.height:
            row_heights[int(rn)] = rd.height

    for cn, cd in (ws_f.column_dimensions or {}).items():
        idx = openpyxl.utils.column_index_from_string(cn)
        if cd.hidden:
            hidden_cols.add(idx)
        if cd.width:
            col_widths[idx] = cd.width

    # Merged cells
    merged = [str(m) for m in ws_f.merged_cells.ranges]
    merged_set: set[str] = set()
    for mr in ws_f.merged_cells.ranges:
        for r in mr.cells:
            merged_set.add(f"{gcl(r[1])}{r[0]}")

    # Tables
    tables = []
    for tbl in getattr(ws_f, "_tables", {}).values():
        tables.append({
            "name": tbl.displayName,
            "ref":  tbl.ref,
            "cols": [c.name for c in tbl.tableColumns],
        })

    # Data validations
    validations = []
    for dv in ws_f.data_validations.dataValidation:
        v_info = {
            "type":     dv.type,
            "sqref":    str(dv.sqref),
            "formula1": dv.formula1 or "",
            "formula2": dv.formula2 or "",
            "operator": dv.operator or "",
            "show_dropdown": dv.showDropDown,
        }
        validations.append(v_info)

    # Cells
    cells: list[CellData] = []
    formula_cells = {(c.row, c.column): c for row in ws_f.iter_rows() for c in row}
    value_cells   = {(c.row, c.column): c for row in ws_v.iter_rows() for c in row}

    for (r, c), fc in formula_cells.items():
        raw_formula = fc.value
        raw_value   = value_cells.get((r, c), fc).value

        if raw_formula is None and raw_value is None:
            continue

        is_form = isinstance(raw_formula, str) and raw_formula.startswith("=")
        cl = gcl(c)
        ref = f"{cl}{r}"

        cells.append(CellData(
            row=r, col=c, col_letter=cl, ref=ref,
            value=raw_value if not is_form else raw_value,
            formula=raw_formula if is_form else "",
            is_formula=is_form,
            is_merged=ref in merged_set,
            is_hidden_row=r in hidden_rows,
            is_hidden_col=c in hidden_cols,
        ))

    max_r = max((c.row for c in cells), default=0)
    max_c = max((c.col for c in cells), default=0)

    meta = SheetMeta(
        name=sheet_name,
        visible=vis,
        tab_color=tab_color,
        used_range=f"A1:{gcl(max_c)}{max_r}" if max_r and max_c else "N/A",
        max_row=max_r,
        max_col=max_c,
    )

    wb_f.close()
    wb_v.close()

    return SheetData(
        meta=meta, cells=cells,
        merged_ranges=merged,
        hidden_rows=hidden_rows,
        hidden_cols=hidden_cols,
        col_widths=col_widths,
        row_heights=row_heights,
        tables=tables,
        data_validations=validations,
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def open_workbook_meta(wb_path: str) -> WorkbookData:
    """Read workbook-level metadata without loading any sheet data."""
    path = Path(wb_path)
    fmt = "xlsb" if path.suffix.lower() == ".xlsb" else "xlsx"

    log.info(f"Opening workbook: {path.name} ({path.stat().st_size / 1e6:.1f} MB)")

    if fmt == "xlsb":
        names, visibility = _xlsb_sheet_names(wb_path)
        named_ranges = _xlsb_named_ranges(wb_path)
    else:
        names = _xlsx_sheet_names(wb_path)
        visibility = _xlsx_visibility(wb_path)
        named_ranges = _xlsx_named_ranges(wb_path)

    log.info(f"Found {len(names)} sheets, {len(named_ranges)} named ranges")

    return WorkbookData(
        path=wb_path,
        format=fmt,
        all_sheet_names=names,
        sheet_visibility=visibility,
        named_ranges=named_ranges,
    )


def load_sheet(wb_data: WorkbookData, sheet_name: str) -> SheetData | None:
    """Load a single sheet. Returns None if not found."""
    # Fuzzy match sheet name
    actual = _fuzzy_match(sheet_name, wb_data.all_sheet_names)
    if actual is None:
        log.warning(f"Sheet not found: '{sheet_name}'")
        return None

    log.info(f"Loading sheet: '{actual}'" + (f" (matched from '{sheet_name}')" if actual != sheet_name else ""))

    try:
        if wb_data.format == "xlsb":
            cells = _read_xlsb_sheet(wb_data.path, actual, set(), set())
            max_r = max((c.row for c in cells), default=0)
            max_c = max((c.col for c in cells), default=0)
            vis = wb_data.sheet_visibility.get(actual, "Visible")
            meta = SheetMeta(
                name=actual, visible=vis, tab_color="",
                used_range=f"A1:{col_letter(max_c - 1)}{max_r}" if max_r else "N/A",
                max_row=max_r, max_col=max_c,
            )
            return SheetData(
                meta=meta, cells=cells,
                merged_ranges=[], hidden_rows=set(), hidden_cols=set(),
                col_widths={}, row_heights={},
                tables=[], data_validations=[],
            )
        else:
            return _xlsx_read_sheet(wb_data.path, actual)
    except Exception as e:
        log.error(f"Failed to load '{actual}': {e}", exc_info=True)
        return None


def _fuzzy_match(target: str, names: list[str]) -> str | None:
    """Case-insensitive exact then partial match."""
    tl = target.lower()
    for n in names:
        if n.lower() == tl:
            return n
    for n in names:
        if tl in n.lower() or n.lower() in tl:
            return n
    # Try stripping common prefixes/suffixes
    for n in names:
        cleaned = re.sub(r"[\s_\-]+", " ", n.lower()).strip()
        if cleaned == tl or tl in cleaned:
            return n
    return None
