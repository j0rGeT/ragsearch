// 全局变量
let currentKnowledgeBase = null;
let isLoading = false;

// API基础URL
const API_BASE = window.location.origin;

// DOM元素
const elements = {
    kbName: () => document.getElementById('kb-name'),
    kbDesc: () => document.getElementById('kb-desc'),
    knowledgeBases: () => document.getElementById('knowledge-bases'),
    currentKb: () => document.getElementById('current-kb'),
    fileInput: () => document.getElementById('file-input'),
    uploadBtn: () => document.getElementById('upload-btn'),
    documents: () => document.getElementById('documents'),
    chatHistory: () => document.getElementById('chat-history'),
    chatInput: () => document.getElementById('chat-input'),
    sendBtn: () => document.getElementById('send-btn'),
    topK: () => document.getElementById('top-k'),
    threshold: () => document.getElementById('threshold'),
    useSearchEngine: () => document.getElementById('use-search-engine'),
    statusMessage: () => document.getElementById('status-message'),
    loading: () => document.getElementById('loading')
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadKnowledgeBases();
    setupEventListeners();
});

// 设置事件监听器
function setupEventListeners() {
    // 回车发送消息
    elements.chatInput().addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 文件选择
    elements.fileInput().addEventListener('change', function() {
        const file = this.files[0];
        if (file && currentKnowledgeBase) {
            elements.uploadBtn().disabled = false;
        }
    });
}

// 显示状态消息
function showStatus(message, type = 'info', duration = 3000) {
    const statusEl = elements.statusMessage();
    statusEl.textContent = message;
    statusEl.className = `status-message ${type} show`;
    
    setTimeout(() => {
        statusEl.className = 'status-message';
    }, duration);
}

// 显示/隐藏加载动画
function showLoading(show = true) {
    isLoading = show;
    const loadingEl = elements.loading();
    if (show) {
        loadingEl.classList.remove('hidden');
    } else {
        loadingEl.classList.add('hidden');
    }
}

// API请求封装
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${url}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API请求失败:', error);
        throw error;
    }
}

