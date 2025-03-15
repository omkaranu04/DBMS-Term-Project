import csv
from tqdm import tqdm

# Define input and output file paths
metadata_file = 'Amazon Dataset\\amazon-meta.txt'  # Replace with the actual metadata file name
output_csv = 'Parsed Data\\product_reviews.csv'

# Initialize data structure for product reviews
product_reviews = []

try:
    # Parse the metadata file
    print("Parsing metadata file...")
    with open(metadata_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    current_product = {}
    for line in tqdm(lines, desc="Processing metadata"):
        line = line.strip()
        if line.startswith("Id:"):
            if "Id" in current_product and "reviews" in current_product:
                for review in current_product["reviews"]:
                    product_reviews.append({
                        "Id": current_product["Id"],
                        "Customer": review["customer"],
                        "Date": review["date"],
                        "Rating": review["rating"],
                        "Votes": review["votes"],
                        "Helpful": review["helpful"]
                    })
            current_product = {"Id": line.split(":")[1].strip(), "reviews": []}  # Initialize reviews list for the new product
        elif line.startswith("reviews:"):
            # This line indicates the start of reviews, we can skip it
            continue
        elif "cutomer:" in line:  # Handle the typo here
            # Extract customer, date, rating, votes, and helpful information
            parts = line.split()
            if len(parts) >= 9:  # Ensure there are enough parts to avoid index errors
                review_data = {
                    "date": parts[0],
                    "customer": parts[2],  # Use the typo "cutomer" to extract the customer ID
                    "rating": int(parts[4]),
                    "votes": int(parts[6]),
                    "helpful": int(parts[8])
                }
                current_product["reviews"].append(review_data)
            else:
                print(f"Skipping line due to unexpected format: {line}")

    # Add the last product's reviews if applicable
    if "Id" in current_product and "reviews" in current_product:
        for review in current_product["reviews"]:
            product_reviews.append({
                "Id": current_product["Id"],
                "Customer": review["customer"],
                "Date": review["date"],
                "Rating": review["rating"],
                "Votes": review["votes"],
                "Helpful": review["helpful"]
            })

    # Write the extracted data to a CSV file
    print("Writing product reviews data to CSV...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Id", "Customer", "Date", "Rating", "Votes", "Helpful"])  # Header row
        for entry in tqdm(product_reviews, desc="Writing to CSV"):
            writer.writerow([
                entry["Id"], entry["Customer"], entry["Date"], entry["Rating"], entry["Votes"], entry["Helpful"]
            ])

    print(f"CSV file '{output_csv}' created successfully.")

except FileNotFoundError:
    print(f"Error: File '{metadata_file}' not found. Please ensure the file exists in the specified directory.")