import math
from neo4j import GraphDatabase
from tqdm import tqdm

NEO4J_URI = "bolt://localhost:7687" 
NEO4J_USER = "neo4j" 
NEO4J_PASSWORD = "amazon@dbms"  

def calculate_product_scores(iterations=5):
    """
    Calculate and update product scores in Neo4j using two metrics:
    1. intrinsic_score = (2 ^ avg_rating) * log2(1 + sum of all helpful)
    2. total_score = intrinsic_score + sum for all co-purchased products j with frequency >= 3:
       (frequency_j / total_frequency) * total_score_j
    
    All scores are rounded to 2 decimal places.
    
    Args:
        iterations (int): Number of iterations to run for the total_score calculation
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Get total product count for progress bars
            total_products = session.run("MATCH (p:Product) RETURN count(p) AS count").single()["count"]
            print(f"Found {total_products} products in the database")
            
            # Step 1: Calculate intrinsic scores
            print("\nStep 1: Calculating intrinsic scores...")
            intrinsic_progress = tqdm(total=total_products, desc="Intrinsic score calculation", unit="products")
            
            intrinsic_query = """
            MATCH (p:Product)
            OPTIONAL MATCH (u:Consumer)-[r:REVIEWED]->(p)
            WITH p, AVG(r.Rating) AS avg_rating, SUM(r.Helpful) AS total_helpful
            SET p.intrinsic_score = round(
                CASE 
                    WHEN avg_rating IS NULL THEN 0.0
                    ELSE (2.0 ^ avg_rating) * (LOG(1.0 + COALESCE(total_helpful, 0)) / LOG(2))
                END
            , 2)
            RETURN count(p) AS updated_count
            """
            
            result = session.run(intrinsic_query)
            updated_count = result.single()["updated_count"]
            intrinsic_progress.update(updated_count)
            intrinsic_progress.close()
            print(f"✓ Updated intrinsic scores for {updated_count} products")
            
            # Step 2: Initialize total_score with intrinsic_score
            print("\nStep 2: Initializing total scores...")
            init_progress = tqdm(total=total_products, desc="Total score initialization", unit="products")
            
            init_query = """
            MATCH (p:Product)
            SET p.total_score = p.intrinsic_score
            RETURN count(p) AS updated_count
            """
            
            result = session.run(init_query)
            updated_count = result.single()["updated_count"]
            init_progress.update(updated_count)
            init_progress.close()
            print(f"✓ Initialized total scores for {updated_count} products")
            
            # Step 3: Run iterations for total_score
            print("\nStep 3: Running iterations to update total scores...")
            iteration_progress = tqdm(range(iterations), desc="Total score iterations", unit="iter")
            
            for i in iteration_progress:
                iter_num = i + 1
                
                # Count products with co-purchase relationships for better progress tracking
                copurchase_count = session.run("""
                    MATCH (p:Product)-[r:COPURCHASED_WITH]->(:Product) 
                    WHERE r.Frequency >= 2 
                    RETURN count(DISTINCT p) AS count
                """).single()["count"]
                
                update_progress = tqdm(total=total_products, 
                                      desc=f"Iteration {iter_num}/{iterations}", 
                                      unit="products",
                                      leave=False)
                
                update_query = """
                MATCH (p:Product)
                
                WITH p, p.intrinsic_score AS intrinsic_score
                
                OPTIONAL MATCH (p)-[co:COPURCHASED_WITH]->(other:Product)
                WHERE co.Frequency >= 2
                
                WITH p, intrinsic_score,
                     collect({
                         product: other, 
                         frequency: co.Frequency, 
                         score: other.total_score
                     }) AS co_purchases
                
                WITH p, intrinsic_score, co_purchases,
                     REDUCE(total = 0, item IN co_purchases | total + item.frequency) AS total_frequency
                
                WITH p, intrinsic_score,
                     CASE WHEN total_frequency > 0 THEN
                         REDUCE(sum = 0, item IN co_purchases | 
                             sum + (item.frequency / toFloat(total_frequency)) * item.score
                         )
                     ELSE 0 END AS co_purchase_score
                
                SET p.total_score = round(intrinsic_score + co_purchase_score * 0.5, 2)
                
                RETURN count(p) AS updated_count
                """
                
                result = session.run(update_query)
                updated_count = result.single()["updated_count"]
                update_progress.update(updated_count)
                update_progress.close()
                
                iteration_progress.set_postfix({"updated": updated_count})
                print(f"✓ Updated total scores for {updated_count} products in iteration {iter_num}")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.close()
        print("\nProduct score calculation completed!")

if __name__ == "__main__":
    calculate_product_scores(iterations=5)