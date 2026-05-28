"""
MCP Client Implementation
Handles MCP server connections and tool calls
"""
import asyncio
import json
import subprocess
from typing import Dict, List, Optional, Any, Callable, Awaitable, AsyncGenerator
from dataclasses import dataclass, field

from .types import (
    McpServerConfig,
    MCPTool,
    MCPResource,
    ConnectedMCPServer,
    MCPServerState,
    MCPToolResult,
    MCPProgress,
    TransportType,
    ServerConnectionStatus,
)


class MCPClientError(Exception):
    """Base MCP client error"""
    pass


class MCPConnectionError(MCPClientError):
    """Connection failed error"""
    pass


class MCPToolNotFoundError(MCPClientError):
    """Tool not found error"""
    pass


@dataclass
class MCPToolCallRequest:
    """Request to call an MCP tool"""
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]
    progress_callback: Optional[Callable[[MCPProgress], Awaitable[None]]] = None


@dataclass
class MCPToolCallResponse:
    """Response from an MCP tool call"""
    success: bool
    result: Optional[MCPToolResult] = None
    error: Optional[str] = None


class MCPClient:
    """
    MCP Client implementation.
    Manages connections to MCP servers and tool execution.
    """

    def __init__(self, config: Optional[Dict[str, McpServerConfig]] = None):
        self._servers: Dict[str, ConnectedMCPServer] = {}
        self._server_states: Dict[str, MCPServerState] = {}
        self._config: Dict[str, McpServerConfig] = config or {}
        self._running = False
        self._connection_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, server_name: str, config: McpServerConfig) -> ConnectedMCPServer:
        """
        Connect to an MCP server.
        """
        if server_name in self._servers:
            return self._servers[server_name]

        transport_type = config.transport

        try:
            if transport_type == TransportType.STDIO:
                server = await self._connect_stdio(server_name, config)
            elif transport_type == TransportType.SSE:
                server = await self._connect_sse(server_name, config)
            elif transport_type == TransportType.HTTP:
                server = await self._connect_http(server_name, config)
            elif transport_type == TransportType.WS:
                server = await self._connect_ws(server_name, config)
            else:
                raise MCPConnectionError(f"Unsupported transport type: {transport_type}")

            self._servers[server_name] = server
            self._server_states[server_name] = MCPServerState(
                status=ServerConnectionStatus.CONNECTED,
                config=config
            )
            return server

        except Exception as e:
            self._server_states[server_name] = MCPServerState(
                status=ServerConnectionStatus.FAILED,
                config=config,
                error=str(e)
            )
            raise MCPConnectionError(f"Failed to connect to {server_name}: {e}")

    async def _connect_stdio(
        self,
        server_name: str,
        config: McpServerConfig
    ) -> ConnectedMCPServer:
        """
        Connect using stdio transport.
        Spawns the MCP server as a subprocess.
        """
        if not config.command:
            raise MCPConnectionError("No command specified for stdio transport")

        # Build environment
        env = dict(config.env) if config.env else {}
        env.update({
            "MCP_SERVER_NAME": server_name,
        })

        # Start subprocess
        process = await asyncio.create_subprocess_exec(
            config.command,
            *config.args,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Note: Full stdio implementation would use JSON-RPC over stdin/stdout
        # For now, create a placeholder connected server
        return ConnectedMCPServer(
            name=server_name,
            config=config,
            capabilities={"tools": True, "resources": True},
            server_info={"name": server_name, "version": "1.0.0"}
        )

    async def _connect_sse(
        self,
        server_name: str,
        config: McpServerConfig
    ) -> ConnectedMCPServer:
        """Connect using SSE transport"""
        # SSE transport implementation
        return ConnectedMCPServer(
            name=server_name,
            config=config,
            capabilities={"tools": True, "resources": True},
            server_info={"name": server_name, "version": "1.0.0"}
        )

    async def _connect_http(
        self,
        server_name: str,
        config: McpServerConfig
    ) -> ConnectedMCPServer:
        """Connect using HTTP transport"""
        return ConnectedMCPServer(
            name=server_name,
            config=config,
            capabilities={"tools": True, "resources": True},
            server_info={"name": server_name, "version": "1.0.0"}
        )

    async def _connect_ws(
        self,
        server_name: str,
        config: McpServerConfig
    ) -> ConnectedMCPServer:
        """Connect using WebSocket transport"""
        return ConnectedMCPServer(
            name=server_name,
            config=config,
            capabilities={"tools": True, "resources": True},
            server_info={"name": server_name, "version": "1.0.0"}
        )

    async def disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server"""
        if server_name in self._servers:
            del self._servers[server_name]

        if server_name in self._server_states:
            self._server_states[server_name].status = ServerConnectionStatus.DISABLED

        if server_name in self._connection_tasks:
            task = self._connection_tasks[server_name]
            task.cancel()
            del self._connection_tasks[server_name]

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> MCPToolResult:
        """
        Call an MCP tool on a connected server.
        """
        if server_name not in self._servers:
            raise MCPConnectionError(f"Server not connected: {server_name}")

        server = self._servers[server_name]

        # Find the tool
        tool = None
        for t in server.tools:
            if t.name == tool_name or t.original_name == tool_name:
                tool = t
                break

        if not tool:
            # Tool not found in cache, assume server has it
            pass

        # Simulate tool call - actual implementation would use JSON-RPC
        await asyncio.sleep(0.01)

        return MCPToolResult(
            content=[{"type": "text", "text": f"Called {tool_name} on {server_name}"}],
            is_error=False
        )

    async def list_tools(self, server_name: str) -> List[MCPTool]:
        """List available tools from a server"""
        if server_name not in self._servers:
            return []
        return self._servers[server_name].tools

    async def list_resources(self, server_name: str) -> List[MCPResource]:
        """List available resources from a server"""
        if server_name not in self._servers:
            return []
        return self._servers[server_name].resources

    def get_server_state(self, server_name: str) -> Optional[MCPServerState]:
        """Get the state of a server"""
        return self._server_states.get(server_name)

    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return [name for name, state in self._server_states.items()
                if state.status == ServerConnectionStatus.CONNECTED]

    async def reconnect(self, server_name: str) -> bool:
        """Attempt to reconnect to a server"""
        if server_name not in self._server_states:
            return False

        state = self._server_states[server_name]
        if state.reconnect_attempt >= state.max_reconnect_attempts:
            return False

        state.reconnect_attempt += 1
        state.status = ServerConnectionStatus.PENDING

        try:
            await self.connect(server_name, state.config)
            return True
        except Exception:
            return False


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def create_mcp_client(config: Optional[Dict[str, McpServerConfig]] = None) -> MCPClient:
    """Create a new MCP client"""
    return MCPClient(config=config)