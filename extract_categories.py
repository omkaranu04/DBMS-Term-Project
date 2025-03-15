import csv

# Define input and output file paths
input_csv = 'Parsed Data\\product_categories.csv'  # Path to the input CSV file
output_csv = 'Parsed Data\\categories.csv'          # Path to the output CSV file

# Initialize a set to store unique categories
unique_categories = set()

try:
    # Read the product categories from the input CSV file
    with open(input_csv, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            unique_categories.add(row['Category'])  # Add category to the set

    # Write the unique categories to the output CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Category'])  # Write header
        for category in unique_categories:
            writer.writerow([category])  # Write each unique category

    print(f"Unique categories have been written to '{output_csv}' successfully.")

except FileNotFoundError:
    print(f"Error: File '{input_csv}' not found. Please ensure the file exists in the specified directory.")