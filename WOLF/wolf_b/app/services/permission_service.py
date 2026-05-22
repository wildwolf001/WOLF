"""
文件权限服务 - 完全参照 cc-haha 的权限系统
基于规则（Rule-based）的权限检查，使用 gitignore 风格模式匹配

主要功能：
1. checkReadPermissionForTool() - 读取权限检查
2. checkWritePermissionForTool() - 写入权限检查
3. matchingRuleForInput() - 规则匹配引擎
4. 危险文件保护 (.git/, .bashrc, .vscode/ 等)
5. 工作目录自动允许
6. 内部路径自动放行
"""
import os
import re
from pathlib import Path, PureWindowsPath
from typing import Optional, List, Set, Dict, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import fnmatch

from app.services.permission_context import ToolPermissionContext, AdditionalWorkingDirectory, PermissionMode, get_empty_permission_context


# =============================================================================
# 常量定义 - 参照 cc-haha 的危险文件/目录列表
# =============================================================================

DANGEROUS_FILES = [
    '.gitconfig',
    '.gitmodules',
    '.bashrc',
    '.bash_profile',
    '.zshrc',
    '.zprofile',
    '.profile',
    '.ripgreprc',
    '.mcp.json',
    '.claude.json',
]

DANGEROUS_DIRECTORIES = [
    '.git',
    '.vscode',
    '.idea',
    '.claude',
]

# 内部路径白名单（不需要权限检查）
INTERNAL_PATHS = [
    'session-memory',
    'plans',
    'tool-results',
]


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class FilePermissionRule:
    """权限规则"""
    pattern: str
    action: str  # "read" or "edit"
    behavior: str  # "allow", "deny", "ask"
    source: str = "session"  # "session", "userSettings", "projectSettings", etc.


@dataclass
class WorkingDirectory:
    """工作目录条目"""
    path: str
    source: str


class PermissionUpdateType(str, Enum):
    """权限更新类型"""
    ADD_DIRECTORIES = "addDirectories"
    ADD_RULES = "addRules"
    SET_MODE = "setMode"


class PermissionUpdateDestination(str, Enum):
    """权限更新目标"""
    USER_SETTINGS = "userSettings"
    PROJECT_SETTINGS = "projectSettings"
    LOCAL_SETTINGS = "localSettings"
    SESSION = "session"
    CLI_ARG = "cliArg"


@dataclass
class PermissionUpdate:
    """权限更新请求"""
    type: PermissionUpdateType
    destination: PermissionUpdateDestination
    directories: List[str] = field(default_factory=list)
    rules: List[dict] = field(default_factory=list)
    mode: Optional[str] = None


@dataclass
class PermissionSuggestion:
    """权限建议"""
    type: str
    message: str
    directories: List[str] = field(default_factory=list)
    destination: PermissionUpdateDestination = PermissionUpdateDestination.SESSION


@dataclass
class PermissionDecision:
    """权限决策结果"""
    behavior: str  # "allow", "deny", "ask", "passthrough"
    message: str = ""
    suggestions: List[PermissionUpdate] = field(default_factory=list)
    decision_reason: dict = field(default_factory=dict)


# =============================================================================
# 路径工具函数 - 参照 cc-haha
# =============================================================================

def normalize_case_for_comparison(path: str) -> str:
    """
    规范化路径进行大小写比较
    防止在大小写不敏感的文件系统上通过混合大小写绕过安全检查
    """
    return path.lower()


def expand_path(path: str) -> str:
    """展开路径，处理 ~ 和 ..."""
    if not path:
        return path

    # 处理 Windows 驱动器路径 (如 E:\)
    is_windows_drive = len(path) >= 2 and path[1] == ':'

    if is_windows_drive:
        # 对 Windows 驱动器路径，只做基本规范化
        normalized = ''
        for c in path:
            if ord(c) >= 32 or c in '\t\n\r\\/:':
                normalized += c
        normalized = normalized.replace('/', '\\')
        if len(normalized) > 3:
            normalized = normalized.rstrip('\\')
        return os.path.normpath(normalized) if len(normalized) > 3 else normalized

    # 处理 ~
    if path.startswith('~'):
        path = os.path.expanduser(path)

    # 处理 ..
    return os.path.normpath(os.path.abspath(path))


def get_directory_for_path(path: str) -> str:
    """获取路径的父目录"""
    return os.path.dirname(expand_path(path))


def contains_path_traversal(path: str) -> bool:
    """检查路径是否包含 .. 遍历"""
    return '..' in path.split(os.sep)


