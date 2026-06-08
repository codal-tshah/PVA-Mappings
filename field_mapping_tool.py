"""
field_mapping_tool.py
=====================
Reads Retail_Entity.csv, semantically aligns fields across sources
(ERD, CoStar, GreenST, Trepp) for each entity, and writes the result
to Google Sheets with colour-coded match highlighting.

Colour legend written to every sheet:
  🟢 GREEN  – 2+ sources share the same semantic concept (full match)
  🟡 YELLOW – field appears in only one source but has a known synonym group
  ⬜ WHITE  – unmatched / unique field

HOW TO RUN
----------
1.  pip install gspread gspread-formatting google-auth pandas
2.  Create a Google Cloud service-account, download the JSON key.
3.  Share your target Google Sheet with the service-account e-mail
    (Editor permission).
4.  Fill in the three constants below (CSV_FILE, SPREADSHEET_ID, CREDS_FILE).
5.  python field_mapping_tool.py

ADDING MORE ENTITIES / SOURCES LATER
--------------------------------------
- The CSV is the single source of truth. Add new entity rows or new
  source columns there; the script auto-detects them on next run.
- To add extra synonym rules, append a new frozenset to SYNONYM_GROUPS.
"""

import re
import sys
import time
import pandas as pd
from collections import defaultdict, OrderedDict

