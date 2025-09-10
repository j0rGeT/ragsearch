from openai import OpenAI
from typing import List, Dict, Optional
from config import config

class DeepSeekClient:
    """DeepSeek LLM客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.base_url = base_url or config.DEEPSEEK_BASE_URL
        
        if not self.api_key:
            print("警告: DeepSeek API密钥未设置，请在.env文件中配置DEEPSEEK_API_KEY")
            self.client = None
        else:
            # 配置OpenAI客户端使用DeepSeek
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
    
    async def generate_response(self, query: str, context: List[str], 
                              model: str = "deepseek-chat") -> str:
        """
        生成基于上下文的回答
        
        Args:
            query: 用户查询
            context: 检索到的上下文列表
            model: 使用的模型名称
            
        Returns:
            生成的回答
        """
        if not self.client:
            return "错误: DeepSeek API未配置，请设置DEEPSEEK_API_KEY环境变量"
            
        # 构建系统提示
        system_prompt = """你是一个专业的AI助手，专门回答基于提供的知识库内容的问题。

请严格遵循以下规则：
1. 主要基于提供的上下文信息回答问题，优先使用知识库内容
2. 如果上下文中没有相关信息，请明确说明"根据提供的知识库内容，我无法找到相关信息"
3. 如果知识库中没有相关信息但搜索引擎提供了有用信息，可以基于搜索引擎结果回答，但要明确说明信息来源
4. 如果知识库和搜索引擎都没有相关信息，请诚实回答"我无法从知识库和网络搜索中找到相关信息"
5. 保持回答准确、简洁、有帮助，避免编造信息
6. 如果可能，引用具体的上下文内容并注明来源
7. 使用中文回答
8. 当知识库内容不足时，可以提供一些通用的建议或询问是否需要补充更多信息

上下文信息：
"""
        
        # 添加上下文
        if context:
            for i, ctx in enumerate(context, 1):
                system_prompt += f"\n[上下文{i}]\n{ctx}\n"
        else:
            system_prompt += "\n暂无相关上下文信息。\n"
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"LLM生成回答失败: {str(e)}"
    
    def test_connection(self) -> bool:
        """测试API连接"""
        if not self.client:
            return False
            
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            print(f"API连接测试失败: {e}")
            return False