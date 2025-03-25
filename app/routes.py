from flask import Blueprint, render_template, request, jsonify
from config import neo4j_conn
from rag_engine import RAGEngine

main_bp = Blueprint('main', __name__)

rag_engine = RAGEngine()

@main_bp.route('/')
def home():
    query = """
    MATCH (g:Group)
    RETURN g.name AS group_name
    ORDER BY g.name
    """
    
    try:
        results = neo4j_conn.query(query)
        groups = [record["group_name"] for record in results]
    except Exception as e:
        print(f"Error fetching groups: {e}")
        groups = []
    
    return render_template('home_page.html', groups=groups)

def get_pagination_range(page, total_pages, block_size=5): # for pagination in the pages with high number of products
    """
    Calculate the range of page numbers to display in pagination.
    """
    page = max(1, min(page, total_pages))
    start = max(1, page - block_size // 2)
    end = min(total_pages, start + block_size - 1)
    if end - start + 1 < block_size:
        start = max(1, end - block_size + 1)
    return range(start, end + 1)

# GROUP PRODUCTS ROUTE
@main_bp.route('/group/<group_name>')
def group_products(group_name):
    page = request.args.get('page', 1, type=int)
    per_page = 21
    query = """
    MATCH (g:Group {name: $group_name})
    CALL apoc.path.expandConfig(g, {
        relationshipFilter: "<PART_OF",
        minLevel: 1,
        maxLevel: 1
    }) YIELD path
    WITH last(nodes(path)) as p
    RETURN p.title AS product_title, p.ASIN AS product_asin
    ORDER BY p.total_score DESC
    SKIP $skip LIMIT $limit
    """
    try:
        result = neo4j_conn.query(query, parameters={
            "group_name": group_name,
            "skip": (page - 1) * per_page,
            "limit": per_page
        })
        products = [{"title": record["product_title"], "asin": record["product_asin"]} for record in result]
        
        count_query = """
        MATCH (g:Group {name: $group_name})
        CALL apoc.path.subgraphNodes(g, {
            relationshipFilter: "<PART_OF",
            minLevel: 1,
            maxLevel: 1
        }) YIELD node
        RETURN count(node) AS total
        """
        count_result = neo4j_conn.query(count_query, parameters={"group_name": group_name})
        total = count_result[0]["total"]
        
        total_pages = (total + per_page - 1) // per_page
        pagination_range = get_pagination_range(page, total_pages)
        
        return render_template('products_by_group.html', group_name=group_name, products=products,
                               page=page, per_page=per_page, total=total,
                               total_pages=total_pages, pagination_range=pagination_range)
    except Exception as e:
        print(f"Error fetching products for group {group_name}: {e}")
        return render_template('products_by_group.html', group_name=group_name, products=[])
    
# FOR CATEGORY PRODUCTS ROUTE
@main_bp.route('/category/<category_name>')
def products_by_category(category_name):
    page = request.args.get('page', 1, type=int)
    items_per_page = 21
    
    # Query to fetch products belonging to the selected category with pagination
    query = """
    MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category_name})
    RETURN p.title AS title, p.ASIN AS asin, p.avg_rating AS avg_rating,
           p.salesrank AS salesrank, p.total_score AS total_score
    ORDER BY p.total_score DESC
    SKIP $skip LIMIT $limit
    """
    
    try:
        skip = (page - 1) * items_per_page
        result = neo4j_conn.query(query, parameters={
            "category_name": category_name, 
            "skip": skip, 
            "limit": items_per_page
        })
        
        products = [{"title": record["title"], 
                    "asin": record["asin"], 
                    "avg_rating": record["avg_rating"],
                    "salesrank": record["salesrank"],
                    "total_score": record["total_score"]} for record in result]
        
        # Query to count total products in the category
        count_query = """
        MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category_name})
        RETURN count(p) AS total_products
        """
        count_result = neo4j_conn.query(count_query, parameters={"category_name": category_name})
        total_products = count_result[0]["total_products"] if count_result else 0
        
        total_pages = (total_products + items_per_page - 1) // items_per_page
        pagination_range = get_pagination_range(page, total_pages)
        
    except Exception as e:
        print(f"Error fetching products for category {category_name}: {e}")
        products = []
        total_pages = 1
        pagination_range = range(1, 2)
    
    return render_template('products_by_category.html', 
                          category_name=category_name, 
                          products=products,
                          page=page,
                          total_pages=total_pages,
                          pagination_range=pagination_range)

# MULTIPLE CATEGORY SEARCH ROUTE    
@main_bp.route('/api/categories/search')
def search_categories():
    query = request.args.get('q', '').strip().lower()
    if len(query) < 2:
        return jsonify({"categories": []})

    # Improved Levenshtein distance implementation
    def levenshtein(s1, s2):
        if len(s1) < len(s2):
            return levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    # Modified Cypher query to get a broader range of initial matches
    search_query = """
    MATCH (c:Category)
    WHERE toLower(c.name) CONTAINS toLower($query)
    OR apoc.text.levenshteinSimilarity(toLower(c.name), toLower($query)) > 0.6
    RETURN c.name AS category_name
    ORDER BY c.name
    LIMIT 200
    """
    
    try:
        results = neo4j_conn.query(search_query, parameters={"query": query})
        categories = [record["category_name"] for record in results]
        
        processed = []
        for category in categories:
            lower_category = category.lower()
            
            # Check for exact match or starts with
            if lower_category == query or lower_category.startswith(query):
                processed.append((category, 0, 0))  # Highest priority
                continue
            
            # Check for contains
            if query in lower_category:
                processed.append((category, 1, lower_category.index(query)))
                continue
            
            # Calculate Levenshtein distance
            distance = levenshtein(query, lower_category[:len(query)])
            
            # Calculate word similarity
            category_words = lower_category.split()
            query_words = query.split()
            word_similarity = sum(1 for w in query_words if any(w in cw for cw in category_words))
            
            # Combine distance and word similarity
            score = distance - word_similarity
            
            processed.append((category, score, len(category)))
        
        # Sort by: 1) score (lower is better), 2) length (shorter is better), 3) alphabetical
        processed.sort(key=lambda x: (x[1], x[2], x[0].lower()))
        categories = [item[0] for item in processed[:10]]

        return jsonify({"categories": categories})
    
    except Exception as e:
        print(f"Error searching categories: {e}")
        return jsonify({"error": str(e), "categories": []}), 500

# For common categories
@main_bp.route('/api/common-products')
def common_products():
    categories = request.args.getlist('categories')
    page = request.args.get('page', 1, type=int)
    per_page = 21
    
    if not categories:
        return jsonify({"error": "No categories provided", "products": []}), 400
    
    query = """
    MATCH (p:Product)
    WHERE EXISTS {
      MATCH (p)-[:BELONGS_TO]->(:Category {name: $categories[0]})
    }
    AND ALL(category IN $categories[1..] WHERE 
          EXISTS {
            MATCH (p)-[:BELONGS_TO]->(:Category {name: category})
          })
    RETURN p.title AS title, p.ASIN AS asin, p.avg_rating AS rating
    ORDER BY p.total_score DESC
    SKIP $skip
    LIMIT $limit
    """
    
    count_query = """
    MATCH (p:Product)
    WHERE EXISTS {
      MATCH (p)-[:BELONGS_TO]->(:Category {name: $categories[0]})
    }
    AND ALL(category IN $categories[1..] WHERE 
          EXISTS {
            MATCH (p)-[:BELONGS_TO]->(:Category {name: category})
          })
    RETURN count(p) AS total
    """
    
    try:
        skip = (page - 1) * per_page
        results = neo4j_conn.query(query, parameters={
            "categories": categories,
            "skip": skip,
            "limit": per_page
        })
        
        count_result = neo4j_conn.query(count_query, parameters={"categories": categories})
        total = count_result[0]["total"] if count_result else 0
        
        products = [{"title": record["title"], "asin": record["asin"], "rating": record["rating"]} 
                   for record in results]
        
        return jsonify({
            "products": products,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        })
    except Exception as e:
        print(f"Error fetching common products: {e}")
        return jsonify({"error": str(e), "products": []}), 500

@main_bp.route('/category', methods=['GET'])
def categories_page():
    return render_template('multiple_category_search.html')

# PRODUCT PAGE ROUTE
@main_bp.route('/product/<product_asin>')
def product_detail(product_asin):
    product_query = """
    MATCH (p:Product {ASIN: $product_asin})
    RETURN p.title AS title, p.ASIN AS asin, p.Id AS id, 
           p.salesrank AS salesrank, p.avg_rating AS avg_rating, p.total_score AS total_score
    """
    
    categories_query = """
    MATCH (p:Product {ASIN: $product_asin})-[:BELONGS_TO]->(c:Category)
    RETURN c.name AS category_name
    """
    
    similar_products_query = """
    MATCH (p:Product {ASIN: $product_asin})-[:SIMILAR]->(s:Product)
    ORDER BY s.total_score DESC
    RETURN s.title AS title, s.ASIN AS asin
    """
    
    copurchased_query = """
    MATCH (p:Product {ASIN: $product_asin})-[r:COPURCHASED_WITH]->(c:Product)
    WHERE r.Frequency > 1
    RETURN c.title AS title, c.ASIN AS asin, r.Frequency AS frequency
    ORDER BY r.Frequency DESC
    """
    
    reviews_query = """
    MATCH (u:Consumer)-[r:REVIEWED]->(p:Product {ASIN: $product_asin})
    RETURN u.Customer AS user_id, r.Date AS date, r.Rating AS rating, 
           r.Helpful AS helpful, r.Votes AS votes
    ORDER BY r.Helpful DESC
    """
    
    try:
        product_result = neo4j_conn.query(product_query, parameters={"product_asin": product_asin})
        if not product_result:
            return "Product not found", 404
        
        product = product_result[0]
        
        categories_result = neo4j_conn.query(categories_query, parameters={"product_asin": product_asin})
        categories = [record["category_name"] for record in categories_result]
        
        similar_products_result = neo4j_conn.query(similar_products_query, parameters={"product_asin": product_asin})
        similar_products = [{"title": record["title"], "asin": record["asin"]} for record in similar_products_result]
        
        copurchased_result = neo4j_conn.query(copurchased_query, parameters={"product_asin": product_asin})
        copurchased_products = [{"title": record["title"], "asin": record["asin"], "frequency": record["frequency"]} 
                               for record in copurchased_result]
        
        reviews_result = neo4j_conn.query(reviews_query, parameters={"product_asin": product_asin})
        reviews = [{"user_id": record["user_id"], 
                   "date": record["date"], 
                   "rating": record["rating"],
                   "helpful": record["helpful"],
                   "votes": record["votes"]} for record in reviews_result]
        
        return render_template('product_detail.html', 
                              product=product, 
                              categories=categories, 
                              similar_products=similar_products,
                              copurchased_products=copurchased_products,
                              reviews=reviews)
    except Exception as e:
        print(f"Error fetching product details for {product_asin}: {e}")
        return "An error occurred", 500
    
# CHATBOX ROUTE
@main_bp.route('/chat', methods=['POST'])
def chat():
    try:
        query = request.json.get('query', '')
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        # Process the query using the RAG engine
        result = rag_engine.process_query(query)
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500