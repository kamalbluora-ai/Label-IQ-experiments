"""
Create embeddings system for common_name_all table to enable semantic search for rule evaluation
"""

import sqlite3, config
import numpy as np
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import pickle
from typing import List, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity

# OpenAI Client for embeddings
client = OpenAI(api_key=config.OPENAI_API_KEY)

class CommonNameEmbeddingSystem:
    """System for creating and using embeddings from common_name_all table for rule evaluation"""
    
    def __init__(self, db_path: str = str(Path(__file__).parent.parent / "data" / "ilt_requirements.db")):
        self.db_path = Path(db_path)
        self.embeddings_cache = {}
        self.knowledge_base = []
        
    def create_embeddings_table(self):
        """Create table to store embeddings"""
        
        if not self.db_path.exists():
            print(f"Error: Database {self.db_path} does not exist!")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create embeddings table
        cursor.execute("DROP TABLE IF EXISTS common_name_embeddings")
        create_table_sql = """
        CREATE TABLE common_name_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            source_table TEXT NOT NULL,
            rule_number INTEGER,
            content_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content_text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            embedding_model TEXT NOT NULL,
            created_date DATETIME NOT NULL,
            FOREIGN KEY (source_id) REFERENCES common_name_all (id)
        )
        """
        
        cursor.execute(create_table_sql)
        print("✓ Created common_name_embeddings table")
        
        conn.commit()
        conn.close()
    
    def generate_embeddings(self):
        """Generate embeddings for all common_name_all records"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all records from common_name_all
        cursor.execute("""
        SELECT id, source_table, rule_number, content_type, title, 
               original_content, concise_summary, compliance_keywords,
               regulatory_context, section_reference, applicability_scope,
               related_urls_concise_summary
        FROM common_name_all 
        ORDER BY rule_number, id
        """)
        
        records = cursor.fetchall()
        print(f"Found {len(records)} records to process for embeddings")
        
        processed_count = 0
        created_date = datetime.utcnow()
        
        for record in records:
            (record_id, source_table, rule_number, content_type, title, 
             original_content, concise_summary, compliance_keywords,
             regulatory_context, section_reference, applicability_scope,
             url_summaries) = record
            
            try:
                # Create comprehensive text for embedding
                content_text = self._create_embedding_text(
                    title, original_content, concise_summary, 
                    compliance_keywords, regulatory_context, 
                    section_reference, applicability_scope, url_summaries
                )
                
                # Generate embedding
                embedding = self._get_embedding(content_text)
                
                if embedding is not None:
                    # Store embedding in database
                    embedding_blob = pickle.dumps(embedding)
                    
                    cursor.execute("""
                    INSERT INTO common_name_embeddings 
                    (source_id, source_table, rule_number, content_type, title, 
                     content_text, embedding, embedding_model, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record_id, source_table, rule_number, content_type, title,
                        content_text, embedding_blob, "text-embedding-3-small", created_date
                    ))
                    
                    processed_count += 1
                    print(f"  ✓ Generated embedding for record {record_id}: {title}")
                
            except Exception as e:
                print(f"  ✗ Error processing record {record_id}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"\n✓ Generated {processed_count} embeddings")
        return processed_count
    
    def _create_embedding_text(self, title, original_content, concise_summary, 
                             compliance_keywords, regulatory_context, 
                             section_reference, applicability_scope, url_summaries):
        """Create comprehensive text for embedding generation"""
        
        parts = []
        
        # Title and summary
        if title:
            parts.append(f"Title: {title}")
        
        if concise_summary:
            parts.append(f"Summary: {concise_summary}")
        elif original_content:
            # Use original content if no summary
            content_preview = original_content[:500] + "..." if len(original_content) > 500 else original_content
            parts.append(f"Content: {content_preview}")
        
        # Compliance information
        if compliance_keywords:
            parts.append(f"Keywords: {compliance_keywords}")
        
        if regulatory_context:
            parts.append(f"Regulations: {regulatory_context}")
        
        if section_reference:
            parts.append(f"Sections: {section_reference}")
        
        if applicability_scope:
            parts.append(f"Applies to: {applicability_scope}")
        
        # URL summaries
        if url_summaries:
            parts.append(f"References: {url_summaries}")
        
        return " | ".join(parts)
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI API"""
        
        try:
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
            
        except Exception as e:
            print(f"    Embedding error: {str(e)}")
            return None
    
    def load_knowledge_base(self):
        """Load embeddings and create searchable knowledge base"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT e.source_id, e.rule_number, e.content_type, e.title, 
               e.content_text, e.embedding, 
               c.concise_summary, c.compliance_keywords, c.regulatory_context
        FROM common_name_embeddings e
        JOIN common_name_all c ON e.source_id = c.id
        ORDER BY e.rule_number, e.id
        """)
        
        records = cursor.fetchall()
        
        self.knowledge_base = []
        for record in records:
            (source_id, rule_number, content_type, title, content_text, 
             embedding_blob, concise_summary, compliance_keywords, regulatory_context) = record
            
            embedding = pickle.loads(embedding_blob)
            
            self.knowledge_base.append({
                'source_id': source_id,
                'rule_number': rule_number,
                'content_type': content_type,
                'title': title,
                'content_text': content_text,
                'embedding': embedding,
                'concise_summary': concise_summary,
                'compliance_keywords': compliance_keywords,
                'regulatory_context': regulatory_context
            })
        
        conn.close()
        print(f"✓ Loaded {len(self.knowledge_base)} embeddings into knowledge base")
        return len(self.knowledge_base)
    
    def search_relevant_context(self, query: str, rule_number: int = None, 
                               top_k: int = 5) -> List[Dict]:
        """Search for relevant context using semantic similarity"""
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return []
        
        # Calculate similarities
        similarities = []
        for item in self.knowledge_base:
            # Filter by rule number if specified
            if rule_number and item['rule_number'] != rule_number:
                continue
            
            similarity = cosine_similarity(
                [query_embedding], 
                [item['embedding']]
            )[0][0]
            
            similarities.append((similarity, item))
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        return [item for _, item in similarities[:top_k]]

if __name__ == "__main__":
    print("Common Name Embeddings System")
    print("=" * 50)
    
    # Initialize system
    embedding_system = CommonNameEmbeddingSystem()
    
    # Create embeddings table
    embedding_system.create_embeddings_table()
    
    # Generate embeddings for all records
    count = embedding_system.generate_embeddings()
    
    # Test loading knowledge base
    embedding_system.load_knowledge_base()
    
    # Test semantic search
    print(f"\n{'='*50}")
    print("TESTING SEMANTIC SEARCH")
    print("="*50)
    
    test_queries = [
        "common name text size requirements",
        "principal display panel placement",
        "exemptions from common name",
        "small package labelling"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = embedding_system.search_relevant_context(query, top_k=2)
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']}")
            print(f"     {result['concise_summary'][:100]}...")
    
    print(f"\n{'='*50}")
    print("EMBEDDINGS SYSTEM READY!")
    print("="*50)