def relative_path(from_path: str, to_path: str) -> str:
    """
    计算相对路径，返回 POSIX 风格路径
    跨平台兼容
    """
    # Windows 转 POSIX
    if os.sep == '\\':
        from_path = from_path.replace('\\', '/')
        to_path = to_path.replace('\\', '/')

    # 找到共同前缀
    from_parts = from_path.rstrip('/').split('/')
    to_parts = to_path.rstrip('/').split('/')

    # 找到共同前缀长度
    common_len = 0
    for i in range(min(len(from_parts), len(to_parts))):
        if from_parts[i].lower() == to_parts[i].lower():
            common_len += 1
        else:
            break

    # 构建相对路径
    up_count = len(from_parts) - common_len
    relative = '/'.join(['..'] * up_count + to_parts[common_len:])

    return relative if relative else '.'


def path_in_working_path(path: str, working_path: str) -> bool:
    """
    检查路径是否在特定工作目录内 - 参照 cc 的 pathInWorkingPath
    """
    if not path or not working_path:
        return False

    absolute_path = expand_path(path)
    absolute_working_path = expand_path(working_path)

    # 路径等于工作目录
    if absolute_path == absolute_working_path:
        return True

    # 大小写规范化比较
    case_normalized_path = normalize_case_for_comparison(absolute_path)
    case_normalized_working_path = normalize_case_for_comparison(absolute_working_path)

    # 使用相对路径检查
    relative = relative_path(case_normalized_working_path, case_normalized_path)

    # 相同路径
    if relative == '' or relative == '.':
        return True

    # 检查是否有 .. 遍历
    if contains_path_traversal(relative):
        return False

    # 相对路径不是绝对路径，说明在工作目录内
    return not relative.startswith('/')


def get_paths_for_permission_check(path: str) -> List[str]:
    """
    获取要检查的路径列表（包含原始路径和解析后的符号链接路径）
    参照 cc 的 getPathsForPermissionCheck
    """
    paths = [expand_path(path)]

    try:
        real = os.path.realpath(path)
        real_expanded = expand_path(real)
        if real_expanded not in paths:
            paths.append(real_expanded)
    except Exception:
        pass

    return paths


def has_suspicious_windows_path_pattern(path: str) -> bool:
    """
    检测可疑的 Windows 路径模式
    参照 cc 的 hasSuspiciousWindowsPathPattern
    """
    # NTFS Alternate Data Streams (如 file.txt::$DATA)
    colon_index = path.index(':') if ':' in path else -1
    if colon_index > 2:  # 跳过驱动器字母后的冒号
        return True

    # 8.3 短名称 (如 GIT~1)
    if '~' in path and re.search(r'~\d', path):
        return True

    # 长路径前缀 (如 \\?\C:\...)
    if path.startswith('\\\\?\\') or path.startswith('\\\\.\\') or path.startswith('//?/') or path.startswith('//./'):
        return True

    # 尾部点和空格
    if re.search(r'[.\s]+$', path):
        return True

    # DOS 设备名 (如 .git.CON)
    if re.search(r'\.(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', path, re.IGNORECASE):
        return True

    # 三个或更多连续点
    if re.search(r'(^|\/|\\)\.{3,}(\/|\\|$)', path):
        return True

    # UNC 路径
    if path.startswith('\\\\') or path.startswith('//'):
        return True

    return False


def is_dangerous_file_path(path: str) -> bool:
    """
    检查路径是否为危险文件
    参照 cc 的 isDangerousFilePathToAutoEdit
    """
    absolute_path = expand_path(path)
    path_segments = absolute_path.split(os.sep)
    filename = path_segments[-1] if path_segments else ""

    # 检查危险目录
    for segment in path_segments:
        normalized_segment = normalize_case_for_comparison(segment)
        for dangerous_dir in DANGEROUS_DIRECTORIES:
            if normalized_segment == dangerous_dir.lower():
                # 特殊处理 .claude/worktrees/
                if dangerous_dir == '.claude':
                    idx = path_segments.index(segment)
                    next_segment = path_segments[idx + 1] if idx + 1 < len(path_segments) else None
                    if next_segment and normalize_case_for_comparison(next_segment) == 'worktrees':
                        continue
                return True

    # 检查危险文件名
    if filename:
        normalized_filename = normalize_case_for_comparison(filename)
        for dangerous_file in DANGEROUS_FILES:
            if normalized_filename == dangerous_file.lower():
                return True

    return False


def is_claude_settings_path(path: str) -> bool:
    """检查路径是否为 Claude 设置文件"""
    absolute_path = expand_path(path)
    normalized_path = normalize_case_for_comparison(absolute_path)

    sep = os.sep
    if normalized_path.endswith(f'{sep}.claude{sep}settings.json') or \
       normalized_path.endswith(f'{sep}.claude{sep}settings.local.json'):
        return True

    return False


