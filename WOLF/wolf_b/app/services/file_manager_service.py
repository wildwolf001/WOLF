"""
文件管理服务 - 统一的文件操作服务
支持读取、写入、上传、浏览本地文件系统
"""
import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import mimetypes
import hashlib

from app.services.permission_service import permission_service, get_permission_service, PermissionAction

# Import permission mode checker from permissions API
def _check_permission_mode(operation: str) -> tuple[bool, str]:
    """Check if current permission mode allows the operation"""
    try:
        from app.api.routes.permissions import can_perform_file_operation
        return can_perform_file_operation(operation)
    except ImportError:
        # If permissions module not available, allow by default
        return True, "Allowed"

class FileInfo:
    """文件信息"""
    def __init__(
        self,
        name: str,
        path: str,
        is_directory: bool,
        size: int = 0,
        modified_time: float = 0,
        extension: str = "",
        mime_type: str = ""
    ):
        self.name = name
        self.path = path
        self.is_directory = is_directory
        self.size = size
        self.modified_time = modified_time
        self.extension = extension
        self.mime_type = mime_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "is_directory": self.is_directory,
            "size": self.size,
            "size_formatted": self._format_size(self.size),
            "modified_time": self.modified_time,
            "modified_time_formatted": datetime.fromtimestamp(self.modified_time).strftime("%Y-%m-%d %H:%M:%S") if self.modified_time else "",
            "extension": self.extension,
            "mime_type": self.mime_type
        }

    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

