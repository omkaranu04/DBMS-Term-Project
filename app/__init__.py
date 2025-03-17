from flask import Flask
from config import neo4j_conn 
from .routes import main_bp    

def create_app():
    """
    Factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    
    app.register_blueprint(main_bp)
    
    return app