def is_internal_writable_path(path: str) -> bool:
    """
    检查路径是否为内部可写路径（plan files, scratchpad 等）
    不需要权限检查
    """
    absolute_path = expand_path(path)
    normalized_path = normalize_case_for_comparison(absolute_path)

    # Plan files
    # 简单检查是否在 .claude 目录下
    if '.claude' + os.sep in normalized_path:
        return True

    return False


def is_internal_readable_path(path: str) -> bool:
    """
    检查路径是否为内部可读路径（session-memory, plans, tool-results 等）
    不需要权限检查
    """
    return is_internal_writable_path(path)


# =============================================================================
# 规则匹配引擎 - 参照 cc-haha 的 matchingRuleForInput
# =============================================================================

def pattern_with_root(pattern: str, source: str) -> Tuple[str, Optional[str]]:
    """
    处理模式前缀，返回 (relative_pattern, root)
    参照 cc 的 patternWithRoot
    """
    # 模式以 // 开头
    if pattern.startswith('//'):
        pattern_without_double_slash = pattern[1:]
        # Windows POSIX 风格路径 (如 //c/Users/...)
        if len(pattern_without_double_slash) >= 3 and pattern_without_double_slash[1] == '/':
            drive_letter = pattern_without_double_slash[0].upper()
            return (pattern_without_double_slash[2:], f"{drive_letter}:\\")
        return (pattern_without_double_slash, '/')

    # 模式以 ~ 开头
    if pattern.startswith('~' + os.sep) or pattern.startswith('~/'):
        home = os.path.expanduser('~')
        return (pattern[2:], home)

    # 模式以 / 开头
    if pattern.startswith('/'):
        return (pattern[1:], os.getcwd())

    # 无前缀模式 - 在当前目录匹配
    return (pattern, None)


def get_patterns_by_root(
    context: ToolPermissionContext,
    tool_type: str,  # "read" or "edit"
    behavior: str  # "allow", "deny", "ask"
) -> Dict[Optional[str], Dict[str, FilePermissionRule]]:
    """
    按 root 分组获取规则
    参照 cc 的 getPatternsByRoot
    """
    patterns_by_root: Dict[Optional[str], Dict[str, FilePermissionRule]] = {}

    # 获取所有规则
    rules = _get_rules_for_tool(context, tool_type, behavior)

    for rule in rules:
        relative_pattern, root = pattern_with_root(rule.pattern, rule.source)

        if root not in patterns_by_root:
            patterns_by_root[root] = {}

        patterns_by_root[root][relative_pattern] = rule

    return patterns_by_root


def _get_rules_for_tool(
    context: ToolPermissionContext,
    tool_type: str,
    behavior: str
) -> List[FilePermissionRule]:
    """获取指定工具类型和行为的规则"""
    rules = []

    # 从 always_allow_rules 获取
    if behavior == 'allow':
        for source, source_rules in context.always_allow_rules.items():
            for rule_dict in source_rules:
                if isinstance(rule_dict, dict):
                    rules.append(FilePermissionRule(
                        pattern=rule_dict.get('pattern', ''),
                        action=tool_type,
                        behavior='allow',
                        source=source
                    ))

    # 从 always_deny_rules 获取
    if behavior == 'deny':
        for source, source_rules in context.always_deny_rules.items():
            for rule_dict in source_rules:
                if isinstance(rule_dict, dict):
                    rules.append(FilePermissionRule(
                        pattern=rule_dict.get('pattern', ''),
                        action=tool_type,
                        behavior='deny',
                        source=source
                    ))

    # 从 always_ask_rules 获取
    if behavior == 'ask':
        for source, source_rules in context.always_ask_rules.items():
            for rule_dict in source_rules:
                if isinstance(rule_dict, dict):
                    rules.append(FilePermissionRule(
                        pattern=rule_dict.get('pattern', ''),
                        action=tool_type,
                        behavior='ask',
                        source=source
                    ))

    return rules


def matching_rule_for_input(
    path: str,
    context: ToolPermissionContext,
    tool_type: str,  # "read" or "edit"
    behavior: str  # "allow", "deny", "ask"
) -> Optional[FilePermissionRule]:
    """
    检查路径是否匹配特定工具类型和行为的规则
    参照 cc 的 matchingRuleForInput
    """
    file_absolute_path = expand_path(path)

    # Windows 转 POSIX 风格以便模式匹配
    if os.sep == '\\' and '\\' in file_absolute_path:
        file_absolute_path = file_absolute_path.replace('\\', '/')

    patterns_by_root = get_patterns_by_root(context, tool_type, behavior)

    for root, pattern_map in patterns_by_root.items():
        # 构建忽略模式
        patterns = list(pattern_map.keys())

        # 简化 /** 后缀
        adjusted_patterns = []
        for p in patterns:
            if p.endswith('/**'):
                adjusted_patterns.append(p[:-3])
            else:
                adjusted_patterns.append(p)

        # 使用 fnmatch 进行简单模式匹配
        for pattern in adjusted_patterns:
            # 检查是否匹配
            if _path_matches_pattern(file_absolute_path, root, pattern):
                return pattern_map[pattern if not pattern.endswith('/**') else pattern + '/**']

    return None


