# RAG检索系统

基于Python开发的RAG（Retrieval-Augmented Generation）检索系统，支持文档上传、知识库管理、向量化存储和智能对话，集成外部API和搜索引擎增强。

## 🎯 功能特性

✅ **文档解析支持**: PDF、Word、TXT格式文档解析  
✅ **知识库管理**: 创建、删除、管理多个知识库  
✅ **外部Embedding API**: 支持OpenAI、Cohere、HuggingFace等API  
✅ **向量化存储**: 使用FAISS进行高效相似度搜索  
✅ **搜索引擎增强**: 集成Serper、Bing、Google搜索结果  
✅ **智能对话**: 基于DeepSeek大模型的混合检索对话  
✅ **Web界面**: 现代化响应式Web用户界面  
✅ **REST API**: 完整的Web API接口  
✅ **可配置**: 支持灵活的API和模型配置  

## 项目结构

```
ragsearch/
├── main.py                 # FastAPI应用入口
├── cli.py                  # 命令行工具
├── start.py               # 启动脚本
├── config.py               # 配置管理
├── requirements.txt        # 依赖列表
├── .env.example           # 环境变量模板
├── src/
│   ├── __init__.py
│   ├── document_parser.py  # 文档解析
│   ├── database.py        # 数据库管理
│   ├── vector_store.py    # 向量存储
│   ├── embedding_client.py # 外部Embedding API客户端
│   ├── search_engine.py   # 搜索引擎客户端
│   ├── llm_client.py      # DeepSeek LLM客户端
│   └── rag_service.py     # RAG核心服务
├── static/                # Web静态文件
│   ├── css/style.css      # 样式文件
│   └── js/app.js          # 前端JavaScript
├── templates/             # HTML模板
│   └── index.html         # 主页面
├── uploads/               # 上传文件目录
└── vector_store/          # 向量存储目录
```

## 快速开始

### 1. 环境设置

```bash
# 克隆项目
git clone <your-repo-url>
cd ragsearch

# 安装依赖
pip install -r requirements.txt

# 复制环境配置
cp .env.example .env
```

### 2. 配置API密钥

编辑 `.env` 文件，配置必要的API密钥：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Embedding API配置（必需）
EMBEDDING_API_TYPE=openai
EMBEDDING_API_KEY=your_openai_api_key_here

# 搜索引擎配置（可选）
ENABLE_SEARCH_ENGINE=true
SEARCH_ENGINE_TYPE=bing_direct
```

**必需配置项：**
- `DEEPSEEK_API_KEY`: DeepSeek API密钥用于LLM对话
- `EMBEDDING_API_KEY`: 外部API密钥用于文本向量化

**可选配置项：**
- `ENABLE_SEARCH_ENGINE`: 是否启用搜索引擎增强（默认使用Bing直接爬取，无需API密钥）

### 3. 启动服务

```bash
# 使用启动脚本（推荐）
python start.py

# 或直接启动
python main.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后：
- **Web界面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

### 4. 使用命令行工具

```bash
# 查看系统信息
python cli.py --info

# 测试API连接
python cli.py --test-api

# 测试embedding模型
python cli.py --test-embedding

# 进入交互模式
python cli.py --interactive
```

## API使用示例

### 创建知识库

```bash
curl -X POST "http://localhost:8000/knowledge_bases" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "我的知识库",
       "description": "测试知识库"
     }'
```

### 上传文档

```bash
curl -X POST "http://localhost:8000/knowledge_bases/1/documents" \
     -F "file=@document.pdf"
```

### 智能对话

```bash
curl -X POST "http://localhost:8000/knowledge_bases/1/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "你好，请问文档中提到了什么内容？",
       "use_search_engine": true
     }'
```

### 搜索知识库

```bash
curl -X POST "http://localhost:8000/knowledge_bases/1/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "搜索关键词",
       "top_k": 5
     }'
```

## 配置选项

### 环境变量配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | 必需 |
| `EMBEDDING_API_TYPE` | Embedding API类型 | `openai` |
| `EMBEDDING_API_KEY` | Embedding API密钥 | 必需 |
| `EMBEDDING_MODEL` | Embedding模型名称 | `text-embedding-3-small` |
| `ENABLE_SEARCH_ENGINE` | 启用搜索引擎 | `true` |
| `SEARCH_ENGINE_TYPE` | 搜索引擎类型 | `bing_direct` |
| `SERPER_API_KEY` | Serper API密钥 | 可选 |
| `DATABASE_PATH` | 数据库文件路径 | `rag_system.db` |
| `VECTOR_STORE_PATH` | 向量存储目录 | `vector_store` |
| `UPLOAD_DIR` | 上传文件目录 | `uploads` |
| `CHUNK_SIZE` | 文本分块大小 | `500` |
| `CHUNK_OVERLAP` | 文本块重叠 | `50` |
| `TOP_K` | 默认检索数量 | `5` |
| `SIMILARITY_THRESHOLD` | 相似度阈值 | `0.7` |

### 支持的API服务

#### Embedding API
- **OpenAI**: `text-embedding-3-small`, `text-embedding-3-large` 等
- **Cohere**: `embed-english-v2.0`, `embed-multilingual-v2.0` 等  
- **HuggingFace**: 支持各种开源embedding模型

#### 搜索引擎服务
- **Bing直接爬取**: 无需API密钥，直接爬取Bing搜索结果 (默认推荐)
- **Serper**: Google搜索API服务
- **Bing API**: Microsoft Bing搜索API
- **Google API**: Google Custom Search API

## API接口说明

### 知识库管理

- `POST /knowledge_bases` - 创建知识库
- `GET /knowledge_bases` - 获取所有知识库
- `GET /knowledge_bases/{kb_id}` - 获取指定知识库
- `DELETE /knowledge_bases/{kb_id}` - 删除知识库

### 文档管理

- `POST /knowledge_bases/{kb_id}/documents` - 上传文档
- `GET /knowledge_bases/{kb_id}/documents` - 获取知识库文档列表
- `DELETE /documents/{doc_id}` - 删除文档

### 搜索和对话

- `POST /knowledge_bases/{kb_id}/search` - 搜索知识库
- `POST /knowledge_bases/{kb_id}/chat` - 基于知识库对话

### 系统信息

- `GET /health` - 健康检查
- `GET /stats` - 系统统计信息

## 开发说明

### 添加新的文档解析器

在 `src/document_parser.py` 中添加新的解析方法：

```python
async def _parse_new_format(self, file_path: str) -> str:
    # 实现新格式解析
    pass
```

### 切换向量数据库

修改 `src/vector_store.py` 中的存储实现，支持其他向量数据库如Milvus、Pinecone等。

### 集成其他LLM

在 `src/llm_client.py` 中添加新的LLM客户端实现。

## 故障排除

### 常见问题

1. **API连接失败**
   - 检查DeepSeek API密钥是否正确
   - 确认网络连接正常

2. **文档解析失败**
   - 检查文件格式是否支持
   - 确认文件未损坏

3. **向量搜索无结果**
   - 检查相似度阈值设置
   - 确认知识库中有相关内容

4. **内存占用过高**
   - 调整文本分块大小
   - 选择更轻量的embedding模型

### 日志查看

系统运行时会输出详细日志，包括：
- 文档解析进度
- 向量化处理状态
- API请求响应

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 更新日志

### v1.0.0
- 初始版本发布
- 支持PDF/Word/TXT文档解析
- 基于FAISS的向量存储
- DeepSeek LLM集成
- 完整的REST API
- 命令行管理工具