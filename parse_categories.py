import csv
from tqdm import tqdm

# Define input and output file paths
metadata_file = 'Amazon Dataset\\amazon-meta.txt'  # Replace with the actual metadata file name
output_csv = 'Parsed Data\\product_categories.csv'

# Initialize data structure for product-category relationships
product_categories = []

try:
    # Parse the metadata file
    print("Parsing metadata file...")
    with open(metadata_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    current_product = {}
    for line in tqdm(lines, desc="Processing metadata"):
        line = line.strip()
        if line.startswith("Id:"):
            if "Id" in current_product and "categories" in current_product:
                # Add unique categories for the current product
                unique_categories = set(current_product["categories"])
                for category in unique_categories:
                    product_categories.append({"Id": current_product["Id"], "Category": category})
            current_product = {"Id": line.split(":")[1].strip()}
            current_product["categories"] = []  # Initialize categories list for the new product
        elif line.startswith("|"):
            # Extract all category levels from the path
            category_path = line.strip()
            # Split by | and extract category names (removing brackets and numbers)
            categories = []
            for part in category_path.split("|"):
                if part and "[" in part:  # Skip empty parts and ensure it has a category
                    category_name = part.split("[")[0].strip()
                    if category_name:  # Add non-empty category names
                        categories.append(category_name)
            
            # Add each individual category to the list
            current_product["categories"].extend(categories)

    # Add the last product if it has both Id and categories
    if "Id" in current_product and "categories" in current_product:
        unique_categories = set(current_product["categories"])
        for category in unique_categories:
            product_categories.append({"Id": current_product["Id"], "Category": category})

    # Write the extracted data to a CSV file
    print("Writing product categories data to CSV...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Id", "Category"])  # Header row
        for entry in tqdm(product_categories, desc="Writing to CSV"):
            writer.writerow([entry["Id"], entry["Category"]])

    print(f"CSV file '{output_csv}' created successfully.")

except FileNotFoundError:
    print(f"Error: File '{metadata_file}' not found. Please ensure the file exists in the specified directory.")