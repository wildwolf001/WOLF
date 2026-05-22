"""
Glob Tool - Find files by name pattern
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import fnmatch
from datetime import datetime

router = APIRouter()


class GlobTool:
    """GlobTool class for compatibility"""
    pass


class GlobInput(BaseModel):
    pattern: str
    path: Optional[str] = None


class GlobOutput(BaseModel):
    duration_ms: int
    num_files: int
    filenames: List[str]
    truncated: bool = False


def find_files(pattern: str, path: Optional[str] = None) -> dict:
    """Find files matching glob pattern"""
    start_time = datetime.now()
    search_path = path or os.getcwd()
    abs_path = os.path.abspath(os.path.expanduser(search_path))

    # Security: UNC path check
    if abs_path.startswith('\\\\') or abs_path.startswith('//'):
        raise HTTPException(status_code=400, detail="UNC paths are not allowed")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

    results = []
    max_results = 100

    for root, dirs, files in os.walk(abs_path):
        # Skip VCS directories
        dirs[:] = [d for d in dirs if d not in ['.git', '.svn', '.hg', '.bzr']]

        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, abs_path)
                results.append(rel_path)

                if len(results) >= max_results:
                    break

        if len(results) >= max_results:
            break

    # Sort by modification time (newest first)
    def get_mtime(f):
        try:
            return os.path.getmtime(os.path.join(abs_path, f))
        except Exception:
            return 0

    results.sort(key=get_mtime, reverse=True)

    truncated = len(results) >= max_results

    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    return {
        "duration_ms": duration_ms,
        "num_files": len(results),
        "filenames": results,
        "truncated": truncated
    }


@router.post("/glob")
async def glob(input: GlobInput) -> GlobOutput:
    """Find files matching pattern"""
    try:
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="glob",
            request_type="file_read",
            description=f"搜索文件: {input.pattern}",
            path=input.path,
            risk_level="LOW"
        )

        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

        result = find_files(input.pattern, input.path)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))