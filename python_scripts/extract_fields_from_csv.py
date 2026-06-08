import csv

# Input and output file names
input_csv = "industrial mappings aligned.csv"
output_csv = "industrial.csv"

# Column name you want to extract
column_name = "Field Lighboxdata aligned"

# Read the column data
column_data = []

with open(input_csv, mode="r", newline="", encoding="utf-8") as infile:
    reader = csv.DictReader(infile)

    # Check if column exists
    if column_name not in reader.fieldnames:
        raise ValueError(f"Column '{column_name}' not found in CSV file.")

    for row in reader:
        column_data.append([row[column_name]])

# Write to new CSV
with open(output_csv, mode="w", newline="", encoding="utf-8") as outfile:
    writer = csv.writer(outfile)

    # Write header
    writer.writerow([column_name])

    # Write column values
    writer.writerows(column_data)

print(f"Column '{column_name}' copied successfully to '{output_csv}'")