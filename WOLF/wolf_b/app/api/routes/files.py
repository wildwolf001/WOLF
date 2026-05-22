"""
File Manager API - 文件管理 API
提供文件浏览、读取、上传等功能
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import os

from app.services.file_manager_service import file_manager
from app.services.permission_service import permission_service

router = APIRouter()


@router.get("/list")
async def list_directory(path: str = ".", include_hidden: bool = False):
    """
    列出目录内容

    Args:
        path: 目录路径（默认当前工作目录）
        include_hidden: 是否包含隐藏文件
    """
    result = file_manager.list_directory(path, include_hidden)
    return result


@router.get("/tree")
async def get_file_tree(path: str = ".", max_depth: int = 2):
    """
    获取目录树形结构

    Args:
        path: 目录路径
        max_depth: 最大递归深度
    """
    result = file_manager.get_file_tree(path, max_depth)
    return result


@router.get("/read")
async def read_file(
    path: str,
    offset: int = 0,
    limit: int = None,
    as_base64: bool = False
):
    """
    读取文件内容

    Args:
        path: 文件路径
        offset: 起始行号（0-indexed）
        limit: 读取行数限制
        as_base64: 是否以 base64 返回
    """
    result = file_manager.read_file(path, offset, limit, as_base64)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Read failed"))
    return result


@router.post("/write")
async def write_file(path: str, content: str, append: bool = False):
    """
    写入文件内容

    Args:
        path: 文件路径
        content: 文件内容
        append: 是否追加模式
    """
    result = file_manager.write_file(path, content, append)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Write failed"))
    return result


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    target_dir: Optional[str] = None
):
    """
    上传文件

    Args:
        file: 上传的文件
        target_dir: 目标目录（可选）
    """
    content = await file.read()
    result = file_manager.upload_file(file.filename, content, target_dir)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Upload failed"))
    return result


@router.get("/info")
async def get_file_info(path: str):
    """
    获取文件信息

    Args:
        path: 文件路径
    """
    result = file_manager.get_file_info(path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Get info failed"))
    return result


@router.post("/mkdir")
async def create_directory(path: str):
    """
    创建目录

    Args:
        path: 目录路径
    """
    result = file_manager.create_directory(path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Create directory failed"))
    return result


@router.post("/delete")
async def delete_file(path: str, recursive: bool = False):
    """
    删除文件或目录

    Args:
        path: 文件或目录路径
        recursive: 是否递归删除（仅对目录有效）
    """
    result = file_manager.delete_file(path, recursive)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Delete failed"))
    return result


@router.post("/copy")
async def copy_file(source: str, destination: str):
    """
    复制文件

    Args:
        source: 源文件路径
        destination: 目标路径
    """
    result = file_manager.copy_file(source, destination)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Copy failed"))
    return result


@router.get("/search")
async def search_files(directory: str, pattern: str, recursive: bool = True):
    """
    搜索文件

    Args:
        directory: 搜索目录
        pattern: 文件名模式（支持 glob）
        recursive: 是否递归搜索
    """
    result = file_manager.search_files(directory, pattern, recursive)
    return result


@router.get("/allowed-directories")
async def get_allowed_directories():
    """获取所有允许访问的目录"""
    return {
        "success": True,
        "directories": permission_service.list_allowed_directories()
    }


@router.get("/preview/{path:path}")
async def preview_file(path: str, offset: int = 0, limit: int = 100):
    """
    预览文件内容（用于前端文件浏览器）

    Args:
        path: 文件路径
        offset: 起始行号
        limit: 读取行数
    """
    result = file_manager.read_file(path, offset, limit)
    return result