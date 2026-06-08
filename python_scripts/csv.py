# import csv
# import os
# import argparse
# import re
# import difflib


# #commands to use

# # python csv_tools.py extract --input input.csv --output emails.csv --column Email
# # python csv_tools.py extract-sql --input schema.sql --output list.txt
# # python csv_tools.py align --input mappings.csv --output aligned.csv
# # python csv_tools.py align-multi --input file.csv --output out.csv --refs "Col1" "Col2" --source "SourceCol" --result "ResultCol"
# # python csv_tools.py sort --input users.csv
# # python csv_tools.py sort --input users.csv --reverse
# # python csv_tools.py sort --input data.csv --output data.csv --column "ID"
# # python csv_tools.py --help
# # python csv_tools.py extract --help
# # python csv_tools.py extract-sql --help
# # python csv_tools.py align --help
# # python csv_tools.py sort --help

# def extract_column_to_csv(input_file, output_file, column_name):
#     """
#     Extract a single column from a CSV file
#     and save it into a new CSV file.
#     """

#     column_data = []

#     with open(input_file, mode="r", newline="", encoding="utf-8") as infile:
#         reader = csv.DictReader(infile)

#         if column_name not in reader.fieldnames:
#             raise ValueError(f"Column '{column_name}' not found.")

#         for row in reader:
#             column_data.append([row[column_name]])

#     with open(output_file, mode="w", newline="", encoding="utf-8") as outfile:
#         writer = csv.writer(outfile)

#         # Write header
#         writer.writerow([column_name])

#         # Write rows
#         writer.writerows(column_data)

#     print(f"Column '{column_name}' extracted successfully.")
#     print(f"Saved to: {output_file}")


# def extract_fields_sql(input_file, output_file):
#     """
#     Extract field names from a SQL ERD file.
#     Specifically looks for backticked names in table definitions.
#     """
#     # Regex to match field names inside backticks that are part of a table definition
#     field_pattern = re.compile(r'^\s*`([^`]+)`', re.MULTILINE)

#     if not os.path.exists(input_file):
#         print(f"Error: {input_file} not found.")
#         return

#     with open(input_file, 'r', encoding='utf-8') as f:
#         content = f.read()

#     # Find all matches (indented backticked names)
#     matches = field_pattern.findall(content)

#     # Exclude table names (following CREATE TABLE)
#     table_names = re.findall(r'CREATE TABLE `([^`]+)`', content)
    
#     fields = [m for m in matches if m not in table_names]

#     # Deduplicate while preserving order
#     unique_fields = []
#     seen = set()
#     for field in fields:
#         if field not in seen:
#             unique_fields.append(field)
#             seen.add(field)

#     with open(output_file, 'w', encoding='utf-8') as f:
#         for field in unique_fields:
#             f.write(field + '\n')

#     print(f"SQL fields extracted successfully ({len(unique_fields)} fields).")
#     print(f"Saved to: {output_file}")


# def normalize_field_name(name):
#     """
#     Normalizes a name for better matching:
#     1. Lowercase.
#     2. Removes common prefixes like 'Parcel_', 'Improvement_', etc.
#     3. Removes underscores, spaces, and dots.
#     4. Handles common real estate abbreviations.
#     """
#     if not name:
#         return ""
    
#     name = name.lower().strip()
    
#     # Remove common prefixes followed by underscores or spaces
#     prefixes = [
#         'parcel_', 'improvement_', 'sales_', 'sites_', 'rent roll summary_', 
#         'unit lease summary_', 'incexp_', 'assessment_', 'saleinfo_', 'unit lease_'
#     ]
#     for prefix in prefixes:
#         if name.startswith(prefix):
#             name = name[len(prefix):]
            
#     # Remove all non-alphanumeric characters
#     name = re.sub(r'[^a-z0-9]', '', name)
    
#     # Common abbreviations/synonyms mapping
#     synonyms = {
#         'sf': 'squarefeet', 'sqft': 'squarefeet', 'sqfeet': 'squarefeet',
#         'ra': 'rentablearea', 'gla': 'grossleasablearea', 'gba': 'grossbuildingarea',
#         'bldg': 'building', 'yr': 'year', 'no': 'number', 'noof': 'numberof',
#         'addr': 'address', 'amt': 'amount', 'prop': 'property',
#         'zip': 'postalcode', 'pc': 'postalcode'
#     }
    
