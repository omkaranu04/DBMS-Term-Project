from flask import Flask, jsonify
from config import neo4j_conn 
from .routes import main_bp    

def create_app():
    """
    Factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    
    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({"error": str(e)}), 500
    
    app.register_blueprint(main_bp)
    
    return app