# ── CONFIGURE THESE ──────────────────────────────────────────────────────────
CSV_FILE        = "Industrial Entity.csv"          # path to your CSV
SPREADSHEET_ID  = "1A0r_FoNvFatX8w2NOqXGxeqcJdtxXSoD-IlrRCO0ZFc"   # from the sheet URL
CREDS_FILE      = "service_account.json"        # Google service-account key
OUTPUT_CSV_FILE = "Industrial_Entity_Output.csv"  # local Excel output (optional)
SHEET_TITLE = "Industrial Entity Mappings"                 # name of the sheet tab to create/update
# email = pva-gsheet@codal-iq-v2.iam.gserviceaccount.com
# ─────────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════
#  SYNONYM DICTIONARY  –  extend freely
# ═══════════════════════════════════════════════════════════════════════════
SYNONYM_GROUPS: list[frozenset] = [
    # ── identifiers ──────────────────────────────────────────────────────
    frozenset({"propertyid", "property_id", "parcelid", "parcel_id",
               "propid", "prop_id", "fileid", "file_id"}),
    frozenset({"geographyid", "geography_id", "geoid", "geo_id"}),
    frozenset({"projectid", "project_id"}),
    frozenset({"improvementid", "improvement_id", "buildingid", "building_id"}),

    # ── names / descriptions ─────────────────────────────────────────────
    frozenset({"propertyname", "property_name", "propname", "prop_name",
               "name", "assetname", "asset_name"}),
    frozenset({"projectname", "project_name"}),
    frozenset({"clientname", "client_name"}),
    frozenset({"geoname", "geo_name", "geographyname", "geography_name",
               "submarket_name", "submarketname"}),
    frozenset({"districtname", "district_name"}),

    # ── address / location ───────────────────────────────────────────────
    frozenset({"address", "propertyaddress", "property_address",
               "parceladdress", "parcel_address", "streetaddress",
               "street_address"}),
    frozenset({"city", "cityname", "city_name"}),
    frozenset({"state", "statename", "state_name", "statecode", "state_code"}),
    frozenset({"county", "countyname", "county_name"}),
    frozenset({"zip", "zipcode", "zip_code", "postalcode", "postal_code"}),
    frozenset({"msa", "msaname", "msa_name", "cbsa", "cbsacode", "cbsa_code",
               "metroname", "metro_name"}),
    frozenset({"lat", "latitude", "latcentroid", "lat_centroid"}),
    frozenset({"lng", "lon", "longitude", "lngcentroid", "lng_centroid"}),
    frozenset({"country", "countryname", "country_name"}),
    frozenset({"continent", "continentname"}),

    # ── property type ─────────────────────────────────────────────────────
    frozenset({"propertytype", "property_type", "proptype", "prop_type",
               "assettype", "asset_type"}),
    frozenset({"propertysubtype", "property_subtype", "subtype", "sub_type",
               "propertysubtype2"}),
    frozenset({"majortype", "major_type", "propertyclass", "property_class",
               "propertyclassname", "property_class_name"}),

    # ── ownership ─────────────────────────────────────────────────────────
    frozenset({"owner", "ownername", "owner_name", "parcelowner",
               "parcel_owner"}),

    # ── appraisal ─────────────────────────────────────────────────────────
    frozenset({"appraisalfile", "appraisal_file", "parcelappraisalfile",
               "parcel_appraisalfile"}),
    frozenset({"appraisalusage", "appraisal_usage"}),

    # ── dates / timestamps ───────────────────────────────────────────────
    frozenset({"createdat", "created_at", "creationdate", "creation_date",
               "datecreated", "date_created", "ingestiontimestamp",
               "ingestion_timestamp", "mergetimestamp", "merge_timestamp",
               "addedatdate", "added_at"}),
    frozenset({"updatedat", "updated_at", "updatedate", "update_date",
               "dateupdated", "date_updated"}),
    frozenset({"createdby", "created_by", "createdbyuserid",
               "created_by_user_id", "createdbyuser"}),
    frozenset({"updatedby", "updated_by", "updatedbyuserid",
               "updated_by_user_id"}),
    frozenset({"dataloaddate", "data_load_date", "stmtfiledate",
               "stmt_file_date", "dataupdatedate", "data_update_date"}),
    frozenset({"stmtbegindate", "stmt_begin_date", "leasestartdate",
               "lease_start_date", "startdate", "start_date",
               "leasestartdate", "sessionstart", "session_start"}),
    frozenset({"stmtenddate", "stmt_end_date", "leaseenddate",
               "lease_end_date", "leaseexpiredate", "lease_expiration_date",
               "enddate", "end_date", "sessionend", "session_end"}),

    # ── building / improvement ───────────────────────────────────────────
    frozenset({"yearbuilt", "year_built", "yrbuilt", "yr_built",
               "constructiondate", "construction_date"}),
    frozenset({"yearrenovated", "year_renovated", "monthrenovated",
               "month_renovated"}),
    frozenset({"noofstories", "no_of_stories", "numberofstories",
               "number_of_stories", "numstories", "stories"}),
    frozenset({"noofunits", "no_of_units", "numberofunits",
               "number_of_units", "propunits", "prop_units",
               "unitcount", "unit_count"}),
    frozenset({"gba", "gbatotal", "gba_total", "grossbuildingarea",
               "gross_building_area", "propqft", "prop_sqft",
               "rba", "totalsf", "total_sf", "inventorysf", "inventory_sf",
               "squarefeet", "square_feet", "sqft"}),
    frozenset({"parkingspaces", "parking_spaces", "noofparkingspaces",
               "no_of_parking_spaces", "numberofparkingspaces"}),
    frozenset({"buildingtax", "building_tax", "taxexpense", "tax_expense",
               "taxestotal", "taxes_total", "buildingtaxexpenses",
               "building_tax_expenses"}),
    frozenset({"constructionclass", "construction_class",
               "buildingclass", "building_class", "constructiontype",
               "construction_type"}),
    frozenset({"noofrooms", "no_of_rooms", "numberofrooms",
               "number_of_rooms"}),
    frozenset({"noofbeds", "no_of_beds", "noofbedrooms", "no_of_bedrooms",
               "numberofbedrooms", "number_of_bedrooms"}),
    frozenset({"noofbathrooms", "no_of_bathrooms", "numberofbathrooms",
               "number_of_bathrooms", "noofbaths", "no_of_baths"}),

    # ── occupancy / vacancy ──────────────────────────────────────────────
    frozenset({"occupancy", "occupancyrate", "occupancy_rate",
               "occrate", "occ_rate", "stmtoccrate", "stmt_occ_rate",
               "mroccrate", "mr_occ_rate", "calcoccrate", "calc_occ_rate",
               "percentleased", "percent_leased"}),
    frozenset({"occupancydate", "occupancy_date", "occdate", "occ_date",
               "mroccdt", "mr_occdt", "calcoccdt", "calc_occdt"}),
    frozenset({"vacancyrate", "vacancy_rate", "vacantrate", "vacant_rate",
               "commvacancyrate", "comm_vacancy_rate"}),

    # ── financials ───────────────────────────────────────────────────────
    frozenset({"income", "noi", "netoperatingincome",
               "net_operating_income", "noiindex", "noi_index"}),
    frozenset({"baserent", "base_rent", "baserentpersf", "base_rent_sf",
               "rentpersf", "rent_per_sf", "avgrent", "avg_rent"}),
    frozenset({"percentrent", "percent_rent"}),
    frozenset({"expensereimbursements", "expense_reimbursements"}),
    frozenset({"totalexpenses", "total_expenses",
               "buildingoperatingexpenses", "building_operating_expenses"}),
    frozenset({"taxexpense", "tax_expense", "taxestotal", "taxes_total"}),

    # ── geography stats ──────────────────────────────────────────────────
    frozenset({"population", "pop", "populationcount", "population_count"}),
    frozenset({"medianhhincome", "median_hh_income", "medianhouseholdincome",
               "median_household_income", "medianincome"}),
    frozenset({"medianhomevalue", "median_home_value"}),
    frozenset({"geosubtype", "geo_subtype", "geotype", "geo_type",
               "geographytype", "geography_type"}),
    frozenset({"geocode", "geo_code", "geographycode", "geography_code",
               "geoidentifier"}),
    frozenset({"parentgeoid", "parent_geo_id", "parentgeo", "parent_geo"}),

    # ── flood / environmental ────────────────────────────────────────────
    frozenset({"floodzone", "flood_zone", "femafloodzone",
               "fema_flood_zone"}),
    frozenset({"floodmappanel", "flood_map_panel", "femamapidentifier",
               "fema_map_identifier", "firmid", "firm_id",
               "firmpanelnumber", "firm_panel_number"}),
    frozenset({"femamapdate", "fema_map_date"}),

    # ── land / site ──────────────────────────────────────────────────────
    frozenset({"landuse", "land_use"}),
    frozenset({"landarea", "land_area", "siteacres", "site_acres",
               "landsf", "land_sf", "landareaac", "landareaacres"}),
    frozenset({"landunits", "land_units", "allowableunits",
               "allowable_units"}),
    frozenset({"zoningcode", "zoning_code", "zoningdesignation",
               "zoning_designation", "zoningdistrict", "zoning_district"}),

    # ── sale ─────────────────────────────────────────────────────────────
    frozenset({"saleprice", "sale_price", "salesprice", "sales_price",
               "totalsaleprice", "total_sale_price"}),
    frozenset({"saledate", "sale_date", "transactiondate",
               "transaction_date", "closingdate", "closing_date"}),
    frozenset({"priceperunit", "price_per_unit", "priceperroom",
               "price_per_room"}),
    frozenset({"pricepersf", "price_per_sf", "priceperfoot",
               "price_per_foot"}),

    # ── lease ─────────────────────────────────────────────────────────────
    frozenset({"tenantname", "tenant_name"}),
    frozenset({"lessorname", "lessor_name"}),
    frozenset({"leasetype", "lease_type"}),
    frozenset({"leasetermmonths", "lease_term_months",
               "leasedurationmonths"}),
    frozenset({"unitsf", "unit_sf", "leasedarea", "leased_area"}),

    # ── status / meta ─────────────────────────────────────────────────────
    frozenset({"status", "projectstatus", "project_status",
               "buildingstatus", "building_status"}),
    frozenset({"isactive", "is_active", "active"}),
    frozenset({"datasource", "data_source", "source", "sourcesystem",
               "source_system"}),
    frozenset({"reportingyear", "reporting_year", "taxyear", "tax_year"}),
    frozenset({"customfields", "custom_fields"}),
    frozenset({"notes", "comments", "description", "remarks"}),
]

