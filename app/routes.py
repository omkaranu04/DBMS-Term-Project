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
main_bp = Blueprint('main', __name__)
rag_engine = RAGEngine()


# Performance logging setup
performance_logger = logging.getLogger('performance')
file_handler = logging.FileHandler('performance_log.txt')
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
performance_logger.addHandler(file_handler)
performance_logger.setLevel(logging.INFO)

# Enhanced performance logging decorator with multi-value parameter support
def log_performance(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Capture route info
        route_name = func.__name__
        endpoint = request.path
        
        # Start monitoring
        start_time = time.time()
        process = psutil.Process(os.getpid())
        start_cpu = psutil.cpu_percent(interval=None)
        start_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Run the actual route function
        result = func(*args, **kwargs)
        
        # End monitoring
        end_time = time.time()
        duration = end_time - start_time
        end_cpu = psutil.cpu_percent(interval=0.1)
        end_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Format the log entry with clear sections and alignment
        log_entry = (
            f"ENDPOINT: {endpoint}\n"
            f"ROUTE FUNCTION: {route_name}\n"
            f"PERFORMANCE METRICS:\n"
            f"  Query Execution Time: {duration:.4f} seconds\n"
            f"  CPU Usage: {end_cpu:.2f}%\n"
            f"  Memory Change: {abs(end_memory - start_memory):.2f} MB\n"
            f"{'=' * 80}\n"
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
            WHEN 'salesrank' THEN p.salesrank
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
            WHEN 'salesrank' THEN p.salesrank
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
            WHEN 'salesrank' THEN p.salesrank
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
            WHEN 'salesrank' THEN p.salesrank
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
    valid_sort_fields = ['total_score', 'title', 'avg_rating', 'salesrank']
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
    elif sort_by == 'salesrank':
        order_clause = f"p.salesrank {sort_order}"
    
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
    
# Trending Products Route
@main_bp.route('/trending')
@log_performance
def trending_products():
    start_date_str = "2005-06-28"
    end_date_str = "2005-07-06"

    try:
        query = """
        MATCH (c:Consumer)-[r:REVIEWED]->(p:Product)
        WHERE date(r.Date) >= date($start_date) AND date(r.Date) <= date($end_date)
        WITH p, count(r) AS review_count, p.total_score AS total_score
        ORDER BY review_count DESC, total_score DESC
        LIMIT 10
        RETURN p.title AS product_title, p.ASIN AS product_asin, 
               review_count, total_score
        """

        result = neo4j_conn.query(query, parameters={
            "start_date": start_date_str,
            "end_date": end_date_str,
        })

        products = [{
            "title": record["product_title"], 
            "asin": record["product_asin"],
            "review_count": record["review_count"],
            "total_score": record["total_score"]
        } for record in result]

        return render_template(
            'trending.html',
            products=products,
            start_date=start_date_str,
            end_date=end_date_str
        )
    except Exception as e:
        print(f"Error fetching trending products: {e}")
        return render_template('trending.html', products=[], start_date=start_date_str, end_date=end_date_str)
    
@main_bp.route('/top-users')
@log_performance
def top_users():
    try:
        query = """
        MATCH (c:Consumer)
        WHERE c.score IS NOT NULL
        RETURN c.name AS user_name, c.Customer AS user_id, c.score AS user_score
        ORDER BY c.score DESC
        LIMIT 10
        """

        result = neo4j_conn.query(query)

        users = [{
            "name": record["user_name"],
            "id": record["user_id"],
            "score": record["user_score"]
        } for record in result]

        return render_template(
            'top_users.html',
            users=users
        )
    except Exception as e:
        print(f"Error fetching top users: {e}")
        return render_template('top_users.html', users=[])

@main_bp.route('/user-reviews/<user_id>')
@log_performance
def user_reviews(user_id):
    try:
        query = """
        MATCH (c:Consumer {Customer: $user_id})-[r:REVIEWED]->(p:Product)
        RETURN p.title AS product_title, p.ASIN AS product_asin, 
               r.Helpful AS helpful, r.Rating AS rating, r.Date AS date
        ORDER BY r.Helpful DESC
        LIMIT 10
        """

        result = neo4j_conn.query(query, parameters={"user_id": user_id})

        reviews = [{
            "product_title": record["product_title"],
            "product_asin": record["product_asin"],
            "helpful": record["helpful"],
            "rating": record["rating"],
            "date": record["date"]
        } for record in result]

        # Get user name
        user_query = """
        MATCH (c:Consumer {Customer: $user_id})
        RETURN c.name AS user_name, c.score AS user_score
        """
        user_result = neo4j_conn.query(user_query, parameters={"user_id": user_id})
        user_info = user_result[0] if user_result else {"user_name": "Unknown", "user_score": 0}

        return render_template(
            'user_reviews.html',
            reviews=reviews,
            user_id=user_id,
            user_name=user_info["user_name"],
            user_score=user_info["user_score"]
        )
    except Exception as e:
        print(f"Error fetching user reviews: {e}")
        return render_template('user_reviews.html', reviews=[], user_id=user_id, user_name="Unknown", user_score=0)
