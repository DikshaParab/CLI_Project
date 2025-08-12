import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import HuggingFaceEmbeddings  
import os
from utils import print_error

class ChromaManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=".chromadb",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.embedding_function = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},  
            encode_kwargs={'normalize_embeddings': False}
        )
    
    def store_documents(self, repo_name, documents, metadatas, ids):
        collection = self.client.get_or_create_collection(repo_name)
        embeddings = self.embedding_function.embed_documents(documents)
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
    
    def search_repo(self, repo_name, query, n_results=5):
        try:
            collection = self.client.get_collection(repo_name)
            
            query_embedding = self.embedding_function.embed_query(query)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            return results
        except Exception as e:
            print_error(f"Search failed: {str(e)}")
            return None
    
    def search_all(self, query, n_results=5):
        results = {}
        
        query_embedding = self.embedding_function.embed_query(query)
        
        for collection in self.client.list_collections():
            try:
                query_result = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results
                )
                if query_result['documents'][0]:
                    results[collection.name] = query_result
            except Exception:
                continue
        return results
    
    def list_indexed_repos(self):
        return [col.name for col in self.client.list_collections()]