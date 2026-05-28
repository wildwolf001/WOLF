"""
Workflow Registry - 工作流注册表
"""
import asyncio
from typing import Dict, List, Optional

from .engine import WorkflowDefinition, WorkflowInstance

class WorkflowRegistry:
    """Workflow注册表"""

    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        """注册工作流"""
        self._workflows[workflow.id] = workflow

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """获取工作流"""
        return self._workflows.get(workflow_id)

    def list(self) -> List[WorkflowDefinition]:
        """列出所有工作流"""
        return list(self._workflows.values())

    def unregister(self, workflow_id: str) -> bool:
        """注销工作流"""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    async def load_from_directory(self, directory: str) -> None:
        """从目录加载工作流"""
        from .loader import load_workflows_from_dir
        workflows = await load_workflows_from_dir(directory)
        for workflow in workflows:
            self.register(workflow)

# 全局注册表
workflow_registry = WorkflowRegistry()