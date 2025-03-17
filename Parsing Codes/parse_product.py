import csv
from tqdm import tqdm

# Define input and output file paths
metadata_file = '..\\Amazon Dataset\\amazon-meta.txt'  # Replace with the actual metadata file name
output_csv = '..\\Parsed Data\\product_data.csv'

# Initialize data structure for products
products = []

try:
    # Parse the metadata file
    print("Parsing metadata file...")
    with open(metadata_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    current_product = {}
    for line in tqdm(lines, desc="Processing metadata"):
        line = line.strip()
        if line.startswith("Id:"):
            if current_product:
                products.append(current_product)
            current_product = {"Id": line.split(":")[1].strip()}
        elif line.startswith("ASIN:"):
            current_product["ASIN"] = line.split(":")[1].strip()
        elif line.startswith("title:"):
            current_product["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("salesrank:"):
            current_product["salesrank"] = int(line.split(":")[1].strip())
        elif "avg rating:" in line:
            try:
                # Split the line by spaces and extract the average rating
                parts = line.split()
                avg_rating_index = parts.index("avg") + 2  # Find the index of "avg" and get the next element
                avg_rating = float(parts[avg_rating_index])  # Convert to float
                current_product["avg_rating"] = avg_rating
            except (ValueError, IndexError) as e:
                print(f"Error extracting avg rating from line: {line} - {e}")
                current_product["avg_rating"] = 0.0  # Default to 0.0 if extraction fails

    if current_product:
        products.append(current_product)

    # Write the extracted data to a CSV file
    print("Writing product data to CSV...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Id", "ASIN", "title", "salesrank", "avg_rating"])
        for product in tqdm(products, desc="Writing to CSV"):
            writer.writerow([
                product.get("Id", ""),
                product.get("ASIN", ""),
                product.get("title", ""),
                product.get("salesrank", ""),
                product.get("avg_rating", 0.0)  # Write avg_rating as a float
            ])

    print(f"CSV file '{output_csv}' created successfully.")

except FileNotFoundError:
    print(f"Error: File '{metadata_file}' not found. Please ensure the file exists in the specified directory.")