#     for abbr, full in synonyms.items():
#         if abbr in name:
#             name = name.replace(abbr, full)
            
#     return name


# def get_similarity_score(str1, str2):
#     """Calculate similarity score between two strings."""
#     norm1 = normalize_field_name(str1)
#     norm2 = normalize_field_name(str2)
    
#     if not norm1 or not norm2:
#         return 0
    
#     if norm1 == norm2:
#         return 1.0
        
#     return difflib.SequenceMatcher(None, norm1, norm2).ratio()


# def align_csv_data(input_file, output_file):
#     """
#     Aligns ERD fields with LightBox data in a CSV based on semantic similarity.
#     Appends unmatched fields at the end.
#     """
#     print(f"Reading {input_file} for alignment...")
    
#     rows = []
#     lb_candidates = []
    
#     with open(input_file, 'r', encoding='utf-8') as f:
#         reader = csv.DictReader(f)
#         fieldnames = reader.fieldnames
#         for row in reader:
#             rows.append(row)
#             lb_val = row.get('Field LightBox Data', '').strip()
#             if lb_val and lb_val not in lb_candidates:
#                 lb_candidates.append(lb_val)

#     used_candidates = set()
#     matches_count = 0
    
#     for row in rows:
#         erd_field = row.get('FIELD ERD', '').strip()
#         if not erd_field:
#             row['Field Lighboxdata aligned'] = ''
#             continue
            
#         best_match = None
#         best_score = 0
        
#         for cand in lb_candidates:
#             if cand in used_candidates:
#                 continue
            
#             score = get_similarity_score(erd_field, cand)
#             if score > best_score and score > 0.8:
#                 best_score = score
#                 best_match = cand
        
#         if best_match:
#             row['Field Lighboxdata aligned'] = best_match
#             used_candidates.add(best_match)
#             matches_count += 1
#         else:
#             row['Field Lighboxdata aligned'] = ''

#     unmatched_candidates = [cand for cand in lb_candidates if cand not in used_candidates]
#     print(f"Successfully aligned {matches_count} fields. Found {len(unmatched_candidates)} unmatched.")

#     # Append unmatched candidates at the end, mirrored in both columns
#     for cand in unmatched_candidates:
#         new_row = {key: '' for key in fieldnames}
#         # new_row['Field LightBox Data'] = cand
#         new_row['Field Lighboxdata aligned'] = cand
#         rows.append(new_row)

#     with open(output_file, 'w', encoding='utf-8', newline='') as f:
#         writer = csv.DictWriter(f, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(rows)
        
#     print(f"Aligned data saved to: {output_file}")

# def align_dynamic_data(input_file, output_file, ref_cols, source_col, result_col):
#     """
#     Dynamically aligns fields from a source pool column against multiple reference columns.
    
#     Parameters:
#     - input_file : source file path
#     - output_file : output file path
#     - ref_cols : List of columns to match against
#     - source_col : Column containing the pool of potential matches
#     - result_col : Column where the best match will be stored
#     """
#     print(f"Reading {input_file} for dynamic alignment...")
#     print(f"Reference columns: {ref_cols}")
#     print(f"Source pool: {source_col} -> Result: {result_col}")
    
#     rows = []
#     candidates = []
    
#     with open(input_file, 'r', encoding='utf-8') as f:
#         reader = csv.DictReader(f)
#         fieldnames = list(reader.fieldnames)
#         if result_col not in fieldnames:
#             fieldnames.append(result_col)
            
#         for row in reader:
#             rows.append(row)
#             val = row.get(source_col, '').strip()
#             if val and val not in candidates:
#                 candidates.append(val)

#     print(f"Found {len(candidates)} candidates in pool.")
    
#     used_candidates = set()
#     matches_count = 0
    
#     # Matching pass
#     for row in rows:
#         best_match = None
#         best_total_score = 0
        
#         # Check against each reference column requested
#         for col in ref_cols:
#             ref_val = row.get(col, '').strip()
#             if not ref_val:
#                 continue
            
#             for cand in candidates:
#                 if cand in used_candidates:
#                     continue
                
#                 score = get_similarity_score(ref_val, cand)
#                 # We want the highest score across all reference columns for this row
#                 if score > best_total_score and score > 0.8:
#                     best_total_score = score
#                     best_match = cand
                    
#         if best_match:
#             row[result_col] = best_match
#             used_candidates.add(best_match)
#             matches_count += 1
#         else:
#             row[result_col] = ''
            
