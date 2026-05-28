"""
Workflow Loader - 工作流加载器
"""
import os
import yaml
from pathlib import Path
from typing import List, Optional

from .engine import WorkflowDefinition, WorkflowStep

async def load_workflow_from_file(file_path: str) -> Optional[WorkflowDefinition]:
    """从文件加载工作流"""
    path = Path(file_path)

    if not path.exists():
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading workflow from {file_path}: {e}")
        return None

    if not data:
        return None

    steps = []
    for step_data in data.get('steps', []):
        step = WorkflowStep(
            id=step_data.get('id', str(uuid.uuid4())),
            name=step_data.get('name', ''),
            action=step_data.get('action', ''),
            args=step_data.get('args', {}),
            continue_on_error=step_data.get('continue_on_error', False),
            max_retries=step_data.get('max_retries', 3),
            timeout=step_data.get('timeout')
        )
        steps.append(step)

    return WorkflowDefinition(
        id=data.get('id', path.stem),
        name=data.get('name', path.stem),
        description=data.get('description', ''),
        steps=steps,
        parallel=data.get('parallel', False),
        metadata=data.get('metadata', {})
    )

async def load_workflows_from_dir(directory: str) -> List[WorkflowDefinition]:
    """从目录加载所有工作流"""
    workflows = []
    path = Path(directory)

    if not path.exists():
        return workflows

    for yaml_file in path.glob("**/*.yaml"):
        workflow = await load_workflow_from_file(str(yaml_file))
        if workflow:
            workflows.append(workflow)

    for yml_file in path.glob("**/*.yml"):
        workflow = await load_workflow_from_file(str(yml_file))
        if workflow:
            workflows.append(workflow)

    return workflows

import uuid