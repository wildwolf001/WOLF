"""
SSE (Server-Sent Events) for real-time streaming responses
Dual-layer architecture:
- Layer 1: Request classification (simple file ops vs complex tasks)
- Layer 2: MainAgent for all tasks (single-agent direct execution, Claude Code style)

================================================================================
DEPRECATED: Multi-agent path (PM decomposition, get_or_create_agent) disabled
================================================================================
Complex tasks now use MainAgent.think() directly instead of PM decomposition.
"""
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import re
import uuid
from typing import AsyncGenerator
from app.services.llm_service import llm_service
from app.services.context_service import context_service, get_full_context, format_context_for_llm
from app.services.tools_service import tools_service

router = APIRouter()


def classify_request(message: str) -> dict:
    """
    Layer 1: Classify request type to determine execution path.

    Returns:
        {
            "type": "simple_file_operation" | "complex",
            "operation": "list" | "read" | "search" | "edit" | None,
            "path": detected path or None,
            "reason": explanation
        }
    """
    msg_lower = message.lower()
    msg_original = message

    # File operation keywords (indicates simple file operation)
    list_keywords = ["列出", "list files", "目录", "文件夹", "当前目录", "浏览", "有什么文件", "查看有哪些"]
    read_keywords = ["读取", "read", "打开", "查看内容", "cat "]
    search_keywords = ["搜索", "search", "查找", "grep", "包含"]
    edit_keywords = ["修改", "edit", "write", "写入", "创建"]

    # Complex intent keywords - these override file operation detection
    complex_intent_keywords = [
        "研究", "research", "分析", "analyze", "写论文", "写报告",
        "compare", "对比", "总结", "summarize", "review", "审核",
        "详细", "完整", "报告", "技术", "架构", "架构分析",
        "了解", "理解", "是什么", "做什么", "用来干嘛",
        "技术栈", "栈", "主要架构", "整体架构",
        "所有", "全部", "完整", "全面", "深入",
    ]

    is_complex_intent = any(k in msg_lower for k in complex_intent_keywords)

    operation = None
    if any(k in msg_lower for k in list_keywords):
        operation = "list"
    elif any(k in msg_lower for k in read_keywords):
        operation = "read"
    elif any(k in msg_lower for k in search_keywords):
        operation = "search"
    elif any(k in msg_lower for k in edit_keywords):
        operation = "edit"

    if is_complex_intent:
        return {
            "type": "complex",
            "operation": None,
            "path": None,
            "reason": f"Complex intent detected"
        }

    if operation:
        path = _extract_path(msg_original)
        return {
            "type": "simple_file_operation",
            "operation": operation,
            "path": path,
            "reason": f"Detected {operation} operation"
        }

    return {
        "type": "complex",
        "operation": None,
        "path": None,
        "reason": "Unclear intent, defaulting to MainAgent"
    }