def _path_matches_pattern(path: str, root: Optional[str], pattern: str) -> bool:
    """
    检查路径是否匹配模式
    简单的 glob 风格匹配
    """
    # 确定要匹配的基准路径
    if root:
        match_base = root
    else:
        match_base = os.getcwd()

    # 计算相对路径
    relative = relative_path(match_base, path)

    # 使用 fnmatch 进行模式匹配
    # 简单的 glob 模式支持：** 匹配任意目录，* 匹配任意字符
    if '**' in pattern:
        # 处理 ** 模式
        pattern_parts = pattern.split('**')
        relative_parts = relative.split('/')

        pattern_idx = 0
        relative_idx = 0

        while pattern_idx < len(pattern_parts) and relative_idx < len(relative_parts):
            if pattern_parts[pattern_idx]:
                if not fnmatch.fnmatch(relative_parts[relative_idx], pattern_parts[pattern_idx]):
                    return False
            pattern_idx += 1
            relative_idx += 1

        return True
    else:
        return fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path, pattern)


# =============================================================================
# 权限检查函数 - 参照 cc-haha 的 checkReadPermissionForTool / checkWritePermissionForTool
# =============================================================================

def check_read_permission_for_tool(
    tool_name: str,
    path: str,
    context: ToolPermissionContext
) -> PermissionDecision:
    """
    检查读取权限 - 参照 cc 的 checkReadPermissionForTool

    流程：
    1. 防御性检查（UNC 路径、Windows 可疑模式）
    2. READ 特定 deny 规则
    3. READ 特定 ask 规则
    4. 编辑权限隐含读取权限
    5. 工作目录内允许
    6. 内部路径允许
    7. allow 规则
    8. 默认询问
    """
    if not path:
        return PermissionDecision(
            behavior='ask',
            message='Path is empty'
        )

    paths_to_check = get_paths_for_permission_check(path)

    # 1. 防御性检查 - UNC 路径
    for path_to_check in paths_to_check:
        if path_to_check.startswith('\\\\') or path_to_check.startswith('//'):
            return PermissionDecision(
                behavior='ask',
                message=f'Reading from UNC path is not allowed: {path}',
                decision_reason={'type': 'UNC path', 'reason': 'UNC path detected'}
            )

    # 2. 防御性检查 - Windows 可疑模式
    for path_to_check in paths_to_check:
        if has_suspicious_windows_path_pattern(path_to_check):
            return PermissionDecision(
                behavior='ask',
                message=f'Path contains suspicious Windows path pattern: {path}',
                decision_reason={'type': 'Windows pattern', 'reason': 'Suspicious Windows path pattern'}
            )

    # 3. READ 特定 deny 规则
    for path_to_check in paths_to_check:
        deny_rule = matching_rule_for_input(path_to_check, context, 'read', 'deny')
        if deny_rule:
            return PermissionDecision(
                behavior='deny',
                message=f'Reading from {path} has been denied',
                decision_reason={'type': 'rule', 'rule': deny_rule}
            )

    # 4. READ 特定 ask 规则
    for path_to_check in paths_to_check:
        ask_rule = matching_rule_for_input(path_to_check, context, 'read', 'ask')
        if ask_rule:
            return PermissionDecision(
                behavior='ask',
                message=f'Claude requested permissions to read from {path}, but you haven\'t granted it yet.',
                decision_reason={'type': 'rule', 'rule': ask_rule}
            )

    # 5. 编辑权限隐含读取权限
    write_decision = check_write_permission_for_tool(tool_name, path, context, paths_to_check)
    if write_decision.behavior == 'allow':
        return write_decision

    # 6. 工作目录内允许
    if path_in_allowed_working_path(path, context):
        return PermissionDecision(
            behavior='allow',
            message='',
            decision_reason={'type': 'mode', 'mode': 'default'}
        )

    # 7. 内部路径允许
    if is_internal_readable_path(path):
        return PermissionDecision(
            behavior='allow',
            message='',
            decision_reason={'type': 'internal', 'reason': 'Internal path allowed'}
        )

    # 8. allow 规则
    for path_to_check in paths_to_check:
        allow_rule = matching_rule_for_input(path_to_check, context, 'read', 'allow')
        if allow_rule:
            return PermissionDecision(
                behavior='allow',
                message='',
                decision_reason={'type': 'rule', 'rule': allow_rule}
            )

    # 8. 默认允许（放权模式：不需要每次询问用户）
    return PermissionDecision(
        behavior='allow',
        message='Allowed (default permit mode)',
        decision_reason={'type': 'default', 'mode': 'permissive'}
    )


