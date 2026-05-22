"""
MainAgent - 单Agent直接执行模式

参考 Claude Code 架构：
1. 接收用户请求，直接执行
2. 调用 LLM 处理
3. 使用工具完成工作
4. 返回结果

不再使用协作讨论模式。
"""
from typing import Dict, Any, List, Optional, Tuple
from app.agents.base import BaseAgent, AgentStatus
from app.services.llm_service import llm_service
from app.agents.system_prompt import system_prompt_cache, register_system_section
from app.agents.working_memory import WorkingMemory
from app.agents.session_memory import get_session_memory, SessionMemoryService
from app.types.message import (
    Message, UserMessage, AssistantMessage, SystemMessage,
    TextBlock, ToolResultBlock, parse_history_item, format_message_for_api
)
from app.services.message_service import (
    normalize_messages_for_api, convert_history_list_to_messages, format_messages_for_llm
)
from app.services.permission_context import ToolPermissionContext, PermissionMode, get_empty_permission_context
import asyncio
import os
import re
import json
import subprocess
from datetime import datetime
from dataclasses import dataclass, field


class ExplorationTracker:
    """
    追踪探索进度，防止循环 - 参考 cc-haha 的设计

    不是意图检测，只是操作追踪
    """

    def __init__(self):
        self.operations: List[Tuple[str, str]] = []  # (tool_name, path)
        self.errors: List[str] = []
        self.loop_threshold = 2  # 同一操作超过2次认为循环

    def record(self, tool_name: str, path: str = "", error: str = ""):
        """记录操作或错误"""
        if error:
            self.errors.append(error)
            return

        if path:
            self.operations.append((tool_name, path))

    def is_loop(self) -> bool:
        """检测是否循环 - 连续2次相同操作"""
        if len(self.operations) < 2:
            return False
        last_two = self.operations[-2:]
        return last_two[0] == last_two[1]  # (tool, path) 完全相同

    def should_retry(self, tool_name: str, path: str) -> bool:
        """检查是否应该重试"""
        recent_same = [op for op in self.operations[-5:]
                      if op[0] == tool_name and op[1] == path]
        return len(recent_same) <= self.loop_threshold

    def get_repeated_operation(self) -> Optional[Tuple[str, str]]:
        """获取重复的操作"""
        if len(self.operations) < 2:
            return None
        if self.operations[-1] == self.operations[-2]:
            return self.operations[-1]
        return None

    def has_permission_error(self) -> bool:
        """检查是否有权限错误"""
        return any("outside allowed" in e.lower() or "permission" in e.lower()
                  for e in self.errors)

    def clear(self):
        """清空"""
        self.operations.clear()
        self.errors.clear()


