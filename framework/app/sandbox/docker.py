"""
Docker Sandbox — Isolated execution environment for agent verification
"""
import os
import asyncio
import subprocess
import shutil
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SandboxResult:
    """沙箱命令执行结果"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    mode: str  # "docker" or "host"


class DockerSandbox:
    """
    Docker 容器沙箱

    为 agent 验证提供隔离的执行环境：
    - 项目目录只读挂载到 /workspace
    - temp/ 目录读写挂载到 /workspace/temp
    - 基础镜像包含 python, node, git
    """

    BASE_IMAGE = "python:3.11-slim"
    SANDBOX_IMAGE = "wolf-sandbox:latest"
    CONTAINER_PREFIX = "wolf-sandbox-"

    def __init__(self, project_root: str, temp_dir: str):
        self._project_root = os.path.abspath(project_root)
        self._temp_dir = os.path.abspath(temp_dir)
        self._available: Optional[bool] = None

    @property
    def is_available(self) -> bool:
        """检查 Docker 是否可用"""
        if self._available is None:
            self._available = self._check_docker()
        return self._available

    def _check_docker(self) -> bool:
        """检测 docker CLI 是否可用"""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    async def ensure_image(self) -> bool:
        """确保沙箱镜像存在，不存在则构建"""
        if not self.is_available:
            return False

        # 检查镜像是否存在
        result = subprocess.run(
            ["docker", "images", "-q", self.SANDBOX_IMAGE],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            return True

        # 构建镜像
        dockerfile = os.path.join(self._temp_dir, "Dockerfile.sandbox")
        self._write_dockerfile(dockerfile)

        proc = await asyncio.create_subprocess_exec(
            "docker", "build", "-t", self.SANDBOX_IMAGE, "-f", dockerfile, ".",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._temp_dir
        )
        stdout, stderr = await proc.communicate()

        # 清理 Dockerfile
        try:
            os.remove(dockerfile)
        except Exception:
            pass

        return proc.returncode == 0

    def _write_dockerfile(self, path: str) -> None:
        """写入沙箱 Dockerfile"""
        content = f"""FROM {self.BASE_IMAGE}

# Install common tools
RUN apt-get update && apt-get install -y --no-install-recommends \\
    git \\
    curl \\
    ca-certificates \\
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \\
    apt-get install -y nodejs && \\
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/temp
CMD ["/bin/bash"]
"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    async def run(
        self,
        command: str,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """
        在 Docker 容器中执行命令

        Args:
            command: 要执行的 bash 命令
            timeout: 超时秒数
            env: 额外的环境变量

        Returns:
            SandboxResult
        """
        if not self.is_available:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="Docker not available",
                exit_code=-1,
                mode="host"
            )

        # 确保镜像存在
        has_image = await self.ensure_image()
        if not has_image:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="Failed to build sandbox image",
                exit_code=-1,
                mode="host"
            )

        # 生成唯一容器名
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        container_name = f"{self.CONTAINER_PREFIX}{ts}"

        # 构建 docker run 命令
        docker_args = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--network", "none",  # 无网络，安全
            "-v", f"{self._project_root}:/workspace:ro",
            "-v", f"{self._temp_dir}:/workspace/temp:rw",
            "-w", "/workspace/temp",
            "--memory", "1g",
            "--cpus", "2",
            "--stop-timeout", "5",
        ]

        # 环境变量
        env_vars = env or {}
        env_vars.setdefault("HOME", "/root")
        env_vars.setdefault("PYTHONUNBUFFERED", "1")
        for k, v in env_vars.items():
            docker_args.extend(["-e", f"{k}={v}"])

        docker_args.append(self.SANDBOX_IMAGE)
        docker_args.extend(["bash", "-c", command])

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            return SandboxResult(
                success=proc.returncode == 0,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                exit_code=proc.returncode,
                mode="docker"
            )
        except asyncio.TimeoutError:
            # 强制停止容器
            try:
                subprocess.run(
                    ["docker", "kill", container_name],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                exit_code=-1,
                mode="docker"
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                mode="docker"
            )

    async def install_packages(self, packages: List[str], tool: str = "pip") -> SandboxResult:
        """在沙箱中安装包"""
        if tool == "pip":
            cmd = f"pip install --no-cache-dir {' '.join(packages)}"
        elif tool == "npm":
            cmd = f"npm install --no-save {' '.join(packages)}"
        else:
            return SandboxResult(False, "", f"Unknown tool: {tool}", -1, "docker")

        return await self.run(cmd, timeout=120)

    async def cleanup(self) -> None:
        """清理残留的沙箱容器"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.CONTAINER_PREFIX}", "--format", "{{.ID}}"],
                capture_output=True, text=True, timeout=10
            )
            for container_id in result.stdout.strip().split('\n'):
                if container_id:
                    subprocess.run(
                        ["docker", "rm", "-f", container_id],
                        capture_output=True, timeout=5
                    )
        except Exception:
            pass