def check_write_permission_for_tool(
    tool_name: str,
    path: str,
    context: ToolPermissionContext,
    precomputed_paths_to_check: List[str] = None
) -> PermissionDecision:
    """
    检查写入权限 - 参照 cc 的 checkWritePermissionForTool

    流程：
    1. deny 规则
    2. 内部可编辑路径
    3. .claude/** allow 规则
    4. 安全检查（危险文件、Windows 模式）
    5. ask 规则
    6. acceptEdits 模式下工作目录内允许
    7. allow 规则
    8. 默认询问
    """
    if not path:
        return PermissionDecision(
            behavior='ask',
            message='Path is empty'
        )

    paths_to_check = precomputed_paths_to_check or get_paths_for_permission_check(path)

    # 1. deny 规则
    for path_to_check in paths_to_check:
        deny_rule = matching_rule_for_input(path_to_check, context, 'edit', 'deny')
        if deny_rule:
            return PermissionDecision(
                behavior='deny',
                message=f'Editing {path} has been denied',
                decision_reason={'type': 'rule', 'rule': deny_rule}
            )

    # 2. 内部可编辑路径
    if is_internal_writable_path(path):
        return PermissionDecision(
            behavior='allow',
            message='',
            decision_reason={'type': 'internal', 'reason': 'Internal path allowed'}
        )

    # 3. .claude/** allow 规则（特殊处理）
    claude_folder_allow_rule = _check_claude_folder_allow_rule(path, context)
    if claude_folder_allow_rule:
        return PermissionDecision(
            behavior='allow',
            message='',
            decision_reason={'type': 'rule', 'rule': claude_folder_allow_rule}
        )

    # 4. 安全检查
    safety_result = _check_path_safety_for_auto_edit(path, paths_to_check)
    if not safety_result['safe']:
        return PermissionDecision(
            behavior='ask',
            message=safety_result['message'],
            suggestions=_get_safety_suggestions(path, context, paths_to_check),
            decision_reason={'type': 'safetyCheck', 'reason': safety_result['message']}
        )

    # 5. ask 规则
    for path_to_check in paths_to_check:
        ask_rule = matching_rule_for_input(path_to_check, context, 'edit', 'ask')
        if ask_rule:
            return PermissionDecision(
                behavior='ask',
                message=f'Claude requested permissions to write to {path}, but you haven\'t granted it yet.',
                decision_reason={'type': 'rule', 'rule': ask_rule}
            )

    # 6. acceptEdits 模式下工作目录内允许
    if context.mode == PermissionMode.ACCEPT_EDITS:
        if path_in_allowed_working_path(path, context):
            return PermissionDecision(
                behavior='allow',
                message='',
                decision_reason={'type': 'mode', 'mode': 'acceptEdits'}
            )

    # 7. allow 规则
    for path_to_check in paths_to_check:
        allow_rule = matching_rule_for_input(path_to_check, context, 'edit', 'allow')
        if allow_rule:
            return PermissionDecision(
                behavior='allow',
                message='',
                decision_reason={'type': 'rule', 'rule': allow_rule}
            )

    # 8. 默认允许（放权模式：不需要每次询问用户）
    # 高危操作在 FilePermissionService.can_execute() 中检查
    return PermissionDecision(
        behavior='allow',
        message='Allowed (default permit mode)',
        decision_reason={'type': 'default', 'mode': 'permissive'}
    )


def _check_claude_folder_allow_rule(path: str, context: ToolPermissionContext) -> Optional[FilePermissionRule]:
    """
    检查 .claude/** allow 规则
    只有 session 级别的规则可以绕过安全检查
    """
    # 暂时简化，不实现完整版本
    return None


def _check_path_safety_for_auto_edit(path: str, paths_to_check: List[str]) -> Dict[str, Any]:
    """
    检查路径安全性（危险文件保护等）
    参照 cc 的 checkPathSafetyForAutoEdit
    """
    for path_to_check in paths_to_check:
        # Windows 可疑模式
        if has_suspicious_windows_path_pattern(path_to_check):
            return {
                'safe': False,
                'message': f'Path contains suspicious Windows path pattern: {path}'
            }

        # Claude 配置文件
        if is_claude_settings_path(path_to_check):
            return {
                'safe': False,
                'message': f'Editing {path} is not allowed (Claude settings)'
            }

        # 危险文件
        if is_dangerous_file_path(path_to_check):
            return {
                'safe': False,
                'message': f'Editing {path} is not allowed (sensitive file)'
            }

    return {'safe': True}


