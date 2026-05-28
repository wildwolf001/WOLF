"""
Task Output Manager - 任务输出管理器
参考 cc-haha-main/src/utils/task/diskOutput.ts
"""
import os
import asyncio
import aiofiles
from pathlib import Path
from typing import AsyncGenerator, Optional
from ..utils.logging import get_logger

logger = get_logger("tasks.output")

def get_task_output_path(task_id: str) -> str:
    """获取任务输出文件路径"""
    cache_dir = Path.home() / ".wolf" / "tasks"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return str(cache_dir / f"{task_id}.output")

class TaskOutputManager:
    """
    任务输出管理器
    管理任务输出的读写和持久化
    """
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.output_path = get_task_output_path(task_id)
        self._offset = 0
        self._lock = asyncio.Lock()

    async def write(self, data: str) -> int:
        """
        追加写入输出
        返回写入的字节数
        """
        async with self._lock:
            try:
                async with aiofiles.open(self.output_path, 'a', encoding='utf-8') as f:
                    await f.write(data)
                    await f.flush()
                return len(data.encode('utf-8'))
            except Exception as e:
                logger.error(f"Failed to write task output: {e}")
                return 0

    async def read(self, offset: int = 0) -> str:
        """读取输出内容"""
        if not os.path.exists(self.output_path):
            return ""
        
        try:
            async with aiofiles.open(self.output_path, 'r', encoding='utf-8') as f:
                await f.seek(offset)
                content = await f.read()
            self._offset = offset + len(content)
            return content
        except Exception as e:
            logger.error(f"Failed to read task output: {e}")
            return ""

    async def read_lines(self, offset: int = 0, limit: int = 100) -> list[str]:
        """读取输出行"""
        content = await self.read(offset)
        lines = content.split('\n')
        return lines[:limit]

    async def stream(self, offset: int = 0) -> AsyncGenerator[str, None]:
        """流式读取输出"""
        while True:
            content = await self.read(offset)
            if content:
                yield content
            await asyncio.sleep(0.1)

    async def clear(self) -> None:
        """清空输出"""
        async with self._lock:
            try:
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                self._offset = 0
            except Exception as e:
                logger.error(f"Failed to clear task output: {e}")

    def get_size(self) -> int:
        """获取当前输出大小"""
        if os.path.exists(self.output_path):
            return os.path.getsize(self.output_path)
        return 0

    @property
    def offset(self) -> int:
        """获取当前偏移量"""
        return self._offset

    async def exists(self) -> bool:
        """检查输出文件是否存在"""
        return os.path.exists(self.output_path)

class TaskOutputReader:
    """
    任务输出读取器 - 用于外部读取任务输出
    """
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.output_path = get_task_output_path(task_id)
        self._last_offset = 0

    async def read_new(self) -> str:
        """读取新内容"""
        content = await self._read_from_offset(self._last_offset)
        self._last_offset += len(content.encode('utf-8'))
        return content

    async def read_all(self) -> str:
        """读取全部内容"""
        return await self._read_from_offset(0)

    async def _read_from_offset(self, offset: int) -> str:
        """从指定偏移读取"""
        if not os.path.exists(self.output_path):
            return ""
        
        try:
            async with aiofiles.open(self.output_path, 'r', encoding='utf-8') as f:
                await f.seek(offset)
                return await f.read()
        except Exception as e:
            logger.error(f"Failed to read task output: {e}")
            return ""

    async def get_delta(self) -> str:
        """获取增量输出"""
        return await self.read_new()

async def init_task_output_as_symlink(task_id: str, target_path: str) -> bool:
    """
    初始化任务输出为符号链接
    用于将任务输出链接到指定路径
    """
    output_path = get_task_output_path(task_id)
    
    try:
        # 确保目标目录存在
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)
        
        # 如果输出文件已存在，先删除
        if os.path.exists(output_path):
            os.remove(output_path)
        
        # 创建符号链接
        os.symlink(target_path, output_path)
        logger.info(f"Created symlink: {output_path} -> {target_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create symlink: {e}")
        return False

async def get_task_output_size(task_id: str) -> int:
    """获取任务输出大小"""
    output_path = get_task_output_path(task_id)
    if os.path.exists(output_path):
        return os.path.getsize(output_path)
    return 0

def ensure_task_output_dir() -> str:
    """确保任务输出目录存在，返回路径"""
    cache_dir = Path.home() / ".wolf" / "tasks"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return str(cache_dir)