#     # Handle unmatched fields (append to the end)
#     unmatched_candidates = [cand for cand in candidates if cand not in used_candidates]
#     print(f"Successfully aligned {matches_count} fields. Found {len(unmatched_candidates)} unmatched.")

#     for cand in unmatched_candidates:
#         new_row = {key: '' for key in fieldnames}
#         new_row[source_col] = cand
#         new_row[result_col] = cand
#         rows.append(new_row)

#     with open(output_file, 'w', encoding='utf-8', newline='') as f:
#         writer = csv.DictWriter(f, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(rows)
        
#     print(f"Dynamic alignment saved to: {output_file}")

# def sort_file_content(input_file, output_file=None, column_name=None, delimiter=None, reverse=False):
#     """
#     Sort content from CSV or plain text file dynamically.

#     Features:
#     - Handles TXT and CSV files
#     - Sorts by specific column (CSV only) or entire row
#     - Optional descending order
#     - Automatically detects file type

#     Parameters:
#     - input_file : source file path
#     - output_file : output file path (optional)
#     - column_name : Name of column to sort by (optional, CSV only)
#     - delimiter : CSV delimiter (optional)
#     - reverse : True for descending order
#     """

#     if output_file is None:
#         name, ext = os.path.splitext(input_file)
#         output_file = f"{name}_sorted{ext}"

#     file_ext = os.path.splitext(input_file)[1].lower()

#     # ---------- CSV FILE ----------
#     if file_ext == ".csv":

#         with open(input_file, mode="r", newline="", encoding="utf-8") as infile:
#             sample = infile.read(2048)
#             infile.seek(0)

#             # Auto detect delimiter if not provided
#             if delimiter is None:
#                 try:
#                     dialect = csv.Sniffer().sniff(sample)
#                     delimiter = dialect.delimiter
#                 except:
#                     delimiter = ","

#             reader = csv.reader(infile, delimiter=delimiter)
#             rows = list(reader)

#         if not rows:
#             print("CSV is empty.")
#             return

#         # Preserve header
#         header = rows[0]
#         data_rows = rows[1:]

#         # Determine sort key
#         if column_name:
#             if column_name in header:
#                 col_index = header.index(column_name)
#                 # Sort by specific column
#                 data_rows.sort(key=lambda x: x[col_index].lower() if col_index < len(x) else "", reverse=reverse)
#                 print(f"Sorting CSV by column: '{column_name}'")
#             else:
#                 print(f"Warning: Column '{column_name}' not found. Sorting by entire row.")
#                 data_rows.sort(key=lambda x: [str(i).lower() for i in x], reverse=reverse)
#         else:
#             # Default: Sort by all columns
#             data_rows.sort(key=lambda x: [str(i).lower() for i in x], reverse=reverse)

#         with open(output_file, mode="w", newline="", encoding="utf-8") as outfile:
#             writer = csv.writer(outfile, delimiter=delimiter)
#             writer.writerow(header)
#             writer.writerows(data_rows)

#         print(f"CSV sorted successfully. Saved to: {output_file}")

#     # ---------- TEXT FILE ----------
#     else:

#         with open(input_file, mode="r", encoding="utf-8") as infile:
#             lines = infile.readlines()

#         # Remove empty lines and sort
#         lines = [line.strip() for line in lines if line.strip()]
#         lines.sort(reverse=reverse)

#         with open(output_file, mode="w", encoding="utf-8") as outfile:
#             for line in lines:
#                 outfile.write(line + "\n")

#         print(f"Text file sorted successfully.")
#         print(f"Saved to: {output_file}")


# # =========================================================
# # Example Usage
# # =========================================================



# if __name__ == "__main__":

#     parser = argparse.ArgumentParser(description="CSV and Text File Utility Tool")

#     subparsers = parser.add_subparsers(dest="command")

#     # =====================================================
#     # Extract Column Command
#     # =====================================================
#     extract_parser = subparsers.add_parser(
#         "extract",
#         help="Extract a column from CSV"
#     )

#     extract_parser.add_argument(
#         "--input",
#         required=True,
#         help="Input CSV file"
#     )

#     extract_parser.add_argument(
#         "--output",
#         required=True,
#         help="Output CSV file"
#     )

#     extract_parser.add_argument(
#         "--column",
#         required=True,
#         help="Column name to extract"
#     )

