from flask import Blueprint, render_template
from config import neo4j_conn

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    query = "MATCH (g:Group) RETURN g.name AS group_name"
    
    try:
        results = neo4j_conn.query(query)
        groups = [record["group_name"] for record in results]
    except Exception as e:
        print(f"Error fetching groups: {e}")
        groups = []
    
    return render_template('home_page.html', groups=groups)

@main_bp.route('/group/<group_name>')
def group_products(group_name):
    query = """
    CALL apoc.cypher.run('
        MATCH (p:Product)-[:PART_OF]->(g:Group {name: $group_name})
        RETURN p.title AS product_title, p.ASIN AS product_asin
        ORDER BY p.title
    ', {group_name: $group_name}) YIELD value
    RETURN value.product_title AS product_title, value.product_asin AS product_asin
    """
    
    try:
        result = neo4j_conn.query(query, parameters={"group_name": group_name})
        products = [{"title": record["product_title"], "asin": record["product_asin"]} for record in result]
    except Exception as e:
        print(f"Error fetching products for group {group_name}: {e}")
        products = [] 
    
    return render_template('products_by_group.html', group_name=group_name, products=products)

@main_bp.route('/product/<product_asin>')
def product_detail(product_asin):
    product_query = """
    MATCH (p:Product {ASIN: $product_asin})
    RETURN p.title AS title, p.ASIN AS asin, p.Id AS id, 
           p.salesrank AS salesrank, p.avg_rating AS avg_rating
    """
    
    categories_query = """
    MATCH (p:Product {ASIN: $product_asin})-[:BELONGS_TO]->(c:Category)
    RETURN c.name AS category_name
    """
    
    similar_products_query = """
    MATCH (p:Product {ASIN: $product_asin})-[:SIMILAR]->(s:Product)
    RETURN s.title AS title, s.ASIN AS asin
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
        
        return render_template('product_detail.html', product=product, categories=categories, similar_products=similar_products)
    except Exception as e:
        print(f"Error fetching product details for {product_asin}: {e}")
        return "An error occurred", 500
    
@main_bp.route('/category/<category_name>')
def products_by_category(category_name):
    query = """
    MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category_name})
    RETURN p.title AS product_title, p.ASIN AS product_asin
    ORDER BY p.title
    """
    
    try:
        result = neo4j_conn.query(query, parameters={"category_name": category_name})
        products = [{"title": record["product_title"], "asin": record["product_asin"]} for record in result]
    except Exception as e:
        print(f"Error fetching products for category {category_name}: {e}")
        products = []
    
    return render_template('products_by_category.html', category_name=category_name, products=products)