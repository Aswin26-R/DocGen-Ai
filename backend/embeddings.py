import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
import faiss
from sentence_transformers import SentenceTransformer
import streamlit as st

class DocumentEmbeddings:
    """FAISS-based vector storage for document embeddings"""
    
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product for cosine similarity
        self.documents = []
        self.metadata = []
        self.index_file = "data/faiss_index.pkl"
        self.load_index()
    
    def add_document(self, text: str, metadata: Dict[str, Any]):
        """Add a document to the vector store"""
        try:
            # Split text into chunks
            chunks = self._chunk_text(text, chunk_size=512, overlap=50)
            
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = self.model.encode([chunk])
                
                # Normalize for cosine similarity
                faiss.normalize_L2(embedding)
                
                # Add to FAISS index
                self.index.add(embedding)
                
                # Store document and metadata
                self.documents.append(chunk)
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_id'] = i
                chunk_metadata['chunk_text'] = chunk
                self.metadata.append(chunk_metadata)
            
            self.save_index()
            return True
        except Exception as e:
            st.error(f"Error adding document to embeddings: {e}")
            return False
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            if self.index.ntotal == 0:
                return []
            
            # Generate query embedding
            query_embedding = self.model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result['similarity_score'] = float(score)
                    result['text'] = self.documents[idx]
                    results.append(result)
            
            return results
        except Exception as e:
            st.error(f"Error searching embeddings: {e}")
            return []
    
    def get_similar_chunks(self, document_id: str, k: int = 3) -> List[str]:
        """Get similar chunks from the same document"""
        try:
            # Find all chunks from the document
            doc_chunks = []
            for i, meta in enumerate(self.metadata):
                if meta.get('document_id') == document_id:
                    doc_chunks.append((i, self.documents[i]))
            
            if not doc_chunks:
                return []
            
            # Return first k chunks or all if less than k
            return [chunk[1] for chunk in doc_chunks[:k]]
        except Exception as e:
            st.error(f"Error getting similar chunks: {e}")
            return []
    
    def remove_document(self, document_id: str):
        """Remove a document from the vector store"""
        try:
            # Find indices to remove
            indices_to_remove = []
            for i, meta in enumerate(self.metadata):
                if meta.get('document_id') == document_id:
                    indices_to_remove.append(i)
            
            # Remove from metadata and documents (reverse order to maintain indices)
            for idx in reversed(indices_to_remove):
                del self.metadata[idx]
                del self.documents[idx]
            
            # Rebuild FAISS index
            self._rebuild_index()
            self.save_index()
            return True
        except Exception as e:
            st.error(f"Error removing document: {e}")
            return False
    
    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks if chunks else [text]
    
    def _rebuild_index(self):
        """Rebuild the FAISS index from current documents"""
        self.index = faiss.IndexFlatIP(self.dimension)
        
        if self.documents:
            embeddings = self.model.encode(self.documents)
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings)
    
    def save_index(self):
        """Save index and metadata to disk"""
        try:
            os.makedirs("data", exist_ok=True)
            
            with open(self.index_file, 'wb') as f:
                pickle.dump({
                    'index': faiss.serialize_index(self.index),
                    'documents': self.documents,
                    'metadata': self.metadata
                }, f)
        except Exception as e:
            st.error(f"Error saving index: {e}")
    
    def load_index(self):
        """Load index and metadata from disk"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'rb') as f:
                    data = pickle.load(f)
                
                self.index = faiss.deserialize_index(data['index'])
                self.documents = data['documents']
                self.metadata = data['metadata']
        except Exception as e:
            # If loading fails, start with empty index
            self.index = faiss.IndexFlatIP(self.dimension)
            self.documents = []
            self.metadata = []
    
    def get_document_stats(self) -> Dict[str, int]:
        """Get statistics about the document store"""
        stats = {
            'total_chunks': len(self.documents),
            'total_documents': len(set(meta.get('document_id', '') for meta in self.metadata)),
            'index_size': self.index.ntotal
        }
        return stats
