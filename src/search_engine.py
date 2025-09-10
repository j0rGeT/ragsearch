import random
import re
from urllib.parse import quote_plus
import httpx
import asyncio
import re
from urllib.parse import quote, urlencode
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from config import config

class SearchResult:
    """搜索结果数据类"""
    def __init__(self, title: str, url: str, snippet: str, source: str = "web"):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source
        }

class SearchEngine:
    """搜索引擎客户端"""
    
    def __init__(self):
        self.engine_type = config.SEARCH_ENGINE_TYPE
        self.enabled = config.ENABLE_SEARCH_ENGINE
        self.results_count = config.SEARCH_RESULTS_COUNT
        
        # API密钥配置
        self.serper_api_key = config.SERPER_API_KEY
        self.bing_api_key = config.BING_API_KEY
        self.google_api_key = config.GOOGLE_API_KEY
        self.google_cx_id = config.GOOGLE_CX_ID
    
    async def search(self, query: str, count: Optional[int] = None) -> List[SearchResult]:
        """
        搜索查询
        
        Args:
            query: 搜索查询
            count: 结果数量
            
        Returns:
            搜索结果列表
        """
        if not self.enabled:
            return []
        
        count = count or self.results_count
        
        try:
            if self.engine_type == "serper":
                return await self._search_with_serper(query, count)
            elif self.engine_type == "bing":
                return await self._search_with_bing(query, count)
            elif self.engine_type == "bing_direct":
                results = await self._search_with_bing(query, count)
                # 如果Bing失败，尝试DuckDuckGo作为备用
                if len(results) == 0:
                    print("Bing搜索失败，尝试DuckDuckGo...")
                    results = await self._search_duckduckgo(query, count)
                return results
            elif self.engine_type == "google":
                return await self._search_with_google(query, count)
            else:
                print(f"不支持的搜索引擎: {self.engine_type}")
                return []
        
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    async def _search_with_serper(self, query: str, count: int) -> List[SearchResult]:
        """使用Serper API搜索"""
        if not self.serper_api_key:
            print("Serper API密钥未配置")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": self.serper_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "num": count,
                        "hl": "zh-cn",
                        "gl": "cn"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    print(f"Serper API调用失败: {response.status_code}")
                    return []
                
                data = response.json()
                results = []
                
                # 处理有机搜索结果
                for item in data.get("organic", [])[:count]:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="serper"
                    ))
                
                return results
        
        except Exception as e:
            print(f"Serper搜索失败: {e}")
            return []

    async def _search_with_bing(self, query: str, count: int) -> List[SearchResult]:
        """使用网页爬虫方式获取Bing搜索结果（无需API密钥）"""
        try:
            # 生成随机User-Agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
            ]

            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }

            # 构建Bing搜索URL
            encoded_query = quote_plus(query)
            search_url = f"https://www.bing.com/search?q={encoded_query}&count={count}&mkt=zh-CN"

            async with httpx.AsyncClient() as client:
                # 添加随机延迟，避免被反爬
                await asyncio.sleep(random.uniform(1, 3))

                response = await client.get(
                    search_url,
                    headers=headers,
                    timeout=15.0,
                    follow_redirects=True
                )

                if response.status_code != 200:
                    print(f"Bing搜索请求失败: {response.status_code}")
                    return []

                # 解析HTML响应
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []

                # 查找搜索结果项 - Bing的搜索结果通常包含在<li class="b_algo">元素中
                search_items = soup.find_all('li', class_='b_algo')

                for item in search_items[:count]:
                    try:
                        # 提取标题
                        title_elem = item.find('h2')
                        title = title_elem.get_text().strip() if title_elem else "无标题"

                        # 提取URL
                        link_elem = item.find('a')
                        url = link_elem.get('href') if link_elem else ""

                        # 提取摘要
                        snippet_elem = item.find('p') or item.find('div', class_='b_caption')
                        snippet = snippet_elem.get_text().strip() if snippet_elem else ""

                        # 清理摘要文本
                        snippet = re.sub(r'\s+', ' ', snippet)

                        if url:  # 确保有有效的URL
                            results.append(SearchResult(
                                title=title,
                                url=url,
                                snippet=snippet,
                                source="bing_web"
                            ))
                    except Exception as e:
                        print(f"解析搜索结果项时出错: {e}")
                        continue

                return results

        except httpx.TimeoutException:
            print("Bing搜索请求超时")
            return []
        except httpx.RequestError as e:
            print(f"Bing搜索网络请求错误: {e}")
            return []
        except Exception as e:
            print(f"Bing搜索失败: {str(e)}")
            return []
    
    async def _search_with_google(self, query: str, count: int) -> List[SearchResult]:
        """使用Google API搜索"""
        if not self.google_api_key or not self.google_cx_id:
            print("Google API密钥或搜索引擎ID未配置")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.google_api_key,
                        "cx": self.google_cx_id,
                        "q": query,
                        "num": min(count, 10),  # Google API最多返回10个结果
                        "lr": "lang_zh-CN",
                        "gl": "cn"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    print(f"Google API调用失败: {response.status_code}")
                    return []
                
                data = response.json()
                results = []
                
                # 处理搜索结果
                for item in data.get("items", [])[:count]:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="google"
                    ))
                
                return results
        
        except Exception as e:
            print(f"Google搜索失败: {e}")
            return []
    
    async def _search_bing_direct(self, query: str, count: int) -> List[SearchResult]:
        """直接爬取Bing搜索结果（无需API密钥）"""
        try:
            # 构建Bing搜索URL - 使用更简单的参数
            params = {
                'q': query,
                'count': min(count, 10),  # 限制结果数量
                'mkt': 'zh-CN',
                'setlang': 'zh-cn',
                'form': 'QBLH'  # 基本搜索表单
            }
            
            search_url = f"https://www.bing.com/search?{urlencode(params)}"
            
            # 设置更真实的浏览器请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
            
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                try:
                    response = await client.get(search_url, headers=headers)
                    
                    # 检查是否被重定向到验证页面
                    final_url = str(response.url)
                    html_content = response.text
                    
                    # 检测CAPTCHA和验证页面
                    if any(indicator in final_url.lower() or indicator in html_content.lower() 
                          for indicator in ['verify', 'challenge', 'captcha', '人机验证', '验证码', '安全检查']):
                        print("检测到验证页面，Bing可能阻止了自动化请求")
                        return []
                    
                    if response.status_code != 200:
                        print(f"Bing搜索请求失败: {response.status_code}")
                        return []
                        
                except Exception as e:
                    print(f"请求异常: {e}")
                    return []
                
                # 解析HTML内容
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # 方法1: 查找主要的搜索结果容器
                # 尝试多种可能的选择器
                selectors = [
                    'li.b_algo',           # 传统Bing结果
                    'div.b_algo',          # 另一种容器
                    'article.b_algo',      # 可能的容器
                    '[data-bm]',           # 数据属性
                    '.b_result',           # 结果类
                    '[class*="b_algo"]',   # 包含b_algo的类
                    '[class*="b_result"]', # 包含b_result的类
                ]
                
                for selector in selectors:
                    result_elements = soup.select(selector)
                    if result_elements:
                        print(f"使用选择器 '{selector}' 找到 {len(result_elements)} 个结果元素")
                        
                        for element in result_elements[:count]:
                            try:
                                # 提取标题链接
                                title_link = element.select_one('h2 a, h3 a, .b_title a, a[href]')
                                if not title_link:
                                    continue
                                
                                title = title_link.get_text(strip=True)
                                url = title_link.get('href', '')
                                
                                # 过滤无效结果
                                if not title or not url or len(title) < 3 or 'bing.com' in url:
                                    continue
                                
                                # 处理相对URL
                                if url.startswith('/'):
                                    url = f"https://www.bing.com{url}"
                                elif not url.startswith('http'):
                                    continue
                                
                                # 提取摘要
                                snippet = ""
                                snippet_selectors = [
                                    '.b_caption p',
                                    '.b_caption',
                                    '.b_attribution',
                                    '[class*="snippet"]',
                                    'p'
                                ]
                                
                                for snippet_selector in snippet_selectors:
                                    snippet_elem = element.select_one(snippet_selector)
                                    if snippet_elem:
                                        snippet = snippet_elem.get_text(separator=' ', strip=True)
                                        if snippet:
                                            break
                                
                                # 如果没有找到摘要，尝试从父元素中提取
                                if not snippet:
                                    parent_text = element.get_text(separator=' ', strip=True)
                                    title_pos = parent_text.find(title)
                                    if title_pos != -1:
                                        start = max(0, title_pos + len(title))
                                        end = min(len(parent_text), start + 200)
                                        snippet = parent_text[start:end].strip()
                                
                                # 创建结果对象
                                result = SearchResult(
                                    title=title[:150],
                                    url=url,
                                    snippet=snippet[:250],
                                    source="bing_direct"
                                )
                                
                                # 去重
                                if not any(r.url == result.url for r in results):
                                    results.append(result)
                                
                                if len(results) >= count:
                                    break
                                    
                            except Exception as e:
                                continue
                        
                        if results:
                            break
                
                # 方法2: 如果上述方法失败，尝试提取所有外部链接
                if not results:
                    print("尝试提取所有外部链接...")
                    all_links = soup.find_all('a', href=True)
                    
                    for link in all_links:
                        if len(results) >= count:
                            break
                        
                        try:
                            title = link.get_text(strip=True)
                            url = link.get('href', '')
                            
                            # 过滤条件
                            if (len(title) >= 5 and 
                                url.startswith('http') and 
                                not url.startswith('https://www.bing.com') and
                                not any(x in url for x in ['/images/', '/videos/', '/maps/', '/redir/'])):
                                
                                # 提取摘要（从链接周围的文本）
                                snippet = ""
                                parent = link.find_parent()
                                if parent:
                                    parent_text = parent.get_text(separator=' ', strip=True)
                                    title_pos = parent_text.find(title)
                                    if title_pos != -1:
                                        start = max(0, title_pos + len(title))
                                        end = min(len(parent_text), start + 150)
                                        snippet = parent_text[start:end].strip()
                                
                                results.append(SearchResult(
                                    title=title[:100],
                                    url=url,
                                    snippet=snippet[:200],
                                    source="bing_links"
                                ))
                                
                        except Exception:
                            continue
                
                print(f"Bing搜索找到 {len(results)} 个结果")
                return results
        
        except Exception as e:
            print(f"Bing直接搜索失败: {e}")
            return []
    
    async def _search_duckduckgo(self, query: str, count: int) -> List[SearchResult]:
        """使用DuckDuckGo搜索（无需API密钥）"""
        try:
            # DuckDuckGo搜索URL
            params = {
                'q': query,
                'kl': 'zh-cn',  # 中文结果
                'kz': '-1'      # 禁用安全搜索
            }
            search_url = f"https://html.duckduckgo.com/html/?{urlencode(params)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(search_url, headers=headers)
                
                if response.status_code != 200:
                    print(f"DuckDuckGo搜索失败: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # DuckDuckGo的结果通常在class="result"的div中
                result_divs = soup.find_all('div', class_='result')
                
                for result_div in result_divs[:count]:
                    try:
                        # 提取标题和链接
                        title_link = result_div.find('a', class_='result__a')
                        if not title_link:
                            continue
                        
                        title = title_link.get_text(strip=True)
                        url = title_link.get('href', '')
                        
                        # DuckDuckGo的URL需要处理（可能包含重定向）
                        if url.startswith('//duckduckgo.com/l/'):
                            # 这是一个重定向链接，我们需要提取真实URL
                            import urllib.parse
                            parsed = urllib.parse.urlparse(url)
                            query_params = urllib.parse.parse_qs(parsed.query)
                            if 'uddg' in query_params:
                                real_url = query_params['uddg'][0]
                                url = urllib.parse.unquote(real_url)
                        
                        # 提取摘要
                        snippet_elem = result_div.find('a', class_='result__snippet')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        # 过滤无效结果
                        if not title or not url.startswith('http'):
                            continue
                        
                        results.append(SearchResult(
                            title=title[:100],
                            url=url,
                            snippet=snippet[:200],
                            source="duckduckgo"
                        ))
                        
                    except Exception as e:
                        print(f"解析DuckDuckGo结果失败: {e}")
                        continue
                
                print(f"DuckDuckGo搜索找到 {len(results)} 个结果")
                return results
                
        except Exception as e:
            print(f"DuckDuckGo搜索失败: {e}")
            return []
    
    def is_enabled(self) -> bool:
        """检查搜索引擎是否启用"""
        return self.enabled
    
    async def test_connection(self) -> bool:
        """测试搜索引擎连接"""
        try:
            results = await self.search("test", 1)
            return len(results) > 0
        except Exception as e:
            print(f"搜索引擎连接测试失败: {e}")
            return False