"""
Memory Service - 记忆系统

参考 cc-haha 的 .claude/memory/ 结构实现

记忆类型:
- user: 用户信息 (角色、偏好、职责)
- feedback: 反馈记录 (用户的纠正和确认)
- project: 项目信息 (目标、进展、决策)
- reference: 参考信息 (外部系统入口)

记忆结构:
.claude/memory/
├── MEMORY.md        # 索引文件
├── user/
│   └── *.md        # 用户记忆
├── feedback/
│   └── *.md        # 反馈记忆
├── project/
│   └── *.md        # 项目记忆
└── reference/
    └── *.md        # 参考记忆

参考 cc-haha 的 memoryTypes.ts 实现
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


MEMORY_TYPES = ['user', 'feedback', 'project', 'reference']


class MemoryService:
    """记忆服务 - 完整实现 cc-haha 风格的记忆系统"""

    def __init__(self, memory_base_path: str = None):
        """
        初始化记忆服务

        Args:
            memory_base_path: 记忆目录，默认为 .claude/memory/
        """
        self.memory_base_path = memory_base_path or self._get_default_memory_path()
        self._ensure_memory_dirs()

    def _get_default_memory_path(self) -> str:
        """获取默认记忆目录"""
        # 优先使用 runtime_config 的 work_directory
        try:
            from app.core.runtime_config import runtime_config
            work_dirs = runtime_config.get_additional_working_directories()
            if work_dirs:
                # 使用第一个工作目录
                work_dir = list(work_dirs.keys())[0]
                return os.path.join(work_dir, ".claude", "memory")
        except Exception:
            pass

        # 回退到当前目录
        return os.path.join(os.getcwd(), ".claude", "memory")

    def _ensure_memory_dirs(self) -> None:
        """确保记忆目录结构存在"""
        dirs = MEMORY_TYPES
        for d in dirs:
            path = os.path.join(self.memory_base_path, d)
            os.makedirs(path, exist_ok=True)

        # 确保 MEMORY.md 存在
        index_path = os.path.join(self.memory_base_path, "MEMORY.md")
        if not os.path.exists(index_path):
            self._init_index_file()

    def _init_index_file(self) -> None:
        """初始化索引文件"""
        index_path = os.path.join(self.memory_base_path, "MEMORY.md")
        content = """# Memory Index

<!-- 每行格式: - [Title](file.md) — one-line hook -->

"""
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            pass

    def save_memory(
        self,
        name: str,
        content: str,
        memory_type: str = "user",
        description: str = ""
    ) -> bool:
        """
        保存记忆

        Args:
            name: 记忆名称（不含.md后缀）
            content: 记忆内容
            memory_type: 记忆类型 (user/feedback/project/reference)
            description: 简短描述

        Returns:
            是否保存成功
        """
        if memory_type not in MEMORY_TYPES:
            memory_type = "user"

        # 构建文件路径
        file_path = os.path.join(self.memory_base_path, memory_type, f"{name}.md")

        # 添加 frontmatter
        frontmatter = f"""---
name: {name}
description: {description}
type: {memory_type}
---

