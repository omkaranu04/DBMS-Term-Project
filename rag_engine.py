import pandas as pd
from cleantext import clean
from embeddings import EmbeddingEngine

class RAGEngine:
    def __init__(self):
        self.embedding_engine = EmbeddingEngine()
        self.products_df = pd.read_csv("Parsed Data/product_data.csv")
    
    def _clean_input(self, text):
        # Use cleantext to clean the input text
        cleaned_text = clean(
            text,
            fix_unicode=True,           # Fix unicode issues
            to_ascii=False,             # Don't convert to ASCII
            lower=True,                 # Convert to lowercase
            no_line_breaks=True,        # Remove line breaks
            no_urls=True,               # Remove URLs
            no_emails=True,             # Remove emails
            no_phone_numbers=True,      # Remove phone numbers
            no_numbers=False,           # Keep numbers (might be important for product models)
            no_digits=False,            # Keep digits
            no_currency_symbols=False,  # Keep currency symbols
            no_punct=True,              # Remove punctuation
            replace_with_punct="",      # Replace punctuation with nothing
            replace_with_url="",        # Replace URLs with nothing
            replace_with_email="",      # Replace emails with nothing
            replace_with_phone_number="", # Replace phone numbers with nothing
            lang="en"                   # English language
        )
        
        # Remove common stop words manually
        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
                     'when', 'where', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
                     'most', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                     'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'}
        
        # Split by spaces, filter out stop words, and rejoin
        words = cleaned_text.split()
        filtered_words = [word for word in words if word not in stop_words]
        
        # Return the cleaned text, or the original if cleaning removed everything
        cleaned_text = ' '.join(filtered_words)
        return cleaned_text if cleaned_text else text
    
    def process_query(self, query, threshold=0.3, top_k=10):
        # Clean the user input
        cleaned_query = self._clean_input(query)
        print(f"Cleaned query: '{cleaned_query}'")
        
        # Find similar items across categories, groups, and products
        similar_items = self.embedding_engine.find_similar(cleaned_query, top_k=top_k, threshold=threshold)
        
        # Extract category and group names
        top_categories = similar_items["categories"]
        top_groups = similar_items["groups"]
        top_products = similar_items["products"]
        
        # Extract direct product matches if available
        direct_product_matches = []
        if top_products:
            direct_product_matches = [
                {"title": item[0], "asin": item[1], "score": float(item[2])} 
                for item in top_products
            ]
        
        # If we have exact product matches, prioritize those
        if direct_product_matches:
            # Enrich with product details
            all_products = self._enrich_products_with_details(
                [p["asin"] for p in direct_product_matches]
            )
            
            # Merge similarity scores
            for p in all_products:
                matching = next((dp for dp in direct_product_matches if dp["asin"] == p["asin"]), None)
                if matching:
                    p["similarity_score"] = matching["score"]
            
            # Sort by similarity score
            all_products = sorted(all_products, key=lambda x: x.get("similarity_score", 0), reverse=True)
        else:
            # Fetch products from categories and groups using CSV data
            category_products = self._fetch_products_by_categories([c[0] for c in top_categories])
            group_products = self._fetch_products_by_groups([g[0] for g in top_groups])
            
            # Combine all products
            combined_products = category_products + group_products
            
            # Remove duplicates
            unique_asins = set()
            all_products = []
            for p in combined_products:
                if p["asin"] not in unique_asins:
                    unique_asins.add(p["asin"])
                    all_products.append(p)
        
        # Generate response
        response = self._generate_response(
            query, 
            [c[0] for c in top_categories], 
            [g[0] for g in top_groups], 
            all_products, 
            has_direct_matches=len(direct_product_matches) > 0
        )
        
        return {
            "response": response,
            "products": all_products[:top_k], 
            "categories": [c[0] for c in top_categories],
            "groups": [g[0] for g in top_groups]
        }
    
    def _enrich_products_with_details(self, asin_list):
        if not asin_list:
            return []
        
        # Filter products by ASIN
        filtered_products = self.products_df[self.products_df['ASIN'].isin(asin_list)]
        
        # Convert to list of dictionaries
        products = []
        for _, row in filtered_products.iterrows():
            product = {
                "title": row.get("title", ""),
                "asin": row.get("ASIN", ""),
                "salesrank": row.get("salesrank", 0),
                "avg_rating": row.get("avg_rating", 0)
            }
            products.append(product)
        
        return products
    
    def _fetch_products_by_categories(self, categories, limit=10):
        if not categories:
            return []
        
        # Load category relationships
        try:
            category_relations = pd.read_csv("Parsed Data/category_relations.csv")
            
            # Filter by categories
            filtered_relations = category_relations[category_relations['Category'].isin(categories)]
            
            # Get unique ASINs
            asins = filtered_relations['ASIN'].unique().tolist()[:limit]
            
            # Get product details
            return self._enrich_products_with_details(asins)
            
        except Exception as e:
            print(f"Error fetching products by categories: {e}")
            return []
    
    def _fetch_products_by_groups(self, groups, limit=10):
        if not groups:
            return []
        
        # Load group relationships
        try:
            group_relations = pd.read_csv("Parsed Data/group_relations.csv")
            
            # Filter by groups
            filtered_relations = group_relations[group_relations['group'].isin(groups)]
            
            # Get unique ASINs
            asins = filtered_relations['ASIN'].unique().tolist()[:limit]
            
            # Get product details
            return self._enrich_products_with_details(asins)
            
        except Exception as e:
            print(f"Error fetching products by groups: {e}")
            return []
    
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