#     # =====================================================
#     # Extract SQL Fields Command
#     # =====================================================
#     sql_parser = subparsers.add_parser(
#         "extract-sql",
#         help="Extract field names from SQL ERD"
#     )

#     sql_parser.add_argument(
#         "--input",
#         required=True,
#         help="Input SQL file"
#     )

#     sql_parser.add_argument(
#         "--output",
#         required=True,
#         help="Output text file"
#     )

#     # =====================================================
#     # Align Data Command
#     # =====================================================
#     align_parser = subparsers.add_parser(
#         "align",
#         help="Align ERD fields with LightBox data"
#     )

#     align_parser.add_argument(
#         "--input",
#         required=True,
#         help="Input CSV file"
#     )

#     align_parser.add_argument(
#         "--output",
#         required=True,
#         help="Output CSV file"
#     )

#     # =====================================================
#     # Dynamic Multi-Column Alignment Command
#     # =====================================================
#     multi_align_parser = subparsers.add_parser(
#         "align-multi",
#         help="Align fields using multiple reference columns"
#     )

#     multi_align_parser.add_argument(
#         "--input",
#         required=True,
#         help="Input CSV file"
#     )

#     multi_align_parser.add_argument(
#         "--output",
#         required=True,
#         help="Output CSV file"
#     )

#     multi_align_parser.add_argument(
#         "--refs",
#         nargs="+",
#         required=True,
#         help="List of reference columns to match against"
#     )

#     multi_align_parser.add_argument(
#         "--source",
#         required=True,
#         help="Column containing the pool of candidates"
#     )

#     multi_align_parser.add_argument(
#         "--result",
#         required=True,
#         help="Column to store aligned results"
#     )

#     # =====================================================
#     # Sort File Command
#     # =====================================================
#     sort_parser = subparsers.add_parser(
#         "sort",
#         help="Sort CSV or text file"
#     )

#     sort_parser.add_argument(
#         "--input",
#         required=True,
#         help="Input file"
#     )

#     sort_parser.add_argument(
#         "--output",
#         help="Output file"
#     )

#     sort_parser.add_argument(
#         "--column",
#         help="Column name to sort by (CSV only)"
#     )

#     sort_parser.add_argument(
#         "--reverse",
#         action="store_true",
#         help="Sort in descending order"
#     )

#     args = parser.parse_args()

#     # =====================================================
#     # Execute Commands
#     # =====================================================

#     if args.command == "extract":
#         extract_column_to_csv(
#             input_file=args.input,
#             output_file=args.output,
#             column_name=args.column
#         )

#     elif args.command == "extract-sql":
#         extract_fields_sql(
#             input_file=args.input,
#             output_file=args.output
#         )

#     elif args.command == "align":
#         align_csv_data(
#             input_file=args.input,
#             output_file=args.output
#         )

#     elif args.command == "align-multi":
#         align_dynamic_data(
#             input_file=args.input,
#             output_file=args.output,
#             ref_cols=args.refs,
#             source_col=args.source,
#             result_col=args.result
#         )

#     elif args.command == "sort":
#         sort_file_content(
#             input_file=args.input,
#             output_file=args.output,
#             column_name=args.column,
#             reverse=args.reverse
#         )

#     else:
#         parser.print_help()


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


