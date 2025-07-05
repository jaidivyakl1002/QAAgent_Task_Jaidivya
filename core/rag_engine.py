import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from pathlib import Path
import openai
from openai import OpenAI
from models.test_case import RAGQuery, RAGResult, VideoSegment, ProcessedVideo

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 vector_store_path: str = "data/vectorstore",
                 openai_api_key: Optional[str] = None):
        """
        Initialize RAG Engine with sentence transformer and FAISS vector store
        
        Args:
            model_name: Sentence transformer model name
            vector_store_path: Path to store vector database
            openai_api_key: OpenAI API key for generation
        """
        self.model_name = model_name
        self.vector_store_path = Path(vector_store_path)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize sentence transformer
        self.encoder = SentenceTransformer(model_name)
        self.embedding_dim = self.encoder.get_sentence_embedding_dimension()
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        self.documents = []
        self.metadata = []
        
        # Initialize OpenAI client
        self.openai_client = None
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
        elif os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Load existing vector store if available
        self.load_vector_store()
    
    def encode_documents(self, documents: List[str]) -> np.ndarray:
        """Encode documents using sentence transformer"""
        try:
            embeddings = self.encoder.encode(documents, normalize_embeddings=True)
            return embeddings
        except Exception as e:
            logger.error(f"Error encoding documents: {e}")
            raise
    
    def add_documents(self, documents: List[str], metadata: List[Dict[str, Any]]):
        """Add documents to the vector store"""
        try:
            if len(documents) != len(metadata):
                raise ValueError("Number of documents and metadata must match")
            
            # Encode documents
            embeddings = self.encode_documents(documents)
            
            # Add to FAISS index
            self.index.add(embeddings)
            
            # Store documents and metadata
            self.documents.extend(documents)
            self.metadata.extend(metadata)
            
            logger.info(f"Added {len(documents)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise
    
    def add_video_segments(self, processed_video: ProcessedVideo):
        """Add video segments to the vector store"""
        try:
            documents = []
            metadata = []
            
            # Add full transcript
            documents.append(processed_video.full_transcript)
            metadata.append({
                'type': 'full_transcript',
                'video_url': processed_video.url,
                'video_title': processed_video.title,
                'duration': processed_video.duration
            })
            
            # Add individual segments
            for i, segment in enumerate(processed_video.segments):
                documents.append(segment.transcript)
                metadata.append({
                    'type': 'segment',
                    'segment_id': i,
                    'start_time': segment.start_time,
                    'end_time': segment.end_time,
                    'action_description': segment.action_description,
                    'ui_elements': segment.ui_elements,
                    'video_url': processed_video.url
                })
            
            # Add extracted flows
            for i, flow in enumerate(processed_video.extracted_flows):
                documents.append(flow)
                metadata.append({
                    'type': 'user_flow',
                    'flow_id': i,
                    'video_url': processed_video.url
                })
            
            self.add_documents(documents, metadata)
            
        except Exception as e:
            logger.error(f"Error adding video segments: {e}")
            raise
    
    def search(self, query: str, top_k: int = 5, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector store is empty")
                return []
            
            # Encode query
            query_embedding = self.encode_documents([query])
            
            # Search in FAISS index
            scores, indices = self.index.search(query_embedding, top_k)
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if score >= similarity_threshold:
                    results.append({
                        'document': self.documents[idx],
                        'metadata': self.metadata[idx],
                        'score': float(score),
                        'rank': i + 1
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise
    
    def generate_response(self, query: str, context_docs: List[str], 
                         system_prompt: str = None) -> str:
        """Generate response using OpenAI GPT"""
        try:
            if not self.openai_client:
                raise ValueError("OpenAI client not initialized")
            
            # Prepare context
            context = "\n\n".join(context_docs)
            
            # Default system prompt
            if not system_prompt:
                system_prompt = """You are QAgenie, a thorough AI QA assistant. 
                Use the provided context to answer questions about testing scenarios, 
                user flows, and UI interactions. Be specific and actionable."""
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuery: {query}"}
            ]
            
            # Generate response
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def query(self, rag_query: RAGQuery, system_prompt: str = None) -> RAGResult:
        """Perform RAG query"""
        try:
            # Search for relevant documents
            search_results = self.search(
                rag_query.query, 
                rag_query.top_k, 
                rag_query.similarity_threshold
            )
            
            # Generate response if OpenAI client available
            generated_response = None
            confidence = 0.0
            
            if self.openai_client and search_results:
                context_docs = [result['document'] for result in search_results]
                generated_response = self.generate_response(
                    rag_query.query, 
                    context_docs, 
                    system_prompt
                )
                
                # Calculate confidence based on top result score
                confidence = search_results[0]['score'] if search_results else 0.0
            
            return RAGResult(
                query=rag_query.query,
                results=search_results,
                generated_response=generated_response,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            raise
    
    def save_vector_store(self):
        """Save vector store to disk"""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.vector_store_path / "faiss_index.bin"))
            
            # Save documents and metadata
            with open(self.vector_store_path / "documents.pkl", "wb") as f:
                pickle.dump(self.documents, f)
            
            with open(self.vector_store_path / "metadata.pkl", "wb") as f:
                pickle.dump(self.metadata, f)
            
            logger.info("Vector store saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            raise
    
    def load_vector_store(self):
        """Load vector store from disk"""
        try:
            index_path = self.vector_store_path / "faiss_index.bin"
            documents_path = self.vector_store_path / "documents.pkl"
            metadata_path = self.vector_store_path / "metadata.pkl"
            
            if all(path.exists() for path in [index_path, documents_path, metadata_path]):
                # Load FAISS index
                self.index = faiss.read_index(str(index_path))
                
                # Load documents and metadata
                with open(documents_path, "rb") as f:
                    self.documents = pickle.load(f)
                
                with open(metadata_path, "rb") as f:
                    self.metadata = pickle.load(f)
                
                logger.info(f"Vector store loaded with {len(self.documents)} documents")
            else:
                logger.info("No existing vector store found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            # Continue with empty store
            pass
    
    def clear_vector_store(self):
        """Clear the vector store"""
        try:
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.documents = []
            self.metadata = []
            logger.info("Vector store cleared")
            
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            'total_documents': len(self.documents),
            'embedding_dimension': self.embedding_dim,
            'model_name': self.model_name,
            'has_openai_client': self.openai_client is not None
        }