"""
Web Fetch Tool
Fetches content from URLs
"""
import asyncio
from typing import Dict, Any, Optional


class WebFetchTool:
    """Tool for fetching web content"""

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        self._headers = headers or {}

    async def execute(
        self,
        url: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Fetch content from URL"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    content = await resp.text()
                    return {
                        "success": True,
                        "url": url,
                        "content": content,
                        "status": resp.status,
                        "content_type": resp.headers.get("Content-Type", "")
                    }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Request timed out after {timeout}s",
                "url": url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        return {
            "name": "web_fetch",
            "description": "Fetch content from a URL",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 30
                    }
                },
                "required": ["url"]
            }
        }


async def web_fetch(
    url: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """Fetch content from URL"""
    tool = WebFetchTool()
    return await tool.execute(url, timeout=timeout)