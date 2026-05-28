"""
Memory Directory Management
参考 cc-haha-main/src/memdir/memdir.ts

注意：记忆数据保存路径是 E:\ai\ARG\WOLF2.0\wolf_b2\wolfdata
但代码模块位于 app/memory/
"""

import os
import re
import os
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

from .types import (
    MemoryEntry,
    MemoryTypeEnum,
    ENTRYPOINT_NAME,
    MAX_ENTRYPOINT_LINES,
    MAX_ENTRYPOINT_BYTES,
)


def _get_env_memory_path() -> Optional[str]:
    """从环境变量获取记忆目录路径 (CC 的 CLAUDE_COWORK_MEMORY_PATH_OVERRIDE)"""
    return os.environ.get('WOLF_MEMORY_DIR') or os.environ.get('CLAUDE_COWORK_MEMORY_PATH_OVERRIDE')


def _get_config_memory_path() -> Optional[str]:
    """从 runtime_config.local_storage_path 构建记忆目录路径"""
    try:
        from ..core.runtime_config import runtime_config
        base = runtime_config.local_storage_path
        if base:
            resolved = str(Path(base).resolve() / 'memory')
            return resolved
    except Exception:
        pass
    return None


def _get_project_memory_path() -> str:
    """默认记忆目录: {local_storage_path}/memory"""
    default_base = Path.cwd() / 'wolfdata' / 'memory'
    return str(default_base)


def resolve_memory_dir(requested_dir: Optional[str] = None) -> str:
    """
    多层 fallback 记忆目录解析

    优先级:
    1. 传入的 requested_dir 参数
    2. WOLF_MEMORY_DIR / CLAUDE_COWORK_MEMORY_PATH_OVERRIDE 环境变量
    3. runtime_config.local_storage_path/memory 配置
    4. 默认路径 ./wolfdata/memory
    """
    if requested_dir:
        return requested_dir

    env_path = _get_env_memory_path()
    if env_path:
        return env_path

    config_path = _get_config_memory_path()
    if config_path:
        return config_path

    return _get_project_memory_path()


# 默认记忆数据存储路径
DEFAULT_MEMORY_DIR = resolve_memory_dir()


