import pandas as pd
from tqdm import tqdm

# Define input CSV file paths
csv_files = [
    '..\\Parsed Data\\copurchased0302.csv',
    '..\\Parsed Data\\copurchased0312.csv',
    '..\\Parsed Data\\copurchased0505.csv',
    '..\\Parsed Data\\copurchased0601.csv'
]

# Output file path
output_file = '..\\Parsed Data\\copurchased_frequencies.csv'

def calculate_edge_frequencies(csv_files, output_file):
    print("Calculating edge frequencies...")
    
    # Combine data from all CSVs
    combined_data = pd.DataFrame()
    for file in tqdm(csv_files, desc="Reading CSV files"):
        try:
            data = pd.read_csv(file)
            combined_data = pd.concat([combined_data, data], ignore_index=True)
        except FileNotFoundError:
            print(f"File not found: {file}. Skipping...")
    
    # Check if combined_data is empty
    if combined_data.empty:
        print("No valid data found in the provided CSV files.")
        return
    
    # Ensure columns are properly named
    if 'FromNodeId' not in combined_data.columns or 'ToNodeId' not in combined_data.columns:
        raise KeyError("Columns 'FromNodeId' and 'ToNodeId' are missing from the input CSV files.")
    
    # Group by FromNodeId and ToNodeId to calculate frequency
    grouped_data = combined_data.groupby(['FromNodeId', 'ToNodeId']).size().reset_index(name='Frequency')
    
    # Save the frequency data to a new CSV file
    grouped_data.to_csv(output_file, index=False)
    print(f"Edge frequencies saved to {output_file}")

# Execute the function
calculate_edge_frequencies(csv_files, output_file)