from flask import Blueprint, render_template, request, jsonify
import psutil
import time
import os
import logging
import functools
from datetime import datetime
import re
from config import neo4j_conn
from rag_engine import RAGEngine

# Performance logging setup
performance_logger = logging.getLogger('performance')
file_handler = logging.FileHandler('performance_log.txt')
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
performance_logger.addHandler(file_handler)
performance_logger.setLevel(logging.INFO)

main_bp = Blueprint('main', __name__)

rag_engine = RAGEngine()

# Enhanced performance logging decorator with multi-value parameter support
def log_performance(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Capture route info
        route_name = func.__name__
        endpoint = request.path
        
        # Extract all possible parameters
        params = {}
        
        # 1. URL path parameters (from the route)
        if kwargs:
            params.update({"path_params": kwargs})
            
        # 2. Query parameters - enhanced to handle multi-value params
        if request.args:
            query_params = {}
            for key in request.args.keys():
                # Check if this is a multi-value parameter
                values = request.args.getlist(key)
                if len(values) > 1:
                    query_params[key] = values
                else:
                    query_params[key] = request.args.get(key)
            params.update({"query_params": query_params})
            
        # 3. Form data - also handle multi-value form fields
        if request.form:
            form_data = {}
            for key in request.form.keys():
                values = request.form.getlist(key)
                if len(values) > 1:
                    form_data[key] = values
                else:
                    form_data[key] = request.form.get(key)
            params.update({"form_data": form_data})
            
        # 4. JSON data
        if request.is_json and request.json:
            # Only include if not too large to avoid bloating logs
            json_data = request.json
            if isinstance(json_data, dict):
                # For large JSON payloads, just log the keys
                if len(str(json_data)) > 1000:
                    params.update({"json_keys": list(json_data.keys())})
                else:
                    params.update({"json_data": json_data})
        
        # Start monitoring
        start_time = time.time()
        start_cpu = psutil.cpu_percent(interval=None)
        process = psutil.Process(os.getpid())
        start_process_memory = process.memory_info().rss / (1024 * 1024)  # Convert to MB
        
        # Run the actual route function
        result = func(*args, **kwargs)
        
        # End monitoring
        end_time = time.time()
        duration = end_time - start_time
        end_cpu = psutil.cpu_percent(interval=0.1)  # Get CPU with minimal interval
        end_memory = psutil.virtual_memory()
        end_process_memory = process.memory_info().rss / (1024 * 1024)  # Convert to MB
        
        # Calculate metrics - ensure non-negative values
        cpu_load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        memory_change_mb = max(0, end_process_memory - start_process_memory)  # Ensure non-negative
        
        # Determine query name based on route function
        query_name = "Unknown"
        if hasattr(func, "__doc__") and func.__doc__:
            # Extract query name from docstring if available
            query_name = func.__doc__.strip().split('\n')[0]
        else:
            query_name = route_name
        
        # Log performance data
        log_entry = (
            f"Route: {route_name} | "
            f"Endpoint: {endpoint} | "
            f"Query: {query_name} | "
            f"Duration: {duration:.4f}s | "
            f"CPU Usage: {end_cpu:.2f}% | "
            f"CPU Load (1/5/15 min): {cpu_load[0]:.2f}/{cpu_load[1]:.2f}/{cpu_load[2]:.2f} | "
            f"Memory Usage: {end_memory.percent:.2f}% | "
            f"Process Memory: {end_process_memory:.2f}MB | "
            f"Memory Change: {memory_change_mb:.2f}MB | "
            f"Parameters: {params}"
        )
        performance_logger.info(log_entry)
        
        return result
    return wrapper

@main_bp.route('/')
@log_performance
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
@log_performance
def group_products(group_name):
    page = request.args.get('page', 1, type=int)
    per_page = 21
    sort_by = request.args.get('sort_by', 'total_score')
    sort_order = request.args.get('sort_order', 'DESC')
    
    if sort_order == 'ASC':
        query = """
        MATCH (g:Group {name: $group_name})
        CALL apoc.path.expandConfig(g, {
            relationshipFilter: "<PART_OF",
            minLevel: 1,
            maxLevel: 1
        }) YIELD path
        WITH last(nodes(path)) as p
        RETURN p.title AS product_title, p.ASIN AS product_asin, p.total_score AS total_score, p.avg_rating AS avg_rating
        ORDER BY 
        CASE $sort_by 
            WHEN 'total_score' THEN p.total_score 
            WHEN 'title' THEN p.title 
            WHEN 'avg_rating' THEN p.avg_rating 
        END ASC
        SKIP $skip LIMIT $limit
        """
    else:
        query = """
        MATCH (g:Group {name: $group_name})
        CALL apoc.path.expandConfig(g, {
            relationshipFilter: "<PART_OF",
            minLevel: 1,
            maxLevel: 1
        }) YIELD path
        WITH last(nodes(path)) as p
        RETURN p.title AS product_title, p.ASIN AS product_asin, p.total_score AS total_score, p.avg_rating AS avg_rating
        ORDER BY 
        CASE $sort_by 
            WHEN 'total_score' THEN p.total_score 
            WHEN 'title' THEN p.title 
            WHEN 'avg_rating' THEN p.avg_rating 
        END DESC
        SKIP $skip LIMIT $limit
        """
    try:
        result = neo4j_conn.query(query, parameters={
            "group_name": group_name,
            "skip": (page - 1) * per_page,
            "limit": per_page,
            "sort_by": sort_by,
            "sort_order": sort_order
        })
        products = [{"title": record["product_title"], "asin": record["product_asin"], 
                     "total_score": record["total_score"], "avg_rating": record["avg_rating"]} for record in result]
        
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
@log_performance
def products_by_category(category_name):
    page = request.args.get('page', 1, type=int)
    items_per_page = 21
    sort_by = request.args.get('sort_by', 'total_score')
    sort_order = request.args.get('sort_order', 'DESC')
    
    # Query to fetch products belonging to the selected category with pagination
    if sort_order == 'ASC':
        query = """
        MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category_name})
        RETURN p.title AS title, p.ASIN AS asin, p.avg_rating AS avg_rating,
               p.salesrank AS salesrank, p.total_score AS total_score
        ORDER BY 
        CASE $sort_by 
            WHEN 'total_score' THEN p.total_score 
            WHEN 'title' THEN p.title 
            WHEN 'avg_rating' THEN p.avg_rating
        END ASC
        SKIP $skip LIMIT $limit
        """
    else:
        query = """
        MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category_name})
        RETURN p.title AS title, p.ASIN AS asin, p.avg_rating AS avg_rating,
               p.salesrank AS salesrank, p.total_score AS total_score
        ORDER BY 
        CASE $sort_by 
            WHEN 'total_score' THEN p.total_score 
            WHEN 'title' THEN p.title 
            WHEN 'avg_rating' THEN p.avg_rating
        END DESC
        SKIP $skip LIMIT $limit
        """
    
    try:
        skip = (page - 1) * items_per_page
        result = neo4j_conn.query(query, parameters={
            "category_name": category_name, 
            "skip": skip, 
            "limit": items_per_page,
            "sort_by": sort_by
        })
        
        products = [{"title": record["title"], 
                    "asin": record["asin"], 
                    "avg_rating": record["avg_rating"],
                    "salesrank": record["salesrank"],
                    "total_score": record["total_score"]} for record in result]
        
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
                          pagination_range=pagination_range,
                          sort_by=sort_by,
                          sort_order=sort_order)