class FileManagerService:
    """
    文件管理服务

    功能：
    1. 列出目录内容（树形结构）
    2. 读取文件内容（支持 offset/limit）
    3. 写入文件
    4. 上传文件
    5. 获取文件信息
    6. 创建目录
    7. 删除文件/目录
    """

    # 支持预览的文件扩展名
    PREVIEWABLE_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx', '.json',
        '.yaml', '.yml', '.xml', '.html', '.css', '.scss', '.less',
        '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs',
        '.sql', '.sh', '.bash', '.bat', '.ps1', '.log', '.ini',
        '.cfg', '.conf', '.env', '.gitignore', '.dockerfile',
        '.ipynb', '.rst', '.tex'
    }

    # 支持的图片扩展名
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico', '.svg'}

    # 支持的 PDF 扩展名
    PDF_EXTENSIONS = {'.pdf'}

    def __init__(self):
        self.permission_service = get_permission_service()
        mimetypes.init()

    def _get_mime_type(self, path: str) -> str:
        """获取文件的 MIME 类型"""
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type or 'application/octet-stream'

    def _get_extension(self, path: str) -> str:
        """获取文件扩展名"""
        return Path(path).suffix.lower()

    def _validate_path(self, path: str) -> Tuple[bool, str, str]:
        """验证路径是否合法且有权限"""
        return self.permission_service.validate_path(path)

    def list_directory(self, path: str, include_hidden: bool = False) -> Dict[str, Any]:
        """
        列出目录内容

        Args:
            path: 目录路径
            include_hidden: 是否包含隐藏文件

        Returns:
            目录内容和子目录树形结构
        """
        # 验证路径
        is_valid, error_msg, normalized_path = self._validate_path(path)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not os.path.exists(normalized_path):
            return {"success": False, "error": f"Path does not exist: {path}"}

        if not os.path.isdir(normalized_path):
            return {"success": False, "error": f"Path is not a directory: {path}"}

        try:
            entries = []
            directories = []
            files = []

            for entry_name in os.listdir(normalized_path):
                # 跳过隐藏文件
                if not include_hidden and entry_name.startswith('.'):
                    continue

                entry_path = os.path.join(normalized_path, entry_name)
                is_dir = os.path.isdir(entry_path)

                try:
                    stat = os.stat(entry_path)
                    file_info = FileInfo(
                        name=entry_name,
                        path=entry_path,
                        is_directory=is_dir,
                        size=stat.st_size if not is_dir else 0,
                        modified_time=stat.st_mtime,
                        extension=self._get_extension(entry_path),
                        mime_type=self._get_mime_type(entry_path) if not is_dir else ""
                    )

                    if is_dir:
                        directories.append(file_info.to_dict())
                    else:
                        files.append(file_info.to_dict())
                except Exception:
                    continue

            # 按名称排序（目录在前）
            directories.sort(key=lambda x: x['name'].lower())
            files.sort(key=lambda x: x['name'].lower())

            return {
                "success": True,
                "path": normalized_path,
                "directories": directories,
                "files": files,
                "total_count": len(directories) + len(files)
            }

        except PermissionError:
            return {"success": False, "error": "Permission denied"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_file_tree(self, path: str, max_depth: int = 2, current_depth: int = 0) -> Dict[str, Any]:
        """
        获取目录树形结构

        Args:
            path: 目录路径
            max_depth: 最大递归深度
            current_depth: 当前深度
        """
        is_valid, error_msg, normalized_path = self._validate_path(path)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not os.path.exists(normalized_path):
            return {"success": False, "error": f"Path does not exist: {path}"}

        result = {
            "name": os.path.basename(normalized_path) or normalized_path,
            "path": normalized_path,
            "is_directory": True,
            "children": []
        }

        if current_depth >= max_depth:
            result["truncated"] = True
            return {"success": True, **result}

        try:
            for entry_name in os.listdir(normalized_path):
                if entry_name.startswith('.'):
                    continue

                entry_path = os.path.join(normalized_path, entry_name)
                is_dir = os.path.isdir(entry_path)

                try:
                    stat = os.stat(entry_path)
                    ext = self._get_extension(entry_path)

                    child = {
                        "name": entry_name,
                        "path": entry_path,
                        "is_directory": is_dir,
                        "size": stat.st_size if not is_dir else 0,
                        "extension": ext
                    }

                    if is_dir:
                        child["children"] = self.get_file_tree(entry_path, max_depth, current_depth + 1).get("children", [])
                        child["truncated"] = len(child["children"]) == 0 and current_depth + 1 < max_depth

                    result["children"].append(child)
                except Exception:
                    continue

            # 排序
            result["children"].sort(key=lambda x: (not x["is_directory"], x["name"].lower()))

        except PermissionError:
            result["error"] = "Permission denied"
        except Exception as e:
            result["error"] = str(e)

        return {"success": True, **result}

    def read_file(
        self,
        path: str,
        offset: int = 0,
        limit: int = None,
        as_base64: bool = False
    ) -> Dict[str, Any]:
        """
        读取文件内容

        Args:
            path: 文件路径
            offset: 起始行号
            limit: 读取行数限制
            as_base64: 是否以 base64 返回（用于二进制文件）
        """
        is_valid, error_msg, normalized_path = self._validate_path(path)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not os.path.exists(normalized_path):
            return {"success": False, "error": f"File does not exist: {path}"}

        if os.path.isdir(normalized_path):
            return {"success": False, "error": f"Path is a directory: {path}"}

        try:
            stat = os.stat(normalized_path)
            ext = self._get_extension(normalized_path)

            # 检查是否为图片或 PDF（可以用 base64 返回）
            if ext in self.IMAGE_EXTENSIONS or ext in self.PDF_EXTENSIONS:
                if as_base64:
                    with open(normalized_path, 'rb') as f:
                        import base64
                        content = base64.b64encode(f.read()).decode('utf-8')
                    return {
                        "success": True,
                        "name": os.path.basename(normalized_path),
                        "path": normalized_path,
                        "size": stat.st_size,
                        "extension": ext,
                        "mime_type": self._get_mime_type(normalized_path),
                        "content": content,
                        "encoding": "base64"
                    }

            # 文本文件 - 支持 offset/limit
            if ext in self.PREVIEWABLE_EXTENSIONS or not ext:
                with open(normalized_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                total_lines = len(lines)
                start = min(offset, total_lines)
                end = min(offset + limit, total_lines) if limit else total_lines

                content = ''.join(lines[start:end])

                return {
                    "success": True,
                    "name": os.path.basename(normalized_path),
                    "path": normalized_path,
                    "size": stat.st_size,
                    "extension": ext,
                    "content": content,
                    "total_lines": total_lines,
                    "read_lines": end - start,
                    "start_line": start + 1,  # 1-indexed for user display
                    "encoding": "utf-8"
                }

            # 其他二进制文件
            return {
                "success": False,
                "error": f"Binary file type '{ext}' cannot be read as text. Use as_base64=True to read as base64.",
                "name": os.path.basename(normalized_path),
                "path": normalized_path,
                "size": stat.st_size,
                "extension": ext
            }

        except UnicodeDecodeError:
            return {"success": False, "error": "File is not a valid UTF-8 text file"}
        except PermissionError:
            return {"success": False, "error": "Permission denied"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        写入文件内容

        Args:
            path: 文件路径
            content: 文件内容
            append: 是否追加模式
        """
        # Check permission mode
        allowed, reason = _check_permission_mode("write")
        if not allowed:
            return {"success": False, "error": f"Permission denied: {reason}"}

        is_valid, error_msg, normalized_path = self._validate_path(path)
        if not is_valid:
            return {"success": False, "error": error_msg}

        try:
            # 确保父目录存在
            os.makedirs(os.path.dirname(normalized_path), exist_ok=True)

            mode = 'a' if append else 'w'
            with open(normalized_path, mode, encoding='utf-8') as f:
                f.write(content)

            stat = os.stat(normalized_path)
            return {
                "success": True,
                "path": normalized_path,
                "size": stat.st_size,
                "action": "appended" if append else "written"
            }

        except PermissionError:
            return {"success": False, "error": "Permission denied"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_file(self, filename: str, content: bytes, target_dir: str = None) -> Dict[str, Any]:
        """
        上传文件

        Args:
            filename: 文件名
            content: 文件内容（bytes）
            target_dir: 目标目录（如果为 None，使用上传目录）
        """
        # Check permission mode
        allowed, reason = _check_permission_mode("write")
        if not allowed:
            return {"success": False, "error": f"Permission denied: {reason}"}

        from app.core.config import settings

        if target_dir is None:
            target_dir = settings.UPLOAD_PATH

        is_valid, error_msg, normalized_dir = self._validate_path(target_dir)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not os.path.exists(normalized_dir):
            try:
                os.makedirs(normalized_dir, exist_ok=True)
            except Exception as e:
                return {"success": False, "error": f"Cannot create directory: {str(e)}"}

        target_path = os.path.join(normalized_dir, filename)

        # 检查路径是否安全（防止路径遍历）
        if not self.permission_service.check_path_traversal(target_path, normalized_dir):
            return {"success": False, "error": "Invalid target path"}

        try:
            with open(target_path, 'wb') as f:
                f.write(content)

            stat = os.stat(target_path)
            return {
                "success": True,
                "path": target_path,
                "name": filename,
                "size": stat.st_size
            }

        except PermissionError:
            return {"success": False, "error": "Permission denied"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """获取文件详细信息"""
        is_valid, error_msg, normalized_path = self._validate_path(path)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not os.path.exists(normalized_path):
            return {"success": False, "error": f"File does not exist: {path}"}

        try:
            stat = os.stat(normalized_path)
            ext = self._get_extension(normalized_path)
            is_dir = os.path.isdir(normalized_path)

            info = FileInfo(
                name=os.path.basename(normalized_path),
                path=normalized_path,
                is_directory=is_dir,
                size=stat.st_size if not is_dir else 0,
                modified_time=stat.st_mtime,
                extension=ext,
                mime_type=self._get_mime_type(normalized_path) if not is_dir else "directory"
            )

            return {
                "success": True,
                **info.to_dict(),
                "created_time": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_directory(self, path: str) -> Dict[str, Any]:
        """创建目录"""
        # Check permission mode
        allowed, reason = _check_permission_mode("write")
        if not allowed:
            return {"success": False, "error": f"Permission denied: {reason}"}

        is_valid, error_msg, normalized_path = self._validate_path(path)
        if not is_valid:
            return {"success": False, "error": error_msg}

        try:
            os.makedirs(normalized_path, exist_ok=True)
            return {
                "success": True,
                "path": normalized_path,
                "action": "created"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """删除文件或目录"""
        # Check permission mode
        allowed, reason = _check_permission_mode("delete")
        if not allowed:
            return {"success": False, "error": f"Permission denied: {reason}"}

        is_valid, error_msg, normalized_path = self._validate_path(path)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not os.path.exists(normalized_path):
            return {"success": False, "error": f"Path does not exist: {path}"}

        try:
            if os.path.isdir(normalized_path):
                if recursive:
                    shutil.rmtree(normalized_path)
                else:
                    os.rmdir(normalized_path)
            else:
                os.remove(normalized_path)

            return {
                "success": True,
                "path": normalized_path,
                "action": "deleted"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def copy_file(self, source: str, destination: str) -> Dict[str, Any]:
        """复制文件"""
        is_valid, error_msg, normalized_source = self._validate_path(source)
        if not is_valid:
            return {"success": False, "error": error_msg}

        is_valid, error_msg, normalized_dest = self._validate_path(destination)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not os.path.exists(normalized_source):
            return {"success": False, "error": f"Source does not exist: {source}"}

        try:
            os.makedirs(os.path.dirname(normalized_dest), exist_ok=True)
            shutil.copy2(normalized_source, normalized_dest)
            stat = os.stat(normalized_dest)
            return {
                "success": True,
                "source": normalized_source,
                "destination": normalized_dest,
                "size": stat.st_size
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_files(self, directory: str, pattern: str, recursive: bool = True) -> Dict[str, Any]:
        """
        搜索文件

        Args:
            directory: 搜索目录
            pattern: 文件名模式（支持 glob）
            recursive: 是否递归搜索
        """
        is_valid, error_msg, normalized_dir = self._validate_path(directory)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if not os.path.exists(normalized_dir):
            return {"success": False, "error": f"Directory does not exist: {directory}"}

        if not os.path.isdir(normalized_dir):
            return {"success": False, "error": f"Path is not a directory: {directory}"}

        try:
            import fnmatch
            matches = []

            if recursive:
                for root, dirs, files in os.walk(normalized_dir):
                    # 跳过隐藏目录
                    dirs[:] = [d for d in dirs if not d.startswith('.')]

                    for filename in files:
                        if fnmatch.fnmatch(filename, pattern):
                            filepath = os.path.join(root, filename)
                            try:
                                stat = os.stat(filepath)
                                matches.append({
                                    "name": filename,
                                    "path": filepath,
                                    "size": stat.st_size,
                                    "modified_time": stat.st_mtime
                                })
                            except Exception:
                                continue
            else:
                for filename in os.listdir(normalized_dir):
                    if fnmatch.fnmatch(filename, pattern):
                        filepath = os.path.join(normalized_dir, filename)
                        if os.path.isfile(filepath):
                            try:
                                stat = os.stat(filepath)
                                matches.append({
                                    "name": filename,
                                    "path": filepath,
                                    "size": stat.st_size,
                                    "modified_time": stat.st_mtime
                                })
                            except Exception:
                                continue

            return {
                "success": True,
                "directory": normalized_dir,
                "pattern": pattern,
                "matches": matches,
                "count": len(matches)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局实例
file_manager = FileManagerService()


def get_file_manager() -> FileManagerService:
    """获取文件管理服务实例"""
    return file_manager