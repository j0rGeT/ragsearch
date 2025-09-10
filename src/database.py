import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime
import os

class DatabaseManager:
    """数据库管理器，处理知识库和文档元数据"""
    
    def __init__(self, db_path: str = "rag_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_bases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kb_id INTEGER,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    content_preview TEXT,
                    chunk_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (kb_id) REFERENCES knowledge_bases (id) ON DELETE CASCADE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER,
                    chunk_index INTEGER,
                    content TEXT NOT NULL,
                    vector_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents (id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
    
    def create_knowledge_base(self, name: str, description: str = "") -> int:
        """创建知识库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO knowledge_bases (name, description) VALUES (?, ?)",
                (name, description)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_knowledge_bases(self) -> List[Dict]:
        """获取所有知识库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT kb.*, COUNT(d.id) as doc_count
                FROM knowledge_bases kb
                LEFT JOIN documents d ON kb.id = d.kb_id
                GROUP BY kb.id
                ORDER BY kb.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_knowledge_base(self, kb_id: int) -> Optional[Dict]:
        """获取指定知识库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_knowledge_base(self, kb_id: int) -> bool:
        """删除知识库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def add_document(self, kb_id: int, filename: str, file_path: str, 
                    file_type: str, file_size: int, content_preview: str = "") -> int:
        """添加文档到知识库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO documents (kb_id, filename, file_path, file_type, file_size, content_preview)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (kb_id, filename, file_path, file_type, file_size, content_preview))
            conn.commit()
            return cursor.lastrowid
    
    def get_documents(self, kb_id: int) -> List[Dict]:
        """获取知识库中的所有文档"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC",
                (kb_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_document(self, doc_id: int) -> Optional[Dict]:
        """获取指定文档"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_document(self, doc_id: int) -> bool:
        """删除文档"""
        doc = self.get_document(doc_id)
        if doc and os.path.exists(doc['file_path']):
            os.remove(doc['file_path'])
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def add_document_chunk(self, doc_id: int, chunk_index: int, content: str, vector_id: str = "") -> int:
        """添加文档块"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO document_chunks (doc_id, chunk_index, content, vector_id)
                VALUES (?, ?, ?, ?)
            """, (doc_id, chunk_index, content, vector_id))
            
            # 更新文档的chunk_count
            conn.execute("""
                UPDATE documents SET chunk_count = (
                    SELECT COUNT(*) FROM document_chunks WHERE doc_id = ?
                ) WHERE id = ?
            """, (doc_id, doc_id))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_document_chunks(self, doc_id: int) -> List[Dict]:
        """获取文档的所有块"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM document_chunks WHERE doc_id = ? ORDER BY chunk_index",
                (doc_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_chunks_by_kb(self, kb_id: int) -> List[Dict]:
        """获取知识库的所有文档块"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT dc.*, d.filename
                FROM document_chunks dc
                JOIN documents d ON dc.doc_id = d.id
                WHERE d.kb_id = ?
                ORDER BY dc.created_at
            """, (kb_id,))
            return [dict(row) for row in cursor.fetchall()]