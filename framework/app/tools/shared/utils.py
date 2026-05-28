"""
Tool Shared Utilities
"""
import os
import hashlib
from typing import Any


def compute_file_hash(path: str) -> str:
    """Compute SHA256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def safe_path(path: str, base_dir: str) -> str:
    """Ensure path is within base directory (prevent path traversal)"""
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(os.path.join(base_dir, path))
    if not abs_path.startswith(abs_base):
        raise ValueError(f"Path outside base directory: {path}")
    return abs_path


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable form"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def truncate_string(s: str, max_len: int = 100) -> str:
    """Truncate string with ellipsis"""
    if len(s) <= max_len:
        return s
    return s[:max_len-3] + "..."