"""
Memory System Package
统一记忆系统入口 (LLM-driven extraction + session bridging)

代码模块位置: app/memory/
记忆数据保存路径: 由 runtime_config.local_storage_path/memory 决定
"""

from .types import (
    MemoryTypeEnum,
    MemoryEntry,
    MEMORY_TYPES,
    parse_memory_type,
    MEMORY_TYPE_SPECS,
    WHAT_NOT_TO_SAVE,
    WHEN_TO_ACCESS_MEMORIES,
    MEMORY_DRIFT_CAVEAT,
    TRUSTING_RECALL_SECTION,
    MEMORY_FRONTMATTER_EXAMPLE,
    ENTRYPOINT_NAME,
    MAX_ENTRYPOINT_LINES,
    MAX_ENTRYPOINT_BYTES,
)

from .directory import (
    MemoryDirectory,
    get_memory_directory,
    reset_memory_directory,
    reset_memory_directory_with_config,
    DEFAULT_MEMORY_DIR,
)

from .prompt_builder import (
    MemoryPromptBuilder,
    get_memory_prompt_builder,
    build_memory_system_prompt,
)

from .search import (
    MemorySearchService,
    get_memory_search_service,
    reset_memory_search,
)

from .management import (
    MemoryManagementService,
    get_memory_management_service,
    reset_memory_management,
)

from .extraction import (
    MemoryExtractionService,
    get_memory_extraction_service,
    reset_memory_extraction,
)

from .llm_extraction import (
    LLMMemoryExtractionService,
    get_llm_extraction_service,
    reset_llm_extraction,
)

from .session_bridge import (
    SessionBridgeService,
    get_session_bridge,
    reset_session_bridge,
)

from .memory_tools import (
    register_memory_tools,
    MEMORY_READ_TOOL_NAME,
    MEMORY_WRITE_TOOL_NAME,
    MEMORY_SEARCH_TOOL_NAME,
    MEMORY_DELETE_TOOL_NAME,
    MEMORY_LIST_TOOL_NAME,
)


def setup_memory_system(memory_dir: str = None) -> MemoryDirectory:
    """
    初始化记忆系统
    在应用启动时调用

    记忆数据保存路径: E:/ai/ARG/WOLF2.0/wolf_b2/wolfdata
    """
    memory_directory = get_memory_directory(memory_dir)

    try:
        from .memory_tools import register_memory_tools
        register_memory_tools()
    except ImportError:
        pass

    return memory_directory


__all__ = [
    'MemoryTypeEnum',
    'MemoryEntry',
    'MEMORY_TYPES',
    'parse_memory_type',
    'ENTRYPOINT_NAME',
    'MAX_ENTRYPOINT_LINES',
    'MAX_ENTRYPOINT_BYTES',
    'MEMORY_TYPE_SPECS',
    'WHAT_NOT_TO_SAVE',
    'WHEN_TO_ACCESS_MEMORIES',
    'MEMORY_DRIFT_CAVEAT',
    'TRUSTING_RECALL_SECTION',
    'MEMORY_FRONTMATTER_EXAMPLE',
    'MemoryDirectory',
    'get_memory_directory',
    'reset_memory_directory',
    'reset_memory_directory_with_config',
    'DEFAULT_MEMORY_DIR',
    'MemoryPromptBuilder',
    'get_memory_prompt_builder',
    'build_memory_system_prompt',
    'MemorySearchService',
    'get_memory_search_service',
    'reset_memory_search',
    'MemoryManagementService',
    'get_memory_management_service',
    'reset_memory_management',
    'MemoryExtractionService',
    'get_memory_extraction_service',
    'reset_memory_extraction',
    'LLMMemoryExtractionService',
    'get_llm_extraction_service',
    'reset_llm_extraction',
    'SessionBridgeService',
    'get_session_bridge',
    'reset_session_bridge',
    'register_memory_tools',
    'MEMORY_READ_TOOL_NAME',
    'MEMORY_WRITE_TOOL_NAME',
    'MEMORY_SEARCH_TOOL_NAME',
    'MEMORY_DELETE_TOOL_NAME',
    'MEMORY_LIST_TOOL_NAME',
    'setup_memory_system',
]