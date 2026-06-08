"""
field_mapping_tool.py
=====================
Reads Retail_Entity.csv, semantically aligns fields across all sources
(ERD, CoStar, GreenST, Trepp — or any columns you add) for every entity,
and writes everything into a SINGLE "Master Field Mapping" tab in Google Sheets.

Colour legend:
  🟢 GREEN  – 2+ sources share the same semantic concept (full match)
  🟡 YELLOW – field in only one source but belongs to a known synonym group
  ⬜ WHITE  – unmatched / unique field
  🔵 BLUE header rows per entity group

USAGE
-----
  python field_mapping_tool.py                # full run (CSV + Sheets)
  python field_mapping_tool.py --local-only   # CSV only, skip Sheets
  python field_mapping_tool.py --entities Geography Property  # filter entities

ADDING MORE DATA LATER
-----------------------
  • New company/source  → add a new column in the CSV. Script auto-detects it.
  • New entity          → add new rows under a new entity name in col A.
  • New synonym rule    → append a frozenset to SYNONYM_GROUPS below.
  Re-run the script; it always rebuilds everything from scratch.
"""

import re, sys, time, argparse, json, os
import pandas as pd
from collections import defaultdict, OrderedDict

# ── CONFIGURE THESE THREE LINES ──────────────────────────────────────────────
CSV_FILE       = "Retail_Entity.csv"
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"   # alphanumeric ID from sheet URL
CREDS_FILE     = "service_account.json"
# ─────────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════
#  SYNONYM DICTIONARY  –  add new frozensets freely at the bottom
# ═══════════════════════════════════════════════════════════════════════════
SYNONYM_GROUPS: list[frozenset] = [
    # identifiers
    frozenset({"propertyid","property_id","parcelid","parcel_id","propid","prop_id","fileid","file_id"}),
    frozenset({"geographyid","geography_id","geoid","geo_id"}),
    frozenset({"projectid","project_id"}),
    frozenset({"improvementid","improvement_id","buildingid","building_id"}),
    frozenset({"salecompid","sale_comp_id","leasecompid","lease_comp_id","rentcompid","rent_comp_id"}),

    # names
    frozenset({"propertyname","property_name","propname","prop_name","name","assetname","asset_name"}),
    frozenset({"projectname","project_name"}),
    frozenset({"clientname","client_name"}),
    frozenset({"geoname","geo_name","geographyname","geography_name","submarket_name","submarketname"}),
    frozenset({"districtname","district_name"}),
    frozenset({"tenantname","tenant_name"}),
    frozenset({"lessorname","lessor_name"}),

    # address / location
    frozenset({"address","propertyaddress","property_address","parceladdress","parcel_address","streetaddress","street_address"}),
    frozenset({"city","cityname","city_name"}),
    frozenset({"state","statename","state_name","statecode","state_code"}),
    frozenset({"county","countyname","county_name"}),
    frozenset({"zip","zipcode","zip_code","postalcode","postal_code"}),
    frozenset({"msa","msaname","msa_name","cbsa","cbsacode","cbsa_code","metroname","metro_name"}),
    frozenset({"lat","latitude","latcentroid","lat_centroid"}),
    frozenset({"lng","lon","longitude","lngcentroid","lng_centroid"}),
    frozenset({"country","countryname","country_name"}),
    frozenset({"continent","continentname"}),

    # property type
    frozenset({"propertytype","property_type","proptype","prop_type","assettype","asset_type"}),
    frozenset({"propertysubtype","property_subtype","subtype","sub_type","propertysubtype2"}),
    frozenset({"majortype","major_type","propertyclass","property_class","propertyclassname","property_class_name"}),

    # ownership / appraisal
    frozenset({"owner","ownername","owner_name","parcelowner","parcel_owner"}),
    frozenset({"appraisalfile","appraisal_file","parcelappraisalfile","parcel_appraisalfile"}),
    frozenset({"appraisalusage","appraisal_usage"}),

    # dates / timestamps
    frozenset({"createdat","created_at","creationdate","creation_date","datecreated","date_created",
               "ingestiontimestamp","ingestion_timestamp","mergetimestamp","merge_timestamp","addedatdate","added_at"}),
    frozenset({"updatedat","updated_at","updatedate","update_date","dateupdated","date_updated"}),
    frozenset({"createdby","created_by","createdbyuserid","created_by_user_id","createdbyuser"}),
    frozenset({"updatedby","updated_by","updatedbyuserid","updated_by_user_id"}),
    frozenset({"dataloaddate","data_load_date","stmtfiledate","stmt_file_date","dataupdatedate","data_update_date"}),
    frozenset({"stmtbegindate","stmt_begin_date","leasestartdate","lease_start_date","startdate","start_date","sessionstart","session_start"}),
    frozenset({"stmtenddate","stmt_end_date","leaseenddate","lease_end_date","leaseexpiredate","lease_expiration_date","enddate","end_date","sessionend","session_end"}),

    # building / improvement
    frozenset({"yearbuilt","year_built","yrbuilt","yr_built","constructiondate","construction_date"}),
    frozenset({"yearrenovated","year_renovated","monthrenovated","month_renovated"}),
    frozenset({"noofstories","no_of_stories","numberofstories","number_of_stories","numstories","stories"}),
    frozenset({"noofunits","no_of_units","numberofunits","number_of_units","propunits","prop_units","unitcount","unit_count"}),
    frozenset({"gba","gbatotal","gba_total","grossbuildingarea","gross_building_area","propqft","prop_sqft",
               "rba","totalsf","total_sf","inventorysf","inventory_sf","squarefeet","square_feet","sqft"}),
    frozenset({"parkingspaces","parking_spaces","noofparkingspaces","no_of_parking_spaces","numberofparkingspaces"}),
    frozenset({"constructionclass","construction_class","buildingclass","building_class","constructiontype","construction_type"}),
    frozenset({"noofrooms","no_of_rooms","numberofrooms","number_of_rooms"}),
    frozenset({"noofbeds","no_of_beds","noofbedrooms","no_of_bedrooms","numberofbedrooms","number_of_bedrooms"}),
    frozenset({"noofbathrooms","no_of_bathrooms","numberofbathrooms","number_of_bathrooms","noofbaths","no_of_baths"}),

    # occupancy / vacancy
    frozenset({"occupancy","occupancyrate","occupancy_rate","occrate","occ_rate","stmtoccrate","stmt_occ_rate",
               "mroccrate","mr_occ_rate","calcoccrate","calc_occ_rate","percentleased","percent_leased"}),
    frozenset({"occupancydate","occupancy_date","occdate","occ_date","mroccdt","mr_occdt","calcoccdt","calc_occdt"}),
    frozenset({"vacancyrate","vacancy_rate","vacantrate","vacant_rate","commvacancyrate","comm_vacancy_rate"}),

    # financials
    frozenset({"income","noi","netoperatingincome","net_operating_income","noiindex","noi_index"}),
    frozenset({"baserent","base_rent","baserentpersf","base_rent_sf","rentpersf","rent_per_sf","avgrent","avg_rent"}),
    frozenset({"percentrent","percent_rent"}),
    frozenset({"expensereimbursements","expense_reimbursements"}),
    frozenset({"totalexpenses","total_expenses","buildingoperatingexpenses","building_operating_expenses"}),
    frozenset({"buildingtax","building_tax","taxexpense","tax_expense","taxestotal","taxes_total","buildingtaxexpenses","building_tax_expenses"}),

    # geography stats
    frozenset({"population","pop","populationcount","population_count"}),
    frozenset({"medianhhincome","median_hh_income","medianhouseholdincome","median_household_income","medianincome"}),
    frozenset({"medianhomevalue","median_home_value"}),
    frozenset({"geosubtype","geo_subtype","geotype","geo_type","geographytype","geography_type"}),
    frozenset({"geocode","geo_code","geographycode","geography_code","geoidentifier"}),
    frozenset({"parentgeoid","parent_geo_id","parentgeo","parent_geo"}),

    # flood / environmental
    frozenset({"floodzone","flood_zone","femafloodzone","fema_flood_zone"}),
    frozenset({"floodmappanel","flood_map_panel","femamapidentifier","fema_map_identifier",
               "firmid","firm_id","firmpanelnumber","firm_panel_number"}),
    frozenset({"femamapdate","fema_map_date"}),

    # land / site
    frozenset({"landuse","land_use"}),
    frozenset({"landarea","land_area","siteacres","site_acres","landsf","land_sf","landareaac","landareaacres"}),
    frozenset({"landunits","land_units","allowableunits","allowable_units"}),
    frozenset({"zoningcode","zoning_code","zoningdesignation","zoning_designation","zoningdistrict","zoning_district"}),

    # sale
    frozenset({"saleprice","sale_price","salesprice","sales_price","totalsaleprice","total_sale_price"}),
    frozenset({"saledate","sale_date","transactiondate","transaction_date","closingdate","closing_date"}),
    frozenset({"priceperunit","price_per_unit","priceperroom","price_per_room"}),
    frozenset({"pricepersf","price_per_sf","priceperfoot","price_per_foot"}),

    # lease
    frozenset({"leasetype","lease_type"}),
    frozenset({"leasetermmonths","lease_term_months","leasedurationmonths"}),
    frozenset({"unitsf","unit_sf","leasedarea","leased_area"}),

    # status / meta
    frozenset({"status","projectstatus","project_status","buildingstatus","building_status"}),
    frozenset({"isactive","is_active","active"}),
    frozenset({"datasource","data_source","source","sourcesystem","source_system"}),
    frozenset({"reportingyear","reporting_year","taxyear","tax_year"}),
    frozenset({"customfields","custom_fields"}),
    frozenset({"notes","comments","description","remarks"}),
]


