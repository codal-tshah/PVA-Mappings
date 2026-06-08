import re

input_file = "ERD/NEW_ERD.sql"
output_file = "lists.txt"

all_fields = []

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:

        line = line.strip()

        # ONLY skip constraints
        if (
            line.startswith("PRIMARY KEY")
            or line.startswith("FOREIGN KEY")
            or line.startswith("REFERENCES")
            or line.startswith("KEY ")
            or line.startswith("CREATE TABLE")
            or line.startswith(");")
        ):
            continue

        # Extract EVERY column name
        match = re.match(r"`([^`]+)`", line)

        if match:
            field_name = match.group(1)

            # DO NOT REMOVE DUPLICATES
            all_fields.append(field_name)

# Write flat list exactly as encountered
with open(output_file, "w", encoding="utf-8") as f:
    for field in all_fields:
        f.write(field + "\n")

print(f"Done. {len(all_fields)} fields written.")