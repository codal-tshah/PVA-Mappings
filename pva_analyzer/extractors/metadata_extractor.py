"""
PVA Workbench Analyzer — Metadata Extractor
Sheet-level info: visibility, tab color, used range, tables, named ranges used.
"""
from __future__ import annotations
from dataclasses import dataclass

from xlsb_reader import SheetData, WorkbookData
from config import NAMED_RANGE_PREFIXES
from logger import get_logger

log = get_logger("metadata_extractor")


@dataclass
class TabInventoryRecord:
    tab: str
    matched_name: str          # actual sheet name in workbook
    visible: str               # Visible | Hidden | VeryHidden
    tab_color: str
    used_range: str
    max_row: int
    max_col: int
    total_cells: int
    formula_cells: int
    merged_cells: int
    hidden_rows: int
    hidden_cols: int
    tables: str                # table names comma-separated
    data_validations: int
    named_ranges_referenced: str
    notes: str


@dataclass
class NamedRangeRecord:
    name: str
    refers_to: str
    prefix: str
    tabs_referencing: list[str]
    purpose: str


# ── Known named range purposes ─────────────────────────────────────────────────
RANGE_PURPOSES: dict[str, str] = {
    "pvaPropertyTypeKey":          "Master property type composite key — drives Show/Hide on ALL tabs",
    "pvaPropertyTypeKeyDD":        "Property subtype dropdown selection value",
    "pvaUOC_Settings":             "Unit of Comparison setting — cascades to all grids",
    "pvaCbsaId":                   "CBSA ID from DB import — auto-sets MSA in Cap & Mult and Investor Survey",
    "pvaIncomeApproach_QtyLeaseGrids":    "Number of active Lease Grid instances (1/2/3)",
    "pvaIncomeApproach_IsStabilized":     "Subject stabilized Yes/No — No activates MF Lease Up",
    "pvaIncomeApproach_RentalRateMethod": "Rental rate quoting method — cascades through all income tabs",
    "pvaIncomeApproach_MethodsUsed":      "Direct Cap Only | DCF Only | Both",
    "pvaIncomeApproach_QtyStatements":    "Number of historical financial statement tabs",
    "pvaCostApproach_CostorInsurable":    "Full Cost Approach vs Insurable Value Only",
    "pvaCostApproach_HasCostComps":       "Cost comparables Yes/No",
    "pvaCostApproach_GoingConcern":       "Going Concern Value Yes/No",
    "N1Address":                   "Full concatenated subject address for report narrative",
    "N1City":                      "City name for report narrative",
    "N1DBProvince":                "State abbreviation — feeds tblRentalRateMethod lookup",
    "N1DBZip":                     "ZIP code for narrative",
    "N1DBLatitude":                "Subject latitude — used by DistanceBetweenLatLongPoints() UDF",
    "N1DBLongitude":               "Subject longitude — used by DistanceBetweenLatLongPoints() UDF",
    "N1DBGBA":                     "Total Gross Building Area from Improvements",
    "N1BuildingsParkingSpaces":    "Total parking spaces from Improvements",
    "N1DBTopography":              "Topography description for site narrative",
    "N1DBZoning":                  "Zoning code for narrative",
    "N1DirCapValue":               "Direct Cap indicated value — used by @Spell() UDF",
    "N1AsIsValue":                 "As-Is concluded value — @Spell() → Values tab",
    "N1SalesGrid":                 "Sales grid narrative named range",
    "N1SaleHistorySummary":        "Sale history narrative summary",
    "N1_chtRentUtilitiesCostBurden": "Utilities cost burden chart for report",
    "N1_chtCapRatePressures":      "Cap rate pressure analysis chart named range",
    "N1IncomeApproachFinalReconciledValue": "Final reconciled income approach value",
    "pvaMktSur_submarket":         "Submarket from investor interview data",
    "pvaAPI_InvestorSurvey_PropType":   "Property type for investor survey API pull",
    "pvaAPI_InvestorSurvey_MSA":        "MSA for investor survey — auto-set from pvaCbsaId",
    "pvaAPI_InvestorSurvey_PeriodEnd":  "Period end quarter — auto-calc from TODAY()-45",
    "LIST_InvestorSurveyYears":    "Rolling 8-quarter list for period selectors",
    "data_InvestorSurvey_Sources": "Survey source citation string (RERC, PwC, Nareit, NCREIF)",
}


def extract_tab_inventory(
    tab: str,
    matched_name: str,
    sheet: SheetData,
    wb_data: WorkbookData,
) -> TabInventoryRecord:

    formula_count = sum(1 for c in sheet.cells if c.is_formula)
    merged_count  = sum(1 for c in sheet.cells if c.is_merged)

    # Named ranges referenced in this sheet's formulas
    from config import NAMED_RANGE_PREFIXES
    import re
    sheet_nrs: set[str] = set()
    for cell in sheet.cells:
        if cell.formula:
            for prefix in NAMED_RANGE_PREFIXES:
                found = re.findall(rf"\b{re.escape(prefix)}[A-Za-z0-9_]+", cell.formula, re.IGNORECASE)
                sheet_nrs.update(found)

    table_names = ", ".join(t["name"] for t in sheet.tables) if sheet.tables else ""

    return TabInventoryRecord(
        tab=tab,
        matched_name=matched_name,
        visible=sheet.meta.visible,
        tab_color=sheet.meta.tab_color,
        used_range=sheet.meta.used_range,
        max_row=sheet.meta.max_row,
        max_col=sheet.meta.max_col,
        total_cells=len(sheet.cells),
        formula_cells=formula_count,
        merged_cells=merged_count,
        hidden_rows=len(sheet.hidden_rows),
        hidden_cols=len(sheet.hidden_cols),
        tables=table_names,
        data_validations=len(sheet.data_validations),
        named_ranges_referenced=", ".join(sorted(sheet_nrs)[:20]),
        notes="",
    )


def extract_named_ranges(wb_data: WorkbookData, tabs_referencing: dict[str, list[str]] | None = None) -> list[NamedRangeRecord]:
    """Build named range inventory from workbook metadata."""
    records: list[NamedRangeRecord] = []
    if tabs_referencing is None:
        tabs_referencing = {}

    for name, refers_to in wb_data.named_ranges.items():
        prefix = next(
            (p for p in NAMED_RANGE_PREFIXES if name.startswith(p)),
            "other",
        )
        purpose = RANGE_PURPOSES.get(name, "")
        records.append(NamedRangeRecord(
            name=name,
            refers_to=refers_to,
            prefix=prefix,
            tabs_referencing=tabs_referencing.get(name, []),
            purpose=purpose,
        ))

    log.debug(f"Named ranges: {len(records)} total")
    return records
