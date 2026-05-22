"""
Web Search Tool - 网络搜索工具
"""
from typing import Dict, Any, Optional
import json
import re


class WebSearchTool:
    """网络搜索工具"""

    def __init__(self):
        self.name = "websearch"
        self.description = "Search the web for information"
        self.args = ["query", "num_results"]

    async def execute(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        执行网络搜索

        Args:
            query: 搜索查询
            num_results: 返回结果数量

        Returns:
            搜索结果字典
        """
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="websearch",
            request_type="web_search",
            description=f"网络搜索: {query}",
            command=query,
            risk_level="MEDIUM"
        )

        if not allowed:
            return {
                "success": False,
                "error": reason
            }

        try:
            # 尝试使用requests库进行搜索
            import requests

            # 使用 DuckDuckGo HTML API (免费，无需API key)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            url = f"https://duckduckgo.com/html/?q={requests.utils.quote(query)}"

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # 解析HTML结果
                results = self._parse_ddg_html(response.text, num_results)
                return {
                    "success": True,
                    "results": results,
                    "query": query
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }

        except ImportError:
            # 如果没有requests，使用模拟结果
            return {
                "success": True,
                "results": [
                    {
                        "title": f"关于 '{query}' 的搜索结果",
                        "url": "https://example.com",
                        "snippet": "Web search requires the 'requests' library. Please install it to enable live search."
                    }
                ],
                "query": query,
                "note": "Simulated results - install requests for live search"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_ddg_html(self, html: str, num_results: int) -> list:
        """解析DuckDuckGo HTML结果"""
        results = []

        # 匹配结果模式
        patterns = [
            r'<a class="result__a" href="([^"]+)">([^<]+)</a>',
            r'<a href="([^"]+)" class="result__snippet">([^<]+)</a>'
        ]

        seen_urls = set()
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for url, title in matches:
                if url not in seen_urls and not url.startswith('https://duckduckgo'):
                    seen_urls.add(url)
                    results.append({
                        "title": self._clean_html(title),
                        "url": url,
                        "snippet": ""
                    })
                    if len(results) >= num_results:
                        break
            if len(results) >= num_results:
                break

        return results[:num_results]

    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text.strip()


# 单例
web_search_tool = WebSearchTool()


async def search_web(query: str, num_results: int = 5) -> Dict[str, Any]:
    """便捷函数：执行网络搜索"""
    return await web_search_tool.execute(query, num_results)