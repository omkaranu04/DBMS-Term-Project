from embeddings import EmbeddingEngine
from config import neo4j_conn

class RAGEngine:
    def __init__(self):
        self.embedding_engine = EmbeddingEngine()
    
    def process_query(self, query):
        # Find similar items across categories, groups, and products
        similar_items = self.embedding_engine.find_similar(query)
        
        top_categories = [item[0] for item in similar_items["categories"]]
        top_groups = [item[0] for item in similar_items["groups"]]
        
        # Extract direct product matches if available
        direct_product_matches = []
        if "products" in similar_items and similar_items["products"]:
            direct_product_matches = [
                {"title": item[0], "asin": item[1], "score": item[2]} 
                for item in similar_items["products"]
            ]
        
        # Fetch additional products from categories and groups
        category_products = self._fetch_products_by_categories(top_categories)
        group_products = self._fetch_products_by_groups(top_groups)
        
        # Combine all products, prioritizing direct matches
        all_products = direct_product_matches + [
            p for p in (category_products + group_products) 
            if p["asin"] not in [dp["asin"] for dp in direct_product_matches]
        ]
        
        # Generate response
        response = self._generate_response(query, top_categories, top_groups, all_products, 
                                          has_direct_matches=len(direct_product_matches) > 0)
        
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
    
    def _generate_response(self, query, categories, groups, products, has_direct_matches=False):
        if not products:
            return f"I couldn't find any products related to '{query}'. Try a different search term."
        
        if has_direct_matches:
            response = f"I found products that directly match your query '{query}'"
            
            if categories or groups:
                response += ", as well as products in "
                
                if categories:
                    response += f"categories like {', '.join(categories[:2])}"
                    
                if groups:
                    if categories:
                        response += " and "
                    response += f"groups like {', '.join(groups[:2])}"
        else:
            response = f"Based on your query '{query}', I found products in "
            
            if categories:
                response += f"categories like {', '.join(categories[:2])}"
                
            if groups:
                if categories:
                    response += " and "
                response += f"groups like {', '.join(groups[:2])}"
        
        response += f". I've found {len(products)} relevant products for you."
        return response