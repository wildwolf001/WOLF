"""
Logs Route
Provides backend log access by reading log file
"""
import os
import time
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import json

router = APIRouter()

# Log file path
LOG_DIR = "logs"
LOG_FILE = "wolf.log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILE)


def get_log_file_path() -> str:
    """Get the log file path, creating directory if needed"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    return LOG_PATH


def read_log_file(last_position: int = 0, max_lines: int = 500) -> tuple[str, int]:
    """
    Read log file from last position.
    Returns (content, new_position)
    """
    path = get_log_file_path()

    if not os.path.exists(path):
        return "", 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            f.seek(last_position)
            lines = []
            new_pos = last_position
            for i in range(max_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip("\n"))
                new_pos = f.tell()

            return "\n".join(lines), new_pos

    except Exception as e:
        return f"Error reading log file: {e}", last_position


@router.get("/logs/file")
async def get_logs(
    last_position: int = Query(0, description="File position to read from"),
    max_lines: int = Query(500, ge=1, le=5000, description="Maximum lines to return"),
    session_id: Optional[str] = Query(None, description="Filter by session ID (not used in file mode)")
) -> dict:
    """
    Get logs from the log file.
    Returns log content and new file position for next read.
    """
    content, new_position = read_log_file(last_position, max_lines)

    # Parse lines into structured log entries
    logs = []
    for line in content.split("\n"):
        if not line:
            continue

        # Parse log line: [2026-05-22 16:41:25] INFO [websocket:websocket.py:29] message
        try:
            # Extract timestamp
            if line.startswith("["):
                parts = line.split("] ", 2)
                if len(parts) >= 3:
                    timestamp_str = parts[0][1:]
                    # Extract level and location from second part
                    # Format: "INFO [websocket:websocket.py:29]"
                    level_rest = parts[1]
                    if "] [" in level_rest:
                        # Split on "] [" to get level and location
                        level_parts = level_rest.split("] [", 1)
                        level = level_parts[0].strip("[] ")
                        location = level_parts[1].strip("[] ") if len(level_parts) > 1 else ""
                        message = parts[2]
                    else:
                        # No location, just level
                        level = level_rest.strip("[] ")
                        location = ""
                        message = parts[2]

                    logs.append({
                        "id": f"log_{int(time.time() * 1000)}_{len(logs)}",
                        "timestamp": timestamp_str,
                        "level": level.lower() if level.lower() in ["debug", "info", "warn", "error"] else "info",
                        "source": _extract_source(location),
                        "location": location,
                        "message": message,
                    })
        except Exception:
            # If parsing fails, add as-is
            logs.append({
                "id": f"log_{int(time.time() * 1000)}_{len(logs)}",
                "timestamp": datetime.now().isoformat(),
                "level": "info",
                "source": "backend",
                "location": "",
                "message": line,
            })

    return {
        "logs": logs,
        "count": len(logs),
        "position": new_position,
        "has_more": len(content.split("\n")) >= max_lines
    }


def _extract_source(location: str) -> str:
    """Extract source (backend/agent/workflow/tool) from log location"""
    if not location:
        return "backend"

    # Common patterns
    if "agent" in location.lower():
        return "agent"
    if "workflow" in location.lower():
        return "workflow"
    if "tool" in location.lower():
        return "tool"
    if "mcp" in location.lower():
        return "mcp"
    if "query" in location.lower():
        return "query"
    if "tasks" in location.lower():
        return "tasks"

    return "backend"


@router.get("/logs/stream")
async def stream_logs(
    last_position: int = Query(0, description="File position to read from"),
    session_id: Optional[str] = Query(None, description="Filter by session ID (not used in file mode)")
) -> StreamingResponse:
    """
    SSE endpoint for streaming logs from the log file.
    Polls the file periodically for new content.
    """
    async def event_generator():
        current_position = last_position

        while True:
            await asyncio.sleep(1)  # Poll every 1 second

            content, new_position = read_log_file(current_position, 100)

            if content:
                for line in content.split("\n"):
                    if not line:
                        continue

                    # Send each line as a log event
                    yield f"data: {json.dumps({'type': 'log', 'line': line, 'position': new_position})}\n\n".encode()
                current_position = new_position

            # Send keepalive
            yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': int(time.time() * 1000)})}\n\n".encode()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/logs/stats")
async def get_log_stats() -> dict:
    """
    Get statistics about the log file.
    """
    path = get_log_file_path()

    if not os.path.exists(path):
        return {
            "exists": False,
            "size": 0,
            "lines": 0,
            "path": path
        }

    stats = os.stat(path)

    # Count lines
    with open(path, "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)

    return {
        "exists": True,
        "size": stats.st_size,
        "lines": line_count,
        "path": path,
        "modified": datetime.fromtimestamp(stats.st_mtime).isoformat()
    }


@router.delete("/logs/file")
async def clear_log_file() -> dict:
    """
    Clear (truncate) the log file.
    """
    path = get_log_file_path()

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return {"status": "ok", "message": "Log file cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}