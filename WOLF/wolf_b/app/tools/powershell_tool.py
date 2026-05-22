"""
PowerShell Tool - Execute PowerShell commands (Windows)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import subprocess
from datetime import datetime

router = APIRouter()


class PowerShellInput(BaseModel):
    command: str
    timeout: int = 30
    cwd: Optional[str] = None


class PowerShellOutput(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


@router.post("/powershell")
async def run_powershell(input: PowerShellInput) -> PowerShellOutput:
    """Execute a PowerShell command"""
    # 请求权限检查 - 参考 Claude Code，PowerShell 是高风险操作
    from app.services.permission_service import request_permission
    allowed, reason = await request_permission(
        tool_name="powershell",
        request_type="bash",
        description=f"执行 PowerShell: {input.command[:100]}...",
        command=input.command,
        risk_level="HIGH"
    )

    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    start_time = datetime.now()

    try:
        result = subprocess.run(
            ["powershell", "-Command", input.command],
            cwd=input.cwd,
            capture_output=True,
            text=True,
            timeout=input.timeout
        )

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "duration_ms": duration_ms
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Command timed out after {input.timeout} seconds")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))