# MULTIPLE CATEGORY SEARCH ROUTE    
@main_bp.route('/api/categories/search')
@log_performance
def search_categories():
    query = request.args.get('q', '').strip().lower()
    if len(query) < 2:
        return jsonify({"categories": []})
    
    try:
        # First get exact and partial matches from database
        search_query = """
        MATCH (c:Category)
        RETURN c.name AS category_name
        ORDER BY c.name
        """
        
        results = neo4j_conn.query(search_query)
        all_categories = [record["category_name"] for record in results]
        
        # Use TheFuzz for better fuzzy matching
        from thefuzz import process
        
        # Get top matches using token_sort_ratio for better partial matching
        matches = process.extract(query, all_categories, limit=15, scorer=process.fuzz.token_sort_ratio)
        
        # Filter matches with a minimum score of 60
        filtered_matches = [match[0] for match in matches if match[1] >= 60]
        
        return jsonify({"categories": filtered_matches})
    
    except Exception as e:
        print(f"Error searching categories: {e}")
        return jsonify({"error": str(e), "categories": []}), 500


# For common categories
@main_bp.route('/api/common-products')
@log_performance
def common_products():
    categories = request.args.getlist('categories')
    page = request.args.get('page', 1, type=int)
    per_page = 21
    sort_by = request.args.get('sort_by', 'total_score')
    sort_order = request.args.get('sort_order', 'DESC')
    
    if not categories:
        return jsonify({"error": "No categories provided", "products": []}), 400
    
    # Validate sort_by parameter
    valid_sort_fields = ['total_score', 'title', 'avg_rating']
    if sort_by not in valid_sort_fields:
        sort_by = 'total_score'
    
    # Validate sort_order parameter
    if sort_order not in ['ASC', 'DESC']:
        sort_order = 'DESC'
    
    # Build the query with conditional ORDER BY clause
    order_clause = f"p.{sort_by} {sort_order}"
    if sort_by == 'title':
        order_clause = f"p.title {sort_order}"
    elif sort_by == 'avg_rating':
        order_clause = f"p.avg_rating {sort_order}"
    
    query = f"""
    MATCH (p:Product)
    WHERE EXISTS {{
      MATCH (p)-[:BELONGS_TO]->(:Category {{name: $categories[0]}})
    }}
    AND ALL(category IN $categories[1..] WHERE 
          EXISTS {{
            MATCH (p)-[:BELONGS_TO]->(:Category {{name: category}})
          }})
    RETURN p.title AS title, p.ASIN AS asin, p.avg_rating AS rating, p.total_score AS total_score
    ORDER BY {order_clause}
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
        
        products = [{"title": record["title"], "asin": record["asin"], 
                    "rating": record["rating"], "total_score": record["total_score"]} 
                   for record in results]
        
        return jsonify({
            "products": products,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
            "sort_by": sort_by,
            "sort_order": sort_order
        })
    except Exception as e:
        print(f"Error fetching common products: {e}")
        return jsonify({"error": str(e), "products": []}), 500

@main_bp.route('/category', methods=['GET'])
@log_performance
def categories_page():
    return render_template('multiple_category_search.html')

# PRODUCT PAGE ROUTE
@main_bp.route('/product/<product_asin>')
@log_performance
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
    
    sort = request.args.get('sort', 'helpful_desc')
    order_clauses = {
        'helpful_desc': 'r.Helpful DESC',
        'helpful_asc': 'r.Helpful ASC',
        'rating_desc': 'r.Rating DESC',
        'rating_asc': 'r.Rating ASC',
        'date_desc': 'r.Date DESC',
        'date_asc': 'r.Date ASC'
    }
    order_by = order_clauses.get(sort, 'r.Helpful DESC')
    reviews_query = """
    MATCH (u:Consumer)-[r:REVIEWED]->(p:Product {ASIN: $product_asin})
    RETURN u.Customer AS user_id, r.Date AS date, r.Rating AS rating, 
           r.Helpful AS helpful, r.Votes AS votes
    ORDER BY 
    """ + order_by
    
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
@log_performance
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