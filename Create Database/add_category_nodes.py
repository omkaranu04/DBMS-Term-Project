from neo4j import GraphDatabase
import csv
from tqdm import tqdm

# Define the Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"  # Update with your Neo4j URI
NEO4J_USER = "neo4j"  # Update with your Neo4j username
NEO4J_PASSWORD = "amazon@dbms"  # Update with your Neo4j password

# Define input CSV file path
csv_file = '..\\Parsed Data\\categories.csv'  # Replace with the actual path to your categories.csv file

# Define batch size for APOC processing
BATCH_SIZE = 1000

def create_category_nodes_and_index_in_neo4j(csv_file, uri, user, password):
    # Connect to Neo4j
    driver = GraphDatabase.driver(uri, auth=(user, password))
    session = driver.session()

    try:
        # Read the CSV file
        print(f"Reading data from {csv_file}...")
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)  # Convert CSV rows to a list for batch processing
        
        print(f"Creating category nodes in Neo4j using APOC batch processing...")
        
        # Batch process the rows using APOC
        for i in tqdm(range(0, len(rows), BATCH_SIZE), desc="Processing batches"):
            batch = rows[i:i + BATCH_SIZE]
            
            query = """
            CALL apoc.periodic.iterate(
                'UNWIND $rows AS row RETURN row',
                'CREATE (c:Category {name: row.Category})',
                {batchSize: $batchSize, params: {rows: $batch}}
            )
            """

            session.run(query, parameters={
                "batchSize": BATCH_SIZE,
                "batch": batch
            })

        print("Category nodes created successfully in Neo4j.")

        # Create index on the name property of Category nodes
        print("Creating index on Category name field...")
        session.run("CREATE INDEX category_name_index IF NOT EXISTS FOR (c:Category) ON (c.name)")
        print("Index created successfully.")

    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found. Please ensure the file exists in the specified directory.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        session.close()
        driver.close()

# Run the function
create_category_nodes_and_index_in_neo4j(csv_file, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)