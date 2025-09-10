import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    # DeepSeek API配置
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    # Embedding API配置
    EMBEDDING_API_TYPE: str = os.getenv("EMBEDDING_API_TYPE", "openai")  # openai, cohere, huggingface
    EMBEDDING_API_KEY: Optional[str] = os.getenv("EMBEDDING_API_KEY")
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))  # text-embedding-3-small的维度
    
    # 搜索引擎配置
    ENABLE_SEARCH_ENGINE: bool = os.getenv("ENABLE_SEARCH_ENGINE", "true").lower() == "true"
    SEARCH_ENGINE_TYPE: str = os.getenv("SEARCH_ENGINE_TYPE", "bing_direct")  # serper, bing, bing_direct, google
    SERPER_API_KEY: Optional[str] = os.getenv("SERPER_API_KEY")
    BING_API_KEY: Optional[str] = os.getenv("BING_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CX_ID: Optional[str] = os.getenv("GOOGLE_CX_ID")
    SEARCH_RESULTS_COUNT: int = int(os.getenv("SEARCH_RESULTS_COUNT", "5"))
    
    # 数据存储配置
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "rag_system.db")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "vector_store")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    
    # 文档处理配置
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    
    # 检索配置
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))

config = Config()