import csv

# Define input and output file paths
input_csv = 'Parsed Data\\product_reviews.csv'  # Path to the input CSV file
output_csv = 'Parsed Data\\customers.csv'  # Path to the output CSV file

# Initialize a set to store unique customers
unique_customers = set()

try:
    # Read the product reviews from the input CSV file
    with open(input_csv, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            unique_customers.add(row['Customer'])  # Add customer to the set

    # Write the unique customers to the output CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Customer'])  # Write header
        for customer in unique_customers:
            writer.writerow([customer])  # Write each unique customer

    print(f"Unique customers have been written to '{output_csv}' successfully.")

except FileNotFoundError:
    print(f"Error: File '{input_csv}' not found. Please ensure the file exists in the specified directory.")