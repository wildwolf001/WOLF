"""
List Tool - List directory contents
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os

router = APIRouter()


class ListInput(BaseModel):
    path: str = "."
    recursive: bool = False
    include_hidden: bool = False


class ListOutput(BaseModel):
    path: str
    directories: List[str]
    files: List[str]
    total_count: int


def list_directory(path: str = ".", recursive: bool = False, include_hidden: bool = False) -> dict:
    """List directory contents"""
    abs_path = os.path.abspath(os.path.expanduser(path))

    # Security: UNC path check
    if abs_path.startswith('\\\\') or abs_path.startswith('//'):
        raise HTTPException(status_code=400, detail="UNC paths are not allowed")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

    directories = []
    files = []

    if recursive:
        for root, dirs, filenames in os.walk(abs_path):
            # Filter hidden files/dirs
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                filenames = [f for f in filenames if not f.startswith('.')]

            for d in dirs:
                rel_path = os.path.relpath(os.path.join(root, d), abs_path)
                directories.append(f"{rel_path}/")

            for f in filenames:
                rel_path = os.path.relpath(os.path.join(root, f), abs_path)
                files.append(rel_path)
    else:
        entries = os.listdir(abs_path)

        # Filter hidden
        if not include_hidden:
            entries = [e for e in entries if not e.startswith('.')]

        for entry in entries:
            full_path = os.path.join(abs_path, entry)
            if os.path.isdir(full_path):
                directories.append(f"{entry}/")
            else:
                files.append(entry)

    directories.sort()
    files.sort()

    return {
        "path": abs_path,
        "directories": directories,
        "files": files,
        "total_count": len(directories) + len(files)
    }


@router.post("/list")
async def list_dir(input: ListInput) -> ListOutput:
    """List directory contents"""
    try:
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="list",
            request_type="file_read",
            description=f"列出目录: {input.path}",
            path=input.path,
            risk_level="LOW"
        )

        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

        result = list_directory(input.path, input.recursive, input.include_hidden)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))