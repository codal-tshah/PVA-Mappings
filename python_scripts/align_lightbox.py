import csv
import re
import difflib
import os

def normalize(name):
    """
    Normalizes a name for better matching:
    1. Lowercase.
    2. Removes common prefixes like 'Parcel_', 'Improvement_', etc.
    3. Removes underscores, spaces, and dots.
    4. Handles common real estate abbreviations.
    """
    if not name:
        return ""
    
    name = name.lower().strip()
    
    # Remove common prefixes followed by underscores or spaces
    prefixes = [
        'parcel_', 'improvement_', 'sales_', 'sites_', 'rent roll summary_', 
        'unit lease summary_', 'incexp_', 'assessment_', 'saleinfo_', 'unit lease_'
    ]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
            
    # Remove all non-alphanumeric characters
    name = re.sub(r'[^a-z0-9]', '', name)
    
    # Common abbreviations/synonyms mapping (normalized)
    synonyms = {
        'sf': 'squarefeet',
        'sqft': 'squarefeet',
        'sqfeet': 'squarefeet',
        'ra': 'rentablearea',
        'gla': 'grossleasablearea',
        'gba': 'grossbuildingarea',
        'bldg': 'building',
        'yr': 'year',
        'no': 'number',
        'noof': 'numberof',
        'addr': 'address',
        'amt': 'amount',
        'prop': 'property'
    }
    
    # Simple replacement for common terms if they are distinct parts of the string
    # Not perfect but helps with 'bldg_sf' -> 'buildingsquarefeet'
    for abbr, full in synonyms.items():
        if abbr in name:
            # We only replace if it's a major part or exact
            name = name.replace(abbr, full)
            
    return name

def get_similarity_score(str1, str2):
    """Calculate similarity score between two strings."""
    norm1 = normalize(str1)
    norm2 = normalize(str2)
    
    if not norm1 or not norm2:
        return 0
    
    if norm1 == norm2:
        return 1.0
        
    # Difflib similarity
    return difflib.SequenceMatcher(None, norm1, norm2).ratio()

def align_lightbox_data(input_file, output_file):
    print(f"Reading {input_file}...")
    
    rows = []
    lb_candidates = []
    
    # First pass: read data and collect all LightBox candidates
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
            lb_val = row.get('Field LightBox Data', '').strip()
            if lb_val and lb_val not in lb_candidates:
                lb_candidates.append(lb_val)

    print(f"Found {len(lb_candidates)} LightBox candidates.")
    
    used_candidates = set()
    matches_count = 0
    
    # Second pass: for each Field ERD, find the best LightBox candidate
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
            
            # Threshold for confidence
            if score > best_score and score > 0.8:
                best_score = score
                best_match = cand
        
        if best_match:
            row['Field Lighboxdata aligned'] = best_match
            used_candidates.add(best_match)
            matches_count += 1
        else:
            row['Field Lighboxdata aligned'] = ''

    print(f"Successfully aligned {matches_count} fields.")

    # Identify unmatched candidates
    unmatched_candidates = [cand for cand in lb_candidates if cand not in used_candidates]
    print(f"Found {len(unmatched_candidates)} unmatched LightBox fields. Appending to the end...")

    # Create new rows for unmatched candidates starting from the last row
    for cand in unmatched_candidates:
        new_row = {key: '' for key in fieldnames}
        # new_row['Field LightBox Data'] = cand
        new_row['Field Lighboxdata aligned'] = cand
        rows.append(new_row)

    # Write the results back
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Aligned data saved to {output_file}")

if __name__ == "__main__":
    input_csv = "Industrial_mappings.csv"
    output_csv = "Industrial_mappings_aligned.csv"
    
    if os.path.exists(input_csv):
        align_lightbox_data(input_csv, output_csv)
    else:
        print(f"Error: {input_csv} not found.")