def _extract_path(message: str) -> str:
    """Extract file/directory path from message"""
    patterns = [
        r'[A-Za-z]:[/\\][^\s\'"]+',
        r'/[^\s\'"]+',
        r'\./[^\s\'"]+',
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group()
    return ""


def _extract_all_paths(message: str) -> list:
    """Extract all absolute paths from message"""
    patterns = [
        r'[A-Za-z]:[/\\][^\s\'"]+',
        r'/[^\s\'"]+',
    ]
    paths = []
    for pattern in patterns:
        matches = re.findall(pattern, message)
        for match in matches:
            cleaned = match.rstrip('.,;:!?）')
            if cleaned and cleaned not in paths:
                paths.append(cleaned)
    return paths


def _get_work_directory() -> str:
    """Get configured work directory"""
    try:
        from app.core.runtime_config import runtime_config
        work_dirs = runtime_config.get_additional_working_directories()
        if work_dirs:
            # 返回第一个目录
            return list(work_dirs.keys())[0]
    except:
        pass
    return ""


async def execute_simple_file_operation(
    user_message: str,
    classification: dict
) -> AsyncGenerator[str, None]:
    """
    Execute simple file operations directly via tools_service.
    """
    operation = classification["operation"]
    path = classification["path"]
    work_dir = _get_work_directory()

    yield f"event: agent_status\ndata: {json.dumps({'agent': 'MainAgent', 'role': 'main', 'status': 'working', 'message': f'Executing {operation}...'})}\n\n"

    try:
        if operation == "list":
            if not path:
                path = work_dir
            result = await tools_service.list_directory(path)

        elif operation == "read":
            if not path:
                yield f"event: error\ndata: {json.dumps({'message': '请指定要读取的文件路径'})}\n\n"
                return
            result = await tools_service.read(path, offset=0, limit=500)

        elif operation == "search":
            pattern = _extract_search_pattern(user_message)
            if not pattern:
                pattern = "*"
            result = await tools_service.grep(pattern=pattern, path=path or work_dir)

        elif operation == "edit":
            yield f"event: error\ndata: {json.dumps({'message': 'Edit operations require full agent. Please use MainAgent.'})}\n\n"
            return

        else:
            yield f"event: error\ndata: {json.dumps({'message': 'Unknown operation type'})}\n\n"
            return

        if result.success:
            content = result.content or ""
            result_msg = "## {} Result\n\n{}".format(operation.title(), content)
            yield f"event: final_result\ndata: {json.dumps({'message': result_msg})}\n\n"
        else:
            error_msg = "## Error\n\n{}".format(result.error)
            yield f"event: final_result\ndata: {json.dumps({'message': error_msg})}\n\n"

        yield f"event: done\ndata: {json.dumps({'message': 'Complete', 'task_count': 1})}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'message': f'Execution error: {str(e)}'})}\n\n"
        yield f"event: done\ndata: {json.dumps({'message': 'Error', 'task_count': 0})}\n\n"


def _extract_search_pattern(message: str) -> str:
    """Extract search pattern from message"""
    patterns = [
        r'搜索[^\s]+',
        r'search for [^\s]+',
        r'查找[^\s]+',
        r'find [^\s]+',
        r'"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1) if match.lastindex else match.group()
    return ""


async def event_stream(user_message: str, session_id: str, history_list: list = None) -> AsyncGenerator[str, None]:
    """Generate SSE events for real-time status updates

    Direct execution mode - all requests go directly to MainAgent.
    """
    if history_list is None:
        history_list = []

    yield f"event: start\ndata: {json.dumps({'type': 'start', 'message': 'Starting...'})}\n\n"

    # Direct to MainAgent - no classification needed
    yield f"event: agent_status\ndata: {json.dumps({'agent': 'MainAgent', 'role': 'main', 'status': 'thinking', 'message': 'Processing request...'})}\n\n"

    async for event in _execute_with_main_agent(user_message, history_list):
        yield event


async def _execute_with_main_agent(user_message: str, history_list: list) -> AsyncGenerator[str, None]:
    """
    Execute complex tasks using MainAgent (Claude Code style)
    Single agent direct execution - no PM decomposition, no multi-agent coordination
    """
    from app.agents.main_agent import MainAgent
    from app.services.task_cancellation_service import cancellation_service

    task_id = f"main_{uuid.uuid4().hex[:8]}"
    cancel_token = await cancellation_service.create_token(task_id)

    # Extract paths and add to permission service
    extracted_paths = _extract_all_paths(user_message)
    for path in extracted_paths:
        try:
            from app.services.permission_service import permission_service
            permission_service.check_and_add_path(path)
        except Exception:
            pass

    main_agent = MainAgent()

    yield f"event: agent_status\ndata: {json.dumps({'agent': 'MainAgent', 'role': 'main', 'status': 'thinking', 'message': 'Main agent analyzing...', 'task_id': task_id})}\n\n"

    # 事件队列用于实时流式传输
    event_queue = asyncio.Queue()

    async def async_event_callback(event_type: str, data: dict):
        """异步事件回调 - 工具执行时调用"""
        await event_queue.put((event_type, data))

    try:
        # 启动 agent（不等待完成）
        agent_task = asyncio.create_task(
            main_agent.think(user_message, cancel_token=cancel_token, history_list=history_list, event_callback=async_event_callback)
        )

        # 并行收集和发送事件
        while not agent_task.done() or not event_queue.empty():
            # 发送队列中的事件
            try:
                event_type, data = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                if event_type == 'tool_start':
                    yield f"event: tool_start\ndata: {json.dumps(data)}\n\n"
                elif event_type == 'tool_result':
                    yield f"event: tool_result\ndata: {json.dumps(data)}\n\n"
                elif event_type == 'content_delta':
                    yield f"event: content_delta\ndata: {json.dumps(data)}\n\n"
                event_queue.task_done()
            except asyncio.TimeoutError:
                # 继续等待
                continue

        # 确保 agent 完成
        if not agent_task.done():
            await agent_task

        result = agent_task.result()

        if cancel_token.is_cancelled:
            yield f"event: cancelled\ndata: {json.dumps({'message': 'Task was cancelled by user'})}\n\n"
            yield f"event: done\ndata: {json.dumps({'message': 'Cancelled', 'task_count': 0})}\n\n"
            return

        yield f"event: agent_status\ndata: {json.dumps({'agent': 'MainAgent', 'role': 'main', 'status': 'completed', 'message': 'Task completed'})}\n\n"

        yield f"event: final_result\ndata: {json.dumps({'message': result})}\n\n"

        yield f"event: done\ndata: {json.dumps({'message': 'Complete', 'task_count': 1})}\n\n"

    except asyncio.CancelledError:
        yield f"event: cancelled\ndata: {json.dumps({'message': 'Task was cancelled'})}\n\n"
        yield f"event: done\ndata: {json.dumps({'message': 'Cancelled', 'task_count': 0})}\n\n"
    except Exception as e:
        error_msg = f"MainAgent execution error: {str(e)}"
        yield f"event: error\ndata: {json.dumps({'message': error_msg})}\n\n"
        yield f"event: done\ndata: {json.dumps({'message': 'Error', 'task_count': 0})}\n\n"
    finally:
        await cancellation_service.remove_token(task_id)


def _build_user_choice_error() -> dict:
    """Build user choice error when all providers fail"""
    return {
        'type': 'user_choice',
        'code': 'ALL_PROVIDERS_FAILED',
        'message': '抱歉，您的请求暂时无法完成。可选方案：',
        'options': [
            {'id': 'retry', 'label': '🔄 重试', 'description': '稍后重新发送请求'},
            {'id': 'simplify', 'label': '📝 简化问题', 'description': '将复杂问题拆分后重试'},
            {'id': 'switch', 'label': '🔀 切换提供商', 'description': '尝试使用其他 AI 提供商'},
            {'id': 'cancel', 'label': '❌ 取消', 'description': '放弃当前请求'}
        ]
    }


@router.get("/stream")
async def stream_process(user_message: str, history: str = "[]", session_id: str = "default"):
    """
    SSE endpoint for streaming real-time status updates.
    Single agent execution via MainAgent.
    """
    import json as json_lib
    try:
        history_list = json_lib.loads(history) if history else []
    except:
        history_list = []

    return StreamingResponse(
        event_stream(user_message, session_id, history_list),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/team-status")
async def get_team_status():
    """Get current status - DEPRECATED, returns empty for single-agent mode"""
    return {"success": True, "agents": [], "message": "Multi-agent team status deprecated. Using single-agent MainAgent."}