class MainAgent(BaseAgent):
    """
    MainAgent - 单Agent直接执行

    直接接收用户请求，调用 LLM + 工具完成工作。
    不再使用"主持人+协作讨论"模式。
    """

    def __init__(self, work_directory: str = None):
        """
        初始化 MainAgent

        Args:
            work_directory: 工作目录，默认为配置的 work_directory 或 cwd
        """
        # 获取工作目录（保持向后兼容）
        self.work_directory = self._resolve_work_directory(work_directory)

        # 初始化BaseAgent属性(跳过父类__init__)
        self.agent_id = "main-001"
        self.role = "main"
        self.name = "WOLF AI"
        self.capabilities = ["coordination", "orchestration", "synthesis", "analysis", "execution"]
        from app.agents.base import AgentStatus
        self.status = AgentStatus.IDLE
        self.current_task: Optional[str] = None
        self.message_history: List[Any] = []

        # 初始化 System Prompt 缓存
        self._init_system_prompt_cache()

        # 工作内存 - 管理当前对话上下文
        self.working_memory = WorkingMemory(session_id="main")

        # Session Memory - 当前任务记忆
        self.session_memory = get_session_memory(session_id="main")

        # 工具服务实例
        from app.services.tools_service import ToolsService
        self.tools_service = ToolsService(workspace_path=self.work_directory)

        # 长期记忆服务 - 管理跨会话知识
        from app.services.memory_service import MemoryService
        self.memory_service = MemoryService(memory_base_path=self._get_memory_path())

        # 消息历史（用于多轮对话）
        self.message_history = []

        # 工具使用历史
        self.tool_usage_history = []

        # 探索历史记录（用于追踪探索行为）
        self.exploration_history = []

        # 探索追踪器 - 防止循环
        self.exploration_tracker = ExplorationTracker()

        # 权限上下文 - 参照 cc 的 ToolPermissionContext
        self._permission_context = self._setup_permission_context()

        # 同步工作目录到 runtime_config
        self._sync_working_directories()

    def _sync_working_directories(self):
        """同步工作目录到 runtime_config - 参照 cc 的设计"""
        try:
            from app.core.runtime_config import runtime_config
            # 如果 work_directory 存在且不在 runtime_config 中，添加它
            if self.work_directory:
                abs_path = os.path.abspath(self.work_directory)
                if abs_path not in runtime_config.additional_working_directories:
                    runtime_config.add_working_directory(abs_path, "mainAgent")
        except Exception:
            pass

    def add_working_directory(self, path: str, source: str = "mainAgent") -> bool:
        """添加工作目录 - 参照 cc 的 addDirectories"""
        if not path:
            return False

        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return False

        try:
            from app.core.runtime_config import runtime_config
            runtime_config.add_working_directory(abs_path, source)

            # 同步到 permission_service
            from app.services.permission_service import permission_service
            permission_service.add_working_directory(abs_path, source)

            return True
        except Exception:
            return False

    def remove_working_directory(self, path: str) -> bool:
        """移除工作目录"""
        if not path:
            return False

        abs_path = os.path.abspath(path)
        try:
            from app.core.runtime_config import runtime_config
            return runtime_config.remove_working_directory(abs_path)
        except Exception:
            return False

    def get_working_directories(self) -> List[str]:
        """获取所有工作目录"""
        try:
            from app.core.runtime_config import runtime_config
            return runtime_config.get_additional_working_directories()
        except Exception:
            return []

    def _setup_permission_context(self) -> ToolPermissionContext:
        """设置权限上下文 - 参照 cc 的权限系统"""
        context = get_empty_permission_context()

        # 设置权限模式
        try:
            from app.services.permission_service import interactive_permission_service
            mode = interactive_permission_service.get_mode()
            if hasattr(mode, 'value'):
                context.mode = PermissionMode(mode.value)
            else:
                context.mode = PermissionMode(str(mode))
        except Exception:
            context.mode = PermissionMode.DEFAULT

        # 添加工作目录
        if self.work_directory:
            context.add_working_directory(self.work_directory, "mainAgent")

        # 添加原始 CWD
        try:
            from app.services.permission_service import permission_service
            original_cwd = permission_service.get_original_cwd()
            if original_cwd:
                context.add_working_directory(original_cwd, "originalCwd")
        except Exception:
            pass

        return context

    def _is_topic_change(self, current_msg: str, history_list: list) -> bool:
        """
        检测是否话题发生显著变化

        当用户发送一个方向完全不同的请求时，认为是新任务
        """
        if not history_list or len(history_list) < 2:
            return False

        # 提取最后一条用户消息
        last_user_msg = None
        for item in reversed(history_list):
            if isinstance(item, dict) and item.get("role") == "user":
                last_user_msg = item.get("content", "")
                break

        if not last_user_msg:
            return False

        current_lower = current_msg.lower()
        last_lower = last_user_msg.lower()

        # 任务类型关键词
        TASK_TYPES = {
            "explore": ["是什么项目", "项目分析", "代码结构", "源码", "理解",
                       "analyze", "what is", "project"],
            "write": ["写", "创建", "新建", "帮我写", "帮我创建", "make", "create", "write"],
            "edit": ["修改", "编辑", "改", "fix", "edit", "modify"],
            "search": ["找", "搜索", "查找", "find", "search"]
        }

        def detect_task_type(msg: str) -> Optional[str]:
            msg_lower = msg.lower()
            for task_type, keywords in TASK_TYPES.items():
                for kw in keywords:
                    if kw in msg_lower:
                        return task_type
            return None

        current_type = detect_task_type(current_lower)
        last_type = detect_task_type(last_lower)

        # 类型完全不同，认为是新任务
        if current_type and last_type and current_type != last_type:
            return True

        # 去除功能词后的重叠度
        function_words = {"的", "了", "是", "在", "和", "有", "我", "你",
                         "the", "a", "an", "is", "are", "this", "that"}

        current_words = set(current_lower.split()) - function_words
        last_words = set(last_lower.split()) - function_words

        if current_words and last_words:
            overlap = len(current_words & last_words)
            union = len(current_words | last_words)
            # 重叠度低于 30% 认为无关
            if overlap / union < 0.3:
                return True

        return False

    def _init_system_prompt_cache(self):
        """初始化 System Prompt 缓存 sections"""
        # 使用 compute_fn 延迟计算，避免在 __init__ 时获取不到 work_directory
        register_system_section(
            name="core",
            cacheable=True,
            compute_fn=self._build_core_prompt
        )
        register_system_section(
            name="tools",
            cacheable=True,
            compute_fn=self._build_tools_prompt
        )
        register_system_section(
            name="tone_and_style",
            cacheable=True,
            compute_fn=self._build_tone_style_prompt
        )
        register_system_section(
            name="doing_tasks",
            cacheable=True,
            compute_fn=self._build_doing_tasks_prompt
        )
        register_system_section(
            name="memory",
            cacheable=False,  # 每次都重新计算
            compute_fn=self._build_memory_prompt
        )
        register_system_section(
            name="environment",
            cacheable=True,
            compute_fn=self._build_env_prompt
        )

    def _needs_exploration(self, message: str) -> bool:
        """
        判断用户消息是否需要代码探索

        基于 cc-haha 的 Intent Detection 模式
        当用户询问项目、代码库、结构、实现等问题时触发
        """
        message_lower = message.lower()

        # 探索触发关键词
        EXPLORATION_TRIGGERS = [
            # 项目分析
            "是什么项目", "这个项目", "项目是干什么", "项目结构", "项目分析",
            "what is this", "what does this", "analyze this", "project structure",
            # 代码探索
            "代码结构", "源代码", "源码", "代码库", "怎么实现", "如何实现",
            "code structure", "source code", "how does it work", "how does x work",
            # 架构分析
            "架构", "设计模式", "架构图", "模块", "组件",
            "architecture", "design pattern", "modules", "components",
            # 文件查找
            "有哪些文件", "有什么文件", "文件结构", "查找", "找到",
            "what files", "find files", "locate", "where is",
            # 理解代码
            "理解代码", "分析代码", "解释代码", "读懂",
            "understand", "explain", "describe",
        ]

        for trigger in EXPLORATION_TRIGGERS:
            if trigger in message_lower:
                return True

        return False

    def _build_exploration_plan(self, message: str) -> str:
        """
        为需要探索的任务构建探索计划

        基于 cc-haha 的 Exploration Plan 模式
        """
        message_lower = message.lower()

        # 针对不同问题类型生成不同的探索计划
        if any(t in message_lower for t in ["是什么项目", "this project", "项目是干什么"]):
            return """## 探索计划
1. list("src/") 或 list("app/") - 查看目录结构
2. 查找入口文件 (main.*, index.*, app.*)
3. read 入口文件了解应用启动点
4. grep 关键类和函数
5. read 关键实现文件
6. 综合信息回答"""

        elif any(t in message_lower for t in ["怎么实现", "如何实现", "how does", "how it work"]):
            return """## 探索计划
1. grep 搜索相关关键词定位实现
2. read 实现文件
3. 跟踪逻辑流程
4. 结合实际代码解释"""

        elif any(t in message_lower for t in ["代码结构", "文件结构", "structure", "architecture"]):
            return """## 探索计划
1. list 顶层目录结构
2. glob 查找所有源码文件
3. grep 识别核心模块
4. read 关键文件理解架构"""

        else:
            return """## 探索计划
1. list 查看目录结构
2. glob 查找相关源码
3. grep 定位关键实现
4. read 核心文件
5. 综合回答"""

    def _format_tool_error(self, tool_name: str, error: str,
                          tool_args: Dict[str, Any]) -> str:
        """
        格式化工具错误，返回有意义的消息
        参照 cc-haha 的清晰错误处理

        注意：对于 ask 状态（需要用户确认但可以继续），不应该显示为错误
        而应该让 LLM 知道需要确认，并让工具继续执行
        """
        error_lower = error.lower()
        path = tool_args.get("path", "")

        # 使用权限服务检查实际的权限状态
        try:
            from app.services.permission_service import permission_service
            context = permission_service.get_permission_context()
            from app.services.permission_service import check_read_permission_for_tool, check_write_permission_for_tool

            # 判断是读还是写操作
            is_write = tool_name.lower() in ["write", "edit"]
            if is_write:
                decision = check_write_permission_for_tool(tool_name, path, context)
            else:
                decision = check_read_permission_for_tool(tool_name, path, context)

            # ask 状态：需要确认但不阻止执行
            # 返回提示信息，让 LLM 知道需要确认，但仍然继续执行
            if decision.behavior == 'ask':
                return f"""[Permission Required] {path}

{decision.message}

Please confirm access to continue, or choose a different path."""

        except Exception:
            # 权限服务检查失败，回退到简单的关键字检查
            pass

        # 1. 权限错误 - 改进的关键字检查
        if "permission" in error_lower and ("denied" in error_lower or "outside" in error_lower or "cannot access" in error_lower):
            return f"""[Permission Error] Cannot access: {path}

{error}

Do NOT retry. Use a path within the working directory, or ask user for access."""

        # 2. 路径不存在
        if "does not exist" in error_lower or "not found" in error_lower:
            # 检查是否是目录被当作文件
            if path in [op[1] for op in self.exploration_tracker.operations
                       if op[0] == "list"]:
                return f"""[Error] {path} is a directory, not a file.

Use list() to see its contents. Do NOT use read() on directories."""

            return f"""[Error] Path does not exist: {path}

If you want to create this file, use Write tool directly with the desired path."""

        # 3. 目录被当作文件读
        if "is a directory" in error_lower or "path is a directory" in error_lower:
            return f"""[Error] {path} is a directory.

Use list() to see its contents: list({{"path": "{path}"}})"""

        # 4. 空结果
        if "no matches" in error_lower or "no files" in error_lower:
            return f"""[Info] No matches found for the query.

Try a different search pattern or check the directory path."""

        # 5. 默认错误 - 保留原始错误消息
        return f"""[Error] {error}

Please check the tool arguments and try a different approach."""

    def _is_write_intent(self, message: str) -> bool:
        """判断是否是写操作意图"""
        write_keywords = [
            "写", "创建", "新建", "帮我写", "帮我创建", "帮我做",
            "保存到", "输出到",
            "make", "create", "write", "build", "implement"
        ]
        return any(kw in message.lower() for kw in write_keywords)

    def _check_write_task_completion(self, tool_history: list,
                                      user_intent: str) -> Tuple[bool, str]:
        """
        检查写任务是否真正完成

        Returns: (is_complete: bool, reason: str)
        """
        if not self._is_write_intent(user_intent):
            return True, "not_write_task"

        # 检查是否有实际写操作
        write_ops = [u for u in tool_history
                    if u.get("tool") in ["write", "edit"]]

        if write_ops:
            return True, "write_operation_completed"

        # 没有写操作，检查原因
        # 权限错误 - 只检查明确的权限拒绝消息
        permission_errors = [
            u for u in tool_history
            if isinstance(u, dict) and (
                "permission" in u.get("result", "").lower() and
                ("outside" in u.get("result", "").lower() or "denied" in u.get("result", "").lower())
            )
        ]
        if permission_errors:
            return False, "permission_denied"

        # 路径错误 - 只检查明确的路径不存在消息
        path_errors = [
            u for u in tool_history
            if isinstance(u, dict) and "does not exist" in u.get("result", "").lower()
        ]
        if path_errors:
            return False, "path_not_found"

        # 还没有执行任何操作
        if not tool_history:
            return False, "no_operation_yet"

        return False, "unknown_reason"

    def _get_incomplete_message(self, reason: str, tool_history: list) -> str:
        """生成未完成提示"""
        messages = {
            "permission_denied":
                "Task could not be completed due to permission error. "
                "Please inform the user and suggest using a path within the working directory.",

            "path_not_found":
                "Task could not be completed because the target path does not exist. "
                "Consider creating the necessary directory structure first.",

            "no_operation_yet":
                "No file operations have been performed yet. "
                "Please proceed with the requested task.",

            "unknown_reason":
                "Task may not have been completed successfully. "
                "Please verify the results."
        }

        msg = messages.get(reason, messages["unknown_reason"])

        # 添加最近的操作历史
        if tool_history:
            recent = tool_history[-3:]
            tools = [u.get("tool", "") for u in recent]
            msg += f"\n\nRecent operations: {', '.join(tools)}"

        return msg

    def _build_core_prompt(self) -> str:
        """构建核心提示词（约 1200 tokens，参考 Claude Code）"""
        return """You are WOLF AI, an interactive agent that helps users with software engineering tasks.

# Core principles
- Use tools to gather information, then synthesize results into a coherent response
- When tool execution completes, generate a comprehensive response based on the tool results
- Output text directly to communicate with the user. Use markdown for formatting.
- Tools are executed in permission mode - user approves dangerous operations.
- When user denies a tool call, think why and adjust approach.
- Do NOT propose changes to code you haven't read. If a user asks about or wants you to modify a file, read it first. Understand existing code before suggesting modifications.
- Prefer editing existing files to creating new ones. Do not create files unless absolutely necessary.
- Report outcomes faithfully: if tests fail, say so with the relevant output. Never claim "all tests pass" when output shows failures.

# EXPLORATION FIRST (CRITICAL)
When user asks about a codebase, project, or any code:
1. You MUST explore the actual source code - NOT just documentation
2. Start with list() to see directory structure
3. Read entry point files (main.*, index.*, app.*)
4. Use grep to find key patterns (class definitions, function names)
5. Read actual implementation files, not just *.md files
6. Only after exploration, synthesize and answer

# NEVER do this:
- Don't just read README and assume you understand the project
- Don't skip reading source code and rely only on documentation
- Don't assume documentation is complete or accurate
- Don't give answers without first exploring the relevant code

# ALWAYS do this:
- When asked "what is this project", first explore src/ or main directories
- When asked to analyze code, first use list(), then read key files
- When asked how something works, find and read the actual implementation
- When asked about code structure, explore with glob and grep first

# Exploration efficiency
- If you can answer with 1-2 tools, just do it
- Do not over-explore before answering simple questions
- Use list() once to understand structure, then act
- If an operation fails, do NOT repeat it - try different approach
- Do not explore randomly without purpose
- If you need more than 3 queries, be more focused

# Doing tasks
- The user will primarily request software engineering tasks: solving bugs, adding functionality, refactoring, explaining code, and more.
- When given an unclear or generic instruction, consider it in the context of these tasks and the current working directory.
- You are highly capable - allow users to complete ambitious tasks. Defer to user judgement about whether a task is too large to attempt.
- If an approach fails, diagnose why before switching tactics. Don't retry the identical action blindly, but don't abandon a viable approach after a single failure.
- Be careful not to introduce security vulnerabilities (command injection, XSS, SQL injection, OWASP top 10). If you notice insecure code, immediately fix it.

# Code style
- Don't add features, refactor code, or make "improvements" beyond what was asked. A bug fix doesn't need surrounding code cleaned up.
- Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust internal code and framework guarantees.
- Don't create helpers, utilities, or abstractions for one-time operations. Three similar lines of code is better than a premature abstraction.
- Avoid backwards-compatibility hacks. If you are certain something is unused, delete it completely.

# Executing actions with care
Carefully consider reversibility and blast radius. For actions that are hard to reverse, affect shared systems, or are risky/destructive, check with the user before proceeding:
- Destructive: deleting files/branches, dropping tables, rm -rf, killing processes
- Hard-to-reverse: force-pushing, git reset --hard, amending commits, removing packages
- Actions visible to others: pushing code, creating PRs, posting to external services, modifying shared infrastructure

# Using tools (CRITICAL)
Do NOT use bash when a relevant dedicated tool is provided:
- To read files use Read instead of cat, head, tail, or sed
- To edit files use Edit instead of sed or awk
- To create files use Write instead of cat with heredoc or echo redirection
- To search for files use Glob instead of find or ls
- To search file content use Grep instead of grep or rg
- Reserve Bash exclusively for system commands and terminal operations
- Use absolute paths (e.g., E:/project/src/main.py). Never assume directories exist - create them explicitly with bash.
- For Edit: provide EXACT old_string including all whitespace. The edit will fail if old_string is not found verbatim.
- For Write: provide COMPLETE file content. This overwrites existing content entirely.

# Tool result handling
- After receiving tool results, synthesize the information into a useful response
- Do NOT just say "Task completed" - provide actual content based on tool results
- If tools gathered file contents or directory listings, summarize and explain what was found

# Output format
- Always provide meaningful content, not "Task completed"
- Use markdown headers, lists, and code blocks to structure information
- Do not end responses with "Task completed" - summarize what was done and found
- When referencing code, include file_path:line_number for navigation

# Verification requirements (IMPORTANT)
- After writing code, ALWAYS verify the file was created or modified
- If you used Write tool, read the file back to confirm content is correct
- If you used Edit tool, read the file to confirm old_string was replaced by new_string
- If you created directories, verify they exist with list tool
- If build/test fails, read errors and fix them - don't just report the failure
- Report actual results, not assumptions. If you cannot verify something, say so explicitly.

# Memory system
- When user provides feedback about preferences ("I prefer...", "please don't..."), remember it by saving to memory
- When you learn important project context (deadlines, decisions, stakeholders), save it to memory
- Save memories using Write tool to .claude/memory/[type]/[name].md with frontmatter format
- Memory types: user (preferences), project (context), feedback (corrections), reference (external info)"""

    def _build_tone_style_prompt(self) -> str:
        """构建输出风格提示词"""
        return """# Tone and style
- Only use emojis if the user explicitly requests it. Avoid using emojis unless asked.
- Your responses should be short and concise. Go straight to the point.
- Lead with the answer or action, not the reasoning. Skip filler words and unnecessary transitions.
- When referencing specific functions or pieces of code include the pattern file_path:line_number.
- Do not use a colon before tool calls. Text like "Let me read the file:" followed by a read tool call should just be "Let me read the file." with a period.

# Output efficiency
Keep your text output brief and direct. Focus on:
- Decisions that need the user's input
- High-level status updates at natural milestones
- Errors or blockers that change the plan
If you can say it in one sentence, don't use three."""

    def _build_doing_tasks_prompt(self) -> str:
        """构建任务执行 Prompt - 参考 cc-haha 的 doing_tasks_section"""
        return """# Task Execution

## READ BEFORE WRITE (Critical)
When user asks you to CREATE, WRITE, or MODIFY code:
1. list(".") to see the directory structure
2. Read existing relevant files to understand patterns
3. Write your code with the same style
4. Verify by reading the file back

## EXPLORATION (for UNDERSTANDING only)
When user asks "what is", "analyze", "how does":
1. list() the top-level directory
2. grep/glob to find relevant files
3. Read key files to understand
4. Provide answer based on CODE, not just documentation

## DO NOT DO THIS
- Do NOT explore randomly without purpose
- Do NOT read the same file twice
- Do NOT repeat the same operation if it failed
- Do NOT use read() on a directory (use list() instead)
- Do NOT assume a path exists without checking

## IF AN ERROR OCCURS
- Permission error: Inform user, suggest using working directory
- Path not found: Check if it's a directory (use list) or create it
- Invalid operation: Try a different approach
- Do NOT keep retrying the same failed operation

## TASK COMPLETION
- Write tasks require actual file operations (write/edit)
- If user asked for "write/create" but no file was modified, the task is NOT complete
- Report actual results, not assumptions

## Exploration efficiency
- If you can answer with 1-2 tools, just do it
- Do not over-explore before answering simple questions
- Use list() once to understand structure, then act
- If an operation fails, do NOT repeat it - try different approach"""

    def _build_tools_prompt(self) -> str:
        """构建工具提示词（约 400 tokens）"""
        return """# Available tools
## File operations
- read(path, offset=0, limit=None): Read file contents
- write(path, content): Write content to file (overwrites existing)
- edit(path, old_string, new_string): Edit by replacing exact old_string verbatim
- grep(pattern, path=None, glob=None): Search for pattern in files
- glob(pattern, path=None): Find files matching glob pattern
- bash(command, timeout=30): Execute bash command
- list(path="."): List directory contents
- exists(path): Check if file/directory exists
- get_file_info(path): Get file information

## Web scraping (requires: pip install scrapling)
- scrape(url, selector=None, mode="simple"): Scrape web pages
  - selector: CSS selector like ".article", "h1::text"
  - mode: simple=HTTP request, stealth=bypass anti-bot, dynamic=browser JS rendering
- crawl(start_url, selectors, max_pages=10): Crawl multiple pages
  - selectors: list of CSS selectors to extract
  - max_pages: maximum number of pages to crawl"""

    def _build_memory_prompt(self) -> str:
        """构建记忆提示词（约 200 tokens）"""
        from app.services.memory_service import MemoryService
        memory_service = MemoryService(memory_base_path=self._get_memory_path())
        return memory_service.build_memory_prompt()

    def _build_env_prompt(self) -> str:
        """构建环境提示词（约 100 tokens）"""
        work_dir = self.work_directory
        is_git = self._get_git_status()
        platform_name, os_version = self._get_platform_info()

        return f"""# Environment
<env>
Working directory: {work_dir}
Is git repo: {'Yes' if is_git else 'No'}
Platform: {platform_name}
OS: {os_version}
</env>

- Share file paths as absolute paths
- Avoid emojis in communication
- Use periods instead of colons before tool calls"""

    def _get_system_prompt(self) -> str:
        """获取完整 system prompt"""
        return system_prompt_cache.build_prompt()

    def _resolve_work_directory(self, work_directory: str = None) -> str:
        """解析工作目录"""
        if work_directory and os.path.exists(work_directory):
            return os.path.abspath(work_directory)

        try:
            from app.core.runtime_config import runtime_config
            wd = runtime_config.get_work_directory()
            if wd and os.path.exists(wd):
                return os.path.abspath(wd)
        except Exception:
            pass

        return os.getcwd()

    def _get_memory_path(self) -> str:
        """获取记忆目录路径 - 统一使用 wolf_data/memory"""
        # 获取 wolf_b 目录的父目录（项目根目录）
        wolf_b_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # app/agents/../.. -> wolf_b
        wolf_data_memory = os.path.join(wolf_b_dir, "wolf_data", "memory")
        os.makedirs(wolf_data_memory, exist_ok=True)
        # 确保子目录存在
        for subdir in ["user", "project", "feedback", "reference"]:
            os.makedirs(os.path.join(wolf_data_memory, subdir), exist_ok=True)
        return wolf_data_memory

    def _get_git_status(self) -> bool:
        """检查当前目录是否是git仓库"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.work_directory,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and "true" in result.stdout.lower()
        except Exception:
            return False

    def _get_platform_info(self) -> tuple:
        """获取平台信息"""
        platform = os.name  # 'nt' for Windows, 'posix' for Unix
        platform_name = "Windows" if platform == "nt" else "Linux/macOS"
        try:
            import platform as platform_module
            os_version = f"{platform_module.system()} {platform_module.release()}"
        except Exception:
            os_version = "Unknown"
        return platform_name, os_version

    def _get_system_prompt(self) -> str:
        """获取完整 system prompt"""
        return system_prompt_cache.build_prompt()

    async def think(self, user_message: str, cancel_token=None, history_list: list = None, event_callback=None) -> str:
        """
        直接执行模式 - 处理用户请求

        流程（参考 cc-haha 单Agent模式）：
        1. 从用户消息提取工作目录（如果明确指定）
        2. 构建完整的消息历史（包括历史对话）
        3. 调用 LLM
        4. 如果 LLM 返回工具调用，执行工具
        5. 循环直到完成
        6. 返回最终结果

        Args:
            user_message: 用户消息
            cancel_token: 可选的取消令牌
            history_list: 可选的对话历史列表（来自前端）
            event_callback: 可选的事件回调函数，用于实时流式输出

        Returns:
            最终响应文本
        """
        try:
            # 检查取消令牌
            if cancel_token and cancel_token.is_cancelled:
                return "Task was cancelled"

            # 0. 新任务检测 - 清空探索追踪器
            if history_list and self._is_topic_change(user_message, history_list):
                self.exploration_tracker.clear()
                self.exploration_history = []

            # 1. 从用户消息提取路径（如果明确指定）
            extracted_path = self._extract_path_from_message(user_message)
            if extracted_path and os.path.exists(os.path.dirname(extracted_path) if os.path.isfile(extracted_path) else extracted_path):
                old_work_dir = self.work_directory
                self.work_directory = os.path.abspath(extracted_path)
                if os.path.isfile(extracted_path):
                    self.work_directory = os.path.dirname(self.work_directory)
                # 重新初始化工具服务和记忆服务
                from app.services.tools_service import ToolsService
                self.tools_service = ToolsService(workspace_path=self.work_directory)
                # 更新 system prompt 缓存
                from app.agents.system_prompt import clear_system_prompt_cache
                clear_system_prompt_cache()
                self._init_system_prompt_cache()

            # 2. 预提取并添加所有路径到权限服务（参考 cc-haha）
            # 在调用 LLM 之前，提前准备所有可能的路径
            try:
                from app.services.permission_service import permission_service
                # 使用更精确的模式提取所有路径
                all_path_pattern = r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+)+'
                all_matches = re.findall(all_path_pattern, user_message)
                for match in all_matches:
                    cleaned_path = match.rstrip('.,;:，；： ').strip()
                    # 使用 check_and_add_path 智能添加路径
                    permission_service.check_and_add_path(cleaned_path)
            except Exception:
                pass  # 权限服务可能未初始化，静默忽略

            # 检查取消令牌
            if cancel_token and cancel_token.is_cancelled:
                return "Task was cancelled"

            # 3. 规范化历史消息 - 使用新的消息类型系统
            normalized_messages = self._normalize_history(history_list)

            # 4. 构建消息历史
            self.message_history = [
                {"role": "system", "content": self._get_system_prompt()}
            ]

            # 添加规范化的历史消息（使用新的格式化方法）
            for msg in normalized_messages:
                formatted = format_message_for_api(msg)
                if formatted:
                    self.message_history.append(formatted)
                    # 更新 WorkingMemory
                    content = formatted.get("content", "")
                    if content:
                        if msg.type == "user":
                            self.working_memory.add_user_message(content)
                        elif msg.type == "assistant":
                            self.working_memory.add_assistant_message(content)

            # 5. 添加用户消息
            # 检测是否需要探索，并在需要时添加探索计划
            if self._needs_exploration(user_message):
                exploration_plan = self._build_exploration_plan(user_message)
                user_msg_with_context = f"{exploration_plan}\n\n[User message]\n{user_message}"
                # 记录探索意图
                self.exploration_history.append({
                    "intent": "exploration",
                    "query": user_message[:100],
                    "timestamp": datetime.now().isoformat()
                })
            else:
                user_msg_with_context = self._add_context_to_message(user_message)
            self.message_history.append({
                "role": "user",
                "content": user_msg_with_context
            })
            self.working_memory.add_user_message(user_msg_with_context)

            # 检查是否需要压缩 session memory
            await self._check_and_compact_session()

            # 3. 调用 LLM 并处理响应
            response = await self._execute_llm_loop(cancel_token, event_callback)

            # 4. 检查写任务完成状态
            is_complete, reason = self._check_write_task_completion(
                self.tool_usage_history, user_message
            )

            if not is_complete:
                incomplete_msg = self._get_incomplete_message(
                    reason, self.tool_usage_history
                )
                if incomplete_msg:
                    response = response + "\n\n" + incomplete_msg

            # 5. 保存 Session Memory
            await self._save_session_memory(response)

            return response

        except asyncio.CancelledError:
            return "Task was cancelled"
        except Exception as e:
            return f"Error processing request: {str(e)}"

    def _add_context_to_message(self, message: str) -> str:
        """添加上下文信息到用户消息"""
        # 每次动态创建 MemoryService 实例
        from app.services.memory_service import MemoryService
        memory_service = MemoryService(memory_base_path=self._get_memory_path())
        relevant_memories = memory_service.find_relevant_memories(message)

        if not relevant_memories:
            return message

        context_parts = ["[Relevant context from memory]\n"]

        for mem in relevant_memories[:5]:  # 最多添加5条记忆
            context_parts.append(f"\n## {mem['name']} ({mem['type']})\n{mem['content'][:500]}")

        context_parts.append(f"\n\n[User message]\n{message}")

        return "\n".join(context_parts)

    def _normalize_history(self, history_list: list) -> List[Message]:
        """
        规范化历史消息 - 使用新的消息类型系统

        参照 cc 的 normalizeMessagesForAPI
        支持多种历史格式：
        1. {"role": "user", "content": "..."}
        2. {"agentRole": "user", "content": "..."}
        3. {"sessionId": ..., "agentRole": ..., "content": ...}
        """
        if not history_list:
            return []

        # 第一步：将历史列表转换为内部 Message 对象
        messages = convert_history_list_to_messages(history_list)

        # 第二步：获取可用的工具列表
        available_tools = self.tools_service.get_available_tools() if hasattr(self, 'tools_service') else []

        # 第三步：规范化消息
        normalized = normalize_messages_for_api(messages, available_tools)

        return normalized

    async def _check_and_compact_session(self) -> None:
        """检查是否需要压缩 session memory"""
        if self.session_memory and await self.session_memory.should_compact():
            # 提取对话信息并更新 session memory
            messages_for_compact = [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in self.message_history[-20:]
            ]
            await self.session_memory.extract_from_conversation(messages_for_compact)

    async def _save_session_memory(self, final_response: str) -> None:
        """保存 session memory - 在对话结束时保存关键信息"""
        if not self.session_memory:
            return

        try:
            # 构建当前对话摘要
            messages_for_summary = [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in self.message_history[-10:]
            ]

            # 更新 session memory 的 worklog
            worklog_entry = f"- Response: {final_response[:200]}..."
            current_worklog = await self.session_memory.get_section("worklog")
            if current_worklog:
                updated_worklog = current_worklog + "\n" + worklog_entry
            else:
                updated_worklog = worklog_entry

            await self.session_memory.update_section("worklog", updated_worklog)

            # 如果对话有工具使用，记录文件修改
            if self.tool_usage_history:
                files_modified = []
                for usage in self.tool_usage_history:
                    if usage.get("tool") in ["write", "edit"]:
                        path = usage.get("args", {}).get("path", "")
                        if path:
                            files_modified.append(path)

                if files_modified:
                    current_files = await self.session_memory.get_section("files_and_functions")
                    files_section = current_files + "\n- Modified: " + ", ".join(set(files_modified)) if current_files else "Modified: " + ", ".join(set(files_modified))
                    await self.session_memory.update_section("files_and_functions", files_section)

        except Exception as e:
            # 静默失败，不影响主流程
            pass

    def _extract_path_from_message(self, message: str) -> Optional[str]:
        """从用户消息中提取路径（更严格的验证，参考 cc-haha）"""
        import os
        import re

        # 第一步：提取原始的 Windows 驱动器路径
        # 匹配 E: 或 E:\ 开头后跟内容，排除空格、引号、中文
        # 使用更精确的模式：驱动器字母 + : + 可选 \ + 路径内容
        # 排除所有非 ASCII 字符（包括中文）和特定标点
        drive_pattern = r'[A-Za-z]:(?:(?:\\|/)?[\x20-\x7E]+)+'

        # 在消息中查找所有驱动器路径（不清理，控制字符可能破坏匹配）
        potential_matches = re.findall(drive_pattern, message)

        for match in potential_matches:
            # 清理路径：只保留 ASCII 可打印字符、反斜杠、斜杠、点和连字符
            # 这可以排除中文和其他非 ASCII 字符
            clean_path = ''
            for c in match:
                if c in '\\/:' or c.isalnum() or c in '_-.':
                    clean_path += c

            # 移除尾部标点
            clean_path = clean_path.rstrip('.,;:，；： ')

            if not clean_path or len(clean_path) < 3:
                continue

            # 修复驱动器路径：E:agent -> E:\agent
            if len(clean_path) >= 3 and clean_path[1] == ':' and clean_path[2] not in '\\/:':
                clean_path = clean_path[:2] + '\\' + clean_path[2:]

            # 验证路径是否存在或父目录存在
            if os.path.exists(clean_path):
                return os.path.abspath(clean_path)
            parent = os.path.dirname(clean_path)
            if os.path.exists(parent):
                return os.path.abspath(clean_path)

        # 第二步：如果没找到，尝试清理消息中的控制字符后重试
        # BEL (0x07) 和其他控制字符会干扰 os.path.abspath
        cleaned_message = ''.join(c for c in message if ord(c) >= 32 or c in '\t\n\r\\/:')
        matches = re.findall(drive_pattern, cleaned_message)

        for match in matches:
            clean_path = ''
            for c in match:
                if c in '\\/:' or c.isalnum() or c in '_-.':
                    clean_path += c

            clean_path = clean_path.rstrip('.,;:，；： ')

            if len(clean_path) >= 3 and clean_path[1] == ':' and clean_path[2] not in '\\/:':
                clean_path = clean_path[:2] + '\\' + clean_path[2:]

            if os.path.exists(clean_path):
                return os.path.abspath(clean_path)
            parent = os.path.dirname(clean_path)
            if os.path.exists(parent):
                return os.path.abspath(clean_path)

        return None

    async def _execute_llm_loop(self, cancel_token=None, event_callback=None) -> str:
        """
        LLM 执行循环 - 类似于 cc-haha 的 query 循环

        Args:
            cancel_token: 取消令牌
            event_callback: 事件回调函数，用于实时流式输出
                回调接收: (event_type, data)
                event_type: 'tool_start' | 'tool_result' | 'content_delta' | 'thinking'
        """
        max_iterations = 30
        iteration = 0

        # 只读工具可以并发执行
        READONLY_TOOLS = {"read", "list", "glob", "grep", "exists", "get_file_info"}
        # 写工具需要串行执行
        WRITE_TOOLS = {"write", "edit", "bash"}

        while iteration < max_iterations:
            iteration += 1

            # 检查取消令牌
            if cancel_token and cancel_token.is_cancelled:
                return "Task was cancelled"

            # 构建 messages
            system = self.message_history[0]["content"] if self.message_history else None
            messages = self._build_messages_for_llm()

            # 调用 LLM
            available_tools = self.tools_service.get_available_tools()
            response = await llm_service.complete(
                prompt=None,
                system_prompt=system,
                messages=messages,
                tools=available_tools
            )

            if not response.get("success"):
                error_msg = response.get("error", "Unknown error")
                return f"LLM Error: {str(error_msg)}"

            content = response.get("content", "")
            content = self._remove_thinking_tags(content)

            # 解析工具调用
            official_tool_calls = response.get("tool_calls", [])
            if official_tool_calls:
                tool_calls = []
                for tc in official_tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    arguments = func.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except:
                            arguments = {}
                    tool_calls.append({"name": name, "args": arguments})
            else:
                tool_calls = self._parse_tool_calls(content)

            if not tool_calls:
                # No more tools - this is the final response
                # Remove any thinking tags and system reminders
                clean_content = self._remove_thinking_tags(content)
                if "<system-reminder>" in clean_content:
                    # Skip system reminders and continue to get actual response
                    self.message_history.append({"role": "assistant", "content": clean_content})
                    continue
                # Return the actual response content
                self.message_history.append({"role": "assistant", "content": clean_content})
                self.working_memory.add_assistant_message(clean_content)
                return clean_content

            # 执行工具调用（改进版：并发执行只读工具）
            has_tool_errors = await self._execute_tools_with_concurrency(tool_calls, iteration, event_callback)

            # 如果有工具执行错误，不立即返回
            # 继续循环让 LLM 看到错误并生成修复方案
            if has_tool_errors:
                # 检查是否还有剩余工具调用需要执行
                if self._has_pending_tool_calls():
                    continue

                # 所有工具执行完毕，继续循环让 LLM 生成最终响应或修复方案
                continue

            # 检查是否还有剩余工具调用需要执行
            # 如果有，继续循环（不添加新的 assistant 消息）
            if self._has_pending_tool_calls():
                continue

            # 所有工具执行完毕，继续循环让 LLM 生成最终响应
            continue

        return "Max iterations reached. Please try a more specific request."

    def _build_messages_for_llm(self) -> List[Dict[str, Any]]:
        """构建发送给 LLM 的消息列表，包含智能上下文管理"""
        messages = []
        history_items = self.message_history[1:]  # 跳过 system prompt

        # 上下文管理：智能截断
        max_history = 20
        max_total_chars = 8000

        # 如果历史过长，优先保留工具结果和最近的消息
        if len(history_items) > max_history:
            # 按类型分组
            tool_results = []
            other_items = []

            for h in history_items:
                content = h.get("content", "")
                if "[Tool Result" in content:
                    tool_results.append(h)
                else:
                    other_items.append(h)

            # 优先保留工具结果，其他消息保留最近的
            other_items = other_items[-max_history:]
            history_items = tool_results + other_items
            if len(history_items) > max_history:
                history_items = history_items[-max_history:]

        total_chars = sum(len(m.get("content", "")) for m in history_items)
        if total_chars > max_total_chars and len(history_items) > 3:
            keep_recent = 8
            history_items = history_items[-keep_recent:]

        for msg in history_items:
            messages.append({
                "role": "user" if msg["role"] == "user" else "assistant",
                "content": msg["content"]
            })

        return messages

    async def _execute_tools_with_concurrency(self, tool_calls: list, iteration: int, event_callback=None) -> bool:
        """
        执行工具调用，支持并发执行只读工具

        返回: 是否有工具执行错误（权限错误等）
        """
        READONLY_TOOLS = {"read", "list", "glob", "grep", "exists", "get_file_info"}
        WRITE_TOOLS = {"write", "edit", "bash"}

        # 分离只读和写工具
        readonly_calls = [tc for tc in tool_calls if tc.get("name", "").lower() in READONLY_TOOLS]
        write_calls = [tc for tc in tool_calls if tc.get("name", "").lower() in WRITE_TOOLS]

        has_error = False

        # 1. 先并发执行所有只读工具
        if readonly_calls:
            # 发送工具开始事件
            if event_callback:
                for tool_call in readonly_calls:
                    await event_callback('tool_start', {
                        'tool': tool_call.get("name", ""),
                        'args': tool_call.get("args", {}),
                        'iteration': iteration
                    })

            tasks = []
            for tool_call in readonly_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tasks.append(self._execute_single_tool(tool_name, tool_args, iteration))

            # 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for i, (tool_call, result) in enumerate(zip(readonly_calls, results)):
                tool_name = tool_call.get("name", "")
                if isinstance(result, Exception):
                    tool_result = f"Error: {str(result)}"
                else:
                    tool_result = result

                # 检查是否有错误
                if "[Permission" in tool_result or "[Error]" in tool_result or "[Loop Detected]" in tool_result:
                    has_error = True

                # 压缩过长的结果
                tool_result = self._compress_tool_result(tool_name, tool_result)

                self.tool_usage_history.append({
                    "tool": tool_name,
                    "args": tool_call.get("args", {}),
                    "result_length": len(tool_result),
                    "iteration": iteration
                })

                self.message_history.append({
                    "role": "user",
                    "content": f"[Tool Result for {tool_name}]\n{tool_result}\n\nContinue."
                })

                # 发送工具结果事件
                if event_callback:
                    await event_callback('tool_result', {
                        'tool': tool_name,
                        'args': tool_call.get("args", {}),
                        'result': tool_result,
                        'iteration': iteration
                    })

        # 2. 串行执行写工具
        for tool_call in write_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})

            # 发送工具开始事件
            if event_callback:
                await event_callback('tool_start', {
                    'tool': tool_name,
                    'args': tool_args,
                    'iteration': iteration
                })

            tool_result = await self._execute_single_tool(tool_name, tool_args, iteration)

            # 检查是否有错误
            if "[Permission" in tool_result or "[Error]" in tool_result or "[Loop Detected]" in tool_result:
                has_error = True

            tool_result = self._compress_tool_result(tool_name, tool_result)

            self.tool_usage_history.append({
                "tool": tool_name,
                "args": tool_args,
                "result_length": len(tool_result),
                "iteration": iteration
            })

            self.message_history.append({
                "role": "user",
                "content": f"[Tool Result for {tool_name}]\n{tool_result}\n\nContinue."
            })

            # 发送工具结果事件
            if event_callback:
                await event_callback('tool_result', {
                    'tool': tool_name,
                    'args': tool_args,
                    'result': tool_result,
                    'iteration': iteration
                })

        return has_error

    async def _execute_single_tool(self, tool_name: str, tool_args: Dict[str, Any], iteration: int) -> str:
        """执行单个工具，集成循环检测和错误处理"""
        path = tool_args.get("path", "")

        # 1. 记录操作
        self.exploration_tracker.record(tool_name, path)

        # 2. 检查是否循环
        repeated_op = self.exploration_tracker.get_repeated_operation()
        if repeated_op:
            return f"""[Loop Detected] Same operation repeated twice: {tool_name} on {path}