# ═══════════════════════════════════════════════════════════════════════════
#  NORMALISATION
# ═══════════════════════════════════════════════════════════════════════════

# Common real-estate prefixes to strip before comparing
_PREFIXES = ("parcel", "property", "prop", "geo", "geography",
             "stmt", "mf", "comm", "calc", "mr", "building",
             "leasecomp", "salecomp", "rentcomp")


def normalize(field: str) -> str:
    """
    Collapse a field name to a bare lowercase token:
    strip spaces/underscores/hyphens, lowercase, remove leading prefixes.
    """
    if not field or (isinstance(field, float)):
        return ""
    s = str(field).lower().strip()
    s = re.sub(r"[\s_\-]+", "", s)
    # strip one leading prefix (longest first)
    for prefix in sorted(_PREFIXES, key=len, reverse=True):
        if s.startswith(prefix) and len(s) > len(prefix):
            s = s[len(prefix):]
            break
    return s


def build_synonym_map() -> dict[str, str]:
    """
    Returns {normalized_token: canonical_label}.
    The canonical label is the longest/most-readable member of each group.
    """
    lookup: dict[str, str] = {}
    for group in SYNONYM_GROUPS:
        # pick most readable name: prefer snake_case with underscores
        canonical = max(group, key=lambda x: (x.count("_"), len(x)))
        for term in group:
            norm = normalize(term)
            if norm and norm not in lookup:
                lookup[norm] = canonical
    return lookup


