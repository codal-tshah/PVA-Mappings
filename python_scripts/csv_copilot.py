import csv
import os
import argparse
import re
import difflib


#commands to use

# python csv_tools.py extract --input input.csv --output emails.csv --column Email
# python csv_tools.py extract-sql --input schema.sql --output list.txt
# python csv_tools.py align --input mappings.csv --output aligned.csv
# python csv_tools.py align-multi --input file.csv --output out.csv --refs "Col1" "Col2" --source "SourceCol" --result "ResultCol"
# python csv_tools.py sort --input users.csv
# python csv_tools.py sort --input users.csv --reverse
# python csv_tools.py sort --input data.csv --output data.csv --column "ID"
# python csv_tools.py --help
# python csv_tools.py extract --help
# python csv_tools.py extract-sql --help
# python csv_tools.py align --help
# python csv_tools.py sort --help
# python csv_tools.py tag --input "Sheet11_aligned.csv" --output "Sheet12_tagged.csv"

def extract_column_to_csv(input_file, output_file, column_name):
    """
    Extract a single column from a CSV file
    and save it into a new CSV file.
    """

    column_data = []

    with open(input_file, mode="r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)

        if column_name not in reader.fieldnames:
            raise ValueError(f"Column '{column_name}' not found.")

        for row in reader:
            column_data.append([row[column_name]])

    with open(output_file, mode="w", newline="", encoding="utf-8") as outfile:
        writer = csv.writer(outfile)

        # Write header
        writer.writerow([column_name])

        # Write rows
        writer.writerows(column_data)

    print(f"Column '{column_name}' extracted successfully.")
    print(f"Saved to: {output_file}")


def extract_fields_sql(input_file, output_file):
    """
    Extract field names from a SQL ERD file.
    Specifically looks for backticked names in table definitions.
    """
    # Regex to match field names inside backticks that are part of a table definition
    field_pattern = re.compile(r'^\s*`([^`]+)`', re.MULTILINE)

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all matches (indented backticked names)
    matches = field_pattern.findall(content)

    # Exclude table names (following CREATE TABLE)
    table_names = re.findall(r'CREATE TABLE `([^`]+)`', content)
    
    fields = [m for m in matches if m not in table_names]

    # Deduplicate while preserving order
    unique_fields = []
    seen = set()
    for field in fields:
        if field not in seen:
            unique_fields.append(field)
            seen.add(field)

    with open(output_file, 'w', encoding='utf-8') as f:
        for field in unique_fields:
            f.write(field + '\n')

    print(f"SQL fields extracted successfully ({len(unique_fields)} fields).")
    print(f"Saved to: {output_file}")


def normalize_field_name(name, return_parts=False):
    """
    Normalizes a name for better matching:
    1. Removes parentheticals and units (e.g., "(mi)", "(Industrial)").
    2. Lowercase and split camelCase.
    3. Removes common prefixes and connectors.
    4. Handles real estate abbreviations consistently.
    5. Singularizes terms and removes stop words.
    """
    if not name:
        return ("", []) if return_parts else ""
    
    orig_name = name.strip()
    
    # Strip parentheticals like (mi), (SF), (Industrial)
    name = re.sub(r'\(.*?\)', '', orig_name)
    
    # Replace non-alphanumeric chars ($, /, -, etc.) with spaces
    name = re.sub(r'[^a-zA-Z0-9\s_]', ' ', name)
    
    # Split camelCase / PascalCase before lowercasing to preserve word boundaries
    spaced_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    name = spaced_name.lower()
    
    # Remove common prefixes followed by underscores or spaces
    prefixes = [
        'parcel_', 'improvement_', 'sales_', 'sites_', 'rent roll summary_', 
        'unit lease summary_', 'incexp_', 'assessment_', 'saleinfo_', 'unit lease_',
        'rent roll_', 'rent_roll_', 'rentroll_', 'subrecords_', 'subrecord_', 'inc_exp_'
    ]
    
    # Iteratively remove prefixes
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                changed = True
            
    # Remove common internal connectors
    name = name.replace('_subrecords_', '_').replace('_subrecord_', '_')

    # Replace specific fused words used in the ERD
    name = name.replace('noof', 'number')

    # Handle numeric markers and abbreviations
    synonyms = {
        'sf': 'squarefeet', 'sqft': 'squarefeet', 'sqfeet': 'squarefeet',
        'ra': 'rentablearea', 'gla': 'grossleasablearea', 'gba': 'grossbuildingarea',
        'bldg': 'building', 'yr': 'year', 'no': 'number', 'noof': 'number',
        'addr': 'address', 'amt': 'amount', 'prop': 'property',
        'zip': 'zip', 'postalcode': 'zip', 'pc': 'zip', 'postal': 'zip', 'num': 'number',
        'lat': 'latitude', 'lng': 'longitude', 'm2': 'squaremeters',
        'cam': 'commonareamaintenance', 'sh': 'seniorhousing',
        'comm': 'commercial', 'instr': 'instrument', 'desc': 'description'
    }
    
    stop_words = {'of', 'in', 'the', 'and', 'or', 'to'}
    
    # Tokenize by any non-alphanumeric character
    parts = re.split(r'[^a-z0-9]+', name)
    normalized_parts = []
    
    for p in parts:
        if not p:
            continue
            
        # Remove trailing single digits like address1 -> address
        p = re.sub(r'([a-z]+)[0-9]$', r'\1', p)
        
        # Simple singularization
        if p.endswith('s') and p not in {'address', 'gross', 'sales', 'options', 'status', 'terms', 'bonus'}:
            if len(p) > 3 and not p.endswith('ss'):
                p = p[:-1]
                
        # Special fused term logic: postal code -> zip
        if p == 'code' and normalized_parts and normalized_parts[-1] == 'zip':
            continue 
            
        # Map synonym
        p = synonyms.get(p, p)
        
        if p and p not in stop_words:
            normalized_parts.append(p)
    
    # Final cleanup: join the verified parts
    final_name = "".join(normalized_parts)
            
    if return_parts:
        return final_name, sorted(normalized_parts)
    return final_name


def get_similarity_score(str1, str2, cat1=None, cat2=None):
    """
    Calculate similarity score using a hybrid of SequenceMatcher 
    and token-subset logic.
    Supports Category-based penalty for cross-type noise.
    """
    if not str1 or not str2:
        return 0

    norm1, parts1 = normalize_field_name(str1, return_parts=True)
    norm2, parts2 = normalize_field_name(str2, return_parts=True)
    
    if norm1 == norm2:
        score = 1.0
    else:
        # Holistic similarity
        seq_score = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        
        # Token-based match to handle different word ordering ("taxes total" vs "total taxes")
        if parts1 and parts2:
            joined1 = "".join(parts1)
            joined2 = "".join(parts2)
            if joined1 == joined2:
                seq_score = 1.0
            else:
                token_score = difflib.SequenceMatcher(None, joined1, joined2).ratio()
                seq_score = max(seq_score, token_score)
        
        # Subset boost: if one string is entirely contained in the other
        # Guard: Minimum length of 8 to prevent small tokens like "condition" from boosting
        if norm1 and norm2 and seq_score < 1.0:
            if norm1 in norm2 or norm2 in norm1:
                shorter_len = min(len(norm1), len(norm2))
                if shorter_len >= 8:
                    coverage = shorter_len / max(len(norm1), len(norm2))
                    if coverage > 0.6:
                        seq_score = max(seq_score, 0.85 + (coverage * 0.1))
        
        score = seq_score

    # Apply Category Penalty: If types are mismatched, penalize the score
    if cat1 and cat2 and cat1 != "Other" and cat2 != "Other" and cat1 != cat2:
        score -= 0.15

    return score


def align_csv_data(input_file, output_file):
    """
    Aligns ERD fields with LightBox data in a CSV based on semantic similarity.
    Appends unmatched fields at the end.
    """
    print(f"Reading {input_file} for alignment...")
    
    rows = []
    lb_candidates = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
            lb_val = row.get('Field LightBox Data', '').strip()
            if lb_val and lb_val not in lb_candidates:
                lb_candidates.append(lb_val)

    used_candidates = set()
    matches_count = 0
    
    for row in rows:
        erd_field = row.get('FIELD ERD', '').strip()
        if not erd_field:
            row['Field Lighboxdata aligned'] = ''
            continue
            
        best_match = None
        best_score = 0
        
        for cand in lb_candidates:
            if cand in used_candidates:
                continue
            
            score = get_similarity_score(erd_field, cand)
            if score > best_score and score > 0.8:
                best_score = score
                best_match = cand
        
        if best_match:
            row['Field Lighboxdata aligned'] = best_match
            used_candidates.add(best_match)
            matches_count += 1
        else:
            row['Field Lighboxdata aligned'] = ''

    unmatched_candidates = [cand for cand in lb_candidates if cand not in used_candidates]
    print(f"Successfully aligned {matches_count} fields. Found {len(unmatched_candidates)} unmatched.")

    # Append unmatched candidates at the end, mirrored in both columns
    for cand in unmatched_candidates:
        new_row = {key: '' for key in fieldnames}
        # new_row['Field LightBox Data'] = cand
        new_row['Field Lighboxdata aligned'] = cand
        rows.append(new_row)

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Aligned data saved to: {output_file}")

def align_dynamic_data(input_file, output_file, ref_cols, source_col, result_col):
    """
    Dynamically aligns fields from a source pool column against multiple reference columns.
    Uses TWO-PASS matching: Global scoring follow by descending score assignment.
    
    Features:
    - Global score ranking (best matches in file lock first)
    - Category-aware sorting
    - Confidence score logging
    """
    print(f"Reading {input_file} for two-pass alignment...")
    print(f"Reference columns: {ref_cols}")
    print(f"Source pool: {source_col} -> Result: {result_col}")
    
    rows = []
    candidates = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        
        # Ensure result and debug columns exist
        for col in [result_col, "Confidence Score", "Match Source"]:
            if col not in fieldnames:
                fieldnames.append(col)
            
        for row in reader:
            rows.append(row)
            val = row.get(source_col, '').strip()
            if val and val not in candidates:
                candidates.append(val)

    print(f"Found {len(candidates)} candidates in source pool.")
    
    # Pass 1: Global Scoring
    score_registry = []
    for row_idx, row in enumerate(rows):
        # Initialize result fields for this row
        row[result_col] = ''
        row["Confidence Score"] = ''
        row["Match Source"] = ''
        
        # Get category if available
        row_cat = row.get("Category", "Other")
        
        for col in ref_cols:
            ref_val = row.get(col, '').strip()
            if not ref_val:
                continue
                
            for cand in candidates:
                # We can't know the candidate's category easily unless we tag it
                # For now, we simple rely on the row category for scoring if needed
                score = get_similarity_score(ref_val, cand, cat1=row_cat)
                
                if score > 0.45: # Keep all potential matches
                    score_registry.append({
                        'score': score,
                        'row_idx': row_idx,
                        'candidate': cand,
                        'source_col': col
                    })

    # Sort globally by score descending
    score_registry.sort(key=lambda x: x['score'], reverse=True)
    
    used_rows = set()
    used_candidates = set()
    matches_count = 0
    
    # Pass 2: Greedy Assignment by highest score
    for match in score_registry:
        if match['row_idx'] in used_rows or match['candidate'] in used_candidates:
            continue
            
        # Assignment threshold
        if match['score'] >= 0.75: # Slightly lower threshold since we use global sorting
            row = rows[match['row_idx']]
            row[result_col] = match['candidate']
            row["Confidence Score"] = round(match['score'], 3)
            row["Match Source"] = match['source_col']
            
            used_rows.add(match['row_idx'])
            used_candidates.add(match['candidate'])
            matches_count += 1
            
    # Handle unmatched fields (append to the end)
    unmatched_candidates = [cand for cand in candidates if cand not in used_candidates]
    print(f"Successfully aligned {matches_count} fields. Found {len(unmatched_candidates)} unmatched.")

    for cand in unmatched_candidates:
        new_row = {key: '' for key in fieldnames}
        new_row[result_col] = cand
        rows.append(new_row)

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Two-pass alignment saved to: {output_file}")

def sort_file_content(input_file, output_file=None, column_name=None, delimiter=None, reverse=False):
    """
    Sort content from CSV or plain text file dynamically.

    Features:
    - Handles TXT and CSV files
    - Sorts by specific column (CSV only) or entire row
    - Optional descending order
    - Automatically detects file type

    Parameters:
    - input_file : source file path
    - output_file : output file path (optional)
    - column_name : Name of column to sort by (optional, CSV only)
    - delimiter : CSV delimiter (optional)
    - reverse : True for descending order
    """

    if output_file is None:
        name, ext = os.path.splitext(input_file)
        output_file = f"{name}_sorted{ext}"

    file_ext = os.path.splitext(input_file)[1].lower()

    # ---------- CSV FILE ----------
    if file_ext == ".csv":

        with open(input_file, mode="r", newline="", encoding="utf-8") as infile:
            sample = infile.read(2048)
            infile.seek(0)

            # Auto detect delimiter if not provided
            if delimiter is None:
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    delimiter = dialect.delimiter
                except:
                    delimiter = ","

            reader = csv.reader(infile, delimiter=delimiter)
            rows = list(reader)

        if not rows:
            print("CSV is empty.")
            return

        # Preserve header
        header = rows[0]
        data_rows = rows[1:]

        # Determine sort key
        if column_name:
            if column_name in header:
                col_index = header.index(column_name)
                # Sort by specific column
                data_rows.sort(key=lambda x: x[col_index].lower() if col_index < len(x) else "", reverse=reverse)
                print(f"Sorting CSV by column: '{column_name}'")
            else:
                print(f"Warning: Column '{column_name}' not found. Sorting by entire row.")
                data_rows.sort(key=lambda x: [str(i).lower() for i in x], reverse=reverse)
        else:
            # Default: Sort by all columns
            data_rows.sort(key=lambda x: [str(i).lower() for i in x], reverse=reverse)

        with open(output_file, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.writer(outfile, delimiter=delimiter)
            writer.writerow(header)
            writer.writerows(data_rows)

        print(f"CSV sorted successfully. Saved to: {output_file}")

    # ---------- TEXT FILE ----------
    else:

        with open(input_file, mode="r", encoding="utf-8") as infile:
            lines = infile.readlines()

        # Remove empty lines and sort
        lines = [line.strip() for line in lines if line.strip()]
        lines.sort(reverse=reverse)

        with open(output_file, mode="w", encoding="utf-8") as outfile:
            for line in lines:
                outfile.write(line + "\n")

        print(f"Text file sorted successfully.")
        print(f"Saved to: {output_file}")


def tag_csv_data(input_file, output_file):
    """
    Automatically assigns a real estate category to each row based on keywords 
    found in any of the field columns.
    """
    categories = {
        "Property Identity & Location": [
            "address", "city", "state", "zip", "latitude", "longitude", "country", "county", 
            "market", "location", "property_name", "cbsa", "census", "lat", "lng", "identity",
            "district", "neighborhood", "boundary", "cross_street", "parcel", "name"
        ],
        "Property Characteristics & Building Details": [
            "building", "construction", "year_built", "renovated", "stories", "rba", "gba", 
            "elevators", "condition", "quality", "sprinklers", "exterior_wall", "foundation", 
            "roof", "heating", "cooling", "basement", "floor", "height", "sf", "area", "size",
            "finished", "appeal", "amenities", "features"
        ],
        "Residential & Unit Mix": [
            "beds", "baths", "bedrooms", "unit", "mf_", "senior", "affordable", "resident", 
            "sh_", "units", "room", "affordability", "mfbr", "care_type", "lhtc", "seniorhousing",
            "multifamily"
        ],
        "Industrial & Logistics Specs": [
            "dock", "truck", "crane", "rail", "bay", "ceiling", "clear_height", "column_spacing", 
            "depth", "logistics", "industrial", "warehouse", "levelers"
        ],
        "Parking & Accessibility": [
            "parking", "transit", "walk", "bus", "stop", "garage", "carport", "ratio", "paved", 
            "unpaved", "surface", "access", "accessibility"
        ],
        "Land, Zoning & Development": [
            "site", "land", "acres", "sf", "lot", "zoning", "zoning_code", "density", "frontage", 
            "depth", "earthquake", "soil", "topography", "development", "proposed", "coverage"
        ],
        "Environmental, Risks & Sustainability": [
            "flood", "fema", "risk", "leed", "energy", "contamination", "stigma", "wetland", 
            "environment", "hazardous", "firm", "green", "asbestos", "sfha"
        ],
        "Utilities & Site Infrastructure": [
            "utility", "water", "sewer", "gas", "electricity", "electric", "power", "trash", 
            "fuel", "drainage", "heating_type", "cooling_type"
        ],
        "Ownership, Contact & Property Management": [
            "owner", "manager", "developer", "parent", "contact", "phone", "fax", "grantee", 
            "grantor", "buyer", "seller", "lessor", "attorney", "agent", "recorded", "company"
        ],
        "Financials, Taxes & Sales Information": [
            "tax", "price", "sale", "cap_rate", "expense", "income", "pgi", "egi", "noi", 
            "valuation", "appraisal", "finance", "mortgage", "assessment", "revenue", "multiplier",
            "egim", "pgim", "nim", "financing", "expenditure", "accounting"
        ],
        "Commercial Availability & Leasing": [
            "lease", "rent", "tenant", "vacancy", "anchors", "occupancy", "available", "relet", 
            "sublet", "concession", "commencement", "expiration", "rent_roll", "tenancy", "ti"
        ],
        "Demographics & Location Insights": [
            "population", "household", "demographics", "school", "spending", "traffic", "hh_income",
            "enrollment", "student", "median"
        ],
        "Hospitality & Specialized Operations": [
            "hotel", "revpar", "flag", "room", "guest", "hospitality", "occupancy_rate"
        ]
    }

    print(f"Tagging data in {input_file}...")
    
    rows = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if "Category" not in fieldnames:
            fieldnames.insert(0, "Category")
        
        for row in reader:
            # Check all values in the row to find keywords
            found_category = "Other"
            
            # Combine all field values into a single lowercase searchable string
            combined_text = " ".join([str(val).lower() for val in row.values()]).replace("_", " ")
            
            # Category detection logic
            # Use a scoring system to find the best matching category
            best_cat = "Other"
            max_score = 0
            
            for cat, keywords in categories.items():
                score = 0
                for kw in keywords:
                    # Check for whole word match or prefix match for better precision
                    if kw in combined_text:
                        score += 1
                        # Dynamic column boost: Boost if kw is in columns containing 'ERD', 'CoStar', or 'LightBox'
                        for col in row.keys():
                            if any(x in col for x in ['ERD', 'CoStar', 'LightBox', 'Source', 'Data']) and col != 'Category':
                                if kw in str(row[col]).lower():
                                    score += 2
                
                if score > max_score:
                    max_score = score
                    best_cat = cat
            
            row["Category"] = best_cat
            rows.append(row)

    if not output_file:
        output_file = input_file

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Tagging complete. Saved to: {output_file}")




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="CSV and Text File Utility Tool")

    subparsers = parser.add_subparsers(dest="command")

    # =====================================================
    # Extract Column Command
    # =====================================================
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract a column from CSV"
    )

    extract_parser.add_argument(
        "--input",
        required=True,
        help="Input CSV file"
    )

    extract_parser.add_argument(
        "--output",
        required=True,
        help="Output CSV file"
    )

    extract_parser.add_argument(
        "--column",
        required=True,
        help="Column name to extract"
    )

    # =====================================================
    # Extract SQL Fields Command
    # =====================================================
    sql_parser = subparsers.add_parser(
        "extract-sql",
        help="Extract field names from SQL ERD"
    )

    sql_parser.add_argument(
        "--input",
        required=True,
        help="Input SQL file"
    )

    sql_parser.add_argument(
        "--output",
        required=True,
        help="Output text file"
    )

    # =====================================================
    # Align Data Command
    # =====================================================
    align_parser = subparsers.add_parser(
        "align",
        help="Align ERD fields with LightBox data"
    )

    align_parser.add_argument(
        "--input",
        required=True,
        help="Input CSV file"
    )

    align_parser.add_argument(
        "--output",
        required=True,
        help="Output CSV file"
    )

    # =====================================================
    # Dynamic Multi-Column Alignment Command
    # =====================================================
    multi_align_parser = subparsers.add_parser(
        "align-multi",
        help="Align fields using multiple reference columns"
    )

    multi_align_parser.add_argument(
        "--input",
        required=True,
        help="Input CSV file"
    )

    multi_align_parser.add_argument(
        "--output",
        required=True,
        help="Output CSV file"
    )

    multi_align_parser.add_argument(
        "--refs",
        nargs="+",
        required=True,
        help="List of reference columns to match against"
    )

    multi_align_parser.add_argument(
        "--source",
        required=True,
        help="Column containing the pool of candidates"
    )

    multi_align_parser.add_argument(
        "--result",
        required=True,
        help="Column to store aligned results"
    )

    # =====================================================
    # Sort File Command
    # =====================================================
    sort_parser = subparsers.add_parser(
        "sort",
        help="Sort CSV or text file"
    )

    sort_parser.add_argument(
        "--input",
        required=True,
        help="Input file"
    )

    sort_parser.add_argument(
        "--output",
        help="Output file"
    )

    sort_parser.add_argument(
        "--column",
        help="Column name to sort by (CSV only)"
    )

    sort_parser.add_argument(
        "--reverse",
        action="store_true",
        help="Sort in descending order"
    )

    # =====================================================
    # Tag Categories Command
    # =====================================================
    tag_parser = subparsers.add_parser(
        "tag",
        help="Auto-tag fields with real estate categories"
    )

    tag_parser.add_argument(
        "--input",
        required=True,
        help="Input CSV file"
    )

    tag_parser.add_argument(
        "--output",
        help="Output CSV file (defaults to input)"
    )

    args = parser.parse_args()

    # =====================================================
    # Execute Commands
    # =====================================================

    if args.command == "extract":
        extract_column_to_csv(
            input_file=args.input,
            output_file=args.output,
            column_name=args.column
        )

    elif args.command == "extract-sql":
        extract_fields_sql(
            input_file=args.input,
            output_file=args.output
        )

    elif args.command == "align":
        align_csv_data(
            input_file=args.input,
            output_file=args.output
        )

    elif args.command == "align-multi":
        align_dynamic_data(
            input_file=args.input,
            output_file=args.output,
            ref_cols=args.refs,
            source_col=args.source,
            result_col=args.result
        )

    elif args.command == "sort":
        sort_file_content(
            input_file=args.input,
            output_file=args.output,
            column_name=args.column,
            reverse=args.reverse
        )

    elif args.command == "tag":
        tag_csv_data(
            input_file=args.input,
            output_file=args.output
        )

    else:
        parser.print_help()