"""
Long-term Memory 服务

参考 cc-haha 的 CLAUDE.md 和三级记忆理论：
1. 瞬时记忆 (Working Memory) - 当前对话
2. 工作记忆 (Session Memory) - 当前任务
3. 长期记忆 (Long-term Memory) - 跨会话知识

长期记忆目录结构：
.wolf/memory/
├── user/        # 用户偏好
├── project/     # 项目知识
├── feedback/    # 反馈经验
├── reference/   # 参考信息

每个记忆包含：
- name: 名称
- description: 描述
- type: 类型 (user/feedback/project/reference)
- content: 内容
- why: 为什么重要
- how_to_apply: 如何应用
- created_at: 创建时间
- last_accessed: 最后访问时间
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import asyncio
import re


# 记忆类型常量
MEMORY_TYPE_USER = "user"
MEMORY_TYPE_PROJECT = "project"
MEMORY_TYPE_FEEDBACK = "feedback"
MEMORY_TYPE_REFERENCE = "reference"

MEMORY_TYPES = [MEMORY_TYPE_USER, MEMORY_TYPE_PROJECT, MEMORY_TYPE_FEEDBACK, MEMORY_TYPE_REFERENCE]


@dataclass
class MemoryEntry:
    """记忆条目"""
    name: str
    description: str
    type: str  # user, feedback, project, reference
    content: str
    why: str = ""  # 为什么重要
    how_to_apply: str = ""  # 如何应用
    created_at: str = ""
    last_accessed: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "content": self.content,
            "why": self.why,
            "how_to_apply": self.how_to_apply,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            type=data.get("type", MEMORY_TYPE_REFERENCE),
            content=data.get("content", ""),
            why=data.get("why", ""),
            how_to_apply=data.get("how_to_apply", ""),
            created_at=data.get("created_at", ""),
            last_accessed=data.get("last_accessed", "")
        )

    def update_access_time(self):
        """更新访问时间"""
        self.last_accessed = datetime.now().isoformat()

    def matches_query(self, query: str) -> bool:
        """检查记忆是否与查询相关（简单关键词匹配）"""
        query_lower = query.lower()
        searchable = f"{self.name} {self.description} {self.content} {self.why}".lower()
        return query_lower in searchable


class LongTermMemoryService:
    """
    长期记忆服务

    功能：
    1. 添加记忆
    2. 查找相关记忆（关键词+语义）
    3. 生成记忆上下文提示
    4. 自动清理过期记忆
    """

    def __init__(self, memory_base_path: str = "./.wolf/memory"):
        self.base_path = memory_base_path
        self._type_dirs = {
            MEMORY_TYPE_USER: os.path.join(memory_base_path, MEMORY_TYPE_USER),
            MEMORY_TYPE_PROJECT: os.path.join(memory_base_path, MEMORY_TYPE_PROJECT),
            MEMORY_TYPE_FEEDBACK: os.path.join(memory_base_path, MEMORY_TYPE_FEEDBACK),
            MEMORY_TYPE_REFERENCE: os.path.join(memory_base_path, MEMORY_TYPE_REFERENCE),
        }

        # 确保目录存在
        for path in self._type_dirs.values():
            os.makedirs(path, exist_ok=True)

    def _get_memory_file_path(self, memory_type: str, name: str) -> str:
        """获取记忆文件路径"""
        safe_name = re.sub(r'[^\w\s-]', '', name)[:50]  # 清理文件名
        return os.path.join(self._type_dirs.get(memory_type, self.base_path), f"{safe_name}.json")

    async def add_memory(
        self,
        name: str,
        description: str,
        memory_type: str,
        content: str,
        why: str = "",
        how_to_apply: str = ""
    ) -> bool:
        """
        添加记忆

        Args:
            name: 记忆名称
            description: 描述
            memory_type: 类型 (user/feedback/project/reference)
            content: 内容
            why: 为什么重要
            how_to_apply: 如何应用

        Returns:
            成功返回 True
        """
        if memory_type not in MEMORY_TYPES:
            memory_type = MEMORY_TYPE_REFERENCE

        memory = MemoryEntry(
            name=name[:50],
            description=description[:100],
            type=memory_type,
            content=content,
            why=why[:200] if why else "",
            how_to_apply=how_to_apply[:200] if how_to_apply else ""
        )

        file_path = self._get_memory_file_path(memory_type, name)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save memory: {e}")
            return False

    async def find_relevant(self, query: str, memory_types: List[str] = None, limit: int = 5) -> List[MemoryEntry]:
        """
        查找与查询相关的记忆

        Args:
            query: 查询字符串
            memory_types: 要搜索的类型列表，None表示所有类型
            limit: 返回数量限制

        Returns:
            相关记忆列表
        """
        if memory_types is None:
            memory_types = MEMORY_TYPES

        results = []

        for memory_type in memory_types:
            dir_path = self._type_dirs.get(memory_type)
            if not dir_path or not os.path.exists(dir_path):
                continue

            try:
                for filename in os.listdir(dir_path):
                    if not filename.endswith('.json'):
                        continue

                    file_path = os.path.join(dir_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        memory = MemoryEntry.from_dict(data)

                        if memory.matches_query(query):
                            memory.update_access_time()
                            results.append(memory)
                    except (json.JSONDecodeError, KeyError):
                        continue
            except Exception:
                continue

        # 按相关性排序（关键词匹配数量）
        def relevance_score(m: MemoryEntry) -> int:
            query_lower = query.lower()
            return sum([
                1 if query_lower in m.name.lower() else 0,
                1 if query_lower in m.description.lower() else 0,
                1 if query_lower in m.content.lower() else 0,
            ])

        results.sort(key=relevance_score, reverse=True)
        return results[:limit]

    async def get_context_prompt(self, query: str, memory_types: List[str] = None) -> str:
        """
        生成记忆上下文提示

        Args:
            query: 当前查询
            memory_types: 要包含的类型

        Returns:
            格式化的记忆上下文字符串
        """
        memories = await self.find_relevant(query, memory_types, limit=5)

        if not memories:
            return ""

        parts = ["[Relevant memories from long-term storage]\n"]
        for mem in memories:
            parts.append(f"## {mem.name} ({mem.type})")
            parts.append(f"Content: {mem.content[:500]}")
            if mem.how_to_apply:
                parts.append(f"Apply to: {mem.how_to_apply}")
            parts.append("")

        return "\n".join(parts)

    async def list_memories(self, memory_type: str = None, limit: int = 100) -> List[MemoryEntry]:
        """列出记忆"""
        if memory_type:
            types_to_search = [memory_type]
        else:
            types_to_search = MEMORY_TYPES

        results = []

        for mt in types_to_search:
            dir_path = self._type_dirs.get(mt)
            if not dir_path or not os.path.exists(dir_path):
                continue

            try:
                for filename in os.listdir(dir_path)[:limit]:
                    if not filename.endswith('.json'):
                        continue
                    file_path = os.path.join(dir_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    results.append(MemoryEntry.from_dict(data))
            except Exception:
                continue

        return results

    async def delete_memory(self, name: str, memory_type: str) -> bool:
        """删除记忆"""
        file_path = self._get_memory_file_path(memory_type, name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception:
                pass
        return False

    async def save_memory(self, name: str, content: str, memory_type: str = MEMORY_TYPE_REFERENCE) -> bool:
        """保存记忆（简化接口）"""
        return await self.add_memory(
            name=name,
            description="",
            memory_type=memory_type,
            content=content
        )

    def get_memory_prompt(self) -> str:
        """
        生成记忆提示（用于 system prompt）

        这会在 system prompt 中包含相关记忆
        """
        # 延迟加载，从当前工作目录获取
        return ""  # 默认返回空，在 MainAgent 中动态构建

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {}
        for memory_type, dir_path in self._type_dirs.items():
            if os.path.exists(dir_path):
                count = len([f for f in os.listdir(dir_path) if f.endswith('.json')])
                stats[memory_type] = count
            else:
                stats[memory_type] = 0
        return stats


# 便捷函数
def save_user_memory(name: str, content: str, description: str = "", why: str = "", how_to_apply: str = "") -> bool:
    """保存用户偏好记忆"""
    service = LongTermMemoryService()
    return asyncio.run(service.add_memory(name, description, MEMORY_TYPE_USER, content, why, how_to_apply))


def save_feedback_memory(name: str, content: str, description: str = "", why: str = "", how_to_apply: str = "") -> bool:
    """保存反馈记忆"""
    service = LongTermMemoryService()
    return asyncio.run(service.add_memory(name, description, MEMORY_TYPE_FEEDBACK, content, why, how_to_apply))


def save_project_memory(name: str, content: str, description: str = "", why: str = "", how_to_apply: str = "") -> bool:
    """保存项目记忆"""
    service = LongTermMemoryService()
    return asyncio.run(service.add_memory(name, description, MEMORY_TYPE_PROJECT, content, why, how_to_apply))


# 全局实例
_long_term_memory_instances: Dict[str, LongTermMemoryService] = {}


def get_long_term_memory(memory_base_path: str = "./.wolf/memory") -> LongTermMemoryService:
    """获取长期记忆服务实例"""
    if memory_base_path not in _long_term_memory_instances:
        _long_term_memory_instances[memory_base_path] = LongTermMemoryService(memory_base_path)
    return _long_term_memory_instances[memory_base_path]