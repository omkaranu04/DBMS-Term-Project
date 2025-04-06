from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"  
NEO4J_USER = "neo4j" 
NEO4J_PASSWORD = "amazon@dbms" 

def execute_query(uri, user, password):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    query = """
    CALL apoc.periodic.iterate(
      "
      MATCH ()-[r:REVIEWED]->()
      WHERE r.Date IS NOT NULL
      RETURN r
      ",
      "
      WITH r, split(r.Date, '-') AS parts
      WITH r,
           toInteger(parts[0]) AS year,
           toInteger(parts[1]) AS month,
           toInteger(parts[2]) AS day
      SET r.Date = apoc.temporal.format(date({year: year, month: month, day: day}), 'yyyy-MM-dd')
      ",
      {batchSize: 1000, parallel: false}
    )
    YIELD batches, total
    RETURN batches, total
    """
    
    try:
        with driver.session() as session:
            print("Executing query...")
            result = session.run(query)
            
            record = result.single()
            if record:
                print("\nQuery completed successfully!")
                print(f"Batches: {record['batches']}")
                print(f"Total: {record['total']}")
            else:
                print("Query executed but returned no results")
                
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()
        print("Connection closed")

if __name__ == "__main__":
    print("Starting date format conversion...")
    execute_query(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    print("Process completed")
    
'''
CALL apoc.periodic.iterate(
  "
  MATCH ()-[r:REVIEWED]->()
  WHERE r.Date IS NOT NULL
  RETURN r
  ",
  "
  WITH r, split(r.Date, '-') AS parts
  WITH r,
       toInteger(parts[0]) AS year,
       toInteger(parts[1]) AS month,
       toInteger(parts[2]) AS day
  SET r.Date = apoc.temporal.format(date({year: year, month: month, day: day}), 'yyyy-MM-dd')
  ",
  {batchSize: 1000, parallel: false}
)
'''