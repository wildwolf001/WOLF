"""
Prompt 版本管理 — save / load / rollback / diff / list
JSON 文件持久化 + 语义化版本号
"""
import json
import os
import hashlib
from typing import List, Optional
from datetime import datetime
from .core.schemas import PromptVersion
from .core.constants import VERSION_STORAGE_DIR


class PromptVersioning:
    """Prompt 版本管理器"""

    def __init__(self, storage_dir: str = None):
        self._storage_dir = storage_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            VERSION_STORAGE_DIR
        )
        os.makedirs(self._storage_dir, exist_ok=True)

    def _version_path(self, name: str, version: str) -> str:
        return os.path.join(self._storage_dir, f"{name}_{version}.json")

    def _index_path(self, name: str) -> str:
        return os.path.join(self._storage_dir, f"{name}_index.json")

    def save(self, version: PromptVersion) -> str:
        """保存版本 → 返回文件路径"""
        path = self._version_path(version.name, version.version)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "name": version.name,
                "version": version.version,
                "content": version.content,
                "parent_version": version.parent_version,
                "performance_score": version.performance_score,
                "changelog": version.changelog,
                "created_at": version.created_at,
                "content_hash": hashlib.md5(version.content.encode()).hexdigest()
            }, f, ensure_ascii=False, indent=2)

        # 更新索引
        self._update_index(version.name, version.version)
        return path

    def load(self, name: str, version: str = "latest") -> Optional[PromptVersion]:
        """加载版本"""
        if version == "latest":
            version = self._get_latest_version(name)
            if not version:
                return None
        path = self._version_path(name, version)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PromptVersion(**{k: v for k, v in data.items() if k != "content_hash"})

    def rollback(self, name: str, to_version: str) -> Optional[PromptVersion]:
        """回滚到指定版本"""
        target = self.load(name, to_version)
        if not target:
            return None
        current = self.load(name, "latest")
        new_version = PromptVersion(
            name=name,
            version=self._next_version(name),
            content=target.content,
            parent_version=current.version if current else None,
            changelog=[f"Rollback from {current.version if current else '?'} to {to_version}"],
            created_at=datetime.now().isoformat()
        )
        self.save(new_version)
        return new_version

    def list_versions(self, name: str) -> List[str]:
        """列出所有版本号"""
        path = self._index_path(name)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("versions", [])

    def diff(self, name: str, v1: str, v2: str) -> str:
        """对比两个版本的差异"""
        p1 = self.load(name, v1)
        p2 = self.load(name, v2)
        if not p1 or not p2:
            return ""
        lines1 = p1.content.split("\n")
        lines2 = p2.content.split("\n")
        diff = []
        for i, (l1, l2) in enumerate(zip(lines1, lines2)):
            if l1 != l2:
                diff.append(f"Line {i+1}:\n  - {l1}\n  + {l2}")
        if len(lines1) > len(lines2):
            for i in range(len(lines2), len(lines1)):
                diff.append(f"Line {i+1}:\n  - {lines1[i]}")
        elif len(lines2) > len(lines1):
            for i in range(len(lines1), len(lines2)):
                diff.append(f"Line {i+1}:\n  + {lines2[i]}")
        return "\n".join(diff) if diff else "No differences"

    def _update_index(self, name: str, version: str):
        path = self._index_path(name)
        versions = self.list_versions(name)
        if version not in versions:
            versions.append(version)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"versions": versions, "updated": datetime.now().isoformat()}, f)

    def _get_latest_version(self, name: str) -> Optional[str]:
        versions = self.list_versions(name)
        return versions[-1] if versions else None

    def _next_version(self, name: str) -> str:
        versions = self.list_versions(name)
        if not versions:
            return "v1.0.0"
        # 简单递增 patch 版本
        last = versions[-1].lstrip("v")
        major, minor, patch = map(int, last.split("."))
        return f"v{major}.{minor}.{patch + 1}"


_versioning: Optional[PromptVersioning] = None


def get_prompt_versioning() -> PromptVersioning:
    global _versioning
    if _versioning is None:
        _versioning = PromptVersioning()
    return _versioning
