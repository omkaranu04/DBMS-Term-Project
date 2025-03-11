import pandas as pd

# Read the network data file
network_df = pd.read_csv('Amazon Dataset\Amazon0601.txt', 
                         sep='\t', 
                         skiprows=4,  # Skip the header comments
                         names=['FromNodeId', 'ToNodeId'])

# Save as CSV for Neo4j import
network_df.to_csv('amazon_relationships_0601.csv', index=False)