Do NOT repeat the same operation. Try a different approach:
- If list() failed, try a different directory
- If read() failed, check if it's a directory (use list() instead)
- If grep() found nothing, try a different pattern"""

        # 3. PRE-EXECUTION PERMISSION CHECK (参照 cc-haha)
        # 在工具执行前检查权限，尝试自动添加路径
        if path:
            try:
                from app.services.permission_service import permission_service, check_read_permission_for_tool, check_write_permission_for_tool

                # 获取权限上下文
                context = permission_service.get_permission_context()

                # 判断是读还是写操作
                is_write = tool_name.lower() in ["write", "edit"]
                if is_write:
                    decision = check_write_permission_for_tool(tool_name, path, context)
                else:
                    decision = check_read_permission_for_tool(tool_name, path, context)

                # 如果权限检查失败，不执行工具
                if decision.behavior == 'deny':
                    self.exploration_tracker.record(tool_name, path, error=decision.message)
                    return f"""[Permission Denied] {path}

{decision.message}

Do NOT retry. Ask user for permission."""

                # 如果是 ask 状态，记录但不阻止执行
                if decision.behavior == 'ask':
                    # 尝试自动添加路径
                    permission_service.check_and_add_path(path)

            except Exception:
                pass  # 权限服务可能未初始化，静默忽略

        # 4. 执行工具
        result = await self._execute_tool(tool_name, tool_args)

        # 5. 错误处理（只有明确返回错误格式才处理，参照 cc-haha）
        # cc-haha 不进行 is_error 判断，工具返回什么就传递什么
        # 只有明确以 [Error]/[Permission]/[Loop Detected] 开头的才是需要格式化的错误
        should_format = (
            result.startswith("[Error]") or
            result.startswith("[Permission") or
            result.startswith("[Loop Detected]")
        )

        if should_format and result:
            self.exploration_tracker.record(tool_name, path, error=result)

            # 拒绝追踪
            try:
                from app.services.permission_service import get_denial_tracker
                denial_tracker = get_denial_tracker()

                if "Permission Error" in result or "denied" in result.lower():
                    denial_tracker.record_denial()
                    if denial_tracker.should_fallback():
                        denial_state = denial_tracker.get_state()
                        result = f"""[Permission Denied] Too many denials (consecutive: {denial_state['consecutive_denials']}, total: {denial_state['total_denials']})

