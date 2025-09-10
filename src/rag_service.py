import os
from typing import List, Dict, Optional, Tuple
from src.database import DatabaseManager
from src.vector_store import VectorStoreManager
from src.document_parser import DocumentParser
from src.llm_client import DeepSeekClient
from src.search_engine import SearchEngine
from config import config

class RAGService:
    """RAG服务核心类，整合所有功能"""
    
    def __init__(self):
        self.db = DatabaseManager(config.DATABASE_PATH)
        self.vector_manager = VectorStoreManager()
        self.parser = DocumentParser()
        self.llm_client = DeepSeekClient()
        self.search_engine = SearchEngine()
    
    async def upload_document(self, kb_id: int, file_path: str, filename: str) -> Dict:
        """
        上传并处理文档
        
        Args:
            kb_id: 知识库ID
            file_path: 文件路径
            filename: 文件名
            
        Returns:
            处理结果
        """
        try:
            # 检查知识库是否存在
            kb = self.db.get_knowledge_base(kb_id)
            if not kb:
                raise ValueError(f"知识库ID {kb_id} 不存在")
            
            # 解析文档
            parse_result = await self.parser.parse_document(file_path, filename)
            
            # 保存文档信息到数据库
            file_size = os.path.getsize(file_path)
            content_preview = parse_result['content'][:200] + "..." if len(parse_result['content']) > 200 else parse_result['content']
            
            doc_id = self.db.add_document(
                kb_id=kb_id,
                filename=filename,
                file_path=file_path,
                file_type=parse_result['file_type'],
                file_size=file_size,
                content_preview=content_preview
            )
            
            # 分块文本
            chunks = self.parser.split_text(
                parse_result['content'],
                config.CHUNK_SIZE,
                config.CHUNK_OVERLAP
            )
            
            # 生成向量并存储
            vector_store = self.vector_manager.get_store(kb_id)
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                metadata = {
                    'doc_id': doc_id,
                    'chunk_index': i,
                    'content': chunk,
                    'filename': filename,
                    'kb_id': kb_id
                }
                metadatas.append(metadata)
            
            # 添加到向量存储
            print(f"开始向量化 {len(chunks)} 个文本块...")
            try:
                vector_ids = await vector_store.add_texts(chunks, metadatas)
                print(f"向量化完成，生成了 {len(vector_ids)} 个向量ID")
            except Exception as e:
                print(f"向量化失败: {e}")
                raise e
            
            # 保存文档块到数据库
            for i, (chunk, vector_id) in enumerate(zip(chunks, vector_ids)):
                self.db.add_document_chunk(doc_id, i, chunk, vector_id)
            
            print(f"文档块保存到数据库完成，共 {len(chunks)} 个块")
            
            return {
                'success': True,
                'doc_id': doc_id,
                'filename': filename,
                'chunks_count': len(chunks),
                'message': f'文档 {filename} 处理完成，共生成 {len(chunks)} 个文本块'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def search_knowledge_base(self, kb_id: int, query: str, top_k: int = None, threshold: float = None) -> List[Dict]:
        """
        在知识库中搜索相关内容
        
        Args:
            kb_id: 知识库ID
            query: 搜索查询
            top_k: 返回结果数量
            threshold: 相似度阈值
            
        Returns:
            搜索结果列表
        """
        top_k = top_k or config.TOP_K
        threshold = threshold or config.SIMILARITY_THRESHOLD
        
        try:
            vector_store = self.vector_manager.get_store(kb_id)
            print(f"开始在知识库 {kb_id} 中搜索: {query}")
            print(f"搜索参数: top_k={top_k}, threshold={threshold}")
            
            # 检查向量存储状态
            stats = vector_store.get_stats()
            print(f"向量存储状态: {stats}")
            
            # 检查知识库是否有内容
            if stats['total_vectors'] == 0:
                print(f"知识库 {kb_id} 中没有向量数据，请先上传文档")
                return []
            
            results = await vector_store.search(query, top_k, threshold)
            print(f"搜索完成，找到 {len(results)} 个结果")
            
            # 如果没有找到结果，尝试降低阈值重新搜索
            if len(results) == 0 and threshold > 0.4:
                print(f"未找到结果，尝试降低相似度阈值到 0.5")
                results = await vector_store.search(query, top_k, 0.4)
                print(f"降低阈值后找到 {len(results)} 个结果")
            
            return results
        
        except Exception as e:
            print(f"搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def chat_with_knowledge_base(self, kb_id: int, query: str, top_k: int = None, 
                                     threshold: float = None, use_search_engine: bool = True) -> Dict:
        """
        基于知识库和搜索引擎进行对话
        
        Args:
            kb_id: 知识库ID
            query: 用户查询
            top_k: 检索结果数量
            threshold: 相似度阈值
            use_search_engine: 是否使用搜索引擎
            
        Returns:
            对话结果
        """
        try:
            # 检索相关文档
            kb_results = await self.search_knowledge_base(kb_id, query, top_k, threshold)
            
            # 搜索引擎结果
            search_results = []
            if use_search_engine and self.search_engine.is_enabled():
                search_results = await self.search_engine.search(query, config.SEARCH_RESULTS_COUNT)
            
            # 合并上下文
            contexts = []
            sources = []
            
            # 添加知识库结果
            for result in kb_results:
                contexts.append(result['content'])
                sources.append({
                    'type': 'knowledge_base',
                    'filename': result.get('filename', ''),
                    'similarity_score': result.get('similarity_score', 0),
                    'content_preview': result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                })
            
            # 添加搜索引擎结果
            for result in search_results:
                contexts.append(f"【{result.title}】\n{result.snippet}\n来源: {result.url}")
                sources.append({
                    'type': 'search_engine',
                    'title': result.title,
                    'url': result.url,
                    'content_preview': result.snippet[:100] + "..." if len(result.snippet) > 100 else result.snippet,
                    'source': result.source
                })
            
            # 生成回答
            response = await self.llm_client.generate_response(query, contexts)
            
            return {
                'success': True,
                'query': query,
                'answer': response,
                'knowledge_base_count': len(kb_results),
                'search_engine_count': len(search_results),
                'total_context_count': len(contexts),
                'sources': sources
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_document(self, doc_id: int) -> Dict:
        """删除文档及其向量"""
        try:
            doc = self.db.get_document(doc_id)
            if not doc:
                return {'success': False, 'error': '文档不存在'}
            
            kb_id = doc['kb_id']
            
            # 删除向量
            vector_store = self.vector_manager.get_store(kb_id)
            vector_store.delete_vectors_by_doc_id(doc_id)
            
            # 删除数据库记录
            success = self.db.delete_document(doc_id)
            
            if success:
                return {'success': True, 'message': '文档删除成功'}
            else:
                return {'success': False, 'error': '删除失败'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_knowledge_base(self, kb_id: int) -> Dict:
        """删除知识库"""
        try:
            # 删除向量存储
            self.vector_manager.delete_store(kb_id)
            
            # 删除数据库记录（会级联删除文档和文档块）
            success = self.db.delete_knowledge_base(kb_id)
            
            if success:
                return {'success': True, 'message': '知识库删除成功'}
            else:
                return {'success': False, 'error': '删除失败'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_knowledge_base_stats(self, kb_id: int) -> Dict:
        """获取知识库统计信息"""
        try:
            kb = self.db.get_knowledge_base(kb_id)
            if not kb:
                return {'error': '知识库不存在'}
            
            documents = self.db.get_documents(kb_id)
            vector_store = self.vector_manager.get_store(kb_id)
            vector_stats = vector_store.get_stats()
            
            total_chunks = sum(doc.get('chunk_count', 0) for doc in documents)
            
            return {
                'kb_info': kb,
                'document_count': len(documents),
                'total_chunks': total_chunks,
                'vector_count': vector_stats['total_vectors'],
                'embedding_model': vector_stats['model_name']
            }
        
        except Exception as e:
            return {'error': str(e)}