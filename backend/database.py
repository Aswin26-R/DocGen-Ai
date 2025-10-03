import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import streamlit as st

class Database:
    """PostgreSQL database handler for DocGen"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def init_schema(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Documents table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        type TEXT NOT NULL,
                        file_type TEXT,
                        source TEXT NOT NULL,
                        authors JSONB,
                        abstract TEXT,
                        url TEXT,
                        published TEXT,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        downloaded_at TIMESTAMP,
                        word_count INTEGER,
                        metadata JSONB
                    )
                """)
                
                # Summaries table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS summaries (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        document_title TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        style TEXT,
                        key_concepts JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        word_count INTEGER,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                
                # Quiz history table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_history (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        document_title TEXT NOT NULL,
                        score FLOAT,
                        total_questions INTEGER,
                        correct_answers INTEGER,
                        difficulty TEXT,
                        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        quiz_data JSONB
                    )
                """)
                
                # Activity log table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS activity_log (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        action TEXT NOT NULL,
                        metadata JSONB
                    )
                """)
                
                # Create indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_summaries_user ON summaries(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_quiz_user ON quiz_history(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id)")
                
                conn.commit()
    
    # Document operations
    def save_document(self, user_id: str, document: Dict[str, Any]) -> bool:
        """Save a document to the database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents (id, user_id, title, content, type, file_type, source, 
                                             authors, abstract, url, published, uploaded_at, 
                                             downloaded_at, word_count, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            content = EXCLUDED.content,
                            word_count = EXCLUDED.word_count
                    """, (
                        document['id'], user_id, document['title'], document['content'],
                        document['type'], document.get('file_type'), document['source'],
                        json.dumps(document.get('authors', [])), document.get('abstract'),
                        document.get('url'), document.get('published'),
                        document.get('uploaded_at'), document.get('downloaded_at'),
                        document.get('word_count'), json.dumps(document.get('metadata', {}))
                    ))
                    conn.commit()
            return True
        except Exception as e:
            st.error(f"Error saving document: {e}")
            return False
    
    def get_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM documents WHERE user_id = %s ORDER BY uploaded_at DESC", (user_id,))
                    docs = cur.fetchall()
                    
                    # Convert to list of dicts and parse JSON fields
                    result = []
                    for doc in docs:
                        doc_dict = dict(doc)
                        if doc_dict.get('authors'):
                            doc_dict['authors'] = doc_dict['authors']
                        if doc_dict.get('metadata'):
                            doc_dict['metadata'] = doc_dict['metadata']
                        result.append(doc_dict)
                    return result
        except Exception as e:
            st.error(f"Error loading documents: {e}")
            return []
    
    def delete_document(self, user_id: str, doc_id: str) -> bool:
        """Delete a document"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM documents WHERE id = %s AND user_id = %s", (doc_id, user_id))
                    conn.commit()
            return True
        except Exception as e:
            st.error(f"Error deleting document: {e}")
            return False
    
    # Summary operations
    def save_summary(self, user_id: str, summary: Dict[str, Any]) -> bool:
        """Save a summary to the database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO summaries (id, user_id, document_id, document_title, summary, 
                                             style, key_concepts, created_at, word_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        summary['id'], user_id, summary['document_id'], summary['document_title'],
                        summary['summary'], summary.get('style'), 
                        json.dumps(summary.get('key_concepts', [])),
                        summary.get('created_at'), summary.get('word_count')
                    ))
                    conn.commit()
            return True
        except Exception as e:
            st.error(f"Error saving summary: {e}")
            return False
    
    def get_summaries(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all summaries for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM summaries WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
                    summaries = cur.fetchall()
                    
                    result = []
                    for summary in summaries:
                        summary_dict = dict(summary)
                        if summary_dict.get('key_concepts'):
                            summary_dict['key_concepts'] = summary_dict['key_concepts']
                        result.append(summary_dict)
                    return result
        except Exception as e:
            st.error(f"Error loading summaries: {e}")
            return []
    
    def delete_summary(self, user_id: str, summary_id: str) -> bool:
        """Delete a summary"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM summaries WHERE id = %s AND user_id = %s", (summary_id, user_id))
                    conn.commit()
            return True
        except Exception as e:
            st.error(f"Error deleting summary: {e}")
            return False
    
    # Quiz history operations
    def save_quiz_result(self, user_id: str, quiz_result: Dict[str, Any]) -> bool:
        """Save quiz result to database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO quiz_history (id, user_id, type, document_id, document_title,
                                                score, total_questions, correct_answers, difficulty,
                                                completed_at, quiz_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        quiz_result['id'], user_id, quiz_result['type'], quiz_result['document_id'],
                        quiz_result['document_title'], quiz_result.get('score'),
                        quiz_result.get('total_questions'), quiz_result.get('correct_answers'),
                        quiz_result.get('difficulty'), quiz_result.get('completed_at'),
                        json.dumps(quiz_result)
                    ))
                    conn.commit()
            return True
        except Exception as e:
            st.error(f"Error saving quiz result: {e}")
            return False
    
    def get_quiz_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get quiz history for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM quiz_history WHERE user_id = %s ORDER BY completed_at DESC", (user_id,))
                    quizzes = cur.fetchall()
                    
                    result = []
                    for quiz in quizzes:
                        quiz_dict = dict(quiz)
                        if quiz_dict.get('quiz_data'):
                            quiz_dict.update(quiz_dict['quiz_data'])
                        result.append(quiz_dict)
                    return result
        except Exception as e:
            st.error(f"Error loading quiz history: {e}")
            return []
    
    # Activity log operations
    def log_activity(self, user_id: str, action: str, metadata: Dict[str, Any] = None) -> bool:
        """Log user activity"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO activity_log (user_id, action, metadata)
                        VALUES (%s, %s, %s)
                    """, (user_id, action, json.dumps(metadata or {})))
                    conn.commit()
            return True
        except Exception as e:
            return False
    
    def get_activity_log(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activity log for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM activity_log 
                        WHERE user_id = %s 
                        ORDER BY timestamp DESC 
                        LIMIT %s
                    """, (user_id, limit))
                    activities = cur.fetchall()
                    
                    result = []
                    for activity in activities:
                        activity_dict = dict(activity)
                        activity_dict['timestamp'] = activity_dict['timestamp'].isoformat()
                        result.append(activity_dict)
                    return result
        except Exception as e:
            st.error(f"Error loading activity log: {e}")
            return []
