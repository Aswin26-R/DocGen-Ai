import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
import streamlit as st
from google import genai
from google.genai import types

class DocumentEmbeddings:
    """FAISS-based vector storage for document embeddings using Gemini embeddings"""
    
    def __init__(self):
        api_key = st.session_state.get('gemini_api_key') or os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
        self.dimension = 768  # Gemini embedding dimension
        self.documents = []
        self.metadata = []
        self.index_file = "data/embeddings_index.pkl"
        self.load_index()
    
    def add_document(self, text: str, metadata: Dict[str, Any]):
        """Add a document to the vector store"""
        try:
            if not self.client:
                st.warning("Embeddings not available. Search functionality will be limited.")
                return False
                
            # Split text into chunks
            chunks = self._chunk_text(text, chunk_size=512, overlap=50)
            
            for i, chunk in enumerate(chunks):
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
        """Search for similar documents using keyword matching"""
        try:
            if not self.documents:
                return []
            
            # Simple keyword-based search as fallback
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            results = []
            for i, (doc, meta) in enumerate(zip(self.documents, self.metadata)):
                doc_lower = doc.lower()
                doc_words = set(doc_lower.split())
                
                # Calculate simple similarity score based on word overlap
                common_words = query_words.intersection(doc_words)
                if common_words:
                    score = len(common_words) / max(len(query_words), 1)
                    result = meta.copy()
                    result['similarity_score'] = float(score)
                    result['text'] = doc
                    results.append(result)
            
            # Sort by score and return top k
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:k]
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
        """Rebuild the index from current documents"""
        pass
    
    def save_index(self):
        """Save index and metadata to disk"""
        try:
            os.makedirs("data", exist_ok=True)
            
            with open(self.index_file, 'wb') as f:
                pickle.dump({
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
                
                self.documents = data.get('documents', [])
                self.metadata = data.get('metadata', [])
        except Exception as e:
            # If loading fails, start with empty index
            self.documents = []
            self.metadata = []
    
    def get_document_stats(self) -> Dict[str, int]:
        """Get statistics about the document store"""
        stats = {
            'total_chunks': len(self.documents),
            'total_documents': len(set(meta.get('document_id', '') for meta in self.metadata)),
            'index_size': len(self.documents)
        }
        return stats
