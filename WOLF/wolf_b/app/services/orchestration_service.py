"""
Orchestration Service - 基于共享工作空间的协调服务

================================================================================
DEPRECATED - 此服务已被废弃
================================================================================

此服务用于多Agent任务编排，已被以下新架构取代：
- app/agents/main_agent.py: 单Agent直接执行模式

保留此文件是为了未来参考和可能的扩展需求。

当前主流程不再使用此服务。如需重新启用，请联系开发者。

使用方式变更：
- 旧: OrchestrationService.process_user_request() → 多Agent协作
- 新: MainAgent.think() → 直接响应

================================================================================
"""

from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

# 硬编码禁用 - 当前版本不支持任务编排
ENABLE_ORCHESTRATION_SERVICE = False


# 预留的编排接口（未来扩展用）
class OrchestrationService:
    """
    任务编排服务

    RESERVED for future extension:
    未来如果需要启用多Agent任务编排，可重新实现此服务。
    参考 cc-haha 的 TaskCreateTool、TaskUpdateTool 等实现
    """

    def __init__(self):
        self.active_workspaces: Dict[str, Any] = {}

    async def process_user_request(self, user_request: str, session_id: str = None) -> Dict[str, Any]:
        """
        处理用户请求 - 已禁用

        当前版本请使用 MainAgent.think() 代替
        """
        if not ENABLE_ORCHESTRATION_SERVICE:
            raise RuntimeError(
                "OrchestrationService is deprecated. "
                "Use MainAgent with single-agent direct execution mode instead."
            )

    async def create_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务 - 预留接口"""
        raise NotImplementedError("Future extension")

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新任务 - 预留接口"""
        raise NotImplementedError("Future extension")

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态 - 预留接口"""
        raise NotImplementedError("Future extension")


# 单例实例
orchestration_service = OrchestrationService()