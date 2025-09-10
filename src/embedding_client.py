import httpx
import numpy as np
from typing import List, Dict, Any
from openai import OpenAI
from config import config

class EmbeddingClient:
    """外部API embedding客户端"""
    
    def __init__(self):
        self.api_type = config.EMBEDDING_API_TYPE
        self.api_key = config.EMBEDDING_API_KEY
        self.base_url = config.EMBEDDING_BASE_URL
        self.model = config.EMBEDDING_MODEL
        self.dimension = config.EMBEDDING_DIMENSION
        
        if self.api_type == "openai":
            if not self.api_key:
                print("警告: Embedding API密钥未设置，请在.env文件中配置EMBEDDING_API_KEY")
                self.client = None
            else:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
        else:
            self.client = None
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        对文本列表进行向量化
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        if not self.client:
            raise ValueError("Embedding客户端未正确配置，请检查EMBEDDING_API_KEY是否设置")
        
        print(f"开始向量化 {len(texts)} 个文本，使用API类型: {self.api_type}")
        
        try:
            if self.api_type == "openai":
                return await self._embed_with_openai(texts)
            elif self.api_type == "cohere":
                return await self._embed_with_cohere(texts)
            elif self.api_type == "huggingface":
                return await self._embed_with_huggingface(texts)
            else:
                raise ValueError(f"不支持的embedding API类型: {self.api_type}")
        
        except Exception as e:
            print(f"Embedding生成失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _embed_with_openai(self, texts: List[str]) -> List[List[float]]:
        """使用OpenAI API进行embedding"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            return [embedding.embedding for embedding in response.data]
        
        except Exception as e:
            raise Exception(f"OpenAI Embedding API调用失败: {str(e)}")
    
    async def _embed_with_cohere(self, texts: List[str]) -> List[List[float]]:
        """使用Cohere API进行embedding"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cohere.ai/v1/embed",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "texts": texts,
                        "model": self.model,
                        "input_type": "search_document"
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"API调用失败: {response.status_code} {response.text}")
                
                result = response.json()
                return result["embeddings"]
        
        except Exception as e:
            raise Exception(f"Cohere Embedding API调用失败: {str(e)}")
    
    async def _embed_with_huggingface(self, texts: List[str]) -> List[List[float]]:
        """使用HuggingFace API进行embedding"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api-inference.huggingface.co/models/{self.model}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "inputs": texts,
                        "options": {"wait_for_model": True}
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"API调用失败: {response.status_code} {response.text}")
                
                result = response.json()
                
                # HuggingFace返回格式可能不同，需要适配
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], list):
                        return result
                    elif isinstance(result[0], dict) and "embedding" in result[0]:
                        return [item["embedding"] for item in result]
                
                raise Exception("HuggingFace API返回格式不支持")
        
        except Exception as e:
            raise Exception(f"HuggingFace Embedding API调用失败: {str(e)}")
    
    def get_dimension(self) -> int:
        """获取embedding维度"""
        # 如果配置的维度与实际模型不匹配，根据模型名称返回正确的维度
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "Qwen/Qwen3-Embedding-8B": 4096,
            "BAAI/bge-large-en-v1.5": 1024,
            "sentence-t5-xxl": 768
        }
        
        # 优先使用模型名称对应的维度
        if self.model in model_dimensions:
            return model_dimensions[self.model]
        
        # 如果模型不在预定义列表中，使用配置的维度
        return self.dimension
    
    async def test_connection(self) -> bool:
        """测试API连接"""
        try:
            test_texts = ["test"]
            embeddings = await self.embed_texts(test_texts)
            return len(embeddings) == 1 and len(embeddings[0]) == self.dimension
        except Exception as e:
            print(f"Embedding API连接测试失败: {e}")
            return False