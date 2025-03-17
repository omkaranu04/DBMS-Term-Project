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