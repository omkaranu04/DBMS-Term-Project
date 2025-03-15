from neo4j import GraphDatabase
import csv
from tqdm import tqdm

# Define the Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"  # Update with your Neo4j URI
NEO4J_USER = "neo4j"  # Update with your Neo4j username
NEO4J_PASSWORD = "amazon@dbms"  # Update with your Neo4j password

# Define input CSV file path
csv_file = '..\\Parsed Data\\product_data.csv'  # Replace with the actual path to your CSV file

# Define batch size for APOC processing
BATCH_SIZE = 1000

def create_nodes_and_index_in_neo4j(csv_file, uri, user, password):
    # Connect to Neo4j
    driver = GraphDatabase.driver(uri, auth=(user, password))
    session = driver.session()

    try:
        # Read the CSV file
        print(f"Reading data from {csv_file}...")
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)  # Convert CSV rows to a list for batch processing
        
        print(f"Creating nodes in Neo4j using APOC batch processing...")
        
        # Batch process the rows using APOC
        for i in tqdm(range(0, len(rows), BATCH_SIZE), desc="Processing batches"):
            batch = rows[i:i + BATCH_SIZE]
            
            query = """
            CALL apoc.periodic.iterate(
                'UNWIND $rows AS row RETURN row',
                'CREATE (p:Product {Id: row.Id, ASIN: row.ASIN, title: row.title,
                                    salesrank: toInteger(row.salesrank),
                                    avg_rating: toFloat(row.avg_rating)})',
                {batchSize: $batchSize, params: {rows: $batch}}
            )
            """

            session.run(query, parameters={
                "batchSize": BATCH_SIZE,
                "batch": batch
            })

        print("Nodes created successfully in Neo4j.")

        # Create indexes on Id and ASIN fields
        print("Creating indexes on Id and ASIN fields...")
        session.run("CREATE INDEX product_id_index IF NOT EXISTS FOR (p:Product) ON (p.Id)")
        session.run("CREATE INDEX product_asin_index IF NOT EXISTS FOR (p:Product) ON (p.ASIN)")
        print("Indexes created successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        session.close()
        driver.close()

# Run the function
create_nodes_and_index_in_neo4j(csv_file, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)