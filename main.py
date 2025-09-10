from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import os
import uuid
import shutil
from pydantic import BaseModel

from src.rag_service import RAGService
from config import config

app = FastAPI(title="RAG检索系统", version="1.0.0")

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 全局服务实例
rag_service = RAGService()

# 请求模型
class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    description: str = ""

class ChatRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    threshold: Optional[float] = None
    use_search_engine: Optional[bool] = True

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    threshold: Optional[float] = None

# API路由

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api")
async def api_root():
    """API根路径"""
    return {"message": "RAG检索系统API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "rag-search"}

# 知识库管理
@app.post("/knowledge_bases")
async def create_knowledge_base(request: CreateKnowledgeBaseRequest):
    """创建知识库"""
    try:
        kb_id = rag_service.db.create_knowledge_base(request.name, request.description)
        return {"success": True, "kb_id": kb_id, "name": request.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/knowledge_bases")
async def list_knowledge_bases():
    """获取所有知识库"""
    try:
        kbs = rag_service.db.get_knowledge_bases()
        return {"success": True, "knowledge_bases": kbs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge_bases/{kb_id}")
async def get_knowledge_base(kb_id: int):
    """获取指定知识库信息"""
    try:
        kb = rag_service.db.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        stats = rag_service.get_knowledge_base_stats(kb_id)
        return {"success": True, "knowledge_base": kb, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/knowledge_bases/{kb_id}")
async def delete_knowledge_base(kb_id: int):
    """删除知识库"""
    try:
        result = rag_service.delete_knowledge_base(kb_id)
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 文档管理
@app.post("/knowledge_bases/{kb_id}/documents")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...)
):
    """上传文档到知识库"""
    try:
        # 检查文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.pdf', '.docx', '.txt']:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")
        
        # 保存上传文件
        os.makedirs(config.UPLOAD_DIR, exist_ok=True)
        file_id = str(uuid.uuid4())
        file_path = os.path.join(config.UPLOAD_DIR, f"{file_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 处理文档
        result = await rag_service.upload_document(kb_id, file_path, file.filename)
        
        if result['success']:
            return result
        else:
            # 如果处理失败，删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail=result['error'])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge_bases/{kb_id}/documents")
async def list_documents(kb_id: int):
    """获取知识库中的所有文档"""
    try:
        documents = rag_service.db.get_documents(kb_id)
        return {"success": True, "documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    """删除文档"""
    try:
        result = rag_service.delete_document(doc_id)
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 搜索和对话
@app.post("/knowledge_bases/{kb_id}/search")
async def search_knowledge_base(kb_id: int, request: SearchRequest):
    """在知识库中搜索"""
    try:
        results = await rag_service.search_knowledge_base(
            kb_id, request.query, request.top_k, request.threshold
        )
        return {
            "success": True,
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge_bases/{kb_id}/chat")
async def chat_with_knowledge_base(kb_id: int, request: ChatRequest):
    """基于知识库进行对话"""
    try:
        result = await rag_service.chat_with_knowledge_base(
            kb_id, request.query, request.top_k, request.threshold, request.use_search_engine
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 系统信息
@app.get("/stats")
async def get_system_stats():
    """获取系统统计信息"""
    try:
        kbs = rag_service.db.get_knowledge_bases()
        total_docs = 0
        total_vectors = 0
        
        for kb in kbs:
            docs = rag_service.db.get_documents(kb['id'])
            total_docs += len(docs)
            
            try:
                vector_store = rag_service.vector_manager.get_store(kb['id'])
                stats = vector_store.get_stats()
                total_vectors += stats['total_vectors']
            except:
                pass
        
        return {
            "knowledge_bases": len(kbs),
            "total_documents": total_docs,
            "total_vectors": total_vectors,
            "embedding_model": config.EMBEDDING_MODEL,
            "supported_formats": [".pdf", ".docx", ".txt"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)