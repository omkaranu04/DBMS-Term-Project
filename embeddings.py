import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import pandas as pd

class EmbeddingEngine:
    def __init__(self, embeddings_file='embeddings.pkl', index_file='faiss_index.bin'):
        print("Loading embedding model...")
        self.model = SentenceTransformer('BAAI/bge-small-en-v1.5')  # Load model immediately
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
            with open(self.embeddings_file, 'rb') as f:
                data = pickle.load(f)
                self.categories_embeddings = data['categories']
                self.groups_embeddings = data['groups']
                self.products_embeddings = data['products']
                self.products_asin = data['products_asin']
            
            self.index = faiss.read_index(self.index_file)
            print(f"✅ Loaded embeddings and index from files")
        else:
            # Generate embeddings and save them
            self.generate_and_save_embeddings()
            print("✅ Generated and saved embeddings")

    def generate_and_save_embeddings(self):
        # Load CSV files
        try:
            categories_df = pd.read_csv("Parsed Data/categories.csv")
            groups_df = pd.read_csv("Parsed Data/groups.csv")
            products_df = pd.read_csv("Parsed Data/product_data.csv")
            
            # Extract relevant data
            categories = categories_df["Category"].dropna().unique().tolist()
            groups = groups_df["group"].dropna().unique().tolist()
            
            # For products, get title and ASIN
            products_df = products_df.dropna(subset=['title', 'ASIN'])
            product_titles = products_df["title"].tolist()
            product_asins = products_df["ASIN"].tolist()
            
            # Generate embeddings with progress tracking
            print("Generating embeddings for categories...")
            category_embeddings = self.model.encode(categories, show_progress_bar=True, batch_size=32)
            self.categories_embeddings = {cat: emb for cat, emb in zip(categories, category_embeddings)}

            print("Generating embeddings for groups...")
            group_embeddings = self.model.encode(groups, show_progress_bar=True, batch_size=32)
            self.groups_embeddings = {group: emb for group, emb in zip(groups, group_embeddings)}

            print("Generating embeddings for products...")
            self.products_embeddings = {}
            self.products_asin = {}
            
            # Process products in batches to avoid memory issues
            batch_size = 1000
            for i in tqdm(range(0, len(product_titles), batch_size), desc="Product batches"):
                batch_titles = product_titles[i:i+batch_size]
                batch_asins = product_asins[i:i+batch_size]
                
                # Filter out empty titles
                valid_indices = [j for j, title in enumerate(batch_titles) if str(title).strip()]
                valid_titles = [batch_titles[j] for j in valid_indices]
                valid_asins = [batch_asins[j] for j in valid_indices]
                
                if valid_titles:
                    batch_embeddings = self.model.encode(valid_titles, show_progress_bar=False)
                    for j, (title, asin, emb) in enumerate(zip(valid_titles, valid_asins, batch_embeddings)):
                        self.products_embeddings[title] = emb
                        self.products_asin[title] = asin
            
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
            print("✅ Embeddings saved to", self.embeddings_file)
            
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            raise

    def find_similar(self, query, top_k=3, threshold=0.3):
        # Generate embedding for the query
        query_embedding = self.model.encode(query)
        
        # Normalize query embedding for dot product similarity
        query_embedding_norm = query_embedding / np.linalg.norm(query_embedding)

        # Calculate similarity with categories using dot product
        category_similarities = {
            cat: np.dot(query_embedding_norm, emb / np.linalg.norm(emb)) 
            for cat, emb in self.categories_embeddings.items()
        }

        # Calculate similarity with groups using dot product
        group_similarities = {
            group: np.dot(query_embedding_norm, emb / np.linalg.norm(emb))
            for group, emb in self.groups_embeddings.items()
        }

        # Get top categories and groups
        top_categories = sorted(category_similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]
        top_groups = sorted(group_similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Filter by threshold
        top_categories = [(cat, score) for cat, score in top_categories if score >= threshold]
        top_groups = [(group, score) for group, score in top_groups if score >= threshold]
        
        # Find similar products using FAISS
        top_products = []
        if self.index is not None:
            # Search similar products in FAISS index
            query_embedding_array = np.array([query_embedding_norm]).astype('float32')
            scores, indices = self.index.search(query_embedding_array, top_k)
            
            # Get product titles and ASINs from indices
            product_titles = list(self.products_embeddings.keys())
            for i, idx in enumerate(indices[0]):
                if idx < len(product_titles) and scores[0][i] >= threshold:
                    title = product_titles[idx]
                    asin = self.products_asin[title]
                    score = scores[0][i]
                    top_products.append((title, asin, score))

        return {
            "categories": top_categories,
            "groups": top_groups,
            "products": top_products
        }