def _get_safety_suggestions(path: str, context: ToolPermissionContext, paths_to_check: List[str]) -> List[PermissionUpdate]:
    """获取安全检查失败的建议"""
    suggestions = []

    # 检查是否在 .claude/skills/ 下，如果是，生成窄化规则建议
    # 暂时简化，只生成 addDirectories 建议
    dir_path = get_directory_for_path(path)
    dirs_to_add = [expand_path(dir_path)]

    suggestions.append(PermissionUpdate(
        type=PermissionUpdateType.ADD_DIRECTORIES,
        destination=PermissionUpdateDestination.SESSION,
        directories=dirs_to_add
    ))

    return suggestions


def path_in_allowed_working_path(path: str, context: ToolPermissionContext) -> bool:
    """
    检查路径是否在允许的工作目录内 - 参照 cc 的 pathInAllowedWorkingPath
    """
    paths_to_check = get_paths_for_permission_check(path)

    # 获取所有工作目录
    working_paths = all_working_directories_for_context(context)

    # 所有路径必须在工作目录内
    return all(
        any(path_in_working_path(p, wp) for wp in working_paths)
        for p in paths_to_check
    )


def all_working_directories_for_context(context: ToolPermissionContext) -> List[str]:
    """
    获取权限上下文中的所有工作目录
    参照 cc 的 allWorkingDirectories
    """
    dirs = []

    # 添加 originalCwd（如果存在）
    try:
        from app.core.runtime_config import runtime_config
        work_dirs = runtime_config.get_additional_working_directories()
        if work_dirs:
            dirs.extend(work_dirs.keys())
    except Exception:
        pass

    # 添加 additional_working_directories
    dirs.extend(context.additional_working_directories.keys())

    return dirs


def generate_suggestions(
    path: str,
    operation_type: str,  # "read", "write", "create"
    context: ToolPermissionContext,
    precomputed_paths_to_check: List[str] = None
) -> List[PermissionUpdate]:
    """
    生成权限建议 - 参照 cc 的 generateSuggestions
    """
    paths_to_check = precomputed_paths_to_check or get_paths_for_permission_check(path)

    suggestions = []
    is_outside_working_dir = not path_in_allowed_working_path(path, context)

    if operation_type == 'read' and is_outside_working_dir:
        # 读取操作在工作目录外，添加 Read 规则
        dir_path = get_directory_for_path(path)
        dirs_to_add = [expand_path(dir_path)]

        for dir_to_add in dirs_to_add:
            suggestions.append(PermissionUpdate(
                type=PermissionUpdateType.ADD_RULES,
                destination=PermissionUpdateDestination.SESSION,
                rules=[{
                    'toolName': 'Read',
                    'ruleContent': dir_to_add + '/**',
                    'behavior': 'allow'
                }]
            ))

        return suggestions

    # 写入操作
    should_suggest_accept_edits = context.mode in [PermissionMode.DEFAULT, PermissionMode.PLAN]

    if operation_type in ['write', 'create']:
        updates = []

        if should_suggest_accept_edits:
            updates.append(PermissionUpdate(
                type=PermissionUpdateType.SET_MODE,
                destination=PermissionUpdateDestination.SESSION,
                mode='acceptEdits'
            ))

        if is_outside_working_dir:
            dir_path = get_directory_for_path(path)
            dirs_to_add = [expand_path(dir_path)]

            updates.append(PermissionUpdate(
                type=PermissionUpdateType.ADD_DIRECTORIES,
                destination=PermissionUpdateDestination.SESSION,
                directories=dirs_to_add
            ))

        return updates

    # 默认只建议 setMode
    if should_suggest_accept_edits:
        return [PermissionUpdate(
            type=PermissionUpdateType.SET_MODE,
            destination=PermissionUpdateDestination.SESSION,
            mode='acceptEdits'
        )]

    return []


# =============================================================================
# FilePermissionService 类 - 保留原有接口，核心实现调用新函数
# =============================================================================

