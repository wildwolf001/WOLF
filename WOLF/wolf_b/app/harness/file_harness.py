"""
FileSystemHarness - 文件系统操作封装

提供安全的文件操作，包括：
- 目录创建
- 文件读写
- 路径验证
- 安全检查
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib


class FileSystemHarness:
    """
    文件系统操作封装

    安全措施：
    1. 路径遍历检测
    2. 允许的根目录限制
    3. 操作审计日志
    """

    # 默认允许的根目录
    DEFAULT_ALLOWED_ROOTS = [
        os.getcwd(),
        tempfile.gettempdir(),
        os.path.expanduser("~")
    ]

    def __init__(self, allowed_roots: List[str] = None):
        self.allowed_roots = allowed_roots or self.DEFAULT_ALLOWED_ROOTS
        self._audit_log = []

    def _is_path_safe(self, path: str) -> bool:
        """
        检查路径是否安全

        Args:
            path: 要检查的路径

        Returns:
            是否安全
        """
        # 规范化路径
        try:
            abs_path = os.path.abspath(path)
        except Exception:
            return False

        # 检查是否在允许的根目录下
        for root in self.allowed_roots:
            try:
                root_abs = os.path.abspath(root)
                if abs_path.startswith(root_abs):
                    return True
            except Exception:
                continue

        return False

    def _check_path_traversal(self, path: str) -> bool:
        """
        检测路径遍历攻击

        Args:
            path: 路径

        Returns:
            是否有路径遍历风险
        """
        # 检查 .. 路径遍历
        normalized = os.path.normpath(path)
        return normalized.startswith('..') or '..' in normalized

    def ensure_dirs_exist(self, paths: List[str]) -> Dict[str, bool]:
        """
        确保目录存在

        Args:
            paths: 目录路径列表

        Returns:
            每个路径的创建结果
        """
        results = {}

        for path in paths:
            if not self._is_path_safe(path):
                results[path] = False
                continue

            try:
                os.makedirs(path, exist_ok=True)
                results[path] = True
                self._audit("ensure_dir", path, True)
            except Exception as e:
                results[path] = False
                self._audit("ensure_dir", path, False, str(e))

        return results

    def read_file(self, path: str, offset: int = 0, limit: int = None) -> Dict[str, Any]:
        """
        安全读取文件

        Args:
            path: 文件路径
            offset: 起始偏移
            limit: 读取限制

        Returns:
            读取结果字典
        """
        if not self._is_path_safe(path):
            return {"success": False, "error": "Path not allowed"}

        if not os.path.isfile(path):
            return {"success": False, "error": "Not a file"}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                if offset > 0:
                    f.seek(offset)

                content = f.read(limit) if limit else f.read()

            return {
                "success": True,
                "content": content,
                "path": path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        安全写入文件

        Args:
            path: 文件路径
            content: 内容
            append: 是否追加模式

        Returns:
            写入结果
        """
        if not self._is_path_safe(path):
            return {"success": False, "error": "Path not allowed"}

        try:
            # 确保目录存在
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)

            return {
                "success": True,
                "path": path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def edit_file(self, path: str, old_string: str, new_string: str) -> Dict[str, Any]:
        """
        编辑文件内容

        Args:
            path: 文件路径
            old_string: 要替换的字符串
            new_string: 新字符串

        Returns:
            编辑结果
        """
        if not self._is_path_safe(path):
            return {"success": False, "error": "Path not allowed"}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_string not in content:
                return {"success": False, "error": "old_string not found in file"}

            new_content = content.replace(old_string, new_string)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return {
                "success": True,
                "path": path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str) -> Dict[str, Any]:
        """
        删除文件

        Args:
            path: 文件路径

        Returns:
            删除结果
        """
        if not self._is_path_safe(path):
            return {"success": False, "error": "Path not allowed"}

        try:
            if os.path.isfile(path):
                os.unlink(path)
                return {"success": True}
            else:
                return {"success": False, "error": "Not a file"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_directory(self, path: str) -> Dict[str, Any]:
        """
        列出目录内容

        Args:
            path: 目录路径

        Returns:
            目录内容
        """
        if not self._is_path_safe(path):
            return {"success": False, "error": "Path not allowed"}

        if not os.path.isdir(path):
            return {"success": False, "error": "Not a directory"}

        try:
            entries = os.listdir(path)
            directories = []
            files = []

            for entry in entries:
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    directories.append({"name": entry, "path": full_path})
                else:
                    size = os.path.getsize(full_path)
                    files.append({
                        "name": entry,
                        "path": full_path,
                        "size": size
                    })

            return {
                "success": True,
                "path": path,
                "directories": directories,
                "files": files,
                "total_count": len(directories) + len(files)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        获取文件信息

        Args:
            path: 文件路径

        Returns:
            文件信息
        """
        if not self._is_path_safe(path):
            return {"success": False, "error": "Path not allowed"}

        try:
            stat = os.stat(path)
            return {
                "success": True,
                "path": path,
                "is_file": os.path.isfile(path),
                "is_dir": os.path.isdir(path),
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _audit(self, operation: str, path: str, success: bool, error: str = None):
        """审计日志"""
        self._audit_log.append({
            "operation": operation,
            "path": path,
            "success": success,
            "error": error
        })

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self._audit_log.copy()