class MemoryDirectory:
    """
    管理记忆目录的创建、读取、写入
    对应 CC 的 memdir.ts 功能
    """

    def __init__(self, memory_dir: Optional[str] = None):
        # 使用多层 fallback 解析记忆目录
        resolved_dir = resolve_memory_dir(memory_dir)
        self._memory_dir = Path(resolved_dir)
        self._ensure_exists()

    @property
    def path(self) -> str:
        """记忆目录路径"""
        return str(self._memory_dir)

    @property
    def entrypoint_path(self) -> str:
        """MEMORY.md 索引文件路径"""
        return str(self._memory_dir / ENTRYPOINT_NAME)

    def _ensure_exists(self) -> None:
        """确保目录存在"""
        self._memory_dir.mkdir(parents=True, exist_ok=True)

    async def ensure_memory_dir_exists(self) -> None:
        """确保记忆目录存在"""
        self._ensure_exists()

    # 类型到子目录的映射
    TYPE_SUBDIRS = {
        'user': 'user',
        'feedback': 'feedback',
        'project': 'project',
        'reference': 'reference',
    }
    SESSIONS_SUBDIR = 'sessions'

    def _get_type_subdir(self, entry: MemoryEntry) -> str:
        """获取记忆类型对应的子目录路径"""
        return self.TYPE_SUBDIRS.get(entry.memory_type.value, 'reference')

    def _ensure_type_subdirs(self) -> None:
        """确保所有类型子目录和 sessions 目录存在"""
        for subdir in self.TYPE_SUBDIRS.values():
            (self._memory_dir / subdir).mkdir(parents=True, exist_ok=True)
        (self._memory_dir / self.SESSIONS_SUBDIR).mkdir(parents=True, exist_ok=True)

    def write_memory(self, entry: MemoryEntry) -> str:
        """将记忆写入独立文件（按类型分目录），返回文件路径"""
        self._ensure_type_subdirs()
        safe_name = self._sanitize_filename(entry.name)
        subdir = self._get_type_subdir(entry)

        # session 类型记忆放到 sessions/ 目录
        if safe_name.startswith('session_'):
            subdir = self.SESSIONS_SUBDIR

        filename = f"{safe_name}.md"
        rel_path = f"{subdir}/{filename}"
        filepath = self._memory_dir / rel_path

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(entry.to_frontmatter())

        self._update_entrypoint(entry, rel_path)
        return str(filepath)

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名"""
        safe = name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
        safe = ''.join(c for c in safe if c.isalnum() or c in '_-')
        return safe[:50]

    def _update_entrypoint(self, entry: MemoryEntry, rel_path: str) -> None:
        """更新 MEMORY.md 索引"""
        index_line = f"- [{entry.name}]({rel_path}) — {entry.description}"

        existing_lines = []
        if os.path.exists(self.entrypoint_path):
            with open(self.entrypoint_path, 'r', encoding='utf-8') as f:
                existing_lines = f.read().splitlines()

        name_match = f"- [{entry.name}]"
        new_lines = []
        found = False
        for line in existing_lines:
            if line.startswith(name_match):
                new_lines.append(index_line)
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(index_line)

        content = '\n'.join(new_lines)
        truncated = self._truncate_content(content)

        with open(self.entrypoint_path, 'w', encoding='utf-8') as f:
            f.write(truncated)

    def _truncate_content(self, content: str) -> str:
        """截断内容到行数和字节数上限"""
        trimmed = content.strip()
        lines = trimmed.split('\n')
        line_count = len(lines)
        byte_count = len(trimmed.encode('utf-8'))

        was_line_truncated = line_count > MAX_ENTRYPOINT_LINES
        was_byte_truncated = byte_count > MAX_ENTRYPOINT_BYTES

        if not was_line_truncated and not was_byte_truncated:
            return trimmed

        if was_line_truncated:
            truncated_lines = lines[:MAX_ENTRYPOINT_LINES]
        else:
            truncated_lines = lines

        truncated = '\n'.join(truncated_lines)

        truncated_bytes = truncated.encode('utf-8')
        if len(truncated_bytes) > MAX_ENTRYPOINT_BYTES:
            cut_at = MAX_ENTRYPOINT_BYTES
            for i in range(min(cut_at - 1, len(truncated_bytes) - 1), max(0, cut_at - 200), -1):
                if truncated_bytes[i] == ord('\n'):
                    cut_at = i + 1
                    break
            truncated = truncated_bytes[:cut_at].decode('utf-8', errors='ignore')

        return truncated

    def read_entrypoint(self) -> str:
        """读取 MEMORY.md 索引内容"""
        if not os.path.exists(self.entrypoint_path):
            return ''
        with open(self.entrypoint_path, 'r', encoding='utf-8') as f:
            return f.read()

    def read_memory_file(self, filename: str) -> Optional[MemoryEntry]:
        """读取单条记忆文件 (relative path like user/name.md)"""
        filepath = self._memory_dir / filename
        if not filepath.exists():
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        return MemoryEntry.from_frontmatter(content)

    def list_memory_files(self) -> List[Tuple[str, MemoryEntry]]:
        """列出所有记忆文件（递归搜索类型子目录）"""
        results = []
        # 搜索所有子目录中的 .md 文件
        for filepath in self._memory_dir.rglob('*.md'):
            if filepath.name == ENTRYPOINT_NAME:
                continue
            rel_path = str(filepath.relative_to(self._memory_dir))
            entry = MemoryEntry.from_frontmatter(filepath.read_text(encoding='utf-8'))
            if entry:
                results.append((rel_path, entry))
        return results

    def delete_memory(self, filename: str) -> bool:
        """删除记忆文件并更新索引 (filename can be relative path like user/name.md)"""
        filepath = self._memory_dir / filename
        if filepath.exists():
            filepath.unlink()
            self._remove_from_entrypoint(filename)
            # 清理空目录
            parent = filepath.parent
            try:
                if parent != self._memory_dir and not any(parent.iterdir()):
                    parent.rmdir()
            except Exception:
                pass
            return True
        return False

    def _remove_from_entrypoint(self, filename: str) -> None:
        """从索引中移除条目 (filename can be relative path)"""
        if not os.path.exists(self.entrypoint_path):
            return

        with open(self.entrypoint_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

        new_lines = [l for l in lines if not l.endswith(f'({filename})')]

        with open(self.entrypoint_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))


# 全局实例
_memory_directory: Optional[MemoryDirectory] = None


def get_memory_directory(memory_dir: Optional[str] = None) -> MemoryDirectory:
    """获取全局记忆目录实例"""
    global _memory_directory
    if _memory_directory is None:
        _memory_directory = MemoryDirectory(memory_dir or DEFAULT_MEMORY_DIR)
    return _memory_directory


def reset_memory_directory() -> None:
    """重置全局记忆目录实例"""
    global _memory_directory
    _memory_directory = None


def reset_memory_directory_with_config(memory_dir: Optional[str] = None) -> MemoryDirectory:
    """
    根据当前配置重建 MemoryDirectory（配置变更时调用）
    返回新的 MemoryDirectory 实例
    """
    global _memory_directory
    resolved = resolve_memory_dir(memory_dir)
    _memory_directory = MemoryDirectory(resolved)
    # 同步重置搜索和管理服务
    try:
        from .search import reset_memory_search
        reset_memory_search()
    except Exception:
        pass
    try:
        from .management import reset_memory_management
        reset_memory_management()
    except Exception:
        pass
    return _memory_directory