class FilePermissionService:
    """
    文件访问权限服务
    保留原有接口，核心逻辑委托给新函数
    """

    def __init__(self):
        self.rules: List[FilePermissionRule] = []
        self.allowed_base_paths: Set[str] = set()
        self.denied_paths: Set[str] = set()
        self.additional_working_directories: Dict[str, WorkingDirectory] = {}
        self._original_cwd: Optional[str] = None

    def set_original_cwd(self, cwd: str):
        """设置原始工作目录"""
        self._original_cwd = os.path.abspath(cwd)
        if self._original_cwd not in self.allowed_base_paths:
            self.allowed_base_paths.add(self._original_cwd)

    def get_all_working_directories(self) -> List[str]:
        """获取所有工作目录"""
        dirs = []
        if self._original_cwd:
            dirs.append(self._original_cwd)
        dirs.extend(self.additional_working_directories.keys())
        dirs.extend(self.allowed_base_paths)
        return dirs

    def sync_from_runtime_config(self):
        """从 runtime_config 同步工作目录"""
        try:
            from app.core.runtime_config import runtime_config
            self.additional_working_directories.clear()
            for path, source in runtime_config.additional_working_directories.items():
                self.additional_working_directories[path] = WorkingDirectory(
                    path=path,
                    source=source
                )
        except Exception:
            pass

    def get_permission_context(self) -> ToolPermissionContext:
        """获取权限上下文"""
        context = get_empty_permission_context()

        # 设置模式
        try:
            from app.services.permission_service import interactive_permission_service
            mode = interactive_permission_service.get_mode()
            context.mode = PermissionMode(mode.value if hasattr(mode, 'value') else str(mode))
        except Exception:
            context.mode = PermissionMode.DEFAULT

        # 添加工作目录
        if self._original_cwd:
            context.add_working_directory(self._original_cwd, "originalCwd")

        for path, wd in self.additional_working_directories.items():
            context.add_working_directory(path, wd.source)

        for base_path in self.allowed_base_paths:
            if base_path not in context.additional_working_directories:
                context.add_working_directory(base_path, "allowedBasePath")

        return context

    def all_working_directories(self) -> Set[str]:
        """获取所有工作目录的集合"""
        dirs = set()
        if self._original_cwd:
            dirs.add(self._original_cwd)
        dirs.update(self.additional_working_directories.keys())
        return dirs

    def add_working_directory(self, path: str, source: str = "session") -> bool:
        """添加工作目录"""
        if not path:
            return False

        abs_path = os.path.abspath(path)
        normalized = expand_path(abs_path)

        # 检查是否已经在任何工作目录的子目录内
        for wd in self.get_all_working_directories():
            if path_in_working_path(normalized, wd):
                return True

        # 添加到额外工作目录
        self.additional_working_directories[normalized] = WorkingDirectory(
            path=normalized,
            source=source
        )

        return True

    def remove_working_directory(self, path: str) -> bool:
        """移除工作目录"""
        if not path:
            return False

        normalized = os.path.abspath(path)
        if normalized in self.additional_working_directories:
            del self.additional_working_directories[normalized]
            return True
        return False

    def path_in_allowed_working_path(self, path: str) -> bool:
        """
        检查路径是否可访问（保持向后兼容）
        """
        if not path:
            return False

        normalized = expand_path(path)

        # 只要路径存在就允许访问（cc-haha 模式）
        if os.path.exists(normalized):
            return True

        # 父目录存在，自动添加并允许
        parent = os.path.dirname(normalized)
        if os.path.exists(parent):
            if parent not in self.additional_working_directories:
                self.add_working_directory(parent, "auto_added")
            return True

        # 尝试符号链接解析
        try:
            real_path = os.path.realpath(normalized)
            if os.path.exists(real_path):
                return True
        except Exception:
            pass

        return False

    def check_permission(
        self,
        path: str,
        action: str = "read"
    ) -> Tuple[bool, str]:
        """
        检查权限（保持向后兼容）
        使用新的权限检查逻辑
        """
        context = self.get_permission_context()

        if action == "read":
            decision = check_read_permission_for_tool("Read", path, context)
        else:
            decision = check_write_permission_for_tool("Write", path, context)

        if decision.behavior == 'allow':
            return True, "Allowed"
        elif decision.behavior == 'deny':
            return False, decision.message
        else:
            # ask - 需要用户确认
            return False, decision.message

    def validate_path(self, path: str) -> Tuple[bool, str, str]:
        """
        验证路径安全性（保持向后兼容）
        使用新的权限检查逻辑
        """
        if not path:
            return False, "Path is empty", ""

        # 检查路径遍历字符
        if ".." in path:
            return False, "Invalid path characters detected", ""

        normalized = expand_path(path)

        # 使用新的权限检查
        context = self.get_permission_context()
        decision = check_read_permission_for_tool("Read", path, context)

        if decision.behavior == 'allow':
            return True, "", normalized
        else:
            return False, decision.message, ""

    def generate_suggestions(self, path: str, action: str = "read") -> List[PermissionSuggestion]:
        """生成权限建议（保持向后兼容）"""
        context = self.get_permission_context()

        if action == "read":
            decision = check_read_permission_for_tool("Read", path, context)
        else:
            decision = check_write_permission_for_tool("Write", path, context)

        suggestions = []
        for update in decision.suggestions:
            if update.type == PermissionUpdateType.ADD_DIRECTORIES:
                suggestions.append(PermissionSuggestion(
                    type="addDirectories",
                    message=f"Add directories: {', '.join(update.directories)}",
                    directories=update.directories,
                    destination=update.destination
                ))
            elif update.type == PermissionUpdateType.SET_MODE:
                suggestions.append(PermissionSuggestion(
                    type="enableMode",
                    message=f"Enable mode: {update.mode}",
                    destination=update.destination
                ))

        return suggestions

    def add_rule(self, pattern: str, action: str = "read", allow: bool = True):
        """添加权限规则（保持向后兼容）"""
        self.rules.append(FilePermissionRule(
            pattern=pattern,
            action=action,
            behavior='allow' if allow else 'deny',
            source='session'
        ))

    def set_allowed_base_paths(self, paths: List[str]):
        """设置允许的基础路径"""
        valid_paths = set()
        for p in paths:
            abs_path = os.path.abspath(p)
            if os.path.exists(abs_path):
                valid_paths.add(abs_path)
        self.allowed_base_paths = valid_paths

    def check_and_add_path(self, path: str) -> bool:
        """
        检查路径并在需要时自动添加父目录
        """
        if not path:
            return False

        normalized = expand_path(path)

        if os.path.exists(normalized):
            if os.path.isfile(normalized):
                self.add_working_directory(os.path.dirname(normalized), "auto_added")
            else:
                self.add_working_directory(normalized, "auto_added")
            return True

        # 路径不存在，尝试添加父目录
        parent = os.path.dirname(normalized)
        if os.path.exists(parent):
            self.add_working_directory(parent, "auto_added")
            return True

        return False

    def list_allowed_directories(self) -> List[dict]:
        """列出所有允许访问的目录"""
        result = []
        for base_path in self.allowed_base_paths:
            exists = os.path.exists(base_path)
            is_dir = os.path.isdir(base_path) if exists else False
            result.append({
                "path": base_path,
                "exists": exists,
                "is_directory": is_dir,
                "writable": os.access(base_path, os.W_OK) if exists else False
            })
        for wd_path, wd_info in self.additional_working_directories.items():
            if wd_path not in self.allowed_base_paths:
                exists = os.path.exists(wd_path)
                result.append({
                    "path": wd_path,
                    "source": wd_info.source,
                    "exists": exists,
                    "is_directory": os.path.isdir(wd_path) if exists else False,
                    "writable": os.access(wd_path, os.W_OK) if exists else False
                })
        return result


