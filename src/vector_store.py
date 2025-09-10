import os
import json
import pickle
import numpy as np
import faiss
from typing import List, Dict, Tuple, Optional
from src.embedding_client import EmbeddingClient
from config import config

class VectorStore:
    """向量存储管理器，处理embedding和相似度搜索"""
    
    def __init__(self, kb_id: int):
        self.kb_id = kb_id
        self.embedding_client = EmbeddingClient()
        self.index = None
        self.metadata = []
        
        # 向量存储路径
        self.vector_dir = os.path.join(config.VECTOR_STORE_PATH, f"kb_{kb_id}")
        self.index_path = os.path.join(self.vector_dir, "faiss.index")
        self.metadata_path = os.path.join(self.vector_dir, "metadata.pkl")
        
        os.makedirs(self.vector_dir, exist_ok=True)
        
        # 加载索引
        self._load_index()
    
    def _load_index(self):
        """加载FAISS索引"""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            print(f"已加载向量索引，包含 {len(self.metadata)} 个向量")
        else:
            # 创建新索引
            dimension = self.embedding_client.get_dimension()
            print(f"创建新向量索引，维度: {dimension}")
            self.index = faiss.IndexFlatIP(dimension)  # 使用内积相似度
            self.metadata = []
    
    async def add_texts(self, texts: List[str], metadatas: List[Dict]) -> List[str]:
        """
        添加文本到向量存储
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            
        Returns:
            向量ID列表
        """
        if len(texts) != len(metadatas):
            raise ValueError("文本和元数据数量不匹配")
        
        # 生成embeddings
        embeddings = await self.embedding_client.embed_texts(texts)
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # 规范化向量（用于余弦相似度）
        embeddings_array = embeddings_array / np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        
        # 添加到FAISS索引
        start_id = len(self.metadata)
        self.index.add(embeddings_array)
        
        # 添加元数据
        vector_ids = []
        for i, metadata in enumerate(metadatas):
            vector_id = f"vec_{self.kb_id}_{start_id + i}"
            metadata['vector_id'] = vector_id
            self.metadata.append(metadata)
            vector_ids.append(vector_id)
        
        # 保存索引和元数据
        self._save_index()
        
        return vector_ids
    
    async def search(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """
        搜索相似文本
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            threshold: 相似度阈值
            
        Returns:
            搜索结果列表
        """
        print(f"向量搜索开始 - 索引中有 {self.index.ntotal} 个向量")
        
        if self.index.ntotal == 0:
            print("向量索引为空，返回空结果")
            return []
        
        try:
            # 生成查询向量
            print(f"正在为查询生成embedding: {query}")
            query_embeddings = await self.embedding_client.embed_texts([query])
            print(f"查询embedding生成成功，维度: {len(query_embeddings[0])}")
            
            # 检查维度是否匹配
            expected_dim = self.embedding_client.get_dimension()
            actual_dim = len(query_embeddings[0])
            if expected_dim != actual_dim:
                print(f"警告: 维度不匹配! 配置维度: {expected_dim}, 实际维度: {actual_dim}")
                # 尝试调整维度或返回空结果
                return []
            
            query_embedding = np.array(query_embeddings, dtype=np.float32)
            query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
            
            # 检查查询向量维度是否与索引匹配
            if query_embedding.shape[1] != self.index.d:
                print(f"错误: 查询向量维度({query_embedding.shape[1]})与索引维度({self.index.d})不匹配!")
                return []
            
            # 搜索
            print(f"开始向量搜索，top_k={top_k}, threshold={threshold}")
            scores, indices = self.index.search(query_embedding, top_k)
            print(f"向量搜索完成，得分: {scores[0][:min(5, len(scores[0]))]}")
            print(f"索引: {indices[0][:min(5, len(indices[0]))]}")
            
            results = []
            valid_results = 0
            for score, idx in zip(scores[0], indices[0]):
                print(f"处理结果 - score: {score}, idx: {idx}, threshold: {threshold}")
                if score >= threshold and idx < len(self.metadata) and idx >= 0:
                    result = self.metadata[idx].copy()
                    result['similarity_score'] = float(score)
                    results.append(result)
                    valid_results += 1
                    print(f"添加结果: {result.get('filename', 'unknown')} - 相似度: {score:.3f}")
                else:
                    print(f"跳过结果 - score: {score} < {threshold} 或 idx: {idx} 超出范围 [0, {len(self.metadata)-1}]")
            
            print(f"向量搜索完成，找到 {valid_results} 个有效结果 (总计 {len(results)} 个结果)")
            return results
        
        except Exception as e:
            print(f"向量搜索出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def delete_vectors_by_doc_id(self, doc_id: int):
        """删除指定文档的所有向量"""
        # 找到需要删除的向量索引
        indices_to_remove = []
        new_metadata = []
        
        for i, metadata in enumerate(self.metadata):
            if metadata.get('doc_id') == doc_id:
                indices_to_remove.append(i)
            else:
                new_metadata.append(metadata)
        
        if not indices_to_remove:
            return
        
        # 重建索引（FAISS不支持直接删除）
        if new_metadata:
            # 获取保留的向量
            all_vectors = []
            for i in range(self.index.ntotal):
                if i not in indices_to_remove:
                    vector = self.index.reconstruct(i)
                    all_vectors.append(vector)
            
            if all_vectors:
                # 创建新索引
                dimension = all_vectors[0].shape[0]
                new_index = faiss.IndexFlatIP(dimension)
                vectors_array = np.array(all_vectors).astype('float32')
                new_index.add(vectors_array)
                
                self.index = new_index
                self.metadata = new_metadata
            else:
                # 如果没有向量了，创建空索引
                dimension = self.embedding_client.get_dimension()
                print(f"创建空向量索引，维度: {dimension}")
                self.index = faiss.IndexFlatIP(dimension)
                self.metadata = []
        else:
            # 创建空索引
            dimension = self.embedding_client.get_dimension()
            print(f"创建空向量索引，维度: {dimension}")
            self.index = faiss.IndexFlatIP(dimension)
            self.metadata = []
        
        # 保存更新后的索引
        self._save_index()
    
    def get_stats(self) -> Dict:
        """获取向量存储统计信息"""
        return {
            'kb_id': self.kb_id,
            'total_vectors': self.index.ntotal if self.index else 0,
            'model_name': config.EMBEDDING_MODEL,
            'dimension': self.index.d if self.index else 0
        }
    
    def _save_index(self):
        """保存FAISS索引和元数据"""
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)


class VectorStoreManager:
    """向量存储管理器，管理多个知识库的向量存储"""
    
    def __init__(self):
        self.stores = {}
    
    def get_store(self, kb_id: int) -> VectorStore:
        """获取或创建向量存储"""
        if kb_id not in self.stores:
            self.stores[kb_id] = VectorStore(kb_id)
        return self.stores[kb_id]
    
    def delete_store(self, kb_id: int):
        """删除向量存储"""
        if kb_id in self.stores:
            del self.stores[kb_id]
        
        # 删除存储文件
        vector_dir = os.path.join(config.VECTOR_STORE_PATH, f"kb_{kb_id}")
        if os.path.exists(vector_dir):
            import shutil
            shutil.rmtree(vector_dir)