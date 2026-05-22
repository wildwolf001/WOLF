"""
Bash Tool - Execute shell commands
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import subprocess
import shlex
from datetime import datetime

router = APIRouter()

# Blocked commands for security
BLOCKED_COMMANDS = {
    'rm -rf /', 'rm -rf /*', 'del /f /s /q', 'format',
}


class BashInput(BaseModel):
    command: str
    timeout: int = 30
    cwd: Optional[str] = None


class BashOutput(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


def is_command_blocked(command: str) -> bool:
    """Check if command contains blocked patterns"""
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return True
    return False


def execute_bash(command: str, timeout: int = 30, cwd: Optional[str] = None) -> dict:
    """Execute a bash command"""
    # Security check
    if is_command_blocked(command):
        raise HTTPException(status_code=400, detail="Command blocked for security reasons")

    start_time = datetime.now()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "duration_ms": duration_ms
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Command timed out after {timeout} seconds")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bash")
async def bash(input: BashInput) -> BashOutput:
    """Execute a shell command"""
    try:
        # 请求权限检查 - 参考 Claude Code，Bash 是高风险操作
        from app.services.permission_service import request_permission
        allowed, reason = await request_permission(
            tool_name="bash",
            request_type="bash",
            description=f"执行命令: {input.command[:100]}...",
            command=input.command,
            risk_level="HIGH"
        )

        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

        result = execute_bash(input.command, input.timeout, input.cwd)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))