{content}
"""

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter)

            # 更新索引
            self._update_index(name, memory_type, description)

            return True
        except Exception as e:
            print(f"Error saving memory: {e}")
            return False

    def _update_index(self, name: str, memory_type: str, description: str) -> None:
        """更新 MEMORY.md 索引"""
        index_path = os.path.join(self.memory_base_path, "MEMORY.md")

        # 读取现有索引
        existing_lines = []
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()

        # 检查是否已存在
        entry = f"- [{name}]({memory_type}/{name}.md) — {description}"
        entry_exists = any(entry.split("—")[0].strip() in line for line in existing_lines)

        if not entry_exists:
            # 找到适当位置插入（在 <!-- --> 注释之后）
            insert_idx = 0
            for i, line in enumerate(existing_lines):
                if line.startswith("<!--"):
                    insert_idx = i + 1
                elif line.startswith("- [") and insert_idx > 0:
                    # 找到第一个条目，在它之前插入
                    break
                elif line.strip() and not line.startswith("#"):
                    insert_idx = i + 1

            existing_lines.insert(insert_idx, entry + "\n")

            # 写回
            with open(index_path, 'w', encoding='utf-8') as f:
                f.writelines(existing_lines)

    def load_memory(self, memory_type: str = None) -> List[Dict[str, Any]]:
        """
        加载记忆

        Args:
            memory_type: 可选，加载特定类型的记忆

        Returns:
            记忆列表
        """
        memories = []

        types_to_load = [memory_type] if memory_type else MEMORY_TYPES

        for mt in types_to_load:
            if mt not in MEMORY_TYPES:
                continue
            dir_path = os.path.join(self.memory_base_path, mt)
            if not os.path.exists(dir_path):
                continue

            for filename in os.listdir(dir_path):
                if filename.endswith(".md"):
                    file_path = os.path.join(dir_path, filename)
                    try:
                        memory = self._read_memory_file(file_path, mt)
                        if memory:
                            memories.append(memory)
                    except Exception:
                        pass

        return memories

    def _read_memory_file(self, file_path: str, default_type: str = "user") -> Optional[Dict[str, Any]]:
        """读取单个记忆文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2].strip()

                # 简单解析 frontmatter
                meta = {}
                for line in frontmatter.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        meta[key.strip()] = value.strip()

                name = os.path.basename(file_path)[:-3]  # 移除 .md

                return {
                    "name": meta.get("name", name),
                    "type": meta.get("type", default_type),
                    "description": meta.get("description", ""),
                    "content": body,
                    "file_path": file_path
                }

        return None

    def find_relevant_memories(self, query: str, memory_type: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        查找与查询相关的记忆

        Args:
            query: 查询文本
            memory_type: 可选，限定记忆类型
            limit: 返回数量限制

        Returns:
            相关记忆列表
        """
        all_memories = self.load_memory(memory_type)

        if not all_memories:
            return []

        query_lower = query.lower()

        # 计算相关性分数
        scored_memories = []
        for mem in all_memories:
            score = 0
            mem_name = mem.get("name", "").lower()
            mem_desc = mem.get("description", "").lower()
            mem_content = mem.get("content", "").lower()

            # 名称匹配
            if query_lower in mem_name:
                score += 10
            # 描述匹配
            if query_lower in mem_desc:
                score += 5
            # 内容匹配
            if query_lower in mem_content:
                score += 1

            # 关键词匹配
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 2:
                    if word in mem_name:
                        score += 3
                    if word in mem_desc:
                        score += 2
                    if word in mem_content:
                        score += 0.5

            if score > 0:
                scored_memories.append((score, mem))

        # 排序并返回
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored_memories[:limit]]

    def delete_memory(self, name: str, memory_type: str = "user") -> bool:
        """
        删除记忆

        Args:
            name: 记忆名称
            memory_type: 记忆类型

        Returns:
            是否删除成功
        """
        file_path = os.path.join(self.memory_base_path, memory_type, f"{name}.md")
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                # 从索引中移除
                self._remove_from_index(name, memory_type)
                return True
        except Exception:
            pass
        return False

    def _remove_from_index(self, name: str, memory_type: str) -> None:
        """从索引中移除记忆"""
        index_path = os.path.join(self.memory_base_path, "MEMORY.md")
        if not os.path.exists(index_path):
            return

        with open(index_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 移除相关行
        new_lines = []
        for line in lines:
            if not line.startswith(f"- [{name}]"):
                new_lines.append(line)

        with open(index_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    def build_memory_prompt(self) -> str:
        """
        构建记忆提示词（参考 cc-haha 的 memdir.ts 设计）

        Returns:
            记忆相关的内容字符串
        """
        memories = self.load_memory()

        if not memories:
            lines = [
                "# Memory system",
                "",
                f"You have a persistent, file-based memory system at `{self.memory_base_path}`. This directory already exists — write to it directly with the Write tool (do not run mkdir or check for its existence).",
                "",
                "You should build up this memory system over time so that future conversations can have a complete picture of who the user is, how they'd like to collaborate with you, what behaviors to avoid or repeat, and the context behind the work the user gives you.",
                "",
                "If the user explicitly asks you to remember something, save it immediately as whichever type fits best. If they ask you to forget something, find and remove the relevant entry.",
                "",
                "## Memory types",
                "- **user**: Information about the user's role, preferences, responsibilities",
                "- **project**: Project context, deadlines, decisions and rationale",
                "- **feedback**: Guidance the user has given about how to approach work",
                "- **reference**: Pointers to external systems (dashboards, projects, Slack channels)",
                "",
                "## What NOT to save in memory",
                "- Code patterns, conventions, architecture - derivable from code",
                "- Git history, recent changes - available via git log",
                "- Debugging solutions - the fix is in the code",
                "- Anything documented in CLAUDE.md files",
                "- Ephemeral task details - use tasks instead",
                "",
                "## How to save memories (two-step process)",
                "",
                "**Step 1** — write the memory to its own file using frontmatter format:",
                "",
                "```markdown",
                "---",
                "name: memory_name",
                f"description: one-line description (used to decide relevance, ~150 chars)",
                "type: user  # user | project | feedback | reference",
                "---",
                "",
                "Memory content here...",
                "```",
                "",
                "**Step 2** — add a pointer to MEMORY.md:",
                "`- [Title](file.md) — one-line hook`",
                "",
                f"MEMORY.md is the index. Keep entries under ~150 characters. Memory files go in:",
                f"`{self.memory_base_path}/user/`, `{self.memory_base_path}/project/`, `{self.memory_base_path}/feedback/`, `{self.memory_base_path}/reference/`",
                "",
                "## When to access memory",
                "- When user references prior conversation",
                "- When user asks to recall something",
                "- When starting a new session",
            ]
            return "\n".join(lines)

        sections = [
            "# Memory system",
            "",
            f"You have a persistent, file-based memory system at `{self.memory_base_path}`. This directory already exists — write to it directly with the Write tool.",
            "",
            "## How to save memories (two-step process)",
            "",
            "**Step 1** — write the memory to its own file using frontmatter format:",
            "",
            "```markdown",
            "---",
            "name: memory_name",
            "description: one-line description (~150 chars)",
            "type: user  # user | project | feedback | reference",
            "---",
            "",
            "Memory content here...",
            "```",
            "",
            "**Step 2** — add a pointer to MEMORY.md:",
            "`- [Title](file.md) — one-line hook`",
            "",
            "## Relevant memories",
        ]

        # 按类型分组
        by_type: Dict[str, List] = {}
        for m in memories:
            mt = m.get("type", "user")
            if mt not in by_type:
                by_type[mt] = []
            by_type[mt].append(m)

        for mt, mems in by_type.items():
            sections.append(f"\n### {mt.upper()}\n")
            for mem in mems:
                # 截断过长的内容
                content = mem['content']
                if len(content) > 300:
                    content = content[:300] + "..."
                sections.append(f"**{mem['name']}**: {content}\n")

        return "\n".join(sections)

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        stats = {
            "total": 0,
            "by_type": {},
            "memory_base_path": self.memory_base_path
        }

        for mt in MEMORY_TYPES:
            memories = self.load_memory(mt)
            count = len(memories)
            stats["by_type"][mt] = count
            stats["total"] += count

        return stats


# =============================================================================
# 参考 cc-haha 的 memoryTypes.ts 定义的记忆类型语义
# =============================================================================

MEMORY_TYPE_DESCRIPTIONS = {
    "user": """Contain information about the user's role, goals, responsibilities, and knowledge.
Great user memories help you tailor your future behavior to the user's preferences and perspective.
Your goal in reading and writing these memories is to build up an understanding of who the user is
and how you can be most helpful to them specifically.""",

    "feedback": """Guidance the user has given you about how to approach work — both what to avoid
and what to keep doing. These are a very important type of memory to read and write as they
allow you to remain coherent and responsive to the way you should approach work in the project.
Record from failure AND success: if you only save corrections, you will avoid past mistakes but
drift away from approaches the user has already validated.""",

    "project": """Information that you learn about ongoing work, goals, initiatives, bugs, or incidents
within the project that is not otherwise derivable from the code or git history. Project memories
help you understand the broader context and motivation behind the work users are working on.""",

    "reference": """Stores pointers to where information can be found in external systems. These memories
allow you to remember where to look to find up-to-date information outside of the project directory."""
}


# 全局实例 - 在使用时创建，不使用全局单例
# 使用方式: memory_service = MemoryService(memory_base_path="/path/to/.claude/memory")
