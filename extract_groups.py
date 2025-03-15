import csv

# Define input and output file paths
input_csv = 'Parsed Data\\product_groups.csv'  # Path to the input CSV file
output_csv = 'Parsed Data\\groups.csv'   # Path to the output CSV file

# Initialize a set to store unique groups
unique_groups = set()

try:
    # Read the product groups from the input CSV file
    with open(input_csv, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            unique_groups.add(row['group'])  # Add group to the set

    # Write the unique groups to the output CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['group'])  # Write header
        for group in unique_groups:
            writer.writerow([group])  # Write each unique group

    print(f"Unique groups have been written to '{output_csv}' successfully.")

except FileNotFoundError:
    print(f"Error: File '{input_csv}' not found. Please ensure the file exists in the specified directory.")