def semantic_key(field: str, syn_map: dict[str, str]) -> str:
    """Map a field to its canonical synonym group key (or its own norm)."""
    if not field:
        return ""
    n = normalize(field)
    return syn_map.get(n, n)


# ═══════════════════════════════════════════════════════════════════════════
#  CSV PARSING
# ═══════════════════════════════════════════════════════════════════════════

def parse_csv(filepath: str) -> OrderedDict:
    """
    Returns OrderedDict:
      { entity_name: { source_col_header: [field, ...], ... } }
    Source columns are whatever is in the CSV header (ERD, CoStar, …).
    """
    df = pd.read_csv(filepath, header=0, dtype=str).fillna("")

    # First col = entity name, rest = source columns
    entity_col  = df.columns[0]
    source_cols = list(df.columns[1:])

    entities: OrderedDict = OrderedDict()
    current = None

    for _, row in df.iterrows():
        ename = str(row[entity_col]).strip()
        if ename:
            current = ename
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

def align_entity(
    sources: dict[str, list[str]],
    source_cols: list[str],
    syn_map: dict[str, str],
) -> list[dict]:
    """
    Merge fields from all source columns into semantically aligned rows.

    Returns a list of row dicts:
      { 'semantic_key': ...,
        source_col_1: original_field_or_empty,
        source_col_2: ...,
        ...
        'match_count': int,       # how many sources matched
        'match_type': 'full'|'partial'|'unmatched' }
    """
    # sem_key -> { source_col: [original_fields] }
    groups: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for sc in source_cols:
        for field in sources.get(sc, []):
            key = semantic_key(field, syn_map)
            groups[key][sc].append(field)

    rows = []
    for key, src_map in groups.items():
        row: dict = {"semantic_key": key}
        for sc in source_cols:
            vals = src_map.get(sc, [])
            row[sc] = " | ".join(vals) if vals else ""
        filled = sum(1 for sc in source_cols if row[sc])
        row["match_count"] = filled
        if filled >= 2:
            row["match_type"] = "full"
        else:
            # single-source but has a known synonym (key differs from any norm)
            row["match_type"] = "partial" if key in syn_map.values() else "unmatched"
        rows.append(row)

    # Sort: full matches first, then partial, then unmatched; alpha within groups
    order = {"full": 0, "partial": 1, "unmatched": 2}
    rows.sort(key=lambda r: (order[r["match_type"]], r["semantic_key"]))
    return rows


# ═══════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS WRITER
# ═══════════════════════════════════════════════════════════════════════════

