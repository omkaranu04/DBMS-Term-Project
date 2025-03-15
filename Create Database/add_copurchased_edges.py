import pandas as pd
from neo4j import GraphDatabase
from tqdm import tqdm
# added testing because didn't work in first go
# Define the Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "amazon@dbms"

# Define input CSV file path
csv_file = '..\\Parsed Data\\copurchased_frequencies.csv'

# Define batch size
BATCH_SIZE = 1000

def create_copurchased_with_relationships(csv_file, uri, user, password):
    # Connect to Neo4j
    driver = GraphDatabase.driver(uri, auth=(user, password))
    session = driver.session()

    try:
        # First, let's check if the indices exist, and create them if they don't
        print("Ensuring indices exist...")
        session.run("CREATE INDEX product_id_index IF NOT EXISTS FOR (p:Product) ON (p.Id)")
        
        # Check product structure to verify ID format
        print("Checking product node structure...")
        result = session.run("MATCH (p:Product) RETURN p LIMIT 1")
        sample_product = result.single()
        if sample_product:
            print(f"Sample product: {sample_product}")
        else:
            print("No product nodes found in database!")
            return
        
        # Read the CSV file
        print(f"Reading data from {csv_file}...")
        data = pd.read_csv(csv_file)
        
        # Show sample data
        print(f"Sample data from CSV (first 5 rows):")
        print(data.head())
        
        # Count existing relationships
        result = session.run("MATCH ()-[r:COPURCHASED_WITH]->() RETURN COUNT(r) as count")
        count_before = result.single()["count"]
        print(f"Number of COPURCHASED_WITH relationships before: {count_before}")
        
        # Convert data to a list of dictionaries for batch processing
        rows = data.to_dict('records')
        
        # Check if there are rows to process
        if not rows:
            print("No data to process for creating relationships.")
            return
            
        print(f"Creating COPURCHASED_WITH relationships in Neo4j...")
        
        # Test with a direct approach for a small batch first
        test_batch = rows[:5]
        print("Testing with first 5 rows directly...")
        for row in test_batch:
            query = """
            MATCH (p1:Product), (p2:Product)
            WHERE p1.Id = toString($fromId) AND p2.Id = toString($toId)
            MERGE (p1)-[r:COPURCHASED_WITH]->(p2)
            SET r.Frequency = coalesce(r.Frequency, 0) + $freq
            RETURN p1.Id, p2.Id
            """
            result = session.run(query, parameters={
                "fromId": str(row["FromNodeId"]),
                "toId": str(row["ToNodeId"]),
                "freq": row["Frequency"]
            })
            print(f"Processed: {row} - Result: {result.consume().counters}")
            
        # Count relationships after test
        result = session.run("MATCH ()-[r:COPURCHASED_WITH]->() RETURN COUNT(r) as count")
        count_after_test = result.single()["count"]
        print(f"Number of COPURCHASED_WITH relationships after test: {count_after_test}")
        
        # If test was successful, process the rest
        if count_after_test > count_before:
            print("Test successful! Processing the rest of the data...")
            
            # Batch process the rows
            for i in tqdm(range(5, len(rows), BATCH_SIZE), desc="Processing batches"):
                batch = rows[i:i + BATCH_SIZE]
                
                query = """
                UNWIND $batch AS row
                MATCH (p1:Product), (p2:Product)
                WHERE p1.Id = toString(row.FromNodeId) AND p2.Id = toString(row.ToNodeId)
                MERGE (p1)-[r:COPURCHASED_WITH]->(p2)
                SET r.Frequency = coalesce(r.Frequency, 0) + row.Frequency
                """
                
                session.run(query, parameters={"batch": batch})
                
            # Final count
            result = session.run("MATCH ()-[r:COPURCHASED_WITH]->() RETURN COUNT(r) as count")
            final_count = result.single()["count"]
            print(f"Final number of COPURCHASED_WITH relationships: {final_count}")
        else:
            print("Test failed. No relationships were created.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
        driver.close()

# Run the function
create_copurchased_with_relationships(csv_file, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)