// 创建知识库
async function createKnowledgeBase() {
    const name = elements.kbName().value.trim();
    const description = elements.kbDesc().value.trim();
    
    if (!name) {
        showStatus('请输入知识库名称', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const result = await apiRequest('/knowledge_bases', {
            method: 'POST',
            body: JSON.stringify({ name, description })
        });
        
        showStatus('知识库创建成功', 'success');
        elements.kbName().value = '';
        elements.kbDesc().value = '';
        loadKnowledgeBases();
    } catch (error) {
        showStatus(`创建失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 加载知识库列表
async function loadKnowledgeBases() {
    try {
        const result = await apiRequest('/knowledge_bases');
        const kbs = result.knowledge_bases || [];
        
        const container = elements.knowledgeBases();
        
        if (kbs.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无知识库</div>';
            return;
        }
        
        container.innerHTML = kbs.map(kb => `
            <div class="kb-item ${currentKnowledgeBase?.id === kb.id ? 'selected' : ''}" data-kb-id="${kb.id}">
                <h5>${escapeHtml(kb.name)}</h5>
                <p>${escapeHtml(kb.description || '无描述')}</p>
                <p><i class="fas fa-file"></i> ${kb.doc_count || 0} 个文档</p>
                <div class="actions">
                    <button onclick="selectKnowledgeBase(${kb.id}, '${escapeHtml(kb.name)}')" class="btn btn-primary btn-small">
                        <i class="fas fa-check"></i> 选择
                    </button>
                    <button onclick="deleteKnowledgeBase(${kb.id})" class="btn btn-danger btn-small">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showStatus(`加载知识库失败: ${error.message}`, 'error');
    }
}

// 选择知识库
async function selectKnowledgeBase(kbId, kbName) {
    currentKnowledgeBase = { id: kbId, name: kbName };
    
    // 更新UI
    elements.currentKb().innerHTML = `<i class="fas fa-database"></i> ${escapeHtml(kbName)}`;
    elements.chatInput().disabled = false;
    elements.sendBtn().disabled = false;
    
    // 更新选中状态
    document.querySelectorAll('.kb-item').forEach(item => {
        item.classList.remove('selected');
    });
    document.querySelector(`[data-kb-id="${kbId}"]`).classList.add('selected');
    
    // 加载文档列表
    loadDocuments(kbId);
    
    // 清空对话历史
    clearChatHistory();
    
    showStatus(`已选择知识库: ${kbName}`, 'success');
}

// 删除知识库
async function deleteKnowledgeBase(kbId) {
    if (!confirm('确定要删除这个知识库吗？此操作不可恢复。')) {
        return;
    }
    
    showLoading(true);
    
    try {
        await apiRequest(`/knowledge_bases/${kbId}`, { method: 'DELETE' });
        
        showStatus('知识库删除成功', 'success');
        
        if (currentKnowledgeBase && currentKnowledgeBase.id === kbId) {
            currentKnowledgeBase = null;
            elements.currentKb().textContent = '请先选择知识库';
            elements.chatInput().disabled = true;
            elements.sendBtn().disabled = true;
            elements.uploadBtn().disabled = true;
            elements.documents().innerHTML = '';
            clearChatHistory();
        }
        
        loadKnowledgeBases();
    } catch (error) {
        showStatus(`删除失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 上传文档
async function uploadDocument() {
    if (!currentKnowledgeBase) {
        showStatus('请先选择知识库', 'error');
        return;
    }
    
    const fileInput = elements.fileInput();
    const file = fileInput.files[0];
    
    if (!file) {
        showStatus('请选择文件', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/knowledge_bases/${currentKnowledgeBase.id}/documents`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        showStatus(`文档上传成功: ${result.message}`, 'success');
        fileInput.value = '';
        elements.uploadBtn().disabled = true;
        
        // 刷新文档列表
        loadDocuments(currentKnowledgeBase.id);
        
    } catch (error) {
        showStatus(`上传失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 加载文档列表
async function loadDocuments(kbId) {
    try {
        const result = await apiRequest(`/knowledge_bases/${kbId}/documents`);
        const docs = result.documents || [];
        
        const container = elements.documents();
        
        if (docs.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无文档</div>';
            return;
        }
        
        container.innerHTML = docs.map(doc => `
            <div class="doc-item">
                <h5><i class="fas fa-file"></i> ${escapeHtml(doc.filename)}</h5>
                <p>${escapeHtml(doc.content_preview || '无预览')}</p>
                <p><i class="fas fa-cubes"></i> ${doc.chunk_count || 0} 个文本块 | ${formatFileSize(doc.file_size)}</p>
                <div class="actions">
                    <button onclick="deleteDocument(${doc.id})" class="btn btn-danger btn-small">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showStatus(`加载文档失败: ${error.message}`, 'error');
    }
}

// 删除文档
async function deleteDocument(docId) {
    if (!confirm('确定要删除这个文档吗？')) {
        return;
    }
    
    showLoading(true);
    
    try {
        await apiRequest(`/documents/${docId}`, { method: 'DELETE' });
        
        showStatus('文档删除成功', 'success');
        
        if (currentKnowledgeBase) {
            loadDocuments(currentKnowledgeBase.id);
        }
    } catch (error) {
        showStatus(`删除失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 发送消息
async function sendMessage() {
    if (!currentKnowledgeBase) {
        showStatus('请先选择知识库', 'error');
        return;
    }
    
    const query = elements.chatInput().value.trim();
    if (!query) {
        return;
    }
    
    if (isLoading) {
        return;
    }
    
    // 添加用户消息到聊天历史
    addMessageToChat('user', query);
    
    // 清空输入框
    elements.chatInput().value = '';
    
    // 显示加载状态
    const loadingMessageId = addMessageToChat('assistant', '正在思考...', true);
    
    showLoading(true);
    
    try {
        const topK = parseInt(elements.topK().value) || 5;
        const threshold = parseFloat(elements.threshold().value) || 0.7;
        const useSearchEngine = elements.useSearchEngine().checked;
        
        const result = await apiRequest(`/knowledge_bases/${currentKnowledgeBase.id}/chat`, {
            method: 'POST',
            body: JSON.stringify({ 
                query, 
                top_k: topK, 
                threshold: threshold,
                use_search_engine: useSearchEngine
            })
        });
        
        // 移除加载消息
        removeMessage(loadingMessageId);
        
        if (result.success) {
            // 添加助手回答
            addMessageToChat('assistant', result.answer, false, result.sources);
        } else {
            addMessageToChat('assistant', `错误: ${result.error}`);
        }
        
    } catch (error) {
        removeMessage(loadingMessageId);
        addMessageToChat('assistant', `发生错误: ${error.message}`);
        showStatus(`对话失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 添加消息到聊天历史
function addMessageToChat(role, content, isLoading = false, sources = null) {
    const chatHistory = elements.chatHistory();
    
    // 如果是第一条消息，清除欢迎消息
    const welcomeMsg = chatHistory.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageId = `msg-${Date.now()}-${Math.random()}`;
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.id = messageId;
    
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="sources">
                <strong>参考来源:</strong>
                ${sources.map(source => {
                    if (source.type === 'knowledge_base') {
                        return `
                            <div class="source kb-source">
                                <i class="fas fa-database"></i>
                                <strong>${escapeHtml(source.filename)}</strong> 
                                (相似度: ${(source.similarity_score * 100).toFixed(1)}%)
                                <br><small>${escapeHtml(source.content_preview)}</small>
                            </div>
                        `;
                    } else if (source.type === 'search_engine') {
                        return `
                            <div class="source search-source">
                                <i class="fas fa-search"></i>
                                <strong><a href="${source.url}" target="_blank">${escapeHtml(source.title)}</a></strong>
                                <span class="source-tag">${source.source}</span>
                                <br><small>${escapeHtml(source.content_preview)}</small>
                            </div>
                        `;
                    }
                    return '';
                }).join('')}
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-${role}">
            ${escapeHtml(content)}
            ${sourcesHtml}
            <div class="message-meta">
                ${new Date().toLocaleTimeString()}
            </div>
        </div>
    `;
    
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    return messageId;
}

// 移除消息
function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// 清空聊天历史
function clearChatHistory() {
    const chatHistory = elements.chatHistory();
    chatHistory.innerHTML = `
        <div class="welcome-message">
            <i class="fas fa-robot"></i>
            <p>欢迎使用RAG检索系统！</p>
            <p>请选择知识库，然后开始对话。我会根据知识库内容为您答疑解惑。</p>
        </div>
    `;
}

// 工具函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 错误处理
window.addEventListener('error', function(e) {
    console.error('JavaScript错误:', e.error);
    showStatus('发生了一个错误，请刷新页面重试', 'error');
});

// 网络错误处理
window.addEventListener('unhandledrejection', function(e) {
    console.error('未处理的Promise拒绝:', e.reason);
    if (e.reason.message && e.reason.message.includes('fetch')) {
        showStatus('网络连接失败，请检查服务器状态', 'error');
    }
});