def _col_letter(n: int) -> str:
    """Convert 1-based column index to letter(s): 1→A, 27→AA, etc."""
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def write_to_sheets(
    spreadsheet_id: str,
    creds_file: str,
    entities: OrderedDict,
    source_cols: list[str],
    syn_map: dict[str, str],
    batch_sleep: float = 1.2,          # seconds between API calls (rate-limit)
) -> None:
    """Consolidate all entities into one master worksheet tab."""
    try:
        import gspread
        from gspread_formatting import (
            CellFormat, Color, TextFormat,
            format_cell_range, set_frozen, batch_updater,
        )
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        sys.exit(f"Missing dependency: {e}\n"
                 "Run:  pip install gspread gspread-formatting google-auth")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = Credentials.from_service_account_file(creds_file, scopes=scopes)
    client = gspread.authorize(creds)
    sh     = client.open_by_key(spreadsheet_id)

    # colour palette (RGB 0-1)
    COL_HEADER   = Color(0.204, 0.396, 0.643)   # dark blue
    COL_FULL     = Color(0.839, 0.953, 0.827)   # soft green
    COL_PARTIAL  = Color(1.000, 0.976, 0.816)   # soft yellow
    COL_SUBHEAD  = Color(0.878, 0.878, 0.878)   # light grey entity separator
    WHITE        = Color(1, 1, 1)
    WHITE_TEXT   = Color(1, 1, 1)
    BLACK_TEXT   = Color(0, 0, 0)

    # ── get or create worksheet ──────────────────────────────────────
    sheet_title = SHEET_TITLE
    try:
        ws = sh.worksheet(sheet_title)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_title, rows=1000, cols=len(source_cols) + 2)

    total_cols   = len(source_cols) + 2   # Entity + Semantic Concept + N sources
    last_col_ltr = _col_letter(total_cols)
    headers      = ["Entity", "Semantic Concept"] + source_cols

    # ── build data grid ──────────────────────────────────────────────
    grid = [headers]
    row_meta = ["header"]   # match_type per grid row

    print(f"▶  Aggregating {len(entities)} entities into '{sheet_title}' …")
    for entity_name, sources in entities.items():
        rows = align_entity(sources, source_cols, syn_map)
        if not rows:
            continue
        for r in rows:
            # Add Entity name as the first column
            grid.append([entity_name, r["semantic_key"]] + [r.get(sc, "") for sc in source_cols])
            row_meta.append(r["match_type"])

    # write values
    ws.update(values=grid, range_name="A1", value_input_option="RAW")
    time.sleep(batch_sleep)

    # ── formatting ───────────────────────────────────────────────────
    with batch_updater(sh) as b:
        # header row
        b.format_cell_range(
            ws, f"A1:{last_col_ltr}1",
            CellFormat(
                backgroundColor=COL_HEADER,
                textFormat=TextFormat(bold=True, foregroundColor=WHITE_TEXT),
                horizontalAlignment="CENTER",
            )
        )
        # data rows
        for i, mt in enumerate(row_meta[1:], start=2):
            rng = f"A{i}:{last_col_ltr}{i}"
            if mt == "full":
                bg = COL_FULL
            elif mt == "partial":
                bg = COL_PARTIAL
            else:
                bg = WHITE
            b.format_cell_range(ws, rng, CellFormat(backgroundColor=bg))

        # bold the Entity and Semantic Concept column
        b.format_cell_range(
            ws, f"A2:B{len(grid)}",
            CellFormat(textFormat=TextFormat(bold=True)),
        )

    set_frozen(ws, rows=1, cols=2)
    time.sleep(batch_sleep)
    print(f"✅  Pushed {len(grid)-1} rows to Google Sheets.")


# ═══════════════════════════════════════════════════════════════════════════
#  OPTIONAL: local CSV preview (no Google Sheets needed)
# ═══════════════════════════════════════════════════════════════════════════

def export_to_csv(
    out_path: str,
    entities: OrderedDict,
    source_cols: list[str],
    syn_map: dict[str, str],
) -> None:
    """
    Flat CSV export: Entity | Semantic Concept | <source cols> | Match Type
    Useful for local debugging or feeding into another tool.
    """
    all_rows = []
    col_names = ["Entity", "Semantic Concept"] + source_cols + ["Match Type"]

    for entity_name, sources in entities.items():
        rows = align_entity(sources, source_cols, syn_map)
        for r in rows:
            all_rows.append(
                [entity_name, r["semantic_key"]]
                + [r.get(sc, "") for sc in source_cols]
                + [r["match_type"]]
            )

    pd.DataFrame(all_rows, columns=col_names).to_csv(out_path, index=False)
    print(f"Local CSV saved → {out_path}")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("▶  Parsing CSV …")
    entities, source_cols = parse_csv(CSV_FILE)
    print(f"   Found {len(entities)} entities: {list(entities.keys())}")
    print(f"   Source columns: {source_cols}")

    syn_map = build_synonym_map()
    print(f"   Synonym map: {len(syn_map)} normalized tokens")

    # ── Always export a local CSV for verification ───────────────────────
    export_to_csv(OUTPUT_CSV_FILE, entities, source_cols, syn_map)

    # ── Write to Google Sheets (skip if placeholder ID) ──────────────────
    if SPREADSHEET_ID == "YOUR_SPREADSHEET_ID_HERE":
        print("\n⚠️  SPREADSHEET_ID not set. Skipping Google Sheets upload.")
        print("   Edit the constants at the top of this script and re-run.")
    else:
        print("\n▶  Writing to Google Sheets …")
        write_to_sheets(SPREADSHEET_ID, CREDS_FILE, entities, source_cols, syn_map)
        print("\n✅  All done!")


if __name__ == "__main__":
    main()
