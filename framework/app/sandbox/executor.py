"""
Sandbox Executor — Unified host/docker execution for agent verification
"""
import os
import asyncio
import subprocess
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SandboxResult:
    """沙箱命令执行结果"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    mode: str  # "docker" or "host"


class SandboxExecutor:
    """
    统一沙箱执行器，双模式：
    - host: subprocess 直接跑（快，无依赖）
    - docker: 容器内隔离执行（安全，需装Docker）
    """

    def __init__(
        self,
        mode: str = "auto",
        project_root: Optional[str] = None,
        temp_dir: Optional[str] = None
    ):
        """
        Args:
            mode: "auto" | "host" | "docker"
            project_root: 项目根目录路径
            temp_dir: 临时文件目录
        """
        if project_root is None:
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
        if temp_dir is None:
            temp_dir = os.path.join(project_root, "temp")

        self._project_root = project_root
        self._temp_dir = temp_dir
        self._docker_sandbox = None

        # 确定实际使用的模式
        if mode == "docker":
            self._mode = "docker"
        elif mode == "host":
            self._mode = "host"
        else:  # auto
            self._mode = self._detect_mode()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def temp_dir(self) -> str:
        return self._temp_dir

    def _detect_mode(self) -> str:
        """自动检测最佳执行模式"""
        # 优先使用 Docker（如果可用）
        if self._docker_available():
            return "docker"
        return "host"

    def _docker_available(self) -> bool:
        """检测 Docker 是否可用"""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_docker_sandbox(self):
        """懒加载 Docker 沙箱"""
        if self._mode != "docker":
            return None
        if self._docker_sandbox is None:
            from .docker import DockerSandbox
            self._docker_sandbox = DockerSandbox(
                project_root=self._project_root,
                temp_dir=self._temp_dir
            )
        return self._docker_sandbox

    async def run(
        self,
        command: str,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> SandboxResult:
        """
        执行命令

        Args:
            command: 要执行的命令
            timeout: 超时秒数
            env: 环境变量
            cwd: 工作目录 (host模式下使用)
        """
        if self._mode == "docker":
            sandbox = self._get_docker_sandbox()
            if sandbox and sandbox.is_available:
                return await sandbox.run(command, timeout, env)
            # Docker 不可用时降级到 host
            self._mode = "host"

        return await self._run_host(command, timeout, env, cwd)

    async def install_packages(
        self,
        packages: list,
        tool: str = "pip"
    ) -> SandboxResult:
        """安装依赖包"""
        if self._mode == "docker":
            sandbox = self._get_docker_sandbox()
            if sandbox and sandbox.is_available:
                return await sandbox.install_packages(packages, tool)

        # Host 模式：直接 pip install
        cmd = f"{tool} install --quiet {' '.join(packages)}"
        return await self._run_host(cmd, timeout=120)

    async def _run_host(
        self,
        command: str,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> SandboxResult:
        """在宿主机上直接执行"""
        work_dir = cwd or self._temp_dir
        os.makedirs(work_dir, exist_ok=True)

        merged_env = dict(os.environ)
        if env:
            merged_env.update(env)
        merged_env.setdefault("PYTHONUNBUFFERED", "1")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=merged_env
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            return SandboxResult(
                success=proc.returncode == 0,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                exit_code=proc.returncode,
                mode="host"
            )
        except asyncio.TimeoutError:
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                exit_code=-1,
                mode="host"
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                mode="host"
            )

    async def run_python_file(
        self,
        filepath: str,
        args: str = "",
        timeout: int = 300
    ) -> SandboxResult:
        """运行 Python 文件"""
        full_path = filepath
        if not os.path.isabs(filepath):
            full_path = os.path.join(self._temp_dir, filepath)
        return await self.run(f"python '{full_path}' {args}", timeout=timeout)

    async def run_test_suite(
        self,
        test_path: str = ".",
        timeout: int = 600
    ) -> SandboxResult:
        """运行测试套件"""
        full_path = test_path
        if not os.path.isabs(test_path):
            full_path = os.path.join(self._project_root, test_path)
        return await self.run(
            f"python -m pytest '{full_path}' -v --tb=short 2>&1",
            timeout=timeout
        )

    async def cleanup(self) -> None:
        """清理资源"""
        if self._docker_sandbox:
            await self._docker_sandbox.cleanup()