# ═══════════════════════════════════════════════════════════════════════════
#  NORMALISATION
# ═══════════════════════════════════════════════════════════════════════════
_PREFIXES = ("parcel","property","prop","geo","geography",
             "stmt","mf","comm","calc","mr","building",
             "leasecomp","salecomp","rentcomp")

def normalize(field: str) -> str:
    if not field or isinstance(field, float):
        return ""
    s = str(field).lower().strip()
    s = re.sub(r"[\s_\-]+", "", s)
    for prefix in sorted(_PREFIXES, key=len, reverse=True):
        if s.startswith(prefix) and len(s) > len(prefix):
            s = s[len(prefix):]
            break
    return s

def build_synonym_map() -> dict:
    lookup = {}
    for group in SYNONYM_GROUPS:
        canonical = max(group, key=lambda x: (x.count("_"), len(x)))
        for term in group:
            n = normalize(term)
            if n and n not in lookup:
                lookup[n] = canonical
    return lookup

def semantic_key(field: str, syn_map: dict) -> str:
    if not field:
        return ""
    return syn_map.get(normalize(field), normalize(field))


# ═══════════════════════════════════════════════════════════════════════════
#  CSV PARSING  (FIX: handles duplicate entity names + trailing spaces)
# ═══════════════════════════════════════════════════════════════════════════
def parse_csv(filepath: str):
    df = pd.read_csv(filepath, header=0, dtype=str).fillna("")
    entity_col  = df.columns[0]
    source_cols = list(df.columns[1:])

    entities: OrderedDict = OrderedDict()
    current = None

    for _, row in df.iterrows():
        ename = str(row[entity_col]).strip()
        if ename and ename.lower() not in ("nan", "none", ""):
            current = ename
            # FIX: don't overwrite if entity already seen — extend instead
            if current not in entities:
                entities[current] = {sc: [] for sc in source_cols}

        if current is None:
            continue

        for sc in source_cols:
            val = str(row[sc]).strip()
            if val and val.lower() not in ("nan", "none", ""):
                entities[current][sc].append(val)

    return entities, source_cols


