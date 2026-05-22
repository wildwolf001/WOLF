"""
上下文服务 - 类似于 Claude Code 的 context.ts
提供系统上下文和用户上下文的自动注入
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import lru_cache
import hashlib

class ContextService:
    """上下文服务 - 提供自动上下文注入"""

    def __init__(self, workspace_path: str = None):
        """
        初始化上下文服务

        Args:
            workspace_path: 工作区路径，默认为项目根目录
        """
        self.workspace_path = workspace_path or os.getcwd()
        self._git_status_cache = None
        self._git_status_timestamp = 0
        self._git_status_ttl = 60  # 60秒缓存

    def _get_local_iso_date(self) -> str:
        """获取当前本地日期"""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_git_exe(self) -> str:
        """获取 git 可执行文件路径"""
        return "git"

    async def get_git_status(self) -> Optional[str]:
        """
        获取 git 状态信息 (带缓存，60秒有效期)
        类似于 Claude Code 的 getGitStatus()
        """
        import time
        current_time = time.time()

        # 检查缓存
        if self._git_status_cache and (current_time - self._git_status_timestamp) < self._git_status_ttl:
            return self._git_status_cache

        try:
            is_git = await self._is_git_repo()
            if not is_git:
                return None

            # 并行执行多个 git 命令
            git_cmds = [
                self._get_git_exe(),
                ['--no-optional-locks', 'status', '--short']
            ]
            branch = await self._run_git_command(['branch', '--show-current'])
            main_branch = await self._run_git_command(['branch', '-m', 'main'] or ['branch', '--show-current'])
            status = await self._run_git_command(['status', '--short'])
            log = await self._run_git_command(['log', '--oneline', '-n', '5'])
            user_name = await self._run_git_command(['config', 'user.name'])

            # 截断过长的 status
            max_status_chars = 2000
            truncated_status = status
            truncation_note = ""

            if len(status) > max_status_chars:
                truncated_status = status[:max_status_chars]
                truncation_note = "\n... (truncated because it exceeds 2k characters)"

            git_status = [
                "This is the git status at the start of the conversation.",
                f"Current branch: {branch}" if branch else "Current branch: (unknown)",
                f"Main branch: {main_branch}" if main_branch else "Main branch: (unknown)",
            ]

            if user_name:
                git_status.append(f"Git user: {user_name}")

            git_status.extend([
                f"Status:{truncated_status or '(clean)'}{truncation_note}",
                f"Recent commits:\n{log}" if log else "Recent commits: (none)"
            ])

            result = "\n\n".join(git_status)

            # 更新缓存
            self._git_status_cache = result
            self._git_status_timestamp = current_time

            return result

        except Exception:
            return None

    async def _is_git_repo(self) -> bool:
        """检查当前目录是否是 git 仓库"""
        try:
            result = await self._run_git_command(['rev-parse', '--is-inside-work-tree'])
            return 'true' in result.lower()
        except Exception:
            return False

    async def _run_git_command(self, args: List[str]) -> str:
        """运行 git 命令并返回输出"""
        try:
            result = subprocess.run(
                [self._get_git_exe()] + args,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _find_claude_md_files(self) -> List[Path]:
        """查找 .claude.md 文件"""
        claude_md_files = []
        workspace = Path(self.workspace_path)

        # 向上查找 .claude.md 文件（最多到根目录）
        current = workspace
        while True:
            claude_md = current / ".claude.md"
            if claude_md.exists():
                claude_md_files.append(claude_md)

            # 继续向上一级查找
            parent = current.parent
            if parent == current:  # 已经到达根目录
                break
            current = parent

        # 查找项目根目录下的 .claude.md
        project_root = self._find_project_root()
        if project_root:
            claude_md = project_root / ".claude.md"
            if claude_md.exists() and claude_md not in claude_md_files:
                claude_md_files.insert(0, claude_md)

        return claude_md_files

    def _find_project_root(self) -> Optional[Path]:
        """查找项目根目录"""
        markers = ['.git', '.project', 'package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod']

        current = Path(self.workspace_path)
        while True:
            for marker in markers:
                if (current / marker).exists():
                    return current

            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    async def get_claude_md_content(self) -> Optional[str]:
        """
        获取 .claude.md 文件内容
        类似于 Claude Code 的 getClaudeMds()
        """
        claude_md_files = self._find_claude_md_files()

        if not claude_md_files:
            return None

        contents = []
        for claude_md in claude_md_files:
            try:
                with open(claude_md, 'r', encoding='utf-8') as f:
                    relative_path = claude_md.relative_to(Path(self.workspace_path))
                    contents.append(f"# {relative_path}\n\n{f.read()}")
            except Exception:
                continue

        if not contents:
            return None

        return "\n\n---\n\n".join(contents)

    async def get_system_context(self) -> Dict[str, str]:
        """
        获取系统上下文
        类似于 Claude Code 的 getSystemContext()
        在每次对话开始时自动注入，包含：
        - git 状态信息
        - 缓存破坏标记（如果设置了）
        """
        git_status = await self.get_git_status()

        context = {}
        if git_status:
            context["gitStatus"] = git_status

        return context

    async def get_user_context(self) -> Dict[str, str]:
        """
        获取用户上下文
        类似于 Claude Code 的 getUserContext()
        在每次对话开始时自动注入，包含：
        - .claude.md 文件内容
        - 当前日期
        - 工作目录（如果配置了）
        """
        context = {}

        # 添加当前日期
        context["currentDate"] = f"Today's date is {self._get_local_iso_date()}."

        # 添加 .claude.md 内容
        claude_md_content = await self.get_claude_md_content()
        if claude_md_content:
            context["claudeMd"] = claude_md_content

        # 添加工作目录信息
        work_directory = self._get_work_directory()
        if work_directory:
            context["workDirectory"] = work_directory

        return context

    def _get_work_directory(self) -> Optional[str]:
        """获取配置的工作目录"""
        try:
            from app.core.runtime_config import runtime_config
            work_dirs = runtime_config.get_additional_working_directories()
            if work_dirs:
                # 返回第一个目录
                return list(work_dirs.keys())[0]
        except Exception:
            pass
        return None

    async def get_full_context(self) -> Dict[str, str]:
        """
        获取完整上下文（系统上下文 + 用户上下文）
        用于在发送请求给 LLM 之前自动注入
        """
        system_context = await self.get_system_context()
        user_context = await self.get_user_context()

        return {**system_context, **user_context}

    def format_context_for_llm(self, context: Dict[str, str]) -> str:
        """
        将上下文格式化为字符串，用于注入到 LLM prompt
        """
        if not context:
            return ""

        formatted_parts = []

        for key, value in context.items():
            if key == "gitStatus":
                formatted_parts.append(f"## Git Status\n\n{value}")
            elif key == "claudeMd":
                formatted_parts.append(f"## Project Instructions (.claude.md)\n\n{value}")
            elif key == "currentDate":
                formatted_parts.append(f"## Current Date\n\n{value}")
            elif key == "cacheBreaker":
                formatted_parts.append(f"## Cache Breaker\n\n{value}")
            elif key == "workDirectory":
                formatted_parts.append(f"## Work Directory\n\nYou have access to the following directory for file operations:\n- **Work Directory**: {value}\n\nYou can use tools like Read, Write, Edit, Grep, Glob, and list to access files in this directory.\n\nWhen the user asks you to read, summarize, or analyze files, search in this directory first.")
            else:
                formatted_parts.append(f"## {key}\n\n{value}")

        return "\n\n".join(formatted_parts)


# 全局上下文服务实例
context_service = ContextService()


# 便捷函数
async def get_system_context() -> Dict[str, str]:
    """获取系统上下文"""
    return await context_service.get_system_context()

async def get_user_context() -> Dict[str, str]:
    """获取用户上下文"""
    return await context_service.get_user_context()

async def get_full_context() -> Dict[str, str]:
    """获取完整上下文"""
    return await context_service.get_full_context()

def format_context_for_llm(context: Dict[str, str]) -> str:
    """将上下文格式化为 LLM 可用的字符串"""
    return context_service.format_context_for_llm(context)
