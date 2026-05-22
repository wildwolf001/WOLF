"""
Web Fetch Tool - 网页获取工具
"""
from typing import Dict, Any, Optional
import re


class WebFetchTool:
    """网页获取工具"""

    def __init__(self):
        self.name = "webfetch"
        self.description = "Fetch and extract content from web pages"
        self.args = ["url", "selector", "prompt"]

    async def execute(
        self,
        url: str,
        selector: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取网页内容

        Args:
            url: 网页URL
            selector: 可选的CSS选择器
            prompt: 可选的提取提示

        Returns:
            网页内容字典
        """
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="webfetch",
            request_type="web_fetch",
            description=f"获取网页: {url}",
            command=url,
            risk_level="MEDIUM"
        )

        if not allowed:
            return {
                "success": False,
                "error": reason
            }

        try:
            import requests

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }

            # 尝试编码
            response.encoding = response.apparent_encoding or 'utf-8'
            content = response.text

            # 如果有selector，用正则提取
            if selector:
                content = self._extract_by_selector(content, selector)

            # 清理HTML
            clean_content = self._clean_html(content)

            # 截断过长内容
            if len(clean_content) > 10000:
                clean_content = clean_content[:10000] + "\n\n[内容已截断...]"

            return {
                "success": True,
                "url": url,
                "content": clean_content,
                "title": self._extract_title(content)
            }

        except ImportError:
            return {
                "success": False,
                "error": "Web fetch requires the 'requests' library. Please install it."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_by_selector(self, html: str, selector: str) -> str:
        """用简单正则模拟CSS选择器"""
        # 简化实现，实际应该用BeautifulSoup或playwright
        if selector.startswith('.'):
            # class选择器
            class_name = selector[1:]
            pattern = f'<[^>]*class="[^"]*{class_name}[^"]*"[^>]*>([^<]+)</[^>]+>'
            matches = re.findall(pattern, html)
            return '\n'.join(matches[:10])
        elif selector.startswith('#'):
            # id选择器
            id_name = selector[1:]
            pattern = f'<[^>]*id="{id_name}"[^>]*>([^<]+)</[^>]+>'
            match = re.search(pattern, html)
            return match.group(1) if match else ""
        else:
            return html[:5000]

    def _clean_html(self, html: str) -> str:
        """清理HTML标签"""
        # 移除script和style标签
        html = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html)
        html = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html)
        # 移除注释
        html = re.sub(r'<!--[\s\S]*?-->', '', html)
        # 移除标签
        html = re.sub(r'<[^>]+>', ' ', html)
        # 清理实体
        html = html.replace('&nbsp;', ' ').replace('&amp;', '&')
        html = html.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        # 清理多余空白
        html = re.sub(r'\s+', ' ', html)
        return html.strip()

    def _extract_title(self, html: str) -> str:
        """提取页面标题"""
        match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        return match.group(1).strip() if match else ""


# 单例
web_fetch_tool = WebFetchTool()


async def fetch_web(url: str, selector: str = None, prompt: str = None) -> Dict[str, Any]:
    """便捷函数：获取网页内容"""
    return await web_fetch_tool.execute(url, selector, prompt)