Consider:
1. Using a path within the working directory
2. Enabling acceptEdits mode for writes outside current directory

Last error: {result[:200]}"""
                else:
                    denial_tracker.record_success()
            except Exception:
                pass

            return self._format_tool_error(tool_name, result, tool_args)
        else:
            # 成功时重置拒绝追踪
            try:
                from app.services.permission_service import get_denial_tracker
                get_denial_tracker().record_success()
            except Exception:
                pass

        # 5. 验证写操作
        if tool_name.lower() == "write":
            path = self._resolve_path(tool_args.get("path", ""))
            expected = tool_args.get("content", "")

            # 检查文件是否存在
            if not os.path.exists(path):
                result += "\n[Error: File was not created - please verify path and permissions]"
            else:
                # 检查内容是否匹配
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        actual = f.read()
                    if expected not in actual:
                        result += "\n[Warning: File content may not match expected - please verify]"
                except Exception as e:
                    result += f"\n[Error: Could not verify file content: {str(e)}]"

        elif tool_name.lower() == "edit":
            path = self._resolve_path(tool_args.get("path", ""))
            old_string = tool_args.get("old_string", "")
            new_string = tool_args.get("new_string", "")

            if old_string and new_string:
                if not os.path.exists(path):
                    result += "\n[Error: File does not exist]"
                else:
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            file_content = f.read()

                        # 验证 old_string 是否已移除
                        if old_string in file_content and new_string not in file_content:
                            result += "\n[Warning: Edit may not have been applied - old_string still present, new_string not found]"
                        # 验证 new_string 是否已添加
                        elif new_string not in file_content:
                            result += "\n[Warning: Edit may not have been applied - new_string not found in file]"
                        # 成功情况：old_string 不在文件中（已被替换）且 new_string 在文件中
                        elif old_string not in file_content and new_string in file_content:
                            pass  # 成功，无需警告
                        else:
                            result += "\n[Warning: Edit result unclear - please verify]"
                    except Exception as e:
                        result += f"\n[Error: Could not verify edit: {str(e)}]"

        elif tool_name.lower() == "bash":
            # 验证 bash 命令（特别是 mkdir）
            command = tool_args.get("command", "")
            if command.strip().startswith("mkdir"):
                # 尝试提取创建的目录路径
                import re
                # 匹配 mkdir -p path 或 mkdir path
                match = re.search(r'mkdir\s+(?:-p\s+)?([^\s]+)', command)
                if match:
                    created_path = match.group(1).strip('"\'')
                    # 转换为绝对路径
                    if not os.path.isabs(created_path):
                        created_path = os.path.join(self.work_directory, created_path)
                    # 验证目录是否存在
                    if not os.path.exists(created_path):
                        result += f"\n[Warning: Directory may not have been created: {created_path}]"

        return result

    def _compress_tool_result(self, tool_name: str, result: str, max_length: int = 2000) -> str:
        """
        压缩过长的工具结果，类似于 cc-haha 的 auto-compact

        如果结果超过 max_length，进行截断并添加摘要
        """
        if len(result) <= max_length:
            return result

        # 对于 list 操作，保留前 N 项和总数
        if tool_name.lower() == "list" and "\n" in result:
            lines = result.split("\n")
            if len(lines) > 30:
                # 保留前 20 行和后 10 行，中间省略
                compressed = lines[:20]
                compressed.append(f"\n... [{len(lines) - 30} lines omitted] ...\n")
                compressed.extend(lines[-10:])
                return "\n".join(compressed)

        # 其他情况简单截断
        return result[:max_length] + f"\n...[truncated, total {len(result)} chars]..."

    def _has_pending_tool_calls(self) -> bool:
        """检查是否有剩余工具调用需要执行"""
        # 检查最后一条 assistant 消息是否包含未执行的工具调用
        if len(self.message_history) < 2:
            return False

        last_msg = self.message_history[-1]
        if last_msg.get("role") != "assistant":
            return False

        content = last_msg.get("content", "")
        # 检查是否包含 "[Remaining tool calls" 标记
        return "[Remaining tool calls" in content

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """解析内容中的工具调用"""
        tool_calls = []

        # 格式1: <tool_name>{"key": "value"}</tool_name>
        import re
        pattern = r'<(\w+)>\s*(\{.*?\})\s*</\1>'
        matches = re.findall(pattern, content, re.DOTALL)
        for name, args_str in matches:
            try:
                args = json.loads(args_str) if args_str.strip() else {}
                tool_calls.append({"name": name, "args": args})
            except json.JSONDecodeError:
                pass

        # 格式2: <tool_name>...</tool_name> (无参数)
        if not tool_calls:
            pattern = r'<(\w+)>\s*</\1>'
            matches = re.findall(pattern, content)
            for name in matches:
                if name.lower() in ["read", "write", "edit", "grep", "glob", "bash", "list", "exists", "get_file_info"]:
                    tool_calls.append({"name": name, "args": {}})

        return tool_calls

    def _remove_thinking_tags(self, content: str) -> str:
        """移除思考标签和内容"""
        # 移除 <think>... 标签及其内容
        content = re.sub(r'<think>[\s\S]*?', '', content, flags=re.IGNORECASE)
        # 移除 <thinking>...</thinking> 标签及其内容
        content = re.sub(r'<thinking>[\s\S]*?</thinking>', '', content, flags=re.IGNORECASE)
        # 清理多余的空白行
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """执行工具并返回结果"""
        try:
            # 工具名称标准化
            tool_name_lower = tool_name.lower()

            if tool_name_lower == "read":
                return await self._tool_read(tool_args)
            elif tool_name_lower == "write":
                return await self._tool_write(tool_args)
            elif tool_name_lower == "edit":
                return await self._tool_edit(tool_args)
            elif tool_name_lower == "grep":
                return await self._tool_grep(tool_args)
            elif tool_name_lower == "glob":
                return await self._tool_glob(tool_args)
            elif tool_name_lower == "bash":
                return await self._tool_bash(tool_args)
            elif tool_name_lower in ["list", "list_directory"]:
                return await self._tool_list(tool_args)
            elif tool_name_lower == "exists":
                return await self._tool_exists(tool_args)
            elif tool_name_lower == "get_file_info":
                return await self._tool_get_file_info(tool_args)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _resolve_path(self, path: str) -> str:
        """解析路径为绝对路径，处理 Windows 驱动器路径和控制字符"""
        if not path:
            return self.work_directory
        if os.path.isabs(path):
            # 对驱动器路径使用 _normalize_path 处理 BEL 等控制字符
            if len(path) >= 2 and path[1] == ':':
                return self._normalize_path(path)
            return path
        return os.path.join(self.work_directory, path)

    def _normalize_path(self, path: str) -> str:
        """规范化路径，处理控制字符（参考 permission_service 的实现）"""
        if not path:
            return path
        # 检查是否是 Windows 驱动器路径
        is_drive_path = len(path) >= 2 and path[1] == ':' and path[0].isalpha()
        if is_drive_path:
            # 对驱动器路径，移除控制字符并规范化分隔符
            normalized = ''
            for c in path:
                if ord(c) >= 32 or c in '\t\n\r\\/:':
                    normalized += c
            normalized = normalized.replace('/', '\\')
            if len(normalized) > 3:
                normalized = normalized.rstrip('\\')
            return normalized
        return os.path.normpath(path)

    async def _tool_read(self, args: Dict[str, Any]) -> str:
        """Read 工具"""
        path = self._resolve_path(args.get("path", ""))
        offset = args.get("offset", 0)
        limit = args.get("limit")

        result = await self.tools_service.read(path, offset, limit)
        return result.content if result.success else result.error

    async def _tool_write(self, args: Dict[str, Any]) -> str:
        """Write 工具"""
        path = self._resolve_path(args.get("path", ""))
        content = args.get("content", "")
        append = args.get("append", False)

        result = await self.tools_service.write(path, content, append)
        return result.content if result.success else result.error

    async def _tool_edit(self, args: Dict[str, Any]) -> str:
        """Edit 工具"""
        path = self._resolve_path(args.get("path", ""))
        old_string = args.get("old_string", "")
        new_string = args.get("new_string", "")
        regex = args.get("regex", False)

        result = await self.tools_service.edit(path, old_string, new_string, regex)
        return result.content if result.success else result.error

    async def _tool_grep(self, args: Dict[str, Any]) -> str:
        """Grep 工具"""
        pattern = args.get("pattern", "")
        path = self._resolve_path(args.get("path", self.work_directory))
        glob = args.get("glob")
        case_sensitive = args.get("case_sensitive", True)

        result = await self.tools_service.grep(pattern, path, glob, case_sensitive, True)
        return result.content if result.success else result.error

    async def _tool_glob(self, args: Dict[str, Any]) -> str:
        """Glob 工具"""
        pattern = args.get("pattern", "")
        path = self._resolve_path(args.get("path", self.work_directory))

        result = await self.tools_service.glob(pattern, path)
        return result.content if result.success else result.error

    async def _tool_bash(self, args: Dict[str, Any]) -> str:
        """Bash 工具"""
        command = args.get("command", "")
        timeout = args.get("timeout", 30)

        result = await self.tools_service.bash(command, timeout)
        return result.content if result.success else result.error

    async def _tool_list(self, args: Dict[str, Any]) -> str:
        """List 工具"""
        path = self._resolve_path(args.get("path", "."))

        result = await self.tools_service.list_directory(path)
        return result.content if result.success else result.error

    async def _tool_exists(self, args: Dict[str, Any]) -> str:
        """Exists 工具"""
        path = self._resolve_path(args.get("path", ""))

        result = await self.tools_service.exists(path)
        return result.content if result.success else result.error

    async def _tool_get_file_info(self, args: Dict[str, Any]) -> str:
        """GetFileInfo 工具"""
        path = self._resolve_path(args.get("path", ""))

        result = await self.tools_service.get_file_info(path)
        return result.content if result.success else result.error

    # ==================== 原有方法（保留兼容性） ====================

    async def execute(self, task: Dict[str, Any]) -> str:
        """执行任务 - 同步接口"""
        user_message = task.get("description", task.get("message", ""))
        return await self.think(user_message)

    def update_status(self, status: str) -> None:
        """更新Agent状态"""
        try:
            self.status = AgentStatus(status)
        except ValueError:
            self.status = AgentStatus.IDLE

    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        info = super().get_info()
        info["work_directory"] = self.work_directory
        info["tool_usage_count"] = len(self.tool_usage_history)
        return info

    def save_memory(self, name: str, content: str, memory_type: str = "user", description: str = "") -> bool:
        """保存记忆"""
        return self.memory_service.save_memory(name, content, memory_type, description)

    def load_memories(self, memory_type: str = None) -> List[Dict[str, Any]]:
        """加载记忆"""
        return self.memory_service.load_memory(memory_type)


# 便捷函数
async def create_agent(work_directory: str = None) -> MainAgent:
    """创建 MainAgent 实例"""
    return MainAgent(work_directory=work_directory)
