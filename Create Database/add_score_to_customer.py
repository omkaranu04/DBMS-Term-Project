from neo4j import GraphDatabase
from tqdm import tqdm
import time

NEO4J_URI = "bolt://localhost:7687" 
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "amazon@dbms"
BATCH_SIZE = 1000

def update_consumer_scores_apoc(uri, user, password):
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        print("✅ Connection to Neo4j successful")
    except Exception as e:
        print(f"❌ Connection to Neo4j failed: {e}")
        print(f"Please check if Neo4j is running and accessible at {uri}")
        return

    try:
        print("Starting APOC-based consumer score update...")
        
        with driver.session() as session:
            count_result = session.run("""
                MATCH (c:Consumer)-[r:REVIEWED]->()
                WHERE c.Customer IS NOT NULL AND r.Helpful IS NOT NULL
                RETURN count(DISTINCT c) as consumer_count
            """)
            consumer_count = count_result.single()["consumer_count"]
        
        progress_bar = tqdm(total=consumer_count, desc="Updating consumer scores")
        
        # First, make sure scores are reset to avoid any stale data
        with driver.session() as session:
            session.run("MATCH (c:Consumer) REMOVE c.score")
            print("✅ Reset existing scores")
            
        # Fix the APOC query to correctly calculate and set scores
        with driver.session() as session:
            apoc_query = """
            CALL apoc.periodic.iterate(
                "
                MATCH (c:Consumer)-[r:REVIEWED]->()
                WHERE c.Customer IS NOT NULL AND r.Helpful IS NOT NULL
                RETURN DISTINCT c
                ",
                "
                MATCH (c)-[r:REVIEWED]->()
                WHERE r.Helpful IS NOT NULL
                WITH c, collect(r.Helpful) AS helpful_values
                WITH c, [val IN helpful_values | CASE WHEN val <= 0 THEN 0.0 ELSE toFloat(min(5.0, log10(1 + val) / log10(2))) END] AS logs
                WITH c, reduce(score = 0.0, x IN logs | score + x) AS final_score
                SET c.score = final_score
                ",
                {batchSize: $batchSize, parallel: false}
            ) YIELD batches, total, errorMessages
            RETURN batches, total, errorMessages
            """
            
            result = session.run(apoc_query, parameters={"batchSize": BATCH_SIZE})
            summary = result.single()
            total_batches = summary["batches"]
            total_processed = summary["total"]
            error_messages = summary["errorMessages"]
            
            if error_messages:
                print(f"⚠️ APOC reported errors: {error_messages}")
            else:
                print(f"✅ APOC processed {total_processed} consumers in {total_batches} batches")
                
            progress_bar.n = consumer_count
            progress_bar.refresh()
            progress_bar.close()
            
            # Verify the update worked
            verify_result = session.run("""
                MATCH (c:Consumer)
                WHERE c.score IS NOT NULL
                RETURN count(c) as updated_count
            """)
            final_count = verify_result.single()["updated_count"]
            print(f"Updated {final_count} consumer scores out of {consumer_count} total consumers")
            
            if final_count < consumer_count:
                print("⚠️ Not all consumers were updated. Running diagnostic query...")
                # Diagnostic query to find consumers that weren't updated
                diagnostic = session.run("""
                    MATCH (c:Consumer)-[r:REVIEWED]->()
                    WHERE c.Customer IS NOT NULL AND r.Helpful IS NOT NULL AND c.score IS NULL
                    WITH c, count(r) as review_count
                    RETURN c.Customer as customer_id, review_count
                    LIMIT 5
                """)
                print("Sample of consumers without scores:")
                for record in diagnostic:
                    print(f"Customer {record['customer_id']} with {record['review_count']} reviews")

    except Exception as e:
        print(f"❌ Error during APOC score update: {e}")
    finally:
        if 'progress_bar' in locals() and not progress_bar.closed:
            progress_bar.close()
        driver.close()

if __name__ == "__main__":
    print("Make sure Neo4j is running before executing this script")
    update_consumer_scores_apoc(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
'''
CALL apoc.periodic.iterate(
    "
    MATCH (c:Consumer)-[r:REVIEWED]->()
    WHERE c.Customer IS NOT NULL AND r.Helpful IS NOT NULL
    RETURN DISTINCT c
    ",
    "
    MATCH (c)-[r:REVIEWED]->()
    WHERE r.Helpful IS NOT NULL
    WITH c, collect(r.Helpful) AS helpful_values
    WITH c, [val IN helpful_values | 
        CASE 
          WHEN val <= 0 THEN 0.0 
          ELSE 
            CASE
              WHEN log10(1 + val) / log10(2) > 5.0 THEN 5.0
              ELSE toFloat(log10(1 + val) / log10(2))
            END
        END
    ] AS logs
    WITH c, reduce(score = 0.0, x IN logs | score + x) AS final_score
    SET c.score = final_score
    ",
    {batchSize: 1000, parallel: false}
) YIELD batches, total, errorMessages
RETURN batches, total, errorMessages;
'''