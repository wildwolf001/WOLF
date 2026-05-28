"""
Workflow Engine - 工作流引擎
参考 cc-haha-main/src/tools/WorkflowTool/
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger("workflow.engine")

class WorkflowStatus(str, Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    name: str
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    continue_on_error: bool = False
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'action': self.action,
            'args': self.args,
            'continue_on_error': self.continue_on_error,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
        }

@dataclass
class WorkflowDefinition:
    """工作流定义"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    parallel: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'steps': [s.to_dict() for s in self.steps],
            'parallel': self.parallel,
        }

@dataclass
class WorkflowInstance:
    """工作流实例"""
    definition: WorkflowDefinition
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: int = 0
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    start_time: Optional[Any] = None
    end_time: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'definition_id': self.definition.id,
            'status': self.status.value,
            'current_step': self.current_step,
            'results': self.results,
            'errors': self.errors,
        }

class WorkflowStepError(Exception):
    """工作流步骤错误"""
    def __init__(self, step_name: str, step_id: str, error: str):
        self.step_name = step_name
        self.step_id = step_id
        self.error = error
        super().__init__(f"Workflow step '{step_name}' (id={step_id}) failed: {error}")

class WorkflowEngine:
    """
    工作流引擎
    执行工作流定义中的步骤
    """

    def __init__(self, tool_executor: Optional[Any] = None):
        self._tool_executor = tool_executor
        self._instances: Dict[str, WorkflowInstance] = {}
        self._running: Dict[str, asyncio.Task] = {}

    async def execute(
        self,
        definition: WorkflowDefinition,
        context: Dict[str, Any]
    ) -> WorkflowInstance:
        """执行工作流"""
        instance = WorkflowInstance(
            definition=definition,
            status=WorkflowStatus.RUNNING
        )
        self._instances[definition.id] = instance

        try:
            if definition.parallel:
                results = await self._execute_parallel(definition, context)
            else:
                results = await self._execute_sequential(definition, context, instance)

            instance.status = WorkflowStatus.COMPLETED
            instance.results = results
            logger.info(f"Workflow {definition.id} completed successfully")

        except Exception as e:
            instance.status = WorkflowStatus.FAILED
            instance.errors.append(str(e))
            logger.error(f"Workflow {definition.id} failed: {e}")
            raise

        finally:
            instance.end_time = asyncio.get_event_loop().time()

        return instance

    async def _execute_sequential(
        self,
        definition: WorkflowDefinition,
        context: Dict[str, Any],
        instance: WorkflowInstance
    ) -> Dict[str, Any]:
        """顺序执行步骤"""
        results = {}

        for i, step in enumerate(definition.steps):
            instance.current_step = i

            try:
                result = await self._execute_step(step, context, results)
                results[step.id] = {"status": "success", "result": result}
                logger.info(f"Step {i+1}/{len(definition.steps)} completed: {step.name}")

            except Exception as e:
                logger.error(f"Step {i+1}/{len(definition.steps)} failed: {step.name} - {e}")

                if step.continue_on_error:
                    results[step.id] = {"status": "error", "error": str(e)}
                    instance.errors.append(f"Step {step.name}: {str(e)}")
                    continue
                else:
                    results[step.id] = {"status": "error", "error": str(e)}
                    raise WorkflowStepError(step.name, step.id, str(e))

        return results

    async def _execute_parallel(
        self,
        definition: WorkflowDefinition,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """并行执行步骤"""
        tasks = []

        for step in definition.steps:
            task = self._execute_step(step, context, {})
            tasks.append((step, task))

        step_results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)

        results = {}
        for step, result in zip([s for s, _ in tasks], step_results):
            if isinstance(result, Exception):
                results[step.id] = {"status": "error", "error": str(result)}
            else:
                results[step.id] = {"status": "success", "result": result}

        return results

    async def _execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
        previous_results: Dict[str, Any]
    ) -> Any:
        """执行单个步骤"""
        step_context = {
            **context,
            'previous_results': previous_results,
            'step_id': step.id,
            'step_name': step.name
        }

        last_error = None
        for attempt in range(step.max_retries + 1):
            try:
                if self._tool_executor:
                    result = await self._tool_executor.execute(
                        step.action,
                        step.args,
                        step_context
                    )
                else:
                    await asyncio.sleep(0.1)
                    result = f"Executed {step.action} with args {step.args}"

                return result

            except Exception as e:
                last_error = e
                if attempt < step.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Step {step.name} failed (attempt {attempt+1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Step {step.name} failed after {step.max_retries} retries: {e}")

        raise last_error

    async def stop(self, workflow_id: str) -> bool:
        """停止工作流"""
        if workflow_id in self._running:
            task = self._running[workflow_id]
            task.cancel()
            del self._running[workflow_id]

            instance = self._instances.get(workflow_id)
            if instance:
                instance.status = WorkflowStatus.STOPPED

            logger.info(f"Workflow {workflow_id} stopped")
            return True
        return False

    def get_instance(self, workflow_id: str) -> Optional[WorkflowInstance]:
        """获取工作流实例"""
        return self._instances.get(workflow_id)

    def list_instances(self) -> List[WorkflowInstance]:
        """列出所有工作流实例"""
        return list(self._instances.values())

# 全局工作流引擎实例
workflow_engine = WorkflowEngine()