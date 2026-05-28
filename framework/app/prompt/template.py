"""
Jinja2 模板引擎 — 替代裸字符串拼接
"""
from typing import Dict, Any, Optional
import re


class PromptTemplateEngine:
    """轻量模板引擎 (优先 Jinja2，降级到 Python 正则)"""

    def __init__(self, use_jinja2: bool = True):
        self._jinja2_env = None
        if use_jinja2:
            try:
                from jinja2 import Environment, BaseLoader
                self._jinja2_env = Environment(loader=BaseLoader())
            except ImportError:
                pass

    def render(self, template: str, variables: Dict[str, Any] = None) -> str:
        """渲染模板"""
        variables = variables or {}
        if self._jinja2_env:
            tpl = self._jinja2_env.from_string(template)
            return tpl.render(**variables)
        else:
            return self._simple_render(template, variables)

    def _simple_render(self, template: str, variables: Dict[str, Any]) -> str:
        """Python 原生模板替换 (降级方案)"""
        result = template
        for key, value in variables.items():
            placeholder = "{{ " + key + " }}"
            result = result.replace(placeholder, str(value))
        return result

    def render_file(self, filepath: str, variables: Dict[str, Any] = None) -> str:
        """从文件加载模板并渲染"""
        with open(filepath, "r", encoding="utf-8") as f:
            template = f.read()
        return self.render(template, variables)


_engine: Optional[PromptTemplateEngine] = None


def get_template_engine() -> PromptTemplateEngine:
    global _engine
    if _engine is None:
        _engine = PromptTemplateEngine()
    return _engine
