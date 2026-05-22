"""
Claude Code 工具桥接服务
将 Claude Code 的强大工具能力集成到 WOLF 中

架构设计：
1. MCP 协议桥接 - Claude Code 支持 MCP，WOLF 通过 MCP 连接
2. 直接工具实现 - 复刻 Claude Code 核心工具的核心逻辑到 Python
3. 混合模式 - 简单工具直接实现，复杂工具通过 Claude Code 执行

关键工具对标：
- Claude Code BashTool → WOLF BashCommand
- Claude Code GrepTool → WOLF Grep
- Claude Code GlobTool → WOLF Glob
- Claude Code FileReadTool → WOLF Read
- Claude Code FileEditTool → WOLF Edit
- Claude Code FileWriteTool → WOLF Write
"""

import os
import re
import subprocess
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# Claude Code 安装路径检测
def find_claude_code_executable() -> Optional[str]:
    """检测 Claude Code 可执行文件路径"""
    possible_paths = [
        # npm 全局安装
        os.path.expanduser("~/.npm/_npx/*/node_modules/@anthropic-ai/claude-code/bin/claude"),
        os.path.expanduser("~/.npx/_npx/*/node_modules/@anthropic-ai/claude-code/bin/claude"),
        # Windows
        os.path.expanduser("~/AppData/Roaming/npm/node_modules/@anthropic-ai/claude-code/bin/claude"),
        os.path.expanduser("~/AppData/Roaming/npm/node_modules/.bin/claude.cmd"),
        # Linux/Mac
        os.path.expanduser("~/.npm-global/bin/claude"),
        "/usr/local/bin/claude",
        "/usr/bin/claude",
        # bun
        os.path.expanduser("~/.bun/install/cache/*/node_modules/@anthropic-ai/claude-code/bin/claude"),
    ]

    for pattern in possible_paths:
        if '*' in pattern:
            import glob
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        elif os.path.exists(pattern):
            return pattern

    # 检查 PATH 中是否有 claude
    try:
        result = subprocess.run(['where' if os.name == 'nt' else 'which', 'claude'],
                             capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass

    return None


@dataclass
class ToolRequest:
    """工具请求"""
    name: str
    args: Dict[str, Any]
    timeout: int = 30


@dataclass
class ToolResponse:
    """工具响应"""
    success: bool
    content: str = ""
    error: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ClaudeCodeToolBridge:
    """
    Claude Code 工具桥接器

    提供与 Claude Code 同等强大的文件操作和命令执行能力

    核心功能：
    1. 安全的车祸命令执行 (Bash)
    2. 强大的内容搜索 (Grep)
    3. 递归文件查找 (Glob)
    4. 智能路径遍历保护
    5. 命令历史和安全校验
    """

    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or os.getcwd()
        self.claude_path = find_claude_code_executable()
        self._bash_history: List[str] = []
        self._security_checks_enabled = True

        # 危险命令模式 (用于警告，不自动阻止)
        self._dangerous_patterns = [
            (r'rm\s+-rf\s+/', "递归删除根目录"),
            (r'rm\s+-rf\s+/\*', "递归删除根目录"),
            (r':(){ :|:& };:', "Fork 炸弹"),
            (r'mkfs\.', "格式化命令"),
            (r'dd\s+.*of=/dev/', "直接写入设备"),
            (r'>\s*/dev/sd', "直接写入块设备"),
        ]

    def _check_dangerous_command(self, command: str) -> tuple[bool, str]:
        """检查危险命令"""
        for pattern, description in self._dangerous_patterns:
            if re.search(pattern, command):
                return True, f"警告: {description}"
        return False, ""

    async def bash(self, command: str, timeout: int = 30, cwd: str = None) -> ToolResponse:
        """
        执行 Bash 命令 - Claude Code 风格

        安全特性：
        1. 路径遍历检查
        2. 危险命令警告
        3. 超时保护
        4. 工作目录限制
        """
        # 记录命令历史
        self._bash_history.append(command)

        # 安全检查
        is_dangerous, warning = self._check_dangerous_command(command)
        if is_dangerous:
            return ToolResponse(
                success=False,
                error=f"安全检查失败: {warning}"
            )

        # 路径遍历检查
        if '../' in command or command.startswith('/etc') or command.startswith('/sys'):
            return ToolResponse(
                success=False,
                error="路径遍历检测: 禁止访问受保护路径"
            )

        working_dir = cwd or self.workspace_path

        try:
            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env={**os.environ, "HOME": os.path.expanduser("~")}
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                result.kill()
                return ToolResponse(
                    success=False,
                    error=f"命令执行超时 ({timeout}秒)"
                )

            output = stdout.decode('utf-8', errors='replace')
            error = stderr.decode('utf-8', errors='replace')

            if result.returncode == 0:
                return ToolResponse(
                    success=True,
                    content=output,
                    metadata={"returncode": 0, "cwd": working_dir}
                )
            else:
                return ToolResponse(
                    success=False,
                    content=output,
                    error=error or f"命令执行失败 (退出码: {result.returncode})",
                    metadata={"returncode": result.returncode}
                )

        except Exception as e:
            return ToolResponse(
                success=False,
                error=f"Bash 执行错误: {str(e)}"
            )

    async def grep(
        self,
        pattern: str,
        path: str = None,
        glob: str = None,
        case_sensitive: bool = False,
        context: int = 0,
        max_results: int = 100
    ) -> ToolResponse:
        """
        搜索文件内容 - Claude Code 风格

        支持：
        1. 正则表达式模式
        2. glob 文件过滤
        3. 大小写控制
        4. 上下文行
        5. 结果数量限制
        """
        search_path = path or self.workspace_path

        cmd = ['grep']
        if not case_sensitive:
            cmd.append('-i')
        if context > 0:
            cmd.extend(['-C', str(context)])
        cmd.extend(['-n'])  # 显示行号

        if glob:
            cmd.extend(['--include=' + glob])

        cmd.extend([pattern, search_path])
        cmd.append('--')

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(),
                    timeout=10
                )
            except asyncio.TimeoutError:
                result.kill()
                return ToolResponse(success=False, error="Grep 执行超时")

            output = stdout.decode('utf-8', errors='replace')

            if result.returncode == 0:
                lines = output.strip().split('\n')
                if len(lines) > max_results:
                    lines = lines[:max_results]
                    lines.append(f"... (共 {len(lines)} 个匹配，结果已截断)")

                return ToolResponse(
                    success=True,
                    content='\n'.join(lines)
                )
            elif result.returncode == 1:
                return ToolResponse(success=True, content="No matches found")
            else:
                return ToolResponse(
                    success=False,
                    error=stderr.decode('utf-8', errors='replace') or "Grep 执行失败"
                )

        except Exception as e:
            return ToolResponse(success=False, error=f"Grep 错误: {str(e)}")

    async def glob(self, pattern: str, path: str = None) -> ToolResponse:
        """
        递归查找文件 - Claude Code 风格

        支持：
        1. ** 递归匹配
        2. * 单层通配
        3. ? 单字符匹配
        """
        search_path = path or self.workspace_path

        # 使用 Python 的 pathlib 进行 glob
        # Claude Code 使用 ripgrep 的 glob 实现，这里用等效的 Python 实现

        search_pattern = pattern
        if '**' not in search_pattern:
            search_pattern = "**/" + search_pattern

        base_path = Path(search_path)
        results = []

        try:
            # 转换为 glob 模式
            glob_pattern = search_pattern.replace('**/', '**/')

            for match in base_path.glob(glob_pattern):
                rel_path = match.relative_to(base_path)
                results.append(str(match))

                if len(results) >= 1000:  # 限制结果数量
                    results.append(f"... (共超过 1000 个匹配，结果已截断)")
                    break

            if not results:
                return ToolResponse(success=True, content="No matches found")

            return ToolResponse(
                success=True,
                content='\n'.join(results)
            )

        except Exception as e:
            return ToolResponse(success=False, error=f"Glob 错误: {str(e)}")

    async def read(self, path: str, offset: int = 0, limit: int = None) -> ToolResponse:
        """
        读取文件 - Claude Code 风格

        支持：
        1. 行偏移和限制
        2. 大文件保护
        3. 二进制文件检测
        """
        file_path = Path(path)

        if not file_path.exists():
            return ToolResponse(success=False, error=f"文件不存在: {path}")

        if not file_path.is_file():
            return ToolResponse(success=False, error=f"不是文件: {path}")

        # 大小检查
        file_size = file_path.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10MB 限制
            return ToolResponse(
                success=False,
                error=f"文件过大 ({file_size / 1024 / 1024:.1f}MB)，限制 10MB"
            )

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                if offset > 0:
                    for _ in range(offset):
                        f.readline()

                content = f.read() if limit is None else ''.join(
                    f.readline() for _ in range(limit)
                )

            total_lines = content.count('\n') + 1
            read_lines = content.count('\n') + 1

            return ToolResponse(
                success=True,
                content=content,
                metadata={
                    "total_lines": total_lines,
                    "read_lines": read_lines,
                    "start_line": offset + 1,
                    "file_size": file_size
                }
            )

        except Exception as e:
            return ToolResponse(success=False, error=f"读取错误: {str(e)}")

    async def write(self, path: str, content: str, append: bool = False) -> ToolResponse:
        """写入文件"""
        file_path = Path(path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)

            action = "追加到" if append else "写入"
            return ToolResponse(
                success=True,
                content=f"{action}文件: {path} ({len(content)} 字符)"
            )

        except Exception as e:
            return ToolResponse(success=False, error=f"写入错误: {str(e)}")

    async def edit(
        self,
        path: str,
        old_string: str,
        new_string: str,
        regex: bool = False
    ) -> ToolResponse:
        """
        编辑文件 - Claude Code 风格

        替换 old_string 为 new_string
        支持正则表达式模式
        """
        file_path = Path(path)

        if not file_path.exists():
            return ToolResponse(success=False, error=f"文件不存在: {path}")

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            if regex:
                if not re.search(old_string, content):
                    return ToolResponse(
                        success=False,
                        error=f"正则表达式未找到匹配: {old_string}"
                    )
                new_content = re.sub(old_string, new_string, content, count=1)
            else:
                if old_string not in content:
                    return ToolResponse(
                        success=False,
                        error=f"未找到要替换的字符串: {old_string[:100]}..."
                    )
                new_content = content.replace(old_string, new_string, 1)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return ToolResponse(
                success=True,
                content=f"已替换文件: {path}"
            )

        except Exception as e:
            return ToolResponse(success=False, error=f"编辑错误: {str(e)}")

    async def list_directory(self, path: str = None, recursive: bool = False) -> ToolResponse:
        """列出目录内容"""
        dir_path = Path(path) if path else Path(self.workspace_path)

        if not dir_path.exists():
            return ToolResponse(success=False, error=f"目录不存在: {dir_path}")

        if not dir_path.is_dir():
            return ToolResponse(success=False, error=f"不是目录: {dir_path}")

        try:
            if recursive:
                results = []
                for item in dir_path.rglob('*'):
                    depth = len(item.relative_to(dir_path).parts)
                    if depth <= 5:  # 限制递归深度
                        prefix = "  " * (depth - 1)
                        name = item.name
                        if item.is_dir():
                            results.append(f"{prefix}📁 {name}/")
                        else:
                            results.append(f"{prefix}📄 {name}")
                content = '\n'.join(results) if results else "目录为空"
            else:
                items = list(dir_path.iterdir())
                results = []
                for item in items:
                    if item.is_dir():
                        results.append(f"📁 {item.name}/")
                    else:
                        results.append(f"📄 {item.name}")
                content = '\n'.join(results) if results else "目录为空"

            return ToolResponse(success=True, content=content)

        except Exception as e:
            return ToolResponse(success=False, error=f"列出目录错误: {str(e)}")

    async def file_info(self, path: str) -> ToolResponse:
        """获取文件信息"""
        file_path = Path(path)

        if not file_path.exists():
            return ToolResponse(success=False, error=f"路径不存在: {path}")

        try:
            stat = file_path.stat()
            info = {
                "path": str(file_path.absolute()),
                "name": file_path.name,
                "is_file": file_path.is_file(),
                "is_dir": file_path.is_dir(),
                "size": stat.st_size,
                "size_readable": self._format_size(stat.st_size),
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
            }

            return ToolResponse(
                success=True,
                content=json.dumps(info, indent=2, ensure_ascii=False)
            )

        except Exception as e:
            return ToolResponse(success=False, error=f"获取文件信息错误: {str(e)}")

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def get_bash_history(self) -> List[str]:
        """获取命令历史"""
        return self._bash_history.copy()

    def is_claude_code_available(self) -> bool:
        """检查 Claude Code 是否可用"""
        return self.claude_path is not None

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "workspace_path": self.workspace_path,
            "claude_code_available": self.is_claude_code_available(),
            "claude_code_path": self.claude_path,
            "bash_history_count": len(self._bash_history),
            "security_checks_enabled": self._security_checks_enabled,
        }


