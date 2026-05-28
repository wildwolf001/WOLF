"""
MCP Server Implementation
Handles incoming MCP tool calls and requests
"""
import asyncio
import json
from typing import Dict, List, Optional, Any, Callable, Awaitable, AsyncGenerator
from dataclasses import dataclass, field

from .types import (
    McpServerConfig,
    MCPTool,
    MCPToolResult,
    TransportType,
)


class MCPServerError(Exception):
    """Base MCP server error"""
    pass


@dataclass
class MCPRequest:
    """Incoming MCP request"""
    method: str
    params: Dict[str, Any]
    request_id: Optional[str] = None


@dataclass
class MCPResponse:
    """Outgoing MCP response"""
    result: Any
    error: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class MCPServer:
    """
    MCP Server implementation.
    Handles tool registration and request processing.
    """

    def __init__(self, name: str, config: Optional[McpServerConfig] = None):
        self._name = name
        self._config = config
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, Any] = {}
        self._capabilities: Dict[str, bool] = {
            "tools": True,
            "resources": True,
            "prompts": False,
        }
        self._server_info: Dict[str, str] = {
            "name": name,
            "version": "1.0.0"
        }
        self._running = False
        self._request_handler: Optional[Callable] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> Dict[str, bool]:
        return self._capabilities

    @property
    def server_info(self) -> Dict[str, str]:
        return self._server_info

    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool with the server"""
        self._tools[tool.name] = tool

    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True
        return False

    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a registered tool"""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[MCPTool]:
        """List all registered tools"""
        return list(self._tools.values())

    def register_resource(self, uri: str, resource: Dict[str, Any]) -> None:
        """Register a resource"""
        self._resources[uri] = resource

    def list_resources(self) -> List[Dict[str, Any]]:
        """List all registered resources"""
        return list(self._resources.values())

    def set_request_handler(self, handler: Callable[[MCPRequest], Awaitable[MCPResponse]]) -> None:
        """Set the request handler for JSON-RPC requests"""
        self._request_handler = handler

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an incoming MCP request"""
        if self._request_handler:
            return await self._request_handler(request)

        # Default handlers
        if request.method == "initialize":
            return MCPResponse(
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": self._capabilities,
                    "serverInfo": self._server_info
                },
                request_id=request.request_id
            )
        elif request.method == "tools/list":
            return MCPResponse(
                result={
                    "tools": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.input_schema
                        }
                        for t in self._tools.values()
                    ]
                },
                request_id=request.request_id
            )
        elif request.method == "tools/call":
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})

            tool = self.get_tool(tool_name)
            if not tool:
                return MCPResponse(
                    result=None,
                    error={"code": -32602, "message": f"Tool not found: {tool_name}"},
                    request_id=request.request_id
                )

            try:
                result = await self._execute_tool(tool, arguments)
                return MCPResponse(result=result, request_id=request.request_id)
            except Exception as e:
                return MCPResponse(
                    result=None,
                    error={"code": -32603, "message": str(e)},
                    request_id=request.request_id
                )
        elif request.method == "resources/list":
            return MCPResponse(
                result={"resources": self.list_resources()},
                request_id=request.request_id
            )
        elif request.method == "ping":
            return MCPResponse(result={"pong": True}, request_id=request.request_id)
        else:
            return MCPResponse(
                result=None,
                error={"code": -32601, "message": f"Method not found: {request.method}"},
                request_id=request.request_id
            )

    async def _execute_tool(self, tool: MCPTool, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute a tool (placeholder - actual implementation would call tool function)"""
        await asyncio.sleep(0.01)
        return MCPToolResult(
            content=[{"type": "text", "text": f"Executed {tool.name}"}],
            is_error=False
        )

    async def start_stdio(self) -> None:
        """Start the server with stdio transport"""
        self._running = True

        async for line in asyncio.create_task(_read_stdin()):
            if not line:
                continue

            try:
                request_data = json.loads(line)
                request = MCPRequest(
                    method=request_data.get("method", ""),
                    params=request_data.get("params", {}),
                    request_id=request_data.get("id")
                )

                response = await self.handle_request(request)

                response_data = {"jsonrpc": "2.0"}
                if response.error:
                    response_data["error"] = response.error
                else:
                    response_data["result"] = response.result
                if response.request_id:
                    response_data["id"] = response.request_id

                print(json.dumps(response_data), flush=True)

            except json.JSONDecodeError:
                pass


async def _read_stdin() -> AsyncGenerator[str, None]:
    """Read lines from stdin"""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, getattr(__import__('sys'), 'stdin'))

    while True:
        line = await reader.readline()
        if not line:
            break
        yield line.decode('utf-8').strip()


# Global MCP server registry
class MCPServerRegistry:
    """Registry for MCP servers"""

    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}

    def register_server(self, server: MCPServer) -> None:
        """Register an MCP server"""
        self._servers[server.name] = server

    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get a server by name"""
        return self._servers.get(name)

    def unregister_server(self, name: str) -> bool:
        """Unregister a server"""
        if name in self._servers:
            del self._servers[name]
            return True
        return False

    def list_servers(self) -> List[str]:
        """List all server names"""
        return list(self._servers.keys())


# Global registry
_mcp_server_registry: Optional[MCPServerRegistry] = None


def get_mcp_server_registry() -> MCPServerRegistry:
    """Get the global MCP server registry"""
    global _mcp_server_registry
    if _mcp_server_registry is None:
        _mcp_server_registry = MCPServerRegistry()
    return _mcp_server_registry


async def create_mcp_server(name: str, config: Optional[McpServerConfig] = None) -> MCPServer:
    """Create a new MCP server"""
    return MCPServer(name=name, config=config)