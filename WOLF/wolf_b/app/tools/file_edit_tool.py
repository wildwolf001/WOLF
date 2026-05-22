"""
File Edit Tool - Edit files in place using old_string/new_string replacement
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter()


class FileEditTool:
    """FileEditTool class for compatibility"""
    pass


class FileEditInput(BaseModel):
    file_path: str
    old_string: str
    new_string: str
    replace_all: bool = False


class FileEditOutput(BaseModel):
    file_path: str
    old_string: str
    new_string: str
    replacements: int


def edit_file_content(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict:
    """Edit a file by replacing old_string with new_string"""
    abs_path = os.path.abspath(os.path.expanduser(file_path))

    # Security: UNC path check
    if abs_path.startswith('\\\\') or abs_path.startswith('//'):
        raise HTTPException(status_code=400, detail="UNC paths are not allowed")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find occurrences
    if old_string not in content:
        raise HTTPException(status_code=400, detail="String to replace not found in file")

    replacements = content.count(old_string)

    # Check if multiple matches but replace_all is false
    if replacements > 1 and not replace_all:
        raise HTTPException(
            status_code=400,
            detail=f"Found {replacements} matches, but replace_all is false. Set replace_all=true to replace all."
        )

    # Perform replacement
    if replace_all:
        new_content = content.replace(old_string, new_string)
    else:
        new_content = content.replace(old_string, new_string, 1)

    # Write back
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {
        "file_path": file_path,
        "old_string": old_string,
        "new_string": new_string,
        "replacements": replacements if replace_all else 1
    }


@router.post("/edit")
async def edit_file(input: FileEditInput) -> FileEditOutput:
    """Edit a file in place"""
    try:
        # 请求权限检查 - 参考 Claude Code
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="edit",
            request_type="file_edit",
            description=f"编辑文件: {input.file_path}",
            path=input.file_path,
            risk_level="MEDIUM"
        )

        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

        result = edit_file_content(input.file_path, input.old_string, input.new_string, input.replace_all)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))