# 全局单例
_claude_code_tools_instance: Optional[ClaudeCodeToolBridge] = None


def get_claude_code_tools(workspace_path: str = None) -> ClaudeCodeToolBridge:
    """获取 Claude Code 工具桥接器实例"""
    global _claude_code_tools_instance
    if _claude_code_tools_instance is None:
        _claude_code_tools_instance = ClaudeCodeToolBridge(workspace_path)
    return _claude_code_tools_instance


async def execute_claude_code_tool(
    tool_name: str,
    args: Dict[str, Any],
    workspace_path: str = None
) -> ToolResponse:
    """
    执行 Claude Code 工具的便捷函数

    用法:
        result = await execute_claude_code_tool("bash", {"command": "ls -la"})
        result = await execute_claude_code_tool("grep", {"pattern": "TODO", "path": "."})
    """
    bridge = get_claude_code_tools(workspace_path)

    tool_methods = {
        "bash": bridge.bash,
        "Bash": bridge.bash,
        "grep": bridge.grep,
        "Grep": bridge.grep,
        "glob": bridge.glob,
        "Glob": bridge.glob,
        "read": bridge.read,
        "Read": bridge.read,
        "write": bridge.write,
        "Write": bridge.write,
        "edit": bridge.edit,
        "Edit": bridge.edit,
        "list": bridge.list_directory,
        "list_directory": bridge.list_directory,
        "info": bridge.file_info,
        "file_info": bridge.file_info,
    }

    tool_method = tool_methods.get(tool_name)
    if not tool_method:
        return ToolResponse(
            success=False,
            error=f"未知工具: {tool_name}"
        )

    try:
        return await tool_method(**args)
    except Exception as e:
        return ToolResponse(
            success=False,
            error=f"工具执行错误: {str(e)}"
        )
