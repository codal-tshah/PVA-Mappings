"""
PVA Workbench Field-Level Discovery — Final Deliverable Builder
================================================================
Reads PVA_Workbench_Field_Reference_v2.xlsx (27 tabs already documented)
and adds the missing "Sale Approach" tab from manual inspection.
Outputs a polished Excel file per the JIRA PVA-26 acceptance criteria.

Columns:
  A  #            – Row number within each tab section
  B  Tab          – Workbench tab name
  C  Field / Label
  D  Type         – User Entry | Calculated | Dropdown
  E  Description / Notes
  F  Dropdown Options / Linked Named Range
  G  Cross-Tab Dependency   (which other tabs feed or consume this field)
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from copy import copy

# ── Paths ──────────────────────────────────────────────────────────────
REF_V2 = "PVA_Workbench_Field_Reference_v2.xlsx"
OUTPUT  = "PVA_Workbench_Field_Discovery.xlsx"

# ── JIRA-required tab order ───────────────────────────────────────────
JIRA_TABS = [
    "File Info", "Settings", "Dates, Premises", "Contracts, History",
    "Scope", "Site", "Zoning", "Improvements", "Assessment",
    "Land Grid", "Land Valuation", "Land Comp Profiles",
    "Cost Approach Setup", "Sales Grid", "Sale Approach", "Sale Comp Profiles",
    "Income Approach", "Rent Roll Input", "Rent Roll Config", "Lease Grid",
    "Market Rent", "MF Market Rent", "Rent Comp Profiles",
    "Capitalization and Multipliers", "Investor Survey Input",
    "Investor Survey Output", "MF Lease Up", "DirectCapConclusion",
]

# ── Manual data for "File Info" (missing from v2) ─────────────────────
# Built from workbench_output/File_Info.csv extraction
FILE_INFO_FIELDS = [
    ("Subject ID", "User Entry", "LightBox/database record ID for the subject property (cell I13)", None, "Settings, Sales Grid, Lease Grid — used for API sync"),
    ("Office File / Number", "User Entry", "Internal file or job number (cell G15)", None, None),
    ("Due Date", "User Entry", "Project due date (cell I17)", None, None),
    ("Percent Complete", "User Entry", "Project completion percentage (cell I19)", None, None),
    ("Milestone", "User Entry", "Current project milestone (cell I21)", None, None),
    ("Workfile Location", "User Entry", "Path to project workfile (cell I23)", None, None),
    ("Project Notes", "User Entry", "Free-text project notes (cell I25)", None, None),
    ("Invoice Number", "User Entry", "Invoice reference number", None, None),
    ("Fee", "User Entry", "Primary appraisal fee amount", None, None),
    ("Fee 2", "User Entry", "Secondary fee amount", None, None),
    ("Inspection Fee", "User Entry", "Inspection fee amount", None, None),
    ("Contract Total", "Calculated", "Sum of fees", None, None),
    ("Retainer Fee", "User Entry", "Retainer amount", None, None),
    ("Expenses", "User Entry", "Expense amount", None, None),
    ("Invoice Date", "User Entry", "Date of invoice", None, None),
    ("Display Table Styles", "Dropdown", "Controls table formatting style for the workbook", "Yes | No", None),
    ("Approaches Utilized", "Calculated", "Which valuation approaches are active — reflects Settings toggles for Cost, Sales, Income", None, "Settings → Cost/Sales/Income approach toggles"),
    ("Property Name", "User Entry", "Subject property name → feeds N1PropertyName named range used across all tabs", None, "All tabs via N1PropertyName"),
    ("Property Major Type", "Calculated", "Reflects pvaPropertyTypeKey from Settings (e.g. Multi-Family)", None, "Settings → pvaPropertyTypeKey"),
    ("Property Type", "Calculated", "Subtype from Settings (e.g. Garden/Low-Rise)", None, "Settings → pvaPropertyTypeKeyDD"),
    ("Property Sub-Type", "User Entry", "Additional sub-classification", None, None),
    ("Existing or Proposed?", "Dropdown", "Whether subject is existing or proposed construction", "Existing | Proposed | Under Construction", "Settings → Is this a Proposed Property?"),
    ("Owner Name", "User Entry", "Property owner name", None, None),
    ("Address", "User Entry", "Street address → feeds N1Address, pvaSubjectFullAddress named ranges", None, "All tabs via N1Address"),
    ("City", "User Entry", "City → feeds N1DBCity", None, "All tabs"),
    ("County", "User Entry", "County → feeds N1DBCounty", None, "All tabs"),
    ("Country", "Dropdown", "Country (default: United States)", "United States | Canada", None),
    ("State Abbreviation", "Dropdown", "Two-letter state code → feeds N1DBState", "All US states + territories", "All tabs"),
    ("State Name", "Calculated", "Full state name derived from abbreviation", None, None),
    ("Zip Code", "User Entry", "Postal code → feeds N1DBZip", None, "All tabs"),
    ("Latitude", "User Entry", "GPS latitude → feeds N1DBLatitude for map charts", None, "Sale Approach, Land Comp maps"),
    ("Longitude", "User Entry", "GPS longitude → feeds N1DBLongitude for map charts", None, "Sale Approach, Land Comp maps"),
    ("Tax ID / APN", "User Entry", "Assessor parcel number(s)", None, "Assessment"),
    ("Year Built", "User Entry", "Year of original construction → feeds N1DBYear_Built", None, "Improvements, Sale Approach, Sales Grid"),
    ("Renovations", "User Entry", "Renovation year(s) → feeds N1DBRenovations", None, "Improvements, Sale Approach"),
    ("FIRREA Compliance Flag", "Dropdown", "Controls whether FIRREA sentence is included in Letter of Transmittal", "Yes | No", None),
    ("Client Information — Company Name", "User Entry", "Primary client company name", None, None),
    ("Client Information — Salutation / First / Middle / Last Name", "User Entry", "Client contact name fields", None, None),
    ("Client Information — Display Name", "Calculated", "Formatted name from component fields", None, None),
    ("Client Information — Title", "User Entry", "Client's title", None, None),
    ("Client Information — Address / City / State / Zip / Country", "User Entry", "Client mailing address fields", None, None),
    ("Client Information — Phone / Fax / Email / Website", "User Entry", "Client contact details", None, None),
    ("Second Client Information", "User Entry", "Optional second client — same fields as primary client", None, None),
    ("Property Contact — Company / Name / Address / Phone / Email", "User Entry", "On-site or property management contact details", None, None),
    ("Select Appraiser", "Dropdown", "Pulls from tblAppraisers list; auto-fills appraiser details below", "Appraiser list from tblAppraisers sheet", None),
    ("Appraiser — Display Name / First / Middle / Last", "Calculated", "Auto-populated from selected appraiser record", None, None),
    ("Appraiser — Title / Designation / Phone / Email", "Calculated", "Auto-populated from selected appraiser record", None, None),
    ("Appraiser — Certification State", "Dropdown", "State of appraiser certification", "All US states", None),
    ("Appraiser — Certification Type", "Dropdown", "Type of certification (Certified General, Licensed, etc.)", "Certified General | Licensed | Certified Residential | Trainee", None),
    ("Appraiser — Certification Number / Expiration", "User Entry", "License number and expiration date", None, None),
]

# ── Manual data for "Sale Approach" (missing from v2) ─────────────────
# Built from inspecting workbench_xlsb.xlsx Sales Approach sheet
SALE_APPROACH_FIELDS = [
    # (Field, Type, Description, Dropdown/Options, Cross-Tab)
    ("Comp Search Criteria", "Calculated", "Table of adjustment characteristics (Sales Status, Property Rights, Financing Terms, etc.) populated from tblPropTypeGridAdjustments; rows 7–21", None, "Settings → pvaPropertyTypeKey"),
    ("Filter Criteria (per characteristic)", "User Entry", "Free-text filter criteria for each search attribute (e.g. 'Within last 2 years', 'State of ***', '50 Pads or larger'). Column M user-input cells.", None, None),
    ("Comp Selected IDs", "Calculated", "CompsUsed / CompsSelectedIDs arrays — link which comps from Sales Grid are active on this grid", None, "Sales Grid → selected comp IDs"),
    ("Comparable N — Name / Address", "Calculated", "Property name and full address pulled from CompTableData via INDEX/MATCH on comp ID", None, "Sales Grid → CompTableData"),
    ("Comparable N — Sale Date", "Calculated", "Date of sale from comp data table", None, "Sales Grid → CompTableData"),
    ("Comparable N — Year Built / Renovations", "Calculated", "Year built and renovation year from comp data", None, "Sales Grid → CompTableData"),
    ("Comparable N — No. of Units", "Calculated", "Unit count from comp data (or rooms for Hotels)", None, "Sales Grid → CompTableData"),
    ("Comparable N — Occupancy Rate", "Calculated", "TOS Occupancy Rate from comp data", None, "Sales Grid → CompTableData"),
    ("Comparable N — Sale Price", "Calculated", "Transaction price from comp data", None, "Sales Grid → CompTableData"),
    ("Comparable N — Price per Unit", "Calculated", "Sale price ÷ units; formatted via pvaGridUOC_CurrencyFormat", None, "Sales Grid → CompTableData"),
    ("Comparable N — Cap Rate", "Calculated", "Cap rate from comp data (if available)", None, "Sales Grid → CompTableData"),
    ("Comparable N — Distance from Subject", "Calculated", "Great-circle distance computed via ACOS/COS/RADIANS from lat/lng coordinates", None, "Sales Grid → Lat/Lng; File Info → Subject Lat/Lng"),
    ("Subject Property Row", "Calculated", "Subject name, address, year built, unit count pulled from named ranges (N1PropertyName, pvaSubjectFullAddress, N1DBYear_Built)", None, "File Info, Settings, Improvements"),
    ("Map Data (N1_chtCompSummary)", "Calculated", "Geography, Label, Size, Color, ShowInMap, Address, Latitude, Longitude for each comp + subject; feeds embedded map chart", None, "Sales Grid → CompTableData; File Info → N1DBLatitude/Longitude"),
    ("Adjustment Factor Table", "Calculated", "For each characteristic row: Adjustment Factor name, Definition, and narrative Adjustments text. Pulled from tblPropTypeGridAdjustments and cross-referenced via INDEX/MATCH", None, "Settings → pvaPropertyTypeKey; Sales Grid"),
    ("Adjustment Percentages (per Comp × Characteristic)", "User Entry", "Percentage adjustments entered per comparable per characteristic (e.g. Sales Status +/- %, Location +/- %). Columns OQ–PA, rows matching each comp.", None, "Sales Grid"),
    ("Adjusted Price per Unit (per Comp)", "Calculated", "Base price × cumulative adjustment factor. Formula-driven from adjustment grid.", None, None),
    ("Net / Gross Adjustment %", "Calculated", "Sum of positive and negative adjustments; gross = absolute sum", None, None),
    ("Indicated Value (Price per Unit)", "Calculated", "Reconciled value from adjusted comparables; references OP287 formatted with pvaGridUOC_CurrencyFormat", None, None),
    ("Value Indication — Rounded", "Calculated", "Rounded final value indication for the sales comparison approach", None, "DirectCapConclusion"),
    ("Comp Search Criteria Visibility (Show/Hide)", "Calculated", "Row visibility controlled by formula: =1/((F=\"Show\")+(F<>\"Hide\")*(LEN(J)>1)). 'Auto' = show if filter criteria present.", None, "Settings → pvaPropertyTypeKey"),
    ("Property Type Show/Hide keys", "Calculated", "Column visibility routing based on pvaPropertyTypeKey — determines which columns display for each property type", None, "Settings → pvaPropertyTypeKey"),
    ("Include EGIM Analysis?", "Calculated", "Yes/No flag from tblPropertyTypeKey[hasEGIM_Analysis] based on pvaPropertyTypeKey. Controls EGIM section visibility.", None, "Settings → pvaPropertyTypeKey"),
    ("EGIM Comp Table (Hotels)", "Calculated", "Supplemental comp table for EGIM analysis: Name, City, State, Year Built, Rooms, Date, Price, Expense Ratio, Room Revenue, RevPAR, EGIM. Visible only for Lodging & Hospitality.", None, "Sales Grid → CompTableData"),
    ("EGIM Conclusion Narrative", "User Entry", "Free-text field: 'Enter custom sentence here.' for EGIM conclusion (cell TB480)", None, None),
    ("EGIM vs Expense Ratio Chart Data", "Calculated", "Chart data table with Expense Ratio and EGIM columns for scatter plot (N1_chtSaleEGIMvsExpRatioGraph)", None, None),
    ("GRRM Analysis (Lodging)", "Calculated", "Gross Room Revenue Multiplier analysis: rooms revenue projections across forecast years, deflated stabilized values. Visible only for Lodging property type.", None, "ProForma → revenue projections"),
    ("GRRM Value Indication — Rounded", "Calculated", "Rounded value from GRRM analysis", None, "DirectCapConclusion"),
    ("GRRM Less Capital Deduction", "Calculated", "Capital deduction applied to GRRM value", None, None),
    ("Reconciled Value (Sales Approach)", "Calculated", "Final reconciled value across Price/Unit, EGIM, and GRRM projections", None, "DirectCapConclusion"),
    ("Adjustments to Value — Lease Up", "Calculated", "Lease-up adjustment applied to indicated value. Show/Hide controlled by Auto flag.", None, "MF Lease Up"),
    ("Adjustments to Value — Deferred Maintenance", "Calculated", "Deferred maintenance deduction from indicated value", None, "Cost Approach Setup"),
    ("Market Sale Price Index (Sensitivity)", "Calculated", "Market rent growth change, cap rate sensitivity low/high analysis grid. Uses quarterly data from Geography-linked tables.", None, "Settings → Geography"),
    ("Listing Data Table", "User Entry", "Listing 1–6: Property Name, City, State, Time on Market, List Price. User-entered supplemental listing comparisons.", None, None),
    ("Comp Reliance Weights", "User Entry", "Reliance weighting per comparable (column TS). User-assigned weights for reconciliation.", None, None),
]


def load_v2_data():
    """Read all field rows from v2 reference, keyed by tab name."""
    wb = openpyxl.load_workbook(REF_V2, read_only=True)
    sheet = wb["📊 All Tabs — Field Detail"]

    tab_data = {}          # {tab_name: [(field, type, desc, dropdown_opts, cross_tab), ...]}
    current_tab = None

    for row in sheet.iter_rows(min_row=3, values_only=True):
        # col B = tab, C = field, D = type, E = desc, F = dropdown
        tab_raw = row[1]
        if tab_raw is None:
            continue
        tab = str(tab_raw).strip()
        # Skip section header rows (indented with spaces or dashes)
        if tab.startswith("──") or tab.startswith("  ") or tab == "":
            continue
        # Skip the title row
        if "All Tabs" in tab or tab == "Tab":
            continue

        field = str(row[2]).strip() if row[2] else ""
        ftype = str(row[3]).strip() if row[3] else ""
        desc  = str(row[4]).strip() if row[4] else ""
        dd    = str(row[5]).strip() if row[5] else ""

        # Normalize the tab name for matching
        # v2 uses "Income Approach Setup" but JIRA says "Income Approach"
        tab_key = tab
        if tab_key == "Income Approach Setup":
            tab_key = "Income Approach"

        if tab_key not in tab_data:
            tab_data[tab_key] = []

        if field and field != "None":
            tab_data[tab_key].append((field, ftype, desc, dd, ""))

    wb.close()
    return tab_data


def build_output(tab_data):
    """Create the polished Excel deliverable."""
    wb = openpyxl.Workbook()

    # ── Styles ─────────────────────────────────────────────────────────
    header_font  = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
    header_fill  = PatternFill("solid", fgColor="2F5496")
    tab_hdr_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
    tab_hdr_fill = PatternFill("solid", fgColor="4472C4")
    body_font    = Font(name="Calibri", size=10)
    alt_fill     = PatternFill("solid", fgColor="D6E4F0")
    thin_border  = Border(
        left=Side(style="thin", color="B4C6E7"),
        right=Side(style="thin", color="B4C6E7"),
        top=Side(style="thin", color="B4C6E7"),
        bottom=Side(style="thin", color="B4C6E7"),
    )
    wrap_align   = Alignment(wrap_text=True, vertical="top")

    # ── Sheet 1: All Tabs — Field Detail ──────────────────────────────
    ws = wb.active
    ws.title = "All Tabs — Field Detail"

    headers = ["#", "Tab", "Field / Label", "Type",
               "Description / Notes", "Dropdown Options / Linked Named Range",
               "Cross-Tab Dependency"]
    col_widths = [5, 22, 38, 14, 55, 50, 35]

    for c, (hdr, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=c, value=hdr)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(c)].width = w

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:G1"

    row_num = 2
    for tab_name in JIRA_TABS:
        # Tab section header row
        ws.cell(row=row_num, column=1, value="")
        for c in range(1, 8):
            cell = ws.cell(row=row_num, column=c)
            cell.fill = tab_hdr_fill
            cell.font = tab_hdr_font
            cell.border = thin_border
        ws.cell(row=row_num, column=2, value=f"▸ {tab_name}")
        ws.cell(row=row_num, column=2).alignment = Alignment(vertical="center")
        row_num += 1

        fields = tab_data.get(tab_name, [])
        if not fields:
            # Mark as pending investigation
            ws.cell(row=row_num, column=1, value=1)
            ws.cell(row=row_num, column=2, value=tab_name)
            ws.cell(row=row_num, column=3, value="(No field data — requires manual audit)")
            ws.cell(row=row_num, column=4, value="TBD")
            for c in range(1, 8):
                ws.cell(row=row_num, column=c).font = body_font
                ws.cell(row=row_num, column=c).border = thin_border
                ws.cell(row=row_num, column=c).alignment = wrap_align
            row_num += 1
            continue

        for idx, (field, ftype, desc, dd, xtab) in enumerate(fields, 1):
            ws.cell(row=row_num, column=1, value=idx)
            ws.cell(row=row_num, column=2, value=tab_name)
            ws.cell(row=row_num, column=3, value=field)
            ws.cell(row=row_num, column=4, value=ftype)
            ws.cell(row=row_num, column=5, value=desc)
            ws.cell(row=row_num, column=6, value=dd if dd and dd != "None" else "")
            ws.cell(row=row_num, column=7, value=xtab if xtab else "")

            # Alternate row shading
            fill = alt_fill if idx % 2 == 0 else PatternFill()
            for c in range(1, 8):
                cell = ws.cell(row=row_num, column=c)
                cell.font = body_font
                cell.fill = fill
                cell.border = thin_border
                cell.alignment = wrap_align

            row_num += 1

    # ── Sheet 2: Summary ──────────────────────────────────────────────
    ws2 = wb.create_sheet("Summary")
    sum_headers = ["Tab", "Total Fields", "User Entry", "Calculated", "Dropdown"]
    for c, hdr in enumerate(sum_headers, 1):
        cell = ws2.cell(row=1, column=c, value=hdr)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 14
    ws2.column_dimensions["C"].width = 14
    ws2.column_dimensions["D"].width = 14
    ws2.column_dimensions["E"].width = 14
    ws2.freeze_panes = "A2"

    r = 2
    grand = {"total": 0, "user": 0, "calc": 0, "dd": 0}
    for tab_name in JIRA_TABS:
        fields = tab_data.get(tab_name, [])
        total = len(fields)
        user  = sum(1 for f in fields if f[1] and "User" in f[1])
        calc  = sum(1 for f in fields if f[1] and "Calc" in f[1])
        dd    = sum(1 for f in fields if f[1] and "Drop" in f[1])

        ws2.cell(row=r, column=1, value=tab_name).font = body_font
        ws2.cell(row=r, column=2, value=total).font = body_font
        ws2.cell(row=r, column=3, value=user).font = body_font
        ws2.cell(row=r, column=4, value=calc).font = body_font
        ws2.cell(row=r, column=5, value=dd).font = body_font
        fill = alt_fill if r % 2 == 0 else PatternFill()
        for c in range(1, 6):
            ws2.cell(row=r, column=c).fill = fill
            ws2.cell(row=r, column=c).border = thin_border
            ws2.cell(row=r, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left", vertical="center")

        grand["total"] += total
        grand["user"]  += user
        grand["calc"]  += calc
        grand["dd"]    += dd
        r += 1

    # Grand total row
    for c, val in enumerate(["TOTAL", grand["total"], grand["user"], grand["calc"], grand["dd"]], 1):
        cell = ws2.cell(row=r, column=c, value=val)
        cell.font = Font(name="Calibri", bold=True, size=11)
        cell.fill = PatternFill("solid", fgColor="D9E2F3")
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center" if c > 1 else "left", vertical="center")

    # ── Save ──────────────────────────────────────────────────────────
    wb.save(OUTPUT)
    print(f"\n✅  Deliverable saved: {OUTPUT}")
    print(f"    Sheet 1: 'All Tabs — Field Detail' — {row_num - 2} data rows across {len(JIRA_TABS)} tabs")
    print(f"    Sheet 2: 'Summary' — field count breakdown")
    print(f"    Grand total: {grand['total']} fields ({grand['user']} User Entry, {grand['calc']} Calculated, {grand['dd']} Dropdown)")


def main():
    print("Loading existing reference data from v2...")
    tab_data = load_v2_data()
    print(f"  Loaded {len(tab_data)} tabs from reference v2")
    for t, fields in sorted(tab_data.items()):
        print(f"    {t}: {len(fields)} fields")

    # Inject "File Info" data
    tab_data["File Info"] = [
        (f, t, d, dd if dd else "", xt if xt else "")
        for f, t, d, dd, xt in FILE_INFO_FIELDS
    ]
    print(f"  Added File Info: {len(FILE_INFO_FIELDS)} fields (from CSV extraction)")

    # Inject "Sale Approach" data
    tab_data["Sale Approach"] = [
        (f, t, d, dd if dd else "", xt if xt else "")
        for f, t, d, dd, xt in SALE_APPROACH_FIELDS
    ]
    print(f"\n  Added Sale Approach: {len(SALE_APPROACH_FIELDS)} fields (from manual inspection)")

    # Verify all JIRA tabs are covered
    missing = [t for t in JIRA_TABS if t not in tab_data]
    if missing:
        print(f"\n⚠️  Still missing: {missing}")
    else:
        print(f"\n✅  All {len(JIRA_TABS)} JIRA tabs covered!")

    print("\nBuilding output workbook...")
    build_output(tab_data)


if __name__ == "__main__":
    main()
