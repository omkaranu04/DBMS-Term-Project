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
    CALL gds.pageRank.stream({
        nodeProjection: 'Product',
        relationshipProjection: {
            PART_OF: {
                type: 'PART_OF',
                orientation: 'UNDIRECTED'
            }
        },
        dampingFactor: 0.85,
        maxIterations: 20
    })
    YIELD nodeId, score
    MATCH (p:Product)-[:PART_OF]->(g:Group {name: $group_name})
    WHERE id(p) = nodeId
    RETURN p.title AS product_title, p.asin AS product_asin, score
    ORDER BY score DESC
    """
    
    try:
        result = neo4j_conn.query(query, parameters={"group_name": group_name})
        products = [{"title": record["product_title"], "asin": record["product_asin"], "score": record["score"]} for record in result]
    except Exception as e:
        print(f"Error fetching products for group {group_name}: {e}")
        products = [] 
    
    return render_template('products_by_group.html', group_name=group_name, products=products)