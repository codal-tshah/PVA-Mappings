"""
PVA Workbench Analyzer — Relationship / Mapping Extractor
Identifies cross-tab data dependencies from formulas and known PVA patterns.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

from logger import get_logger

log = get_logger("mapping_extractor")


@dataclass
class RelationshipRecord:
    source_tab: str
    source_field: str
    target_tab: str
    relationship_type: str    # Drives | Feeds | Auto-populates | Configures | Linked from
    what_flows: str
    confidence: str           # confirmed | inferred | known-pattern


# ── Hardcoded known PVA relationships (from prior full analysis) ───────────────
KNOWN_RELATIONSHIPS: list[tuple] = [
    ("File Info", "Subject ID (I13)", "ALL tabs", "Auto-populates",
     "Master DB record key. VBA on open calls database API to import property data, comps, lat/lon, CBSA ID across entire workbook.", "known-pattern"),
    ("File Info", "Property Major Type + Subtype", "Settings → pvaPropertyTypeKey", "Drives",
     "Composite 'MajorType|All' key stored in pvaPropertyTypeKey. Read by Row 1 or Row 19 of every tab for VBA Show/Hide column logic.", "known-pattern"),
    ("Settings", "pvaPropertyTypeKey", "Site, Zoning, Improvements, Sales Grid, Lease Grid, MF Market Rent, all Comp Profile tabs", "Drives",
     "Each tab reads pvaPropertyTypeKey in its header row. VBA Show/Hide macros activate/deactivate property-type-specific columns.", "known-pattern"),
    ("Settings", "Cost Approach = Yes", "Land Grid, Land Valuation, Land Comp Profiles, Cost Approach Setup, Cost tab", "Configures",
     "Activates entire cost approach tab group.", "known-pattern"),
    ("Settings", "Sales Comparison = Yes", "Sales Grid, Sale Comp Profiles, Sales Approach", "Configures",
     "Activates sales comparison tab group.", "known-pattern"),
    ("Settings", "Income Approach = Yes", "Income Approach Setup, Rent Roll Input/Config, Lease Grid(s), Market Rent, MF Market Rent, Cap & Mult, Investor Survey, MF Lease Up, DirectCapConclusion", "Configures",
     "Activates ALL ~15 income approach tabs.", "known-pattern"),
    ("Settings", "pvaIncomeApproach_QtyLeaseGrids", "Lease Grid, Market Rent, Rent Comp Profiles", "Configures",
     "Controls how many Lease Grid + Market Rent + Rent Comp Profiles instances are active (1, 2, or 3).", "known-pattern"),
    ("Settings", "pvaIncomeApproach_IsStabilized = No", "MF Lease Up", "Configures",
     "Activates MF Lease Up when subject is not stabilized.", "known-pattern"),
    ("Settings", "pvaIncomeApproach_RentalRateMethod", "Lease Grid, Market Rent, MF Market Rent, Cap & Mult", "Configures",
     "Rental rate method cascades through ALL income tabs ($/SF/Yr vs $/Unit/Mo etc.).", "known-pattern"),
    ("File Info", "State Abbreviation (N1DBProvince)", "Income Approach Setup", "Auto-populates",
     "tblRentalRateMethod lookup auto-sets rental rate method from state (e.g. CA → $/SF/Mo).", "known-pattern"),
    ("File Info", "pvaCbsaId (from DB import)", "Capitalization & Mult → Investor Survey Output", "Auto-populates",
     "tblPwC_MSA IFERROR-INDEX-MATCH lookup: pvaCbsaId → MSA Short Name → auto-sets MSA selector.", "known-pattern"),
    ("File Info", "N1DBLatitude, N1DBLongitude", "Land Grid, Sales Grid, Lease Grid", "Auto-populates",
     "DistanceBetweenLatLongPoints() custom VBA UDF calculates comp distances.", "known-pattern"),
    ("Site", "Land area, frontage, buildable SF, FAR", "Contracts & History Export section", "Feeds",
     "Price Per Land SF, Price Per Acre, Price Per Primary Frontage, Price Per Buildable SF, Price Per FAR.", "known-pattern"),
    ("Improvements", "Total GBA, NRA, Units, Rooms, Bays", "Contracts & History Export, Sales Grid, Cap & Mult, MF Market Rent", "Feeds",
     "Improvements totals feed: Price metrics in Contracts/History; Subject GBA in Sales Grid; Unit count in MF Market Rent.", "known-pattern"),
    ("Assessment", "Annual Taxes (parcel total)", "Capitalization and Multipliers", "Feeds",
     "DIRECT CELL LINK: Annual Taxes total auto-populates Real Estate Taxes OpEx line in Cap & Mult.", "known-pattern"),
    ("Rent Roll Input + Rent Roll Config", "Raw data + grouping rules", "Rent Roll Master (auto-generated)", "Auto-populates",
     "VBA macro processes pasted unit data + grouping rules → Rent Roll Master processed unit table.", "known-pattern"),
    ("Rent Roll Config", "UnitMix_ConfigID per unit type", "MF Market Rent (column index row 2)", "Auto-populates",
     "Row 2 of MF Market Rent maps column indices to Rent Roll Master positions by UnitMix_ConfigID.", "known-pattern"),
    ("MF Market Rent", "Pro Forma EGI (stabilized)", "MF Lease Up", "Feeds",
     "Pro Forma EGI is the baseline income for MF Lease Up absorption calculations. Direct cell link.", "known-pattern"),
    ("MF Market Rent", "Asking Rent totals by unit type", "Capitalization and Multipliers", "Feeds",
     "MF Market Rent total asking rent feeds PGI in Cap & Mult (Option 1: from Rent Roll).", "known-pattern"),
    ("Lease Grid", "Selected comp rates (0x2a row 19)", "Market Rent", "Feeds",
     "Internal 0x2a markers track selected comp rate per unit type → flow to Market Rent conclusions.", "known-pattern"),
    ("Capitalization and Multipliers", "Net Operating Income (NOI)", "DirectCapConclusion", "Feeds",
     "NOI is the primary input to Direct Capitalization: Value = NOI ÷ Cap Rate.", "known-pattern"),
    ("Capitalization and Multipliers", "Total OpEx", "MF Lease Up", "Feeds",
     "Pro Forma Expenses in MF Lease Up linked from Cap & Mult Total Operating Expenses.", "known-pattern"),
    ("Capitalization and Multipliers", "N1DirCapValue", "Values tab / Appraisal Summary", "Feeds",
     "@Spell(N1DirCapValue, refCell) converts to written words in Values tab.", "known-pattern"),
    ("Investor Survey Output", "Cap Rate Ranges (RERC, PwC, Nareit, NCREIF)", "DirectCapConclusion", "Feeds",
     "Third-party cap rate ranges support cap rate selection in DirectCapConclusion risk factor analysis.", "known-pattern"),
    ("MF Lease Up", "TOTAL PV of NOI Loss", "DirectCapConclusion", "Feeds",
     "Total PV of NOI Loss = lease-up discount: As-Is Value = Direct Cap Value − Discount.", "known-pattern"),
    ("DirectCapConclusion", "As-Is Value (N1AsIsValue)", "Values tab / Appraisal Summary", "Feeds",
     "@Spell(N1AsIsValue) → written words → Values tab and Appraisal Summary.", "known-pattern"),
    ("Scope", "Approach applicability matrix", "N1_chtScopeMethodologyTable → Report", "Feeds",
     "Applicability|Utilized values drive N1_chtScopeMethodologyTable → scope methodology table in report.", "known-pattern"),
]


def extract_relationships(
    tab: str,
    formula_records: list,
    all_tab_names: list[str],
) -> list[RelationshipRecord]:
    """
    Combine known patterns with formula-derived cross-sheet references.
    """
    records: list[RelationshipRecord] = []

    # Known patterns for this tab
    for (src_tab, src_field, tgt_tab, rtype, what, conf) in KNOWN_RELATIONSHIPS:
        if src_tab.lower() == tab.lower() or tgt_tab.lower() == tab.lower():
            records.append(RelationshipRecord(
                source_tab=src_tab,
                source_field=src_field,
                target_tab=tgt_tab,
                relationship_type=rtype,
                what_flows=what,
                confidence=conf,
            ))

    # Formula-derived cross-sheet refs
    for frec in formula_records:
        for ref_sheet in frec.cross_sheet_refs:
            # Match to a known tab
            matched = _match_tab(ref_sheet, all_tab_names)
            if matched and matched != tab:
                records.append(RelationshipRecord(
                    source_tab=tab,
                    source_field=frec.label or frec.cell_ref,
                    target_tab=matched,
                    relationship_type="Linked from",
                    what_flows=f"Formula in {frec.cell_ref} references {ref_sheet}: {frec.formula[:80]}",
                    confidence="inferred",
                ))

    # Deduplicate
    seen: set[tuple] = set()
    deduped: list[RelationshipRecord] = []
    for r in records:
        key = (r.source_tab, r.target_tab, r.relationship_type[:20])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    log.debug(f"  {tab}: {len(deduped)} relationships ({sum(1 for r in deduped if r.confidence=='known-pattern')} known, {sum(1 for r in deduped if r.confidence=='inferred')} inferred)")
    return deduped


def _match_tab(name: str, all_tabs: list[str]) -> str | None:
    nl = name.lower().strip()
    for t in all_tabs:
        if t.lower() == nl:
            return t
    for t in all_tabs:
        if nl in t.lower() or t.lower() in nl:
            return t
    return None
