import csv
from tqdm import tqdm

# Define input and output file paths
metadata_file = '.\\Amazon Dataset\\amazon-meta.txt'  # Replace with the actual metadata file name
output_csv = '.\\Parsed Data\\product_groups.csv'

# Initialize data structure for products with groups
product_groups = []

try:
    # Parse the metadata file
    print("Parsing metadata file...")
    with open(metadata_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    current_product = {}
    for line in tqdm(lines, desc="Processing metadata"):
        line = line.strip()
        if line.startswith("Id:"):
            if "Id" in current_product and "group" in current_product:
                product_groups.append(current_product)
            current_product = {"Id": line.split(":")[1].strip()}
        elif line.startswith("group:"):
            current_product["group"] = line.split(":")[1].strip()

    # Add the last product if it has both Id and group
    if "Id" in current_product and "group" in current_product:
        product_groups.append(current_product)

    # Write the extracted data to a CSV file
    print("Writing product group data to CSV...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Id", "group"])  # Header row
        for product in tqdm(product_groups, desc="Writing to CSV"):
            writer.writerow([product["Id"], product["group"]])

    print(f"CSV file '{output_csv}' created successfully.")

except FileNotFoundError:
    print(f"Error: File '{metadata_file}' not found. Please ensure the file exists in the specified directory.")