def normalize_field_name(name):
    """
    Normalizes a name for better matching:
    1. Lowercase.
    2. Removes common prefixes and connectors.
    3. Handles real estate abbreviations consistently.
    """
    if not name:
        return ""
    
    name = name.lower().strip()
    
    # Remove common prefixes followed by underscores or spaces
    # Added 'rent roll_', 'subrecords_', 'subrecord_'
    prefixes = [
        'parcel_', 'improvement_', 'sales_', 'sites_', 'rent roll summary_', 
        'unit lease summary_', 'incexp_', 'assessment_', 'saleinfo_', 'unit lease_',
        'rent roll_', 'rent_roll_', 'rentroll_', 'subrecords_', 'subrecord_', 'inc_exp_'
    ]
    
    # Iteratively remove prefixes (in case there are multiple or nested)
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                changed = True
            
    # Remove some common internal connectors that confuse matches
    name = name.replace('_subrecords_', '_').replace('_subrecord_', '_')

    # Handle numeric markers and abbreviations
    synonyms = {
        'sf': 'squarefeet', 'sqft': 'squarefeet', 'sqfeet': 'squarefeet',
        'ra': 'rentablearea', 'gla': 'grossleasablearea', 'gba': 'grossbuildingarea',
        'bldg': 'building', 'yr': 'year', 'no': 'number', 'noof': 'numberof',
        'addr': 'address', 'amt': 'amount', 'prop': 'property',
        'zip': 'zip', 'postalcode': 'zip', 'pc': 'zip', 'postal': 'zip', 'num': 'number',
        'lat': 'latitude', 'lng': 'longitude', 'm2': 'squaremeters',
        'cam': 'commonareamaintenance', 'sh': 'seniorhousing',
        'comm': 'commercial', 'instr': 'instrument', 'desc': 'description'
    }
    
    # Tokenize by common separators for precise synonym replacement
    parts = re.split(r'[_.\s]+', name)
    normalized_parts = []
    for p in parts:
        # Remove trailing single digits like address1, address2
        p = re.sub(r'([a-z]+)[0-9]$', r'\1', p)
        
        # Special case: 'postal' 'code' -> 'zip'
        if p == 'code' and normalized_parts and normalized_parts[-1] == 'zip':
            continue 
        p = synonyms.get(p, p)
        if p:
            normalized_parts.append(p)
    
    # Final cleanup: join and remove all non-alphanumeric
    final_name = "".join(normalized_parts)
    final_name = re.sub(r'[^a-z0-9]', '', final_name)
            
    return final_name


def get_similarity_score(str1, str2):
    """
    Calculate similarity score using a hybrid of SequenceMatcher 
    and token-subset logic.
    """
    if not str1 or not str2:
        return 0

    norm1 = normalize_field_name(str1)
    norm2 = normalize_field_name(str2)
    
    if norm1 == norm2:
        return 1.0

    # Holistic similarity
    seq_score = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    
    # Subset boost: if one string is entirely contained in the other
    # it likely represents a match but with different verbosity (e.g. 'loadfactor' in 'loadfactor_comments')
    if norm1 and norm2:
        if norm1 in norm2 or norm2 in norm1:
            # Calculate how much of the long string is covered by the short string
            coverage = min(len(norm1), len(norm2)) / max(len(norm1), len(norm2))
            # If coverage is high (at least 60%), boost the score significantly
            if coverage > 0.6:
                return max(seq_score, 0.85 + (coverage * 0.1))

    return seq_score


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
    
    Parameters:
    - input_file : source file path
    - output_file : output file path
    - ref_cols : List of columns to match against
    - source_col : Column containing the pool of potential matches
    - result_col : Column where the best match will be stored
    """
    print(f"Reading {input_file} for dynamic alignment...")
    print(f"Reference columns: {ref_cols}")
    print(f"Source pool: {source_col} -> Result: {result_col}")
    
    rows = []
    candidates = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if result_col not in fieldnames:
            fieldnames.append(result_col)
            
        for row in reader:
            rows.append(row)
            val = row.get(source_col, '').strip()
            if val and val not in candidates:
                candidates.append(val)

    print(f"Found {len(candidates)} candidates in pool.")
    
    used_candidates = set()
    matches_count = 0
    
    # Matching pass
    for row in rows:
        best_match = None
        best_total_score = 0
        
        # Check against each reference column requested
        for col in ref_cols:
            ref_val = row.get(col, '').strip()
            if not ref_val:
                continue
            
            for cand in candidates:
                if cand in used_candidates:
                    continue
                
                score = get_similarity_score(ref_val, cand)
                # We want the highest score across all reference columns for this row
                if score > best_total_score and score > 0.8:
                    best_total_score = score
                    best_match = cand
                    
        if best_match:
            row[result_col] = best_match
            used_candidates.add(best_match)
            matches_count += 1
        else:
            row[result_col] = ''
            
    # Handle unmatched fields (append to the end)
    unmatched_candidates = [cand for cand in candidates if cand not in used_candidates]
    print(f"Successfully aligned {matches_count} fields. Found {len(unmatched_candidates)} unmatched.")

    for cand in unmatched_candidates:
        new_row = {key: '' for key in fieldnames}
        # Add the unmatched candidate to each field in the unmatched list
        # new_row[source_col] = cand
        new_row[result_col] = cand
        rows.append(new_row)

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Dynamic alignment saved to: {output_file}")

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


# =========================================================
# Example Usage
# =========================================================



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

    else:
        parser.print_help()