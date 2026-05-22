"""
Info Tool - Get file/directory information
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime

router = APIRouter()


class InfoInput(BaseModel):
    path: str


class InfoOutput(BaseModel):
    path: str
    name: str
    type: str  # file, directory, other
    size: int
    size_formatted: str
    created: str
    modified: str
    accessed: str
    is_readable: bool
    is_writable: bool
    is_executable: bool


def format_size(size: int) -> str:
    """Format file size in human-readable form"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def get_file_info(path: str) -> dict:
    """Get detailed file/directory information"""
    abs_path = os.path.abspath(os.path.expanduser(path))

    # Security: UNC path check
    if abs_path.startswith('\\\\') or abs_path.startswith('//'):
        raise HTTPException(status_code=400, detail="UNC paths are not allowed")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    stat_info = os.stat(abs_path)
    is_dir = os.path.isdir(abs_path)

    # Format timestamps
    created = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
    modified = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
    accessed = datetime.fromtimestamp(stat_info.st_atime).isoformat()

    return {
        "path": abs_path,
        "name": os.path.basename(abs_path),
        "type": "directory" if is_dir else "file",
        "size": stat_info.st_size,
        "size_formatted": format_size(stat_info.st_size) if not is_dir else "N/A",
        "created": created,
        "modified": modified,
        "accessed": accessed,
        "is_readable": os.access(abs_path, os.R_OK),
        "is_writable": os.access(abs_path, os.W_OK),
        "is_executable": os.access(abs_path, os.X_OK)
    }


@router.post("/info")
async def get_info(input: InfoInput) -> InfoOutput:
    """Get file or directory information"""
    try:
        result = get_file_info(input.path)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))