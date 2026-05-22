"""
Browser Automation Service - 浏览器自动化服务

基于Playwright实现网页浏览和自动化操作
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio
import re


@dataclass
class BrowserResult:
    """浏览器操作结果"""
    success: bool
    content: str = ""
    title: str = ""
    url: str = ""
    screenshot: Optional[str] = None
    error: str = ""


class BrowserAutomationService:
    """
    浏览器自动化服务

    支持:
    - 页面导航
    - 点击元素
    - 填写表单
    - 提取内容
    - 截图
    """

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._is_initialized = False

    async def initialize(self, headless: bool = True):
        """
        初始化浏览器

        Args:
            headless: 是否无头模式
        """
        if self._is_initialized:
            return

        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720}
            )
            self.page = await self.context.new_page()

            # 设置用户代理
            await self.page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

            self._is_initialized = True

        except ImportError:
            raise ImportError(
                "Playwright is not installed. Please run: pip install playwright && playwright install chromium"
            )

    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self._is_initialized = False

    async def _ensure_initialized(self):
        """确保浏览器已初始化"""
        if not self._is_initialized:
            await self.initialize()

    async def navigate(self, url: str) -> BrowserResult:
        """
        导航到URL

        Args:
            url: 目标URL

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            response = await self.page.goto(url, wait_until="domcontentloaded")

            # 等待页面加载
            await self.page.wait_for_load_state("networkidle", timeout=10000)

            content = await self.page.content()
            title = await self.page.title()

            return BrowserResult(
                success=True,
                content=content,
                title=title,
                url=self.page.url
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def click(self, selector: str) -> BrowserResult:
        """
        点击元素

        Args:
            selector: CSS选择器或XPath

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            # 尝试CSS选择器，然后XPath
            try:
                await self.page.click(selector)
            except:
                await self.page.click(f"xpath={selector}")

            return BrowserResult(
                success=True,
                content=f"Clicked: {selector}"
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def fill(self, selector: str, text: str) -> BrowserResult:
        """
        填写表单

        Args:
            selector: 输入框选择器
            text: 要填写的文本

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            # 清空并填写
            await self.page.fill(selector, "")
            await self.page.fill(selector, text)

            return BrowserResult(
                success=True,
                content=f"Filled: {selector} = {text}"
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def press(self, selector: str, key: str) -> BrowserResult:
        """
        按键

        Args:
            selector: 元素选择器
            key: 按键名称 (Enter, Tab, etc.)

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            await self.page.press(selector, key)

            return BrowserResult(
                success=True,
                content=f"Pressed {key} on {selector}"
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def select(self, selector: str, value: str) -> BrowserResult:
        """
        选择下拉选项

        Args:
            selector: 选择器
            value: 选项值

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            await self.page.select_option(selector, value)

            return BrowserResult(
                success=True,
                content=f"Selected {value} in {selector}"
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def get_text(self, selector: str) -> BrowserResult:
        """
        获取元素文本

        Args:
            selector: 元素选择器

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            element = await self.page.query_selector(selector)
            if element:
                text = await element.text_content()
                return BrowserResult(
                    success=True,
                    content=text or ""
                )
            else:
                return BrowserResult(
                    success=False,
                    error=f"Element not found: {selector}"
                )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def get_attribute(self, selector: str, attribute: str) -> BrowserResult:
        """
        获取元素属性

        Args:
            selector: 元素选择器
            attribute: 属性名

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            element = await self.page.query_selector(selector)
            if element:
                value = await element.get_attribute(attribute)
                return BrowserResult(
                    success=True,
                    content=value or ""
                )
            else:
                return BrowserResult(
                    success=False,
                    error=f"Element not found: {selector}"
                )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def screenshot(self, path: str = None) -> BrowserResult:
        """
        截图

        Args:
            path: 保存路径

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            if path:
                await self.page.screenshot(path=path)
                return BrowserResult(
                    success=True,
                    content=f"Screenshot saved to {path}"
                )
            else:
                # 返回base64编码
                screenshot_bytes = await self.page.screenshot()
                import base64
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
                return BrowserResult(
                    success=True,
                    screenshot=screenshot_b64,
                    content="Screenshot captured"
                )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def extract_content(self, selector: str) -> BrowserResult:
        """
        提取页面内容

        Args:
            selector: 要提取的元素选择器

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            elements = await self.page.query_selector_all(selector)

            contents = []
            for elem in elements:
                text = await elem.text_content()
                if text:
                    contents.append(text.strip())

            return BrowserResult(
                success=True,
                content="\n".join(contents)
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> BrowserResult:
        """
        等待元素出现

        Args:
            selector: 元素选择器
            timeout: 超时时间(毫秒)

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            await self.page.wait_for_selector(selector, timeout=timeout)

            return BrowserResult(
                success=True,
                content=f"Element found: {selector}"
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=f"Timeout waiting for {selector}: {str(e)}"
            )

    async def execute_script(self, script: str) -> BrowserResult:
        """
        执行JavaScript

        Args:
            script: JavaScript代码

        Returns:
            BrowserResult
        """
        try:
            await self._ensure_initialized()

            result = await self.page.evaluate(script)

            return BrowserResult(
                success=True,
                content=str(result)
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    async def get_page_info(self) -> Dict[str, Any]:
        """
        获取页面信息

        Returns:
            页面信息字典
        """
        try:
            await self._ensure_initialized()

            return {
                "url": self.page.url,
                "title": await self.page.title(),
                "content": await self.page.content()[:1000],
                "viewport": self.page.viewport_size
            }
        except Exception as e:
            return {"error": str(e)}


# 单例
browser_service = BrowserAutomationService()


async def init_browser(headless: bool = True):
    """初始化浏览器的便捷函数"""
    await browser_service.initialize(headless)


async def close_browser():
    """关闭浏览器"""
    await browser_service.close()


async def browse(url: str) -> Dict[str, Any]:
    """浏览网页的便捷函数"""
    result = await browser_service.navigate(url)
    return {
        "success": result.success,
        "content": result.content,
        "title": result.title,
        "url": result.url,
        "error": result.error
    }