# ═══════════════════════════════════════════════════════════════════════════
#  SEMANTIC ALIGNMENT
# ═══════════════════════════════════════════════════════════════════════════
def align_entity(sources: dict, source_cols: list, syn_map: dict) -> list:
    groups: dict = defaultdict(lambda: defaultdict(list))

    for sc in source_cols:
        for field in sources.get(sc, []):
            key = semantic_key(field, syn_map)
            groups[key][sc].append(field)

    rows = []
    for key, src_map in groups.items():
        row = {"semantic_key": key}
        for sc in source_cols:
            vals = src_map.get(sc, [])
            row[sc] = " | ".join(vals) if vals else ""
        filled = sum(1 for sc in source_cols if row[sc])
        row["match_count"] = filled
        if filled >= 2:
            row["match_type"] = "full"
        elif key in syn_map.values():
            row["match_type"] = "partial"
        else:
            row["match_type"] = "unmatched"
        rows.append(row)

    order = {"full": 0, "partial": 1, "unmatched": 2}
    rows.sort(key=lambda r: (order[r["match_type"]], r["semantic_key"]))
    return rows


# ═══════════════════════════════════════════════════════════════════════════
#  HELPER: collapse consecutive same-type rows into range strings
#  e.g. rows 2,3,4 all "full" → "A2:F4"  (one API call instead of three)
# ═══════════════════════════════════════════════════════════════════════════
def _col_letter(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result

def _group_row_ranges(row_meta: list, last_col: str) -> dict:
    """
    row_meta: list of match_type strings (index 0 = row 1 in sheet).
    Returns { match_type: ["A2:F5", "A9:F11", ...] }
    """
    ranges = defaultdict(list)
    i = 0
    while i < len(row_meta):
        mt = row_meta[i]
        j = i
        while j < len(row_meta) and row_meta[j] == mt:
            j += 1
        # sheet rows are 1-indexed and we start after the header (row 1)
        start_row = i + 2
        end_row   = j + 1
        ranges[mt].append(f"A{start_row}:{last_col}{end_row}")
        i = j
    return dict(ranges)


# ═══════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS WRITER  (single master sheet, all fixes applied)
# ═══════════════════════════════════════════════════════════════════════════
def write_to_sheets(spreadsheet_id, creds_file, entities, source_cols, syn_map,
                    batch_sleep=1.2):
    try:
        import gspread
        from gspread_formatting import CellFormat, Color, TextFormat, format_cell_range, set_frozen
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        sys.exit(f"Missing dependency: {e}\nRun: pip install gspread gspread-formatting google-auth")

    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds  = Credentials.from_service_account_file(creds_file, scopes=scopes)
    client = gspread.authorize(creds)
    sh     = client.open_by_key(spreadsheet_id)

    # ── colour palette ───────────────────────────────────────────────────
    C_HEADER      = CellFormat(backgroundColor=Color(0.204, 0.396, 0.643),
                               textFormat=TextFormat(bold=True, foregroundColor=Color(1,1,1)),
                               horizontalAlignment="CENTER")
    C_ENTITY_HDR  = CellFormat(backgroundColor=Color(0.851, 0.918, 0.965),
                               textFormat=TextFormat(bold=True, foregroundColor=Color(0.1,0.1,0.4)))
    C_FULL        = CellFormat(backgroundColor=Color(0.839, 0.953, 0.827))
    C_PARTIAL     = CellFormat(backgroundColor=Color(1.000, 0.976, 0.816))
    C_WHITE       = CellFormat(backgroundColor=Color(1, 1, 1))
    C_BOLD        = CellFormat(textFormat=TextFormat(bold=True))

    total_cols   = len(source_cols) + 2   # Entity + Semantic Concept + sources
    last_col_ltr = _col_letter(total_cols)
    headers      = ["Entity", "Semantic Concept"] + source_cols

    # ── build full data grid ─────────────────────────────────────────────
    grid      = [headers]
    row_meta  = []          # "entity_header" | "full" | "partial" | "unmatched"
    entity_header_rows = [] # 1-based sheet row indices of entity separators

    print(f"   Building grid for {len(entities)} entities …")
    for entity_name, sources in entities.items():
        aligned = align_entity(sources, source_cols, syn_map)
        if not aligned:
            continue

        # entity separator row (light blue, bold, merged-looking)
        sep_row = [entity_name] + [""] * (total_cols - 1)
        grid.append(sep_row)
        entity_header_rows.append(len(grid))   # 1-based
        row_meta.append("entity_header")

        for r in aligned:
            grid.append(["", r["semantic_key"]] + [r.get(sc, "") for sc in source_cols])
            row_meta.append(r["match_type"])

    total_rows = len(grid)
    print(f"   Grid size: {total_rows} rows × {total_cols} cols")

    # ── get or create the single worksheet ──────────────────────────────
    sheet_title = "Master Field Mapping"
    try:
        ws = sh.worksheet(sheet_title)
        ws.clear()
        # resize if needed
        if ws.row_count < total_rows + 5:
            ws.resize(rows=total_rows + 50)
    except gspread.WorksheetNotFound:
        # FIX: dynamic row count instead of hardcoded 1000
        ws = sh.add_worksheet(title=sheet_title,
                               rows=total_rows + 50,
                               cols=total_cols + 2)

    # ── write values (gspread 6.x compatible syntax) ─────────────────────
    # FIX: use positional args — gspread 6.x changed keyword arg names
    ws.update("A1", grid, value_input_option="RAW")
    time.sleep(batch_sleep)
    print("   Values written. Applying formatting …")

    # ── formatting: group consecutive same-type rows → fewer API calls ───
    # FIX: batch by range group, not row-by-row, to avoid rate limits
    grouped = _group_row_ranges(row_meta, last_col_ltr)

    # header row
    format_cell_range(ws, f"A1:{last_col_ltr}1", C_HEADER)
    time.sleep(0.5)

    # entity separator rows
    for row_num in entity_header_rows:
        format_cell_range(ws, f"A{row_num}:{last_col_ltr}{row_num}", C_ENTITY_HDR)
    time.sleep(batch_sleep)

    # data rows by match type (one call per contiguous block)
    for mt, ranges in grouped.items():
        if mt == "entity_header":
            continue
        fmt = {"full": C_FULL, "partial": C_PARTIAL, "unmatched": C_WHITE}[mt]
        for rng in ranges:
            format_cell_range(ws, rng, fmt)
        time.sleep(0.3)

    # bold col B (Semantic Concept) for data rows
    format_cell_range(ws, f"B2:B{total_rows}", C_BOLD)
    time.sleep(0.3)

    # FIX: set_frozen signature is (worksheet, rows, cols)
    set_frozen(ws, rows=1, cols=2)

    print(f"   ✅  {total_rows-1} data rows written to '{sheet_title}'.")
    full_count    = row_meta.count("full")
    partial_count = row_meta.count("partial")
    print(f"       🟢 {full_count} full matches  🟡 {partial_count} partial  "
          f"⬜ {row_meta.count('unmatched')} unmatched")


# ═══════════════════════════════════════════════════════════════════════════
#  LOCAL CSV EXPORT
# ═══════════════════════════════════════════════════════════════════════════
def export_to_csv(out_path, entities, source_cols, syn_map):
    all_rows = []
    col_names = ["Entity", "Semantic Concept"] + source_cols + ["Match Type"]
    for entity_name, sources in entities.items():
        for r in align_entity(sources, source_cols, syn_map):
            all_rows.append(
                [entity_name, r["semantic_key"]]
                + [r.get(sc, "") for sc in source_cols]
                + [r["match_type"]]
            )
    pd.DataFrame(all_rows, columns=col_names).to_csv(out_path, index=False)
    print(f"   ✅  Local CSV → {os.path.abspath(out_path)}")


# ═══════════════════════════════════════════════════════════════════════════
#  PRE-FLIGHT CHECKS
# ═══════════════════════════════════════════════════════════════════════════
def preflight_check(spreadsheet_id, creds_file) -> list:
    problems = []
    if not spreadsheet_id or spreadsheet_id == "YOUR_SPREADSHEET_ID_HERE":
        problems.append(
            "SPREADSHEET_ID is not set.\n"
            "  Copy the ID from your sheet URL:\n"
            "  https://docs.google.com/spreadsheets/d/<ID_HERE>/edit"
        )
    elif "/" in spreadsheet_id or "#" in spreadsheet_id:
        problems.append(
            f"SPREADSHEET_ID looks like a full URL.\n"
            f"  Got: {spreadsheet_id}\n"
            "  Paste only the alphanumeric part between /d/ and /edit"
        )
    if not os.path.isfile(creds_file):
        problems.append(
            f"Service-account key not found: '{creds_file}'\n"
            "  Download from: Cloud Console → IAM → Service Accounts → Keys → JSON"
        )
    else:
        try:
            sa    = json.load(open(creds_file))
            email = sa.get("client_email", "")
            if email:
                print(f"\n   Service account email : {email}")
                print( "   ↑ This email MUST have Editor access on your Google Sheet.\n"
                       "     Sheet → Share → paste email → Editor → Send\n")
            else:
                problems.append(f"'{creds_file}' missing 'client_email'. Re-download the JSON key.")
        except json.JSONDecodeError:
            problems.append(f"'{creds_file}' is not valid JSON. Re-download the key.")
    return problems


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Semantic field mapper → single Google Sheet")
    parser.add_argument("--local-only", action="store_true",
                        help="Produce CSV only; skip Google Sheets")
    parser.add_argument("--entities", nargs="*", metavar="ENTITY",
                        help='Filter to specific entities, e.g. --entities Geography Property')
    args = parser.parse_args()

    print("▶  Parsing CSV …")
    entities, source_cols = parse_csv(CSV_FILE)
    print(f"   Entities found : {len(entities)}  {list(entities.keys())}")
    print(f"   Source columns : {source_cols}")

    if args.entities:
        wanted   = {e.lower() for e in args.entities}
        entities = {k: v for k, v in entities.items() if k.lower() in wanted}
        print(f"   Filtered to    : {list(entities.keys())}")
        if not entities:
            sys.exit("❌  No matching entities found. Check spelling.")

    syn_map = build_synonym_map()
    print(f"   Synonym tokens : {len(syn_map)}")

    out_csv = "field_mapping_output.csv"
    export_to_csv(out_csv, entities, source_cols, syn_map)

    if args.local_only:
        print("\n--local-only flag set. Done.")
        return

    print("\n▶  Pre-flight checks …")
    problems = preflight_check(SPREADSHEET_ID, CREDS_FILE)
    if problems:
        print("\n❌  Fix these issues before connecting to Google Sheets:\n")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}\n")
        print("Tip: run with --local-only to skip Sheets and just produce the CSV.")
        sys.exit(1)

    print("\n▶  Writing to Google Sheets …")
    try:
        write_to_sheets(SPREADSHEET_ID, CREDS_FILE, entities, source_cols, syn_map)
        print("\n✅  All done!")
    except Exception as e:
        err = str(e)
        print(f"\n❌  Error: {err[:400]}")
        if "unable to open" in err.lower() or "404" in err or "[-1]" in err:
            print("\n  ↳ The sheet can't be opened. Check:\n"
                  "    1. SPREADSHEET_ID is the ID only (not the full URL)\n"
                  "    2. The service-account email has Editor access on the sheet\n"
                  "    3. Google Sheets API + Drive API are enabled in Cloud Console")
        elif "403" in err or "PERMISSION_DENIED" in err:
            print("\n  ↳ Permission denied. Enable Google Sheets API and Drive API\n"
                  "    in your Google Cloud project, then re-share the sheet.")
        elif "invalid_grant" in err:
            print("\n  ↳ Auth token invalid. Re-download the service-account JSON key.")
        sys.exit(1)

if __name__ == "__main__":
    main()
