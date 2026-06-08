import re
import os

def extract_fields(input_file, output_file):
    # Regex to match field names inside backticks that are part of a table definition
    # We look for lines starting with whitespace, then a backtick, then the field name, then a backtick.
    field_pattern = re.compile(r'^\s*`([^`]+)`', re.MULTILINE)

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r') as f:
        content = f.read()

    # Find all matches
    matches = field_pattern.findall(content)

    # Some matches might be table names if they are at the start of the line or in different contexts.
    # However, in this specific SQL structure provided, Table names follow 'CREATE TABLE '
    # and field names are indented. The regex '^\s*`([^`]+)`' handles this well by looking for leading whitespace.
    
    # Let's also exclude matches that are actually table names just in case.
    # Table names are usually followed by '(' or part of 'CREATE TABLE `name`'
    # table_names = re.findall(r'CREATE TABLE `([^`]+)`', content)
    
    # Filter out table names from the fields list
    # fields = [m for m in matches if m not in table_names]

    # Remove duplicates while preserving order
    unique_fields = []
    seen = set()
    # for field in fields:
    #     if field not in seen:
    #         unique_fields.append(field)
    #         seen.add(field)

    with open(output_file, 'w') as f:
        for field in unique_fields:
            f.write(field + '\n')

    print(f"Successfully extracted {len(unique_fields)} fields to {output_file}")

if __name__ == "__main__":
    input_sql = "testttt.py"
    output_txt = "test.txt"
    extract_fields(input_sql, output_txt)
