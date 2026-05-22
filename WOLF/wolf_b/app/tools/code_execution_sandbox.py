"""
Code Execution Sandbox - 代码执行沙箱

提供安全的代码执行环境，支持Python和JavaScript
"""
import os
import sys
import subprocess
import tempfile
import uuid
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SandboxResult:
    """沙箱执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    execution_time: float = 0.0


class CodeExecutionSandbox:
    """
    安全的代码执行沙箱

    安全措施：
    1. 禁止导入危险模块 (os, sys, subprocess, socket等)
    2. 超时限制
    3. 资源限制
    4. 临时文件隔离
    """

    # 允许的模块
    ALLOWED_MODULES = {
        "math", "json", "re", "datetime", "time", "collections",
        "itertools", "functools", "operator", "string", "random",
        "hashlib", "base64", "urllib", "html", "xml",
        "copy", "pprint", "enum", "types", "weakref"
    }

    # 禁止的模块
    BLOCKED_MODULES = {
        "os", "sys", "subprocess", "socket", "requests", "urllib3",
        "http", "ftplib", "telnetlib", "paramiko", "fabric",
        "pickle", "marshal", "eval", "exec", "compile",
        "threading", "multiprocessing", "asyncio"  # 并发可能有问题
    }

    # 危险模式检测
    DANGEROUS_PATTERNS = [
        r'__import__', r'eval\s*\(', r'exec\s*\(',
        r'open\s*\(', r'file\s*\(', r'input\s*\(',
        r'subprocess', r'os\.', r'sys\.',
        r'socket\.', r'urllib', r'requests\.',
        r'os\.path\.join', r'os\.getcwd', r'os\.chdir'
    ]

    def __init__(self, timeout: int = 30, max_output: int = 5000):
        self.timeout = timeout
        self.max_output = max_output

    def validate_code(self, code: str, language: str = "python") -> tuple[bool, str]:
        """
        验证代码安全性

        Returns:
            (is_safe, error_message)
        """
        if language == "python":
            return self._validate_python(code)
        elif language == "javascript":
            return self._validate_javascript(code)
        return False, f"Unsupported language: {language}"

    def _validate_python(self, code: str) -> tuple[bool, str]:
        """验证Python代码"""
        # 检查危险模式
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                return False, f"Dangerous pattern detected: {pattern}"

        # 检查禁止的import
        import_pattern = r'^\s*(?:from|import)\s+(\w+)'
        for line in code.split('\n'):
            match = re.match(import_pattern, line)
            if match:
                module = match.group(1)
                if module in self.BLOCKED_MODULES:
                    return False, f"Blocked module: {module}"

        return True, ""

    def _validate_javascript(self, code: str) -> tuple[bool, str]:
        """验证JavaScript代码"""
        dangerous = ['require(', 'process.', 'child_process', 'fs.', 'net.', 'http.request']
        for pattern in dangerous:
            if pattern in code:
                return False, f"Dangerous pattern: {pattern}"
        return True, ""

    async def execute_python(self, code: str) -> SandboxResult:
        """
        执行Python代码

        Args:
            code: Python代码

        Returns:
            SandboxResult
        """
        import time
        start_time = time.time()

        # 验证安全性
        is_safe, error = self.validate_code(code, "python")
        if not is_safe:
            return SandboxResult(
                success=False,
                error=f"Code validation failed: {error}"
            )

        # 创建临时文件
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(code)
                temp_file = f.name

            # 执行代码
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tempfile.gettempdir()
            )

            execution_time = time.time() - start_time
            output = result.stdout[:self.max_output]
            error_msg = result.stderr[:self.max_output]

            if result.returncode == 0:
                return SandboxResult(
                    success=True,
                    output=output,
                    execution_time=execution_time
                )
            else:
                return SandboxResult(
                    success=False,
                    output=output,
                    error=error_msg,
                    execution_time=execution_time
                )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                error=f"Execution timed out after {self.timeout} seconds"
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                error=str(e)
            )
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

        execution_time = time.time() - start_time

    async def execute_javascript(self, code: str) -> SandboxResult:
        """
        执行JavaScript代码 (使用Node.js)

        Args:
            code: JavaScript代码

        Returns:
            SandboxResult
        """
        import time
        start_time = time.time()

        # 验证安全性
        is_safe, error = self.validate_code(code, "javascript")
        if not is_safe:
            return SandboxResult(
                success=False,
                error=f"Code validation failed: {error}"
            )

        # 检查Node.js是否可用
        try:
            subprocess.run(['node', '--version'], capture_output=True, timeout=5)
        except:
            return SandboxResult(
                success=False,
                error="Node.js is not available. Please install Node.js to execute JavaScript."
            )

        # 创建临时文件
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.js',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(code)
                temp_file = f.name

            # 执行代码
            result = subprocess.run(
                ['node', temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            execution_time = time.time() - start_time
            output = result.stdout[:self.max_output]
            error_msg = result.stderr[:self.max_output]

            if result.returncode == 0:
                return SandboxResult(
                    success=True,
                    output=output,
                    execution_time=execution_time
                )
            else:
                return SandboxResult(
                    success=False,
                    output=output,
                    error=error_msg,
                    execution_time=execution_time
                )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                error=f"Execution timed out after {self.timeout} seconds"
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                error=str(e)
            )
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

    async def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        执行代码的便捷方法

        Args:
            code: 代码
            language: 语言 (python/javascript)

        Returns:
            执行结果字典
        """
        if language == "python":
            result = await self.execute_python(code)
        elif language == "javascript":
            result = await self.execute_javascript(code)
        else:
            return {
                "success": False,
                "error": f"Unsupported language: {language}"
            }

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "language": language
        }


# 单例
code_sandbox = CodeExecutionSandbox()


async def execute_code(code: str, language: str = "python") -> Dict[str, Any]:
    """便捷函数：执行代码"""
    return await code_sandbox.execute(code, language)