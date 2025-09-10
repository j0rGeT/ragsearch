#!/usr/bin/env python3
"""
RAG检索系统命令行工具
用于配置管理、测试和维护
"""

import argparse
import asyncio
import os
import sys
from typing import Dict, Any

from src.rag_service import RAGService
from src.llm_client import DeepSeekClient
from config import config

class RAGCLIManager:
    def __init__(self):
        self.rag_service = RAGService()
    
    def test_deepseek_connection(self, api_key: str = None) -> Dict[str, Any]:
        """测试DeepSeek API连接"""
        print("测试DeepSeek API连接...")
        
        try:
            client = DeepSeekClient(api_key=api_key)
            success = client.test_connection()
            
            if success:
                print("✅ DeepSeek API连接成功")
                return {"success": True, "message": "连接成功"}
            else:
                print("❌ DeepSeek API连接失败")
                return {"success": False, "message": "连接失败"}
        
        except Exception as e:
            print(f"❌ DeepSeek API连接错误: {e}")
            return {"success": False, "error": str(e)}
    
    def test_embedding_model(self, model_name: str = None) -> Dict[str, Any]:
        """测试embedding模型"""
        model_name = model_name or config.EMBEDDING_MODEL
        print(f"测试embedding模型: {model_name}")
        
        try:
            from src.vector_store import VectorStore
            # 创建临时向量存储来测试模型
            temp_store = VectorStore(999, model_name)  # 使用临时kb_id
            
            # 测试编码
            test_texts = ["这是一个测试文本", "This is a test text"]
            test_metadatas = [{"test": True, "index": i} for i in range(len(test_texts))]
            
            vector_ids = temp_store.add_texts(test_texts, test_metadatas)
            
            # 测试搜索
            results = temp_store.search("测试", top_k=1)
            
            print("✅ Embedding模型测试成功")
            print(f"   - 模型: {model_name}")
            print(f"   - 向量维度: {temp_store.index.d}")
            print(f"   - 测试结果数: {len(results)}")
            
            return {
                "success": True,
                "model": model_name,
                "dimension": temp_store.index.d,
                "test_results": len(results)
            }
        
        except Exception as e:
            print(f"❌ Embedding模型测试失败: {e}")
            return {"success": False, "error": str(e)}
    
    def list_knowledge_bases(self) -> Dict[str, Any]:
        """列出所有知识库"""
        print("知识库列表:")
        
        try:
            kbs = self.rag_service.db.get_knowledge_bases()
            
            if not kbs:
                print("  暂无知识库")
                return {"success": True, "count": 0}
            
            for kb in kbs:
                print(f"  [{kb['id']}] {kb['name']}")
                print(f"      描述: {kb.get('description', '无')}")
                print(f"      文档数: {kb.get('doc_count', 0)}")
                print(f"      创建时间: {kb['created_at']}")
                print()
            
            return {"success": True, "count": len(kbs), "knowledge_bases": kbs}
        
        except Exception as e:
            print(f"❌ 获取知识库列表失败: {e}")
            return {"success": False, "error": str(e)}
    
    def show_system_info(self) -> Dict[str, Any]:
        """显示系统信息"""
        print("RAG检索系统信息:")
        print(f"  配置文件: {config.DATABASE_PATH}")
        print(f"  上传目录: {config.UPLOAD_DIR}")
        print(f"  向量存储目录: {config.VECTOR_STORE_PATH}")
        print(f"  Embedding模型: {config.EMBEDDING_MODEL}")
        print(f"  文本块大小: {config.CHUNK_SIZE}")
        print(f"  文本块重叠: {config.CHUNK_OVERLAP}")
        print(f"  默认检索数量: {config.TOP_K}")
        print(f"  相似度阈值: {config.SIMILARITY_THRESHOLD}")
        print()
        
        # 统计信息
        try:
            kbs = self.rag_service.db.get_knowledge_bases()
            total_docs = 0
            total_vectors = 0
            
            for kb in kbs:
                docs = self.rag_service.db.get_documents(kb['id'])
                total_docs += len(docs)
                
                try:
                    vector_store = self.rag_service.vector_manager.get_store(kb['id'])
                    stats = vector_store.get_stats()
                    total_vectors += stats['total_vectors']
                except:
                    pass
            
            print("系统统计:")
            print(f"  知识库数量: {len(kbs)}")
            print(f"  文档总数: {total_docs}")
            print(f"  向量总数: {total_vectors}")
            
            return {
                "success": True,
                "stats": {
                    "knowledge_bases": len(kbs),
                    "total_documents": total_docs,
                    "total_vectors": total_vectors
                }
            }
        
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def interactive_test(self):
        """交互式测试模式"""
        print("🔍 RAG检索系统交互测试")
        print("输入 'exit' 退出，输入 'help' 查看命令")
        print()
        
        while True:
            try:
                command = input("RAG> ").strip()
                
                if command.lower() == 'exit':
                    print("再见!")
                    break
                
                elif command.lower() == 'help':
                    print("可用命令:")
                    print("  list - 列出知识库")
                    print("  info - 显示系统信息") 
                    print("  test-api - 测试API连接")
                    print("  test-embedding - 测试embedding模型")
                    print("  exit - 退出")
                    print()
                
                elif command.lower() == 'list':
                    self.list_knowledge_bases()
                
                elif command.lower() == 'info':
                    self.show_system_info()
                
                elif command.lower() == 'test-api':
                    self.test_deepseek_connection()
                
                elif command.lower() == 'test-embedding':
                    self.test_embedding_model()
                
                elif command.startswith('chat '):
                    # 简单对话测试
                    parts = command.split(' ', 2)
                    if len(parts) >= 3:
                        kb_id = int(parts[1])
                        query = parts[2]
                        
                        result = await self.rag_service.chat_with_knowledge_base(kb_id, query)
                        
                        if result['success']:
                            print(f"回答: {result['answer']}")
                            print(f"参考来源数: {result['context_count']}")
                        else:
                            print(f"错误: {result['error']}")
                    else:
                        print("用法: chat <kb_id> <查询内容>")
                    print()
                
                else:
                    print(f"未知命令: {command}")
                    print("输入 'help' 查看可用命令")
                    print()
            
            except KeyboardInterrupt:
                print("\n再见!")
                break
            except Exception as e:
                print(f"错误: {e}")
                print()

def main():
    parser = argparse.ArgumentParser(description="RAG检索系统命令行工具")
    parser.add_argument("--test-api", action="store_true", help="测试DeepSeek API连接")
    parser.add_argument("--test-embedding", action="store_true", help="测试embedding模型")
    parser.add_argument("--api-key", help="DeepSeek API密钥")
    parser.add_argument("--model", help="指定embedding模型")
    parser.add_argument("--list-kb", action="store_true", help="列出知识库")
    parser.add_argument("--info", action="store_true", help="显示系统信息")
    parser.add_argument("--interactive", action="store_true", help="进入交互模式")
    
    args = parser.parse_args()
    
    cli = RAGCLIManager()
    
    if args.test_api:
        cli.test_deepseek_connection(args.api_key)
    
    elif args.test_embedding:
        cli.test_embedding_model(args.model)
    
    elif args.list_kb:
        cli.list_knowledge_bases()
    
    elif args.info:
        cli.show_system_info()
    
    elif args.interactive:
        asyncio.run(cli.interactive_test())
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()