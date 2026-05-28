"""
Bash Tool
Executes bash commands
"""
import asyncio
import subprocess
from typing import Dict, Any, Optional


class BashTool:
    """Tool for executing bash commands"""

    def __init__(self, working_dir: Optional[str] = None):
        self._working_dir = working_dir

    async def execute(
        self,
        command: str,
        timeout: int = 60,
        environment: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute a bash command with graceful timeout handling"""
        start_time = None
        try:
            import time
            start_time = time.time()
            result = subprocess.run(
                command,
                shell=True,
                cwd=self._working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**subprocess.os.environ, **(environment or {})}
            )

            elapsed = time.time() - start_time if start_time else 0
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "elapsed": round(elapsed, 2)
            }
        except subprocess.TimeoutExpired as te:
            elapsed = time.time() - start_time if start_time else timeout
            # Capture any partial output from the timed-out process
            partial_stdout = te.stdout.decode('utf-8', errors='replace') if te.stdout else ""
            partial_stderr = te.stderr.decode('utf-8', errors='replace') if te.stderr else ""
            return {
                "success": False,
                "error": f"Command timed out after {timeout}s (elapsed: {elapsed:.1f}s)",
                "stdout": partial_stdout,
                "stderr": partial_stderr,
                "returncode": -1,
                "timedout": True,
                "elapsed": round(elapsed, 2)
            }
        except Exception as e:
            elapsed = time.time() - start_time if start_time else 0
            return {
                "success": False,
                "error": f"{type(e).__name__}: {str(e)}",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "elapsed": round(elapsed, 2)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        return {
            "name": "bash",
            "description": "Execute a bash command",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 60)",
                        "default": 60
                    }
                },
                "required": ["command"]
            }
        }


async def execute_bash(
    command: str,
    working_dir: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """Execute a bash command"""
    tool = BashTool(working_dir=working_dir)
    return await tool.execute(command, timeout=timeout)