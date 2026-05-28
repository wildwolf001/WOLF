"""
四层 Prompt 架构 — 对标 CC sections 设计
RoleLayer(角色) / RulesLayer(规则) / ContextLayer(上下文) / OutputLayer(输出)
"""
from dataclasses import dataclass, field
from typing import Callable, Optional, List
from .core.schemas import LayerType, CacheScope
from .cache import get_section_cache


@dataclass
class PromptLayer:
    """一个 Prompt 层"""
    name: str
    layer_type: LayerType
    compute: Callable[[], str]
    cache_scope: CacheScope = CacheScope.SESSION
    condition: Optional[Callable[[], bool]] = None  # 条件化注入


class PromptAssembler:
    """根据 Agent 当前能力动态组装 Prompt (对标 CC getSessionSpecificGuidanceSection)"""

    def __init__(self):
        self._layers: List[PromptLayer] = []
        self._cache = get_section_cache()

    def add_layer(self, layer: PromptLayer):
        self._layers.append(layer)

    def assemble(self) -> str:
        """组装最终 System Prompt：只注入满足条件的层"""
        sections = []
        for layer in self._layers:
            # 条件检查
            if layer.condition and not layer.condition():
                continue
            # 缓存检查
            value = self._cache.get_or_compute(
                name=f"layer:{layer.name}",
                compute_fn=layer.compute,
                scope=layer.cache_scope
            )
            if value:
                sections.append(value)
        return "\n\n".join(sections)

    def assemble_structured(self) -> dict:
        """结构化组装：返回 {layer_type: content} 字典"""
        result = {}
        for layer in self._layers:
            if layer.condition and not layer.condition():
                continue
            value = self._cache.get_or_compute(
                name=f"layer:{layer.name}",
                compute_fn=layer.compute,
                scope=layer.cache_scope
            )
            if value:
                result[layer.layer_type.value] = value
        return result
