import re
import difflib

def normalize(name):
    """
    Normalizes a field name by:
    1. Lowercasing everything.
    2. Removing common table/subrecord prefixes (e.g., 'improvement_subrecords_').
    3. Removing all underscores and dots.
    """
    if not name:
        return ""
    
    # Lowercase
    name = name.lower().strip()
    
    # Remove common prefixes found in list.txt
    prefixes = ['improvement_subrecords_', 'zoning_subrecords_']
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
            
    # Remove all non-alphanumeric characters (underscores, dots, spaces)
    name = re.sub(r'[^a-z0-9]', '', name)
    
    return name

def are_similar(name1, name2, threshold=0.9):
    """
    Checks if two field names are similar using normalization and fuzzy matching.
    """
    norm1 = normalize(name1)
    norm2 = normalize(name2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return True
    
    # Use difflib for fuzzy similarity on normalized names
    similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    return similarity >= threshold

def merge_erds(file1_path, file2_path, output_path):
    print(f"Reading {file1_path} and {file2_path}...")
    
    with open(file1_path, 'r') as f:
        list1 = [line.strip() for line in f if line.strip()]
        
    with open(file2_path, 'r') as f:
        list2 = [line.strip() for line in f if line.strip()]
    
    all_fields = list(set(list1 + list2))
    all_fields.sort() # Sorting for determinism
    
    merged_fields = []
    seen_normalized = {} # maps normalized_name -> original_name_to_keep

    for field in all_fields:
        norm = normalize(field)
        
        # Check if we already have a normalized version that is extremely similar
        found_match = False
        
        # Priority 1: Check exact normalized match
        if norm in seen_normalized:
            # We already have this field. Keep the one with underscores if possible
            # as it's usually more readable.
            if '_' in field and '_' not in seen_normalized[norm]:
                seen_normalized[norm] = field
            found_match = True
        else:
            # Priority 2: Fuzzy check against existing seen fields
            for existing_norm, original in seen_normalized.items():
                if are_similar(norm, existing_norm, threshold=0.95):
                    # Extremely high similarity, likely the same field
                    found_match = True
                    # Keep the more "descriptive" name (the one with underscores)
                    if field.count('_') > original.count('_'):
                        seen_normalized[existing_norm] = field
                    break
        
        if not found_match:
            seen_normalized[norm] = field

    # Collect the final unique names
    final_list = sorted(list(seen_normalized.values()))

    print(f"Original field count: {len(all_fields)}")
    print(f"Merged unique field count: {len(final_list)}")

    with open(output_path, 'w') as f:
        for field in final_list:
            f.write(field + '\n')
            
    print(f"Final merged list saved to {output_path}")

if __name__ == "__main__":
    merge_erds("old_ERD_fields.txt", "new_ERD_fields.txt", "merged_fields.txt")
