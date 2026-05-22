"""
File Write Tool - Create or overwrite files
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


class FileWriteTool:
    """FileWriteTool class for compatibility"""
    pass


class FileWriteInput(BaseModel):
    file_path: str
    content: str


class FileWriteOutput(BaseModel):
    type: str  # create or update
    file_path: str
    content: str


def write_file_content(file_path: str, content: str) -> dict:
    """Write content to a file"""
    abs_path = os.path.abspath(os.path.expanduser(file_path))

    # Security: UNC path check
    if abs_path.startswith('\\\\') or abs_path.startswith('//'):
        raise HTTPException(status_code=400, detail="UNC paths are not allowed")

    # Ensure parent directory exists
    parent_dir = os.path.dirname(abs_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    # Check if file exists
    file_existed = os.path.exists(abs_path)

    # Get original content for patch
    original_content = None
    if file_existed:
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception:
            pass

    # Write content
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        "type": "update" if file_existed else "create",
        "file_path": file_path,
        "content": content,
        "original_file": original_content
    }


@router.post("/write")
async def write_file(input: FileWriteInput) -> FileWriteOutput:
    """Write content to a file"""
    try:
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="write",
            request_type="file_write",
            description=f"写入文件: {input.file_path}",
            path=input.file_path,
            risk_level="MEDIUM"
        )

        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

        result = write_file_content(input.file_path, input.content)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))