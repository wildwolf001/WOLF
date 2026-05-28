"""版本化工件 — Prompt/Skill/Tool 版本化存储 (AGP 协议核心)"""
import json
import os
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VersionedArtifact:
    artifact_type: str  # "prompt" / "skill" / "tool"
    name: str
    version: str
    content: str
    performance_score: float = 0.0
    parent_version: Optional[str] = None
    changelog: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ArtifactStore:
    """版本化工件存储 (JSON 文件)"""

    def __init__(self, storage_dir: str = None):
        self._dir = storage_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "wolf_data", "evolution"
        )
        os.makedirs(self._dir, exist_ok=True)

    def _path(self, artifact_type: str, name: str, version: str) -> str:
        return os.path.join(self._dir, f"{artifact_type}_{name}_{version}.json")

    def save(self, artifact: VersionedArtifact) -> str:
        path = self._path(artifact.artifact_type, artifact.name, artifact.version)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "artifact_type": artifact.artifact_type,
                "name": artifact.name,
                "version": artifact.version,
                "content": artifact.content,
                "performance_score": artifact.performance_score,
                "parent_version": artifact.parent_version,
                "changelog": artifact.changelog,
                "created_at": artifact.created_at,
            }, f, ensure_ascii=False, indent=2)
        return path

    def load(self, artifact_type: str, name: str, version: str) -> Optional[VersionedArtifact]:
        path = self._path(artifact_type, name, version)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return VersionedArtifact(**data)

    def list_versions(self, artifact_type: str, name: str) -> List[str]:
        versions = []
        prefix = f"{artifact_type}_{name}_"
        for fname in os.listdir(self._dir):
            if fname.startswith(prefix) and fname.endswith(".json"):
                v = fname[len(prefix):-5]
                if v not in versions:
                    versions.append(v)
        return sorted(versions)
