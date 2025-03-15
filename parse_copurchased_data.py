import os
import csv
from tqdm import tqdm

# Define input file paths and output directory
input_files = [
    'Amazon Dataset\\Amazon0302.txt',
    'Amazon Dataset\\Amazon0312.txt',
    'Amazon Dataset\\Amazon0505.txt',
    'Amazon Dataset\\Amazon0601.txt'
]
output_directory = './Parsed Data'  # Directory to save CSV files

# Ensure output directory exists
os.makedirs(output_directory, exist_ok=True)

try:
    # Process each input file
    for input_file in input_files:
        print(f"Parsing file: {input_file}")

        # Extract the date from the filename for naming convention
        base_name = os.path.basename(input_file)
        date_part = base_name.split('Amazon')[1].split('.')[0]  # Extract the date (e.g., "0302")
        output_csv = os.path.join(output_directory, f"copurchased{date_part}.csv")

        # Initialize data structure for edges
        edges = []

        # Read the file and parse edges
        with open(input_file, 'r', encoding='utf-8') as file:
            for line in tqdm(file, desc=f"Processing {input_file}"):
                line = line.strip()
                if not line.startswith("#") and line:  # Skip comment lines and empty lines
                    parts = line.split()
                    from_node, to_node = parts[0], parts[1]
                    edges.append({"FromNodeId": from_node, "ToNodeId": to_node})

        # Write edges to a CSV file
        print(f"Writing parsed data to {output_csv}...")
        with open(output_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["FromNodeId", "ToNodeId"])  # Header row
            for edge in tqdm(edges, desc=f"Writing to {output_csv}"):
                writer.writerow([edge["FromNodeId"], edge["ToNodeId"]])

        print(f"File '{output_csv}' created successfully.")

except FileNotFoundError as e:
    print(f"Error: {e}. Please ensure all input files exist in the specified directory.")