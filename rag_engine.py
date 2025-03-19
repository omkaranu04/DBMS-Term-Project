from embeddings import EmbeddingEngine
from config import neo4j_conn

class RAGEngine:
    def __init__(self):
        self.embedding_engine = EmbeddingEngine()
    
    def process_query(self, query):
        similar_items = self.embedding_engine.find_similar(query)
        
        top_categories = [item[0] for item in similar_items["categories"]]
        top_groups = [item[0] for item in similar_items["groups"]]
        
        category_products = self._fetch_products_by_categories(top_categories)
        
        group_products = self._fetch_products_by_groups(top_groups)
        
        all_products = category_products + group_products
        
        response = self._generate_response(query, top_categories, top_groups, all_products)
        
        return {
            "response": response,
            "products": all_products[:10], 
            "categories": top_categories,
            "groups": top_groups
        }
    
    def _fetch_products_by_categories(self, categories, limit=5):
        if not categories:
            return []
        
        params = {"categories": categories}
        query = """
        MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
        WHERE c.name IN $categories
        RETURN DISTINCT p.title AS title, p.ASIN AS asin
        LIMIT {limit}
        """.format(limit=limit)
        
        result = neo4j_conn.query(query, parameters=params)
        return [{"title": record["title"], "asin": record["asin"]} for record in result]
    
    def _fetch_products_by_groups(self, groups, limit=5):
        if not groups:
            return []
        
        params = {"groups": groups}
        query = """
        MATCH (p:Product)-[:PART_OF]->(g:Group)
        WHERE g.name IN $groups
        RETURN DISTINCT p.title AS title, p.ASIN AS asin
        LIMIT {limit}
        """.format(limit=limit)
        
        result = neo4j_conn.query(query, parameters=params)
        return [{"title": record["title"], "asin": record["asin"]} for record in result]
    
    def _generate_response(self, query, categories, groups, products):
        if not products:
            return f"I couldn't find any products related to '{query}'. Try a different search term."
        
        response = f"Based on your query '{query}', I found products in "
        
        if categories:
            response += f"categories like {', '.join(categories[:2])}"
            
        if groups:
            if categories:
                response += " and "
            response += f"groups like {', '.join(groups[:2])}"
        
        response += f". I've found {len(products)} relevant products for you."
        return response