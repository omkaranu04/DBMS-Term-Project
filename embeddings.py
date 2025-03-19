import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from config import neo4j_conn

class EmbeddingEngine:
    def __init__(self, embeddings_file='embeddings.pkl', index_file='faiss_index.bin'):
        self.model = SentenceTransformer('huawei-noah/TinyBERT_General_4L_312D')
        self.embeddings_file = embeddings_file
        self.index_file = index_file
        self.categories_embeddings = None
        self.groups_embeddings = None
        self.products_embeddings = None
        self.products_asin = None  # Store ASINs for retrieval
        self.index = None  # FAISS index
        self.load_embeddings()

    def load_embeddings(self):
        if os.path.exists(self.embeddings_file) and os.path.exists(self.index_file):
            # Load embeddings and index from files
            with open(self.embeddings_file, 'rb') as f:
                data = pickle.load(f)
                self.categories_embeddings = data['categories']
                self.groups_embeddings = data['groups']
                self.products_embeddings = data['products']
                self.products_asin = data['products_asin']
            
            # Load FAISS index
            self.index = faiss.read_index(self.index_file)
            print(f"Loaded embeddings and index from files")
        else:
            self.generate_and_save_embeddings()

    def generate_and_save_embeddings(self):
        categories_query = "MATCH (c:Category) RETURN c.name AS name"
        groups_query = "MATCH (g:Group) RETURN g.name AS name"
        products_query = "MATCH (p:Product) RETURN p.title AS title, p.ASIN AS asin"

        categories = [record["name"] for record in neo4j_conn.query(categories_query)]
        groups = [record["name"] for record in neo4j_conn.query(groups_query)]
        
        # Get products with their ASINs
        products_result = neo4j_conn.query(products_query)
        product_titles = [record["title"] for record in products_result]
        product_asins = [record["asin"] for record in products_result]

        # Generate embeddings with progress tracking
        print("Generating embeddings for categories...")
        self.categories_embeddings = {
            cat: self.model.encode(cat) for cat in tqdm(categories, desc="Categories")
        }

        print("Generating embeddings for groups...")
        self.groups_embeddings = {
            group: self.model.encode(group) for group in tqdm(groups, desc="Groups")
        }

        print("Generating embeddings for products...")
        self.products_embeddings = {}
        self.products_asin = {}
        
        # Create product embeddings with progress tracking
        for i, title in enumerate(tqdm(product_titles, desc="Products")):
            if title:  # Ensure title is not None or empty
                embedding = self.model.encode(title)
                self.products_embeddings[title] = embedding
                self.products_asin[title] = product_asins[i]
        
        # Create FAISS index for fast similarity search
        print("Building FAISS index...")
        product_embeddings_list = list(self.products_embeddings.values())
        
        if product_embeddings_list:
            # Get dimension from first embedding
            dimension = len(product_embeddings_list[0])
            
            # Create index
            self.index = faiss.IndexFlatIP(dimension)  # Inner product (dot product) index
            
            # Convert to numpy array and add to index
            embeddings_array = np.array(product_embeddings_list).astype('float32')
            self.index.add(embeddings_array)
            
            # Save index to file
            faiss.write_index(self.index, self.index_file)

        # Save embeddings to file
        with open(self.embeddings_file, 'wb') as f:
            pickle.dump({
                'categories': self.categories_embeddings,
                'groups': self.groups_embeddings,
                'products': self.products_embeddings,
                'products_asin': self.products_asin
            }, f)
        print("Embeddings saved to", self.embeddings_file)

    def find_similar(self, query, top_k=3):
        # Generate embedding for the query
        query_embedding = self.model.encode(query)
        
        # Normalize query embedding for dot product similarity
        query_embedding_norm = query_embedding / np.linalg.norm(query_embedding)

        # Calculate similarity with categories using dot product
        category_similarities = {
            cat: np.dot(query_embedding_norm, emb) 
            for cat, emb in self.categories_embeddings.items()
        }

        # Calculate similarity with groups using dot product
        group_similarities = {
            group: np.dot(query_embedding_norm, emb)
            for group, emb in self.groups_embeddings.items()
        }

        # Get top categories and groups
        top_categories = sorted(category_similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]
        top_groups = sorted(group_similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Find similar products using FAISS
        top_products = []
        if self.index is not None:
            # Search similar products in FAISS index
            query_embedding_array = np.array([query_embedding_norm]).astype('float32')
            scores, indices = self.index.search(query_embedding_array, top_k)
            
            # Get product titles and ASINs from indices
            product_titles = list(self.products_embeddings.keys())
            for i, idx in enumerate(indices[0]):
                if idx < len(product_titles):
                    title = product_titles[idx]
                    asin = self.products_asin[title]
                    score = scores[0][i]
                    top_products.append((title, asin, score))

        return {
            "categories": top_categories,
            "groups": top_groups,
            "products": top_products
        }