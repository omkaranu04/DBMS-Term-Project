import csv
from tqdm import tqdm

# Define input and output file paths
metadata_file = 'Amazon Dataset\\amazon-meta.txt'  # Replace with the actual metadata file name
output_csv = 'Parsed Data\\product_similar.csv'

# Initialize data structure for product-similar relationships
product_similar = []

try:
    # Parse the metadata file
    print("Parsing metadata file...")
    with open(metadata_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    current_product = {}
    for line in tqdm(lines, desc="Processing metadata"):
        line = line.strip()
        if line.startswith("Id:"):
            if "Id" in current_product and "similar" in current_product:
                for similar_id in current_product["similar"]:
                    product_similar.append({"Id": current_product["Id"], "Similar": similar_id})
            current_product = {"Id": line.split(":")[1].strip()}
        elif line.startswith("similar:"):
            similar_products = line.split()[2:]  # Extract all ASINs after "similar:"
            current_product["similar"] = similar_products

    # Add the last product if it has both Id and similar products
    if "Id" in current_product and "similar" in current_product:
        for similar_id in current_product["similar"]:
            product_similar.append({"Id": current_product["Id"], "Similar": similar_id})

    # Write the extracted data to a CSV file
    print("Writing product similar data to CSV...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Id", "Similar"])  # Header row
        for entry in tqdm(product_similar, desc="Writing to CSV"):
            writer.writerow([entry["Id"], entry["Similar"]])

    print(f"CSV file '{output_csv}' created successfully.")

except FileNotFoundError:
    print(f"Error: File '{metadata_file}' not found. Please ensure the file exists in the specified directory.")
