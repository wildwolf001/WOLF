"""
Grep Tool - Search file contents using regular expressions
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import re

router = APIRouter()

# Default exclusions
VCS_DIRS = {'.git', '.svn', '.hg', '.bzr'}


class GrepTool:
    """GrepTool class for compatibility"""
    pass


class GrepInput(BaseModel):
    pattern: str
    path: Optional[str] = None
    glob: Optional[str] = None
    output_mode: str = "files_with_matches"  # content, files_with_matches, count
    context_before: Optional[int] = None  # -B
    context_after: Optional[int] = None  # -A
    context: Optional[int] = None  # -C (context around match)
    show_line_numbers: bool = True  # -n
    case_insensitive: bool = False  # -i
    file_type: Optional[str] = None  # --type
    head_limit: Optional[int] = 250
    multiline: bool = False


class GrepOutput(BaseModel):
    mode: str
    num_files: int
    filenames: List[str]
    content: Optional[str] = None
    num_lines: Optional[int] = None
    num_matches: Optional[int] = None


def search_files(
    pattern: str,
    path: Optional[str] = None,
    glob: Optional[str] = None,
    output_mode: str = "files_with_matches",
    context_before: Optional[int] = None,
    context_after: Optional[int] = None,
    context: Optional[int] = None,
    show_line_numbers: bool = True,
    case_insensitive: bool = False,
    file_type: Optional[str] = None,
    head_limit: Optional[int] = 250,
    multiline: bool = False
) -> dict:
    """Search for pattern in files"""
    search_path = path or os.getcwd()
    abs_path = os.path.abspath(os.path.expanduser(search_path))

    # Security: UNC path check
    if abs_path.startswith('\\\\') or abs_path.startswith('//'):
        raise HTTPException(status_code=400, detail="UNC paths are not allowed")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    # Build regex
    flags = re.IGNORECASE if case_insensitive else 0
    if multiline:
        flags |= re.MULTILINE | re.DOTALL
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {e}")

    # Get files to search
    if os.path.isfile(abs_path):
        files_to_search = [abs_path]
    else:
        files_to_search = []
        for root, dirs, files in os.walk(abs_path):
            # Exclude VCS directories
            dirs[:] = [d for d in dirs if d not in VCS_DIRS]

            for filename in files:
                file_path = os.path.join(root, filename)

                # Apply glob filter
                if glob:
                    if not re.match(glob.replace('*', '.*').replace('?', '.'), filename):
                        continue

                # Apply type filter
                if file_type:
                    ext = os.path.splitext(filename)[1]
                    if not ext.lstrip('.') == file_type:
                        continue

                files_to_search.append(file_path)

    results = []
    match_count = 0

    for file_path in files_to_search:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                matches = list(regex.finditer(line))
                if matches:
                    line_num = i + 1
                    prefix = f"{file_path}:{line_num}:" if show_line_numbers else f"{file_path}:"
                    results.append(f"{prefix}{line.rstrip()}")
                    match_count += 1

                    # Check head_limit
                    if head_limit and len(results) >= head_limit:
                        break
        except Exception:
            continue

        if head_limit and len(results) >= head_limit:
            break

    # Build output based on mode
    if output_mode == "files_with_matches":
        # Extract unique filenames
        filenames = list(set(r.split(':')[0] for r in results))
        return {
            "mode": "files_with_matches",
            "num_files": len(filenames),
            "filenames": filenames[:head_limit] if head_limit else filenames,
            "content": None
        }
    elif output_mode == "count":
        # Group by file
        file_counts = {}
        for r in results:
            fname = r.split(':')[0]
            file_counts[fname] = file_counts.get(fname, 0) + 1

        total_matches = sum(file_counts.values())
        content = "\n".join([f"{f}:{c}" for f, c in file_counts.items()])

        return {
            "mode": "count",
            "num_files": len(file_counts),
            "filenames": list(file_counts.keys()),
            "content": content,
            "num_matches": total_matches
        }
    else:  # content
        return {
            "mode": "content",
            "num_files": len(set(r.split(':')[0] for r in results)),
            "filenames": [],
            "content": "\n".join(results),
            "num_lines": len(results)
        }


@router.post("/grep")
async def grep(input: GrepInput) -> GrepOutput:
    """Search file contents"""
    try:
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="grep",
            request_type="file_read",
            description=f"搜索文件内容: {input.pattern}",
            path=input.path,
            risk_level="LOW"
        )

        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

        result = search_files(
            pattern=input.pattern,
            path=input.path,
            glob=input.glob,
            output_mode=input.output_mode,
            context_before=input.context_before,
            context_after=input.context_after,
            context=input.context,
            show_line_numbers=input.show_line_numbers,
            case_insensitive=input.case_insensitive,
            file_type=input.file_type,
            head_limit=input.head_limit,
            multiline=input.multiline
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))