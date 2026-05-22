"""
File Read Tool - Read files from the local filesystem
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
from pathlib import Path

router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
BLOCKED_DEVICES = {
    '/dev/zero', '/dev/random', '/dev/urandom', '/dev/full',
    '/dev/stdin', '/dev/tty', '/dev/console',
    '/dev/stdout', '/dev/stderr',
}


class FileReadInput(BaseModel):
    file_path: str
    offset: Optional[int] = 1  # Line number to start from (1-indexed)
    limit: Optional[int] = None  # Number of lines to read


class FileReadOutput(BaseModel):
    type: str = "text"  # text, image, pdf, notebook
    file: dict


class FileReadTool:
    """FileReadTool class for compatibility"""
    pass


def is_blocked_device(file_path: str) -> bool:
    """Check if path is a blocked device file"""
    if file_path in BLOCKED_DEVICES:
        return True
    # Check /proc/self/fd/* patterns
    if file_path.startswith('/proc/') and file_path.endswith('/fd/0'):
        return True
    if file_path.startswith('/proc/') and file_path.endswith('/fd/1'):
        return True
    if file_path.startswith('/proc/') and file_path.endswith('/fd/2'):
        return True
    return False


def read_file_content(file_path: str, offset: int = 1, limit: Optional[int] = None) -> dict:
    """Read file content with optional line range"""
    abs_path = os.path.abspath(os.path.expanduser(file_path))

    # Security: check for blocked devices
    if is_blocked_device(abs_path):
        raise HTTPException(status_code=400, detail=f"Cannot read device file: {file_path}")

    # Security: UNC path check
    if abs_path.startswith('\\\\') or abs_path.startswith('//'):
        raise HTTPException(status_code=400, detail="UNC paths are not allowed")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Check file size
    file_size = os.path.getsize(abs_path)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})")

    # Detect file type
    ext = os.path.splitext(abs_path)[1].lower()

    # Handle images
    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        with open(abs_path, 'rb') as f:
            import base64
            data = base64.b64encode(f.read()).decode('utf-8')
        return {
            "type": "image",
            "file": {
                "base64": data,
                "media_type": f"image/{ext[1:]}",
                "original_size": file_size
            }
        }

    # Handle notebooks
    if ext == '.ipynb':
        import json
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        try:
            notebook = json.loads(content)
            return {
                "type": "notebook",
                "file": {
                    "file_path": file_path,
                    "cells": notebook.get('cells', [])
                }
            }
        except json.JSONDecodeError:
            pass

    # Handle PDF
    if ext == '.pdf':
        with open(abs_path, 'rb') as f:
            import base64
            data = base64.b64encode(f.read()).decode('utf-8')
        return {
            "type": "pdf",
            "file": {
                "file_path": file_path,
                "base64": data,
                "original_size": file_size
            }
        }

    # Handle text files
    with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    total_lines = len(lines)
    start_idx = max(0, offset - 1)
    end_idx = start_idx + limit if limit else len(lines)

    content = ''.join(lines[start_idx:end_idx])

    return {
        "type": "text",
        "file": {
            "file_path": file_path,
            "content": content,
            "num_lines": end_idx - start_idx,
            "start_line": offset,
            "total_lines": total_lines
        }
    }


@router.post("/read")
async def read_file(input: FileReadInput) -> FileReadOutput:
    """Read a file from the filesystem"""
    try:
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="read",
            request_type="file_read",
            description=f"读取文件: {input.file_path}",
            path=input.file_path,
            risk_level="LOW"
        )

        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

        result = read_file_content(input.file_path, input.offset, input.limit)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read/{path:path}")
async def read_file_get(path: str, offset: Optional[int] = 1, limit: Optional[int] = None) -> FileReadOutput:
    """Read a file from the filesystem (GET method)"""
    try:
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="read",
            request_type="file_read",
            description=f"读取文件: {path}",
            path=path,
            risk_level="LOW"
        )

        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

        result = read_file_content(path, offset, limit)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))