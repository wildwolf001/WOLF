"""
内置工具服务 - 类似于 Claude Code 的内置工具
提供 Read, Edit, Grep, Bash, Glob, Write 等工具供 Agent 使用
"""
import os
import re
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from enum import Enum

class ToolType(str, Enum):
    READ = "Read"
    EDIT = "Edit"
    GREP = "Grep"
    GLOB = "Glob"
    WRITE = "Write"
    BASH = "Bash"
    EXISTS = "Exists"
    LIST = "list"

class ToolResult:
    """工具执行结果"""
    def __init__(self, success: bool, content: str = "", error: str = ""):
        self.success = success
        self.content = content
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error
        }

    def get(self, key: str, default=None):
        """支持 dict 风格的访问，保持向后兼容"""
        if key == "success":
            return self.success
        elif key == "content":
            return self.content
        elif key == "error":
            return self.error
        return default

    def __getitem__(self, key: str):
        """支持 dict[key] 风格访问"""
        if key == "success":
            return self.success
        elif key == "content":
            return self.content
        elif key == "error":
            return self.error
        raise KeyError(key)

class ToolsService:
    """内置工具服务 - Agent 可使用的文件系统工具"""

    def __init__(self, workspace_path: str = None):
        """
        初始化工具服务

        Args:
            workspace_path: 工作区路径，默认为配置的 work_directory
        """
        # 优先使用传入的路径，否则使用 runtime_config 中的 work_directory
        if workspace_path:
            self.workspace_path = workspace_path
        else:
            self.workspace_path = self._get_work_directory() or os.getcwd()

        # 使用 FileManagerService 来进行文件操作（带权限检查）
        from app.services.file_manager_service import get_file_manager
        self.file_manager = get_file_manager()

    def _get_work_directory(self) -> Optional[str]:
        """获取配置的工作目录"""
        try:
            from app.core.runtime_config import runtime_config
            work_dirs = runtime_config.get_additional_working_directories()
            if work_dirs:
                # 返回第一个目录
                return list(work_dirs.keys())[0]
        except Exception:
            pass
        return None

    def _resolve_path(self, path: str) -> Path:
        """解析相对路径为绝对路径"""
        p = Path(path)
        if p.is_absolute():
            # 添加到权限服务
            self._add_path_to_permissions(str(p))
            return p
        resolved = Path(self.workspace_path) / p
        self._add_path_to_permissions(str(resolved))
        return resolved

    def _add_path_to_permissions(self, path: str) -> None:
        """添加路径到权限服务"""
        try:
            from app.services.permission_service import permission_service
            permission_service.check_and_add_path(path)
        except Exception:
            pass

    def _read_file_safe(self, file_path: Path, max_size: int = 1024 * 1024) -> str:
        """安全读取文件内容"""
        if not file_path.exists():
            return f"Error: File '{file_path}' does not exist"

        if file_path.stat().st_size > max_size:
            return f"Error: File '{file_path}' is too large ({file_path.stat().st_size} bytes). Max size is {max_size} bytes."

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            return f"Error: File '{file_path}' is not a valid text file"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def _write_file_safe(self, file_path: Path, content: str) -> str:
        """安全写入文件内容"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    # ========== 内置工具实现 ==========

    async def read(self, path: str, offset: int = 0, limit: int = None) -> ToolResult:
        """
        读取文件内容

        Args:
            path: 文件路径
            offset: 起始行号 (0-indexed)
            limit: 读取行数限制
        """
        # 使用 file_manager 进行读取（带权限检查）
        result = self.file_manager.read_file(path, offset, limit)

        if result.get("success"):
            content = result.get("content", "")
            total_lines = result.get("total_lines", 0)
            read_lines = result.get("read_lines", 0)
            start_line = result.get("start_line", 1)

            prefix = ''
            if offset > 0 or limit:
                prefix = f"[Showing {read_lines} lines, starting at line {start_line} of {total_lines}]\n"

            return ToolResult(True, content=prefix + content)
        else:
            return ToolResult(False, error=result.get("error", "Read failed"))

    async def write(self, path: str, content: str, append: bool = False) -> ToolResult:
        """
        写入文件内容

        Args:
            path: 文件路径
            content: 文件内容
            append: 是否追加模式
        """
        # 使用 file_manager 进行写入（带权限检查）
        result = self.file_manager.write_file(path, content, append)

        if result.get("success"):
            action = "Appended to" if append else "Wrote to"
            return ToolResult(True, content=f"{action} {result.get('path')}")
        else:
            return ToolResult(False, error=result.get("error", "Write failed"))

    async def edit(self, path: str, old_string: str, new_string: str, regex: bool = False) -> ToolResult:
        """
        编辑文件内容

        Args:
            path: 文件路径
            old_string: 要替换的字符串
            new_string: 替换后的字符串
            regex: 是否使用正则表达式
        """
        # 先读取当前内容
        read_result = self.file_manager.read_file(path)
        if not read_result.get("success"):
            return ToolResult(False, error=read_result.get("error", "File not found"))

        content = read_result.get("content", "")
        if not content:
            return ToolResult(False, error="File is empty")

        try:
            if regex:
                new_content, count = re.subn(old_string, new_string, content, count=1)
            else:
                if old_string not in content:
                    return ToolResult(False, error=f"String not found: {old_string}")
                new_content = content.replace(old_string, new_string, 1)

            # 写入修改后的内容
            write_result = self.file_manager.write_file(path, new_content)
            if write_result.get("success"):
                return ToolResult(True, content=f"Replaced 1 occurrence in {path}")
            else:
                return ToolResult(False, error=write_result.get("error", "Write failed"))
        except Exception as e:
            return ToolResult(False, error=f"Error editing file: {str(e)}")

    async def grep(self, pattern: str, path: str = None, glob: str = None,
                   case_sensitive: bool = True, line_numbers: bool = True) -> ToolResult:
        """
        在文件中搜索文本

        Args:
            pattern: 搜索模式
            path: 搜索路径 (默认当前目录)
            glob: 文件名过滤模式 (如 "*.py")
            case_sensitive: 是否区分大小写
            line_numbers: 是否显示行号
        """
        search_path = path if path else self.workspace_path

        # 使用 file_manager 的 search_files 来搜索
        # 注意: file_manager.search_files 搜索文件名，不是文件内容
        # 这里需要用不同的实现方式

        # 直接使用文件系统搜索（因为 file_manager 不直接支持内容搜索）
        search_path_obj = self._resolve_path(search_path)
        if not search_path_obj.exists():
            return ToolResult(False, error=f"Path not found: {search_path}")

        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)

        matches = []
        try:
            if search_path_obj.is_file():
                files_to_search = [search_path_obj]
            else:
                if glob:
                    files_to_search = list(search_path_obj.rglob(glob))
                else:
                    # 搜索所有文本文件
                    text_extensions = ['.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml', '.xml', '.html', '.css']
                    files_to_search = []
                    for ext in text_extensions:
                        files_to_search.extend(search_path_obj.rglob(f'*{ext}'))

            for file_path in files_to_search[:100]:  # 限制搜索文件数量
                if file_path.is_dir() or not file_path.is_file():
                    continue

                # 跳过二进制文件和大文件
                if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_no, line in enumerate(f, 1):
                            if regex.search(line):
                                if line_numbers:
                                    matches.append(f"{file_path}:{line_no}:{line.rstrip()}")
                                else:
                                    matches.append(f"{file_path}:{line.rstrip()}")
                except (UnicodeDecodeError, PermissionError):
                    continue

        except Exception as e:
            return ToolResult(False, error=f"Error searching: {str(e)}")

        if not matches:
            return ToolResult(True, content=f"No matches found for: {pattern}")

        result_content = f"Found {len(matches)} matches for '{pattern}':\n\n" + "\n".join(matches[:100])
        if len(matches) > 100:
            result_content += f"\n\n... and {len(matches) - 100} more matches"

        return ToolResult(True, content=result_content)

    async def glob(self, pattern: str, path: str = None) -> ToolResult:
        """
        查找匹配模式的文件

        Args:
            pattern: 文件名模式 (如 "**/*.py")
            path: 搜索路径 (默认当前目录)
        """
        search_path = path if path else self.workspace_path

        # 使用 file_manager 的 search_files 来搜索
        result = self.file_manager.search_files(search_path, pattern, recursive=True)

        if result.get("success"):
            matches = result.get("matches", [])
            if not matches:
                return ToolResult(True, content=f"No files matching: {pattern}")

            result_content = f"Found {len(matches)} files matching '{pattern}':\n\n"
            result_content += "\n".join([m['path'] for m in matches[:50]])

            if len(matches) > 50:
                result_content += f"\n\n... and {len(matches) - 50} more files"

            return ToolResult(True, content=result_content)
        else:
            return ToolResult(False, error=result.get("error", "Glob failed"))

    async def exists(self, path: str) -> ToolResult:
        """
        检查文件或目录是否存在

        Args:
            path: 文件或目录路径
        """
        # 使用 file_manager 的 get_file_info 来检查
        result = self.file_manager.get_file_info(path)

        if result.get("success"):
            return ToolResult(True, content=f"{path} exists (type: {'directory' if result.get('is_directory') else 'file'}, size: {result.get('size_formatted', 'unknown')})")
        else:
            return ToolResult(True, content=f"{path} does not exist")

    async def bash(self, command: str, timeout: int = 30) -> ToolResult:
        """
        执行 Bash 命令

        Args:
            command: 要执行的命令
            timeout: 超时时间 (秒)
        """
        try:
            import platform
            is_windows = platform.system() == 'Windows'

            # 如果是 Windows 系统，将 Unix 风格的路径转换为 Windows 风格
            if is_windows:
                command = self._convert_unix_to_windows_command(command)

            # Try UTF-8 first, fallback to system locale encoding
            try:
                encoding = 'utf-8'
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                    encoding=encoding,
                    errors='replace',
                    timeout=timeout
                )
            except Exception:
                # Fallback to system locale encoding
                import locale
                encoding = locale.getpreferredencoding(False) or 'cp936'
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                    encoding=encoding,
                    errors='replace',
                    timeout=timeout
                )

            output = result.stdout
            if result.stderr:
                output += "\nSTDERR:\n" + result.stderr

            if result.returncode != 0:
                output += f"\n[Exit code: {result.returncode}]"

            return ToolResult(True, content=output)

        except subprocess.TimeoutExpired:
            return ToolResult(False, error=f"Command timed out after {timeout} seconds")
        except Exception as e:
            return ToolResult(False, error=f"Error executing command: {str(e)}")

    def _convert_unix_to_windows_command(self, command: str) -> str:
        """
        将 Unix 风格的命令转换为 Windows 风格

        例如:
        - cd /e/agent -> cd /d E:\agent
        - ls -> dir
        - pwd -> cd
        """
        import re

        original_cmd = command.strip()

        # 处理 cd /x/path 转换为 cd /d X:\path
        cd_match = re.match(r'^cd\s+/([a-z])/((?:[^\s]*)?)$', original_cmd, re.IGNORECASE)
        if cd_match:
            drive = cd_match.group(1).upper()
            path = cd_match.group(2).strip().replace('/', '\\')
            if path:
                return f'cd /d {drive}:\\{path}'
            else:
                return f'cd /d {drive}:'

        # 处理 ls 命令 - 转换为 dir
        if original_cmd.startswith('ls '):
            # ls /path -> dir "path"
            parts = original_cmd.split(None, 1)
            if len(parts) > 1:
                path = parts[1].strip()
                if path.startswith('/'):
                    # Unix 风格路径
                    path = self._convert_unix_path_to_windows(path)
                return f'dir "{path}"'
            return 'dir'

        # 处理单独的 ls
        if original_cmd == 'ls' or original_cmd == 'ls -la' or original_cmd == 'ls -l':
            return 'dir'

        # 处理 pwd 命令
        if original_cmd == 'pwd' or original_cmd.strip() == 'cd':
            return 'cd'

        # 处理 cat file 命令
        if original_cmd.startswith('cat '):
            path = original_cmd[4:].strip()
            path = self._convert_unix_path_to_windows(path)
            return f'type "{path}"'

        # 处理 find 命令 (grep) - 转换为 findstr 或使用 where
        if original_cmd.startswith('find '):
            # find "pattern" "path" -> findstr "pattern" "path"
            parts = original_cmd.split(None, 2)
            if len(parts) >= 3:
                pattern = parts[1].strip('"')
                path = self._convert_unix_path_to_windows(parts[2].strip())
                return f'findstr /C:"{pattern}" "{path}"'

        # 保持其他命令原样（让 shell 自己处理）
        return command

    def _convert_unix_path_to_windows(self, path: str) -> str:
        """将 Unix 风格的路径转换为 Windows 风格"""
        if not path:
            return path

        # /e/... -> E:\...
        if path.startswith('/'):
            match = re.match(r'^/([a-z])/(.*)$', path, re.IGNORECASE)
            if match:
                drive = match.group(1).upper()
                rest = match.group(2).replace('/', '\\')
                return f'{drive}:\\{rest}'

        return path

    async def list_directory(self, path: str = ".") -> ToolResult:
        """
        列出目录内容

        Args:
            path: 目录路径
        """
        # 使用 file_manager 的 list_directory
        result = self.file_manager.list_directory(path)

        if result.get("success"):
            directories = result.get("directories", [])
            files = result.get("files", [])

            items = []
            for d in directories:
                items.append(f"{d['name']}/ (directory)")
            for f in files:
                items.append(f"{f['name']} (file, {f.get('size_formatted', 'unknown')})")

            result_content = f"Contents of {result.get('path')}:\n\n" + "\n".join(items)
            result_content += f"\n\nTotal: {result.get('total_count', 0)} items"
            return ToolResult(True, content=result_content)
        else:
            return ToolResult(False, error=result.get("error", "List directory failed"))

    async def get_file_info(self, path: str) -> ToolResult:
        """
        获取文件信息

        Args:
            path: 文件路径
        """
        # 使用 file_manager 的 get_file_info
        result = self.file_manager.get_file_info(path)

        if result.get("success"):
            info_str = json.dumps(result, indent=2)
            return ToolResult(True, content=info_str)
        else:
            return ToolResult(False, error=result.get("error", "Get file info failed"))

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    # ========== 新增工具方法 ==========

    async def file_read(self, file_path: str, offset: int = 1, limit: int = None) -> ToolResult:
        """
        读取文件内容

        Args:
            file_path: 文件路径
            offset: 起始行号 (1-indexed)
            limit: 读取行数限制
        """
        try:
            from app.tools.file_read_tool import read_file_content
            result = read_file_content(file_path, offset, limit)
            if result.get("type") == "text":
                file_info = result.get("file", {})
                content = file_info.get("content", "")
                total_lines = file_info.get("total_lines", 0)
                read_lines = file_info.get("num_lines", 0)
                start_line = file_info.get("start_line", 1)

                prefix = f"[Showing {read_lines} lines, starting at line {start_line} of {total_lines}]\n"
                return ToolResult(True, content=prefix + content)
            elif result.get("type") == "image":
                return ToolResult(True, content=f"[Image file: {file_path}]")
            else:
                return ToolResult(True, content=str(result))
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def file_write(self, file_path: str, content: str) -> ToolResult:
        """
        写入文件内容

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        try:
            from app.tools.file_write_tool import write_file_content
            result = write_file_content(file_path, content)
            return ToolResult(True, content=f"Successfully wrote to {file_path} ({result.get('type')})")
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def file_edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
        """
        编辑文件内容

        Args:
            file_path: 文件路径
            old_string: 要替换的字符串
            new_string: 替换后的字符串
            replace_all: 是否替换所有匹配
        """
        try:
            from app.tools.file_edit_tool import edit_file_content
            result = edit_file_content(file_path, old_string, new_string, replace_all)
            return ToolResult(True, content=f"Replaced {result.get('replacements')} occurrence(s) in {file_path}")
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def file_grep(self, pattern: str, path: str = None, glob: str = None,
                       case_insensitive: bool = False, line_numbers: bool = True,
                       output_mode: str = "content", head_limit: int = 100) -> ToolResult:
        """
        在文件中搜索文本

        Args:
            pattern: 搜索模式
            path: 搜索路径 (默认当前目录)
            glob: 文件名过滤模式
            case_insensitive: 是否区分大小写
            line_numbers: 是否显示行号
            output_mode: 输出模式 (content/files_with_matches/count)
            head_limit: 限制结果数量
        """
        try:
            from app.tools.grep_tool import search_files
            result = search_files(
                pattern=pattern,
                path=path,
                glob=glob,
                output_mode=output_mode,
                show_line_numbers=line_numbers,
                case_insensitive=case_insensitive,
                head_limit=head_limit
            )
            if result.get("mode") == "files_with_matches":
                filenames = result.get("filenames", [])
                return ToolResult(True, content=f"Found {len(filenames)} files matching '{pattern}':\n\n" + "\n".join(filenames))
            elif result.get("mode") == "count":
                content = result.get("content", "")
                return ToolResult(True, content=content)
            else:
                content = result.get("content", "")
                return ToolResult(True, content=content)
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def file_glob(self, pattern: str, path: str = None) -> ToolResult:
        """
        查找匹配模式的文件

        Args:
            pattern: 文件名模式
            path: 搜索路径 (默认当前目录)
        """
        try:
            from app.tools.glob_tool import find_files
            result = find_files(pattern, path)
            filenames = result.get("filenames", [])
            truncated = result.get("truncated", False)
            content = f"Found {len(filenames)} files matching '{pattern}':\n\n" + "\n".join(filenames)
            if truncated:
                content += "\n\n(Results truncated - showing first 100)"
            return ToolResult(True, content=content)
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def scrape(self, url: str, selector: str = None, mode: str = "simple") -> ToolResult:
        """
        使用 Scrapling 抓取网页

        Args:
            url: 目标 URL
            selector: CSS 选择器（可选），如 ".article", "h1::text"
            mode: simple=HTTP请求, stealth=绕过反爬, dynamic=浏览器渲染
        """
        try:
            from scrapling.fetchers import Fetcher, StealthyFetcher, DynamicFetcher

            if mode == "stealth":
                page = StealthyFetcher.fetch(url, headless=True)
            elif mode == "dynamic":
                page = DynamicFetcher.fetch(url, headless=True)
            else:  # simple
                page = Fetcher.get(url)

            if selector:
                elements = page.css(selector).getall()
                content = "\n".join(elements) if elements else "[No matches found]"
            else:
                content = page.css('body').get() if page.css('body') else page.html

            return ToolResult(success=True, content=content[:10000])  # 限制长度
        except ImportError:
            return ToolResult(success=False, error="Scrapling not installed. Run: pip install scrapling")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def crawl(self, start_url: str, selectors: List[str], max_pages: int = 10) -> ToolResult:
        """
        使用 Scrapling Spider 爬取多个页面

        Args:
            start_url: 起始 URL
            selectors: CSS 选择器列表
            max_pages: 最大页面数
        """
        try:
            from scrapling.fetchers import Fetcher

            results = []
            seen_urls = set()

            def parse_func(response, selectors):
                for selector in selectors:
                    elements = response.css(selector).getall()
                    if elements:
                        results.append({"selector": selector, "count": len(elements), "sample": elements[:3]})

            page = Fetcher.get(start_url)
            parse_func(page, selectors)
            seen_urls.add(start_url)

            # 简单分页处理
            next_links = page.css('a::attr(href)').getall()[:max_pages-1]
            for link in next_links:
                if link not in seen_urls and link.startswith('http'):
                    try:
                        p = Fetcher.get(link)
                        parse_func(p, selectors)
                        seen_urls.add(link)
                    except:
                        pass

            content = json.dumps({"pages": len(seen_urls), "results": results}, ensure_ascii=False)
            return ToolResult(success=True, content=content)
        except ImportError:
            return ToolResult(success=False, error="Scrapling not installed")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def web_search(self, query: str, num_results: int = 5) -> ToolResult:
        """
        网络搜索

        Args:
            query: 搜索关键词
            num_results: 返回结果数量
        """
        try:
            from app.tools.web_search_tool import search_web
            result = await search_web(query, num_results)
            if result.get("success"):
                results = result.get("results", [])
                content = f"搜索结果 for '{query}':\n\n"
                for i, r in enumerate(results, 1):
                    content += f"{i}. {r.get('title', 'No title')}\n"
                    content += f"   URL: {r.get('url', 'N/A')}\n"
                    if r.get('snippet'):
                        content += f"   {r.get('snippet')}\n"
                    content += "\n"
                return ToolResult(True, content=content)
            else:
                return ToolResult(False, error=result.get("error", "Search failed"))
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def web_fetch(self, url: str, selector: str = None) -> ToolResult:
        """
        获取网页内容

        Args:
            url: 网页URL
            selector: 可选的CSS选择器
        """
        try:
            from app.tools.web_fetch_tool import fetch_web
            result = await fetch_web(url, selector)
            if result.get("success"):
                content = f"页面: {result.get('title', url)}\nURL: {url}\n\n"
                content += result.get("content", "")[:5000]
                return ToolResult(True, content=content)
            else:
                return ToolResult(False, error=result.get("error", "Fetch failed"))
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def execute_code(self, code: str, language: str = "python") -> ToolResult:
        """
        执行代码

        Args:
            code: 代码
            language: 语言 (python/javascript)
        """
        try:
            from app.tools.code_execution_sandbox import execute_code
            result = await execute_code(code, language)
            if result.get("success"):
                output = f"[{language} execution - success]\n\nOutput:\n{result.get('output', 'No output')}"
                return ToolResult(True, content=output)
            else:
                output = f"[{language} execution - failed]\n\nError:\n{result.get('error', 'Unknown error')}"
                return ToolResult(False, error=output)
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def browse(self, url: str, action: str = None, selector: str = None) -> ToolResult:
        """
        浏览器自动化

        Args:
            url: 目标URL
            action: 操作类型 (navigate/click/fill/screenshot)
            selector: 元素选择器
        """
        try:
            from app.services.browser_service import browser_service

            if action == "navigate" or not action:
                result = await browser_service.navigate(url)
            elif action == "click":
                result = await browser_service.click(selector)
            elif action == "fill":
                result = await browser_service.fill(selector, "")
            elif action == "screenshot":
                result = await browser_service.screenshot()
            else:
                result = await browser_service.navigate(url)

            if result.success:
                return ToolResult(True, content=result.content or f"Action '{action}' completed")
            else:
                return ToolResult(False, error=result.error)
        except Exception as e:
            return ToolResult(False, error=str(e))

    # ========== 工具调用接口 ==========

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具 - 统一调用 Claude Code 工具桥接器

        Args:
            tool_name: 工具名称 (支持大小写不敏感)
            tool_args: 工具参数
        """
        # 标准化工具名称（大小写不敏感）
        tool_name_lower = tool_name.lower()

        # 添加工具名称验证
        ALL_TOOLS = {
            "bash", "grep", "glob", "read", "write", "edit",
            "list", "info", "list_directory", "file_info",
            "websearch", "webfetch", "executecode", "browse",
            "scrape", "crawl", "exists", "get_file_info"
        }

        if tool_name_lower not in ALL_TOOLS:
            return {
                "success": False,
                "content": "",
                "error": f"Unknown tool: {tool_name}. Available tools: {', '.join(sorted(ALL_TOOLS))}"
            }

        bridge_tool_map = {
            "bash": "bash",
            "grep": "grep",
            "glob": "glob",
            "read": "read",
            "write": "write",
            "edit": "edit",
            "list": "list_directory",
            "info": "file_info",
            "list_directory": "list_directory",
            "file_info": "file_info",
            # 新工具
            "websearch": "websearch",
            "webfetch": "webfetch",
            "executecode": "executecode",
            "browse": "browse",
            "scrape": "scrape",
            "crawl": "crawl",
        }

        bridge_tool = bridge_tool_map.get(tool_name_lower, tool_name_lower)

        # 处理新工具
        if tool_name_lower == "websearch":
            result = await self.web_search(
                query=tool_args.get("query", ""),
                num_results=tool_args.get("num_results", 5)
            )
            return {"success": result.success, "content": result.content, "error": result.error}

        elif tool_name_lower == "webfetch":
            result = await self.web_fetch(
                url=tool_args.get("url", ""),
                selector=tool_args.get("selector")
            )
            return {"success": result.success, "content": result.content, "error": result.error}

        elif tool_name_lower == "executecode":
            result = await self.execute_code(
                code=tool_args.get("code", ""),
                language=tool_args.get("language", "python")
            )
            return {"success": result.success, "content": result.content, "error": result.error}

        elif tool_name_lower == "browse":
            result = await self.browse(
                url=tool_args.get("url", ""),
                action=tool_args.get("action"),
                selector=tool_args.get("selector")
            )
            return {"success": result.success, "content": result.content, "error": result.error}

        elif tool_name_lower == "scrape":
            result = await self.scrape(
                url=tool_args.get("url", ""),
                selector=tool_args.get("selector"),
                mode=tool_args.get("mode", "simple")
            )
            return {"success": result.success, "content": result.content, "error": result.error}

        elif tool_name_lower == "crawl":
            result = await self.crawl(
                start_url=tool_args.get("start_url", ""),
                selectors=tool_args.get("selectors", []),
                max_pages=tool_args.get("max_pages", 10)
            )
            return {"success": result.success, "content": result.content, "error": result.error}

        # 使用 Claude Code 工具桥接器
        from app.services.claude_code_tools_service import execute_claude_code_tool
        cc_result = await execute_claude_code_tool(
            bridge_tool,
            tool_args,
            self.workspace_path
        )

        return {
            "success": cc_result.success,
            "content": cc_result.content,
            "error": cc_result.error,
            "metadata": cc_result.metadata,
        }

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具的列表 - 符合 Function Calling 标准的格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "Read",
                    "description": "Read file contents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to read"},
                            "offset": {"type": "integer", "description": "Line offset to start reading", "optional": True},
                            "limit": {"type": "integer", "description": "Maximum lines to read", "optional": True}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Write",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to write"},
                            "content": {"type": "string", "description": "Content to write"},
                            "append": {"type": "boolean", "description": "Append to file instead of overwriting", "optional": True}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Edit",
                    "description": "Edit file content by replacing old_string with new_string",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to edit"},
                            "old_string": {"type": "string", "description": "Exact string to replace"},
                            "new_string": {"type": "string", "description": "Replacement string"},
                            "regex": {"type": "boolean", "description": "Treat old_string as regex pattern", "optional": True}
                        },
                        "required": ["path", "old_string", "new_string"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Grep",
                    "description": "Search for pattern in files",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Search pattern"},
                            "path": {"type": "string", "description": "Directory path to search in", "optional": True},
                            "glob": {"type": "string", "description": "File glob pattern to filter", "optional": True},
                            "case_sensitive": {"type": "boolean", "description": "Case sensitive search", "optional": True}
                        },
                        "required": ["pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Glob",
                    "description": "Find files matching a glob pattern",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Glob pattern to match"},
                            "path": {"type": "string", "description": "Directory path to search in", "optional": True}
                        },
                        "required": ["pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Bash",
                    "description": "Execute a bash command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute"},
                            "timeout": {"type": "integer", "description": "Timeout in seconds", "optional": True}
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list",
                    "description": "List directory contents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path to list", "optional": True}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Exists",
                    "description": "Check if file or directory exists",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File or directory path"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_file_info",
                    "description": "Get detailed file information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "WebSearch",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "num_results": {"type": "integer", "description": "Number of results to return", "optional": True}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "WebFetch",
                    "description": "Fetch content from a web page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to fetch"},
                            "selector": {"type": "string", "description": "CSS selector to extract content", "optional": True}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Scrape",
                    "description": "Scrape web pages using Scrapling",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to scrape"},
                            "selector": {"type": "string", "description": "CSS selector like '.article', 'h1::text'", "optional": True},
                            "mode": {"type": "string", "description": "Mode: simple=HTTP, stealth=bypass anti-bot, dynamic=browser JS", "optional": True}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Crawl",
                    "description": "Crawl multiple pages using Scrapling",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_url": {"type": "string", "description": "Starting URL"},
                            "selectors": {"type": "array", "items": {"type": "string"}, "description": "List of CSS selectors to extract"},
                            "max_pages": {"type": "integer", "description": "Maximum number of pages to crawl", "optional": True}
                        },
                        "required": ["start_url", "selectors"]
                    }
                }
            }
        ]

    def get_enhanced_status(self) -> Dict[str, Any]:
        """获取 Claude Code 增强工具状态"""
        from app.services.claude_code_tools_service import get_claude_code_tools
        bridge = get_claude_code_tools(self.workspace_path)
        return {
            "claude_code_available": bridge.is_claude_code_available(),
            "claude_code_path": bridge.claude_path,
            "bash_history_count": len(bridge.get_bash_history()),
            "workspace_path": self.workspace_path,
        }


# 全局工具服务实例
tools_service = ToolsService()
