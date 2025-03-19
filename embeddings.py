import os
import pickle
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from config import neo4j_conn
import numpy as np

class EmbeddingEngine:
    def __init__(self, embeddings_file='embeddings.pkl'):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embeddings_file = embeddings_file
        self.categories_embeddings = None
        self.groups_embeddings = None
        self.load_embeddings()

    def load_embeddings(self):
        if os.path.exists(self.embeddings_file):
            # Load embeddings from file
            with open(self.embeddings_file, 'rb') as f:
                data = pickle.load(f)
                self.categories_embeddings = data['categories']
                self.groups_embeddings = data['groups']
        else:
            # Generate embeddings and save them
            self.generate_and_save_embeddings()

    def generate_and_save_embeddings(self):
        # Fetch all categories and groups from Neo4j
        categories_query = "MATCH (c:Category) RETURN c.name AS name"
        groups_query = "MATCH (g:Group) RETURN g.name AS name"

        categories = [record["name"] for record in neo4j_conn.query(categories_query)]
        groups = [record["name"] for record in neo4j_conn.query(groups_query)]

        # Generate embeddings with progress tracking
        print("Generating embeddings for categories...")
        self.categories_embeddings = {
            cat: self.model.encode(cat) for cat in tqdm(categories, desc="Categories")
        }

        print("Generating embeddings for groups...")
        self.groups_embeddings = {
            group: self.model.encode(group) for group in tqdm(groups, desc="Groups")
        }

        # Save embeddings to file
        with open(self.embeddings_file, 'wb') as f:
            pickle.dump({
                'categories': self.categories_embeddings,
                'groups': self.groups_embeddings
            }, f)
        print("Embeddings saved to", self.embeddings_file)
        
    def find_similar(self, query, top_k=3):
        # Generate embedding for the query
        query_embedding = self.model.encode(query)

        # Calculate similarity with categories
        category_similarities = {
            cat: np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
            for cat, emb in self.categories_embeddings.items()
        }

        # Calculate similarity with groups
        group_similarities = {
            group: np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
            for group, emb in self.groups_embeddings.items()
        }

        # Get top categories and groups
        top_categories = sorted(category_similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]
        top_groups = sorted(group_similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return {
            "categories": top_categories,
            "groups": top_groups
        }