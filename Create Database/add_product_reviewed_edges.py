from neo4j import GraphDatabase
import csv
from tqdm import tqdm

# Define the Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"  # Update with your Neo4j URI
NEO4J_USER = "neo4j"  # Update with your Neo4J username
NEO4J_PASSWORD = "amazon@dbms"  # Update with your Neo4J password

# Define input CSV file path
csv_file = '..\\Parsed Data\\product_reviews.csv'  # Replace with the actual path to your product_reviews.csv file

# Define batch size for APOC processing
BATCH_SIZE = 1000

def create_reviewed_relationships(csv_file, uri, user, password):
    # Connect to Neo4j
    driver = GraphDatabase.driver(uri, auth=(user, password))
    session = driver.session()

    try:
        # Read the CSV file
        print(f"Reading data from {csv_file}...")
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)  # Convert CSV rows to a list for batch processing
        
        print(f"Creating REVIEWED relationships in Neo4j using APOC batch processing...")
        
        # Batch process the rows using APOC
        for i in tqdm(range(0, len(rows), BATCH_SIZE), desc="Processing batches"):
            batch = rows[i:i + BATCH_SIZE]
            
            query = """
            CALL apoc.periodic.iterate(
                'UNWIND $rows AS row RETURN row',
                'MATCH (c:Consumer {Customer: row.Customer}), (p:Product {Id: row.Id})
                 USING INDEX c:Consumer(Customer)
                 USING INDEX p:Product(Id)
                 CREATE (c)-[:REVIEWED {Date: row.Date, Rating: toInteger(row.Rating),
                                        Votes: toInteger(row.Votes), Helpful: toInteger(row.Helpful)}]->(p)',
                {batchSize: $batchSize, params: {rows: $batch}}
            )
            """

            session.run(query, parameters={
                "batchSize": BATCH_SIZE,
                "batch": batch
            })

        print("REVIEWED relationships created successfully in Neo4j.")

    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found. Please ensure the file exists in the specified directory.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        session.close()
        driver.close()

# Run the function
create_reviewed_relationships(csv_file, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