# =============================================================================
# 全局单例
# =============================================================================

_permission_service: Optional[FilePermissionService] = None


def get_permission_service() -> FilePermissionService:
    """获取权限服务单例"""
    global _permission_service
    if _permission_service is None:
        _permission_service = FilePermissionService()
    return _permission_service


# 保留 permission_service 别名以保持向后兼容
permission_service = get_permission_service()


# 别名 - 保持向后兼容
PermissionAction = None  # Deprecated, not used in new implementation


# =============================================================================
# 拒绝追踪（保持向后兼容）
# =============================================================================

class DenialTrackingState:
    """拒绝追踪状态"""

    def __init__(self):
        self._denial_count = 0
        self._last_denial_time = 0

    def record_denial(self):
        """记录一次拒绝"""
        self._denial_count += 1
        import time
        self._last_denial_time = time.time()

    def record_success(self):
        """记录一次成功"""
        self._denial_count = 0

    def should_prompt(self) -> bool:
        """是否应该提示用户"""
        return self._denial_count >= 3


_denial_tracker: Optional[DenialTrackingState] = None


def get_denial_tracker() -> DenialTrackingState:
    """获取拒绝追踪器单例"""
    global _denial_tracker
    if _denial_tracker is None:
        _denial_tracker = DenialTrackingState()
    return _denial_tracker


# =============================================================================
# 交互式权限服务（保持向后兼容）
# =============================================================================

class InteractivePermissionService:
    """交互式权限服务"""

    def __init__(self):
        self._mode = PermissionMode.DEFAULT

    def get_mode(self) -> PermissionMode:
        """获取当前模式"""
        return self._mode

    def set_mode(self, mode: PermissionMode):
        """设置模式"""
        self._mode = mode


_interactive_permission_service: Optional[InteractivePermissionService] = None


def get_interactive_permission_service() -> InteractivePermissionService:
    """获取交互式权限服务单例"""
    global _interactive_permission_service
    if _interactive_permission_service is None:
        _interactive_permission_service = InteractivePermissionService()
    return _interactive_permission_service


# 别名
interactive_permission_service = get_interactive_permission_service()


# =============================================================================
# 初始化函数（保持向后兼容）
# =============================================================================

def init_permission_service():
    """初始化权限服务"""
    global _permission_service, _interactive_permission_service, _denial_tracker

    _permission_service = FilePermissionService()
    _interactive_permission_service = InteractivePermissionService()
    _denial_tracker = DenialTrackingState()

    # 从 runtime_config 同步
    _permission_service.sync_from_runtime_config()