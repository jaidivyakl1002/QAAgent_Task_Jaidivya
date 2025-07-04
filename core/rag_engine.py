import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.docstore.document import Document
from typing import List, Dict, Optional
import json
import os
from config.settings import settings

class RAGEngine:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.vectorstore = None
        
        # Optimized for 6-minute video
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,      # Smaller chunks for better precision
            chunk_overlap=50,    # Less overlap needed
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
    def process_video_transcript(self, transcript_data: Dict) -> None:
        """Process 6-minute video transcript - optimized approach"""
        
        segments = transcript_data.get('segments', [])
        documents = []
        
        # For 6-minute video, we can use multiple granularities
        
        # 1. Segment-level chunks (30-60 seconds each)
        for segment in segments:
            doc = Document(
                page_content=segment['text'],
                metadata={
                    'start_time': segment['start'],
                    'end_time': segment['end'],
                    'segment_id': segment['id'],
                    'source': 'recruter_tutorial_video',
                    'granularity': 'segment'
                }
            )
            documents.append(doc)
        
        # 2. Topic-based chunks (group related segments)
        topic_chunks = self._group_segments_by_topic(segments)
        for topic, chunk_text in topic_chunks.items():
            doc = Document(
                page_content=chunk_text,
                metadata={
                    'topic': topic,
                    'source': 'recruter_tutorial_video',
                    'granularity': 'topic'
                }
            )
            documents.append(doc)
        
        # 3. Full transcript (for global context)
        full_text = transcript_data.get('text', '')
        doc = Document(
            page_content=full_text,
            metadata={
                'source': 'recruter_tutorial_video',
                'granularity': 'full',
                'total_duration': segments[-1]['end'] if segments else 0
            }
        )
        documents.append(doc)
        
        # Create vector store
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=settings.VECTORSTORE_DIR
        )
        self.vectorstore.persist()
    
    def _group_segments_by_topic(self, segments: List[Dict]) -> Dict[str, str]:
        """Group segments by likely topics for 6-minute tutorial"""
        
        # Common topics in SaaS tutorials
        topics = {
            'signup_registration': [],
            'login_authentication': [],
            'dashboard_overview': [],
            'profile_settings': [],
            'main_features': [],
            'navigation': []
        }
        
        # Simple keyword-based grouping (could be enhanced with LLM)
        for segment in segments:
            text = segment['text'].lower()
            
            if any(word in text for word in ['sign up', 'register', 'create account']):
                topics['signup_registration'].append(segment['text'])
            elif any(word in text for word in ['login', 'sign in', 'authenticate']):
                topics['login_authentication'].append(segment['text'])
            elif any(word in text for word in ['dashboard', 'home', 'overview']):
                topics['dashboard_overview'].append(segment['text'])
            elif any(word in text for word in ['profile', 'settings', 'account']):
                topics['profile_settings'].append(segment['text'])
            elif any(word in text for word in ['navigate', 'menu', 'click']):
                topics['navigation'].append(segment['text'])
            else:
                topics['main_features'].append(segment['text'])
        
        # Join segments for each topic
        return {topic: ' '.join(segments) for topic, segments in topics.items() if segments}
    
    def semantic_search(self, query: str, k: int = 3) -> List[Document]:
        """Reduced k value since we have fewer total chunks"""
        if not self.vectorstore:
            self._load_vectorstore()
            
        return self.vectorstore.similarity_search(query, k=k)
    
    def get_contextual_chunks(self, query: str, include_full_transcript: bool = False) -> str:
        """Get relevant context for 6-minute video"""
        
        # Get segment-level matches
        segment_docs = self.vectorstore.similarity_search(
            query, 
            k=2,
            filter={"granularity": "segment"}
        )
        
        # Get topic-level matches
        topic_docs = self.vectorstore.similarity_search(
            query, 
            k=1,
            filter={"granularity": "topic"}
        )
        
        context_parts = []
        
        # Add segment context
        for doc in segment_docs:
            if 'start_time' in doc.metadata:
                context_parts.append(
                    f"[{doc.metadata['start_time']:.1f}s] {doc.page_content}"
                )
        
        # Add topic context
        for doc in topic_docs:
            if 'topic' in doc.metadata:
                context_parts.append(
                    f"[Topic: {doc.metadata['topic']}] {doc.page_content}"
                )
        
        # Optionally include full transcript for comprehensive context
        if include_full_transcript:
            full_docs = self.vectorstore.similarity_search(
                query, 
                k=1,
                filter={"granularity": "full"}
            )
            if full_docs:
                context_parts.append(f"[Full Context] {full_docs[0].page_content}")
        
        return "\n\n".join(context_parts)