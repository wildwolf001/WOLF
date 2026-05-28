"""
Files Route
"""
import os
from typing import Optional
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/files/read")
async def read_file(
    path: str,
    workspace_id: str = "default"
) -> dict:
    """Read a file"""
    from ...tools.definitions.file_read import read_file as read_file_tool

    workspace_path = f"/workspace/{workspace_id}"
    result = await read_file_tool(path, base_path=workspace_path)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.post("/files/write")
async def write_file(
    path: str,
    content: str,
    workspace_id: str = "default"
) -> dict:
    """Write a file"""
    from ...tools.definitions.file_write import write_file as write_file_tool

    workspace_path = f"/workspace/{workspace_id}"
    result = await write_file_tool(path, content, base_path=workspace_path)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.post("/files/edit")
async def edit_file(
    path: str,
    old_text: str,
    new_text: str,
    workspace_id: str = "default"
) -> dict:
    """Edit a file"""
    from ...tools.definitions.file_edit import edit_file as edit_file_tool

    workspace_path = f"/workspace/{workspace_id}"
    result = await edit_file_tool(path, old_text, new_text, base_path=workspace_path)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/files/glob")
async def glob_files(
    pattern: str,
    workspace_id: str = "default"
) -> dict:
    """Find files by pattern"""
    from ...tools.definitions.glob import glob_files as glob_tool

    workspace_path = f"/workspace/{workspace_id}"
    result = await glob_tool(pattern, base_path=workspace_path)

    return result


@router.get("/files/grep")
async def grep_files(
    pattern: str,
    workspace_id: str = "default",
    file_pattern: str = "*"
) -> dict:
    """Search files by pattern"""
    from ...tools.definitions.grep import grep as grep_tool

    workspace_path = f"/workspace/{workspace_id}"
    result = await grep_tool(pattern, base_path=workspace_path, file_pattern=file_pattern)

    return result