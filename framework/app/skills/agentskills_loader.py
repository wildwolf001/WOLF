"""Agent Skills 开放标准加载器 — agentskills.io 兼容"""
import os
import yaml
from typing import Optional, Dict, List


class AgentSkillPackage:
    """标准 Agent Skill 包"""
    def __init__(self, path: str):
        self.path = path
        self.name = ""
        self.description = ""
        self.version = ""
        self._raw_frontmatter = {}
        self._body = ""
        self._references: Dict[str, str] = {}  # filename -> content
        self._loaded = False

    def load(self) -> bool:
        """解析 SKILL.md"""
        skill_md = os.path.join(self.path, "SKILL.md")
        if not os.path.exists(skill_md):
            return False
        with open(skill_md, "r", encoding="utf-8") as f:
            raw = f.read()

        # 解析 YAML frontmatter + Markdown body
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                try:
                    self._raw_frontmatter = yaml.safe_load(parts[1]) or {}
                except Exception:
                    self._raw_frontmatter = {}
                self._body = parts[2].strip()
        else:
            self._body = raw

        self.name = self._raw_frontmatter.get("name", os.path.basename(self.path))
        self.description = self._raw_frontmatter.get("description", "")
        self.version = self._raw_frontmatter.get("version", "0.1.0")
        self._loaded = True
        return True

    def get_metadata(self) -> dict:
        """Layer 1: 元数据 (始终在 System Prompt)"""
        return {"name": self.name, "description": self.description, "version": self.version}

    def get_body(self) -> str:
        """Layer 2: SKILL.md 正文"""
        return self._body

    def get_reference(self, filename: str) -> Optional[str]:
        """Layer 3: 按需加载 references/ 文件"""
        if filename in self._references:
            return self._references[filename]
        ref_path = os.path.join(self.path, "references", filename)
        if os.path.exists(ref_path):
            with open(ref_path, "r", encoding="utf-8") as f:
                self._references[filename] = f.read()
            return self._references[filename]
        return None


class AgentSkillsLoader:
    """批量加载 + 渐进式披露"""

    def __init__(self):
        self._skills: Dict[str, AgentSkillPackage] = {}

    def load_from_dir(self, dir_path: str) -> int:
        """从目录加载所有 Skill (递归)"""
        count = 0
        if not os.path.isdir(dir_path):
            return 0
        for entry in os.listdir(dir_path):
            skill_path = os.path.join(dir_path, entry)
            if os.path.isdir(skill_path) and os.path.exists(os.path.join(skill_path, "SKILL.md")):
                skill = AgentSkillPackage(skill_path)
                if skill.load():
                    self._skills[skill.name] = skill
                    count += 1
        return count

    def get_all_metadata(self) -> List[dict]:
        """渐进式披露 Layer 1: 所有 Skill 的元数据索引"""
        return [s.get_metadata() for s in self._skills.values()]

    def get_skill(self, name: str) -> Optional[AgentSkillPackage]:
        return self._skills.get(name)

    def list_names(self) -> List[str]:
        return list(self._skills.keys())
