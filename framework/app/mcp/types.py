"""
MCP Types and Configuration
Model Context Protocol types for wolf_b2
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Awaitable
from enum import Enum
from pydantic import BaseModel


class TransportType(str, Enum):
    """MCP transport types"""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WS = "ws"
    SDK = "sdk"


class ServerConnectionStatus(str, Enum):
    """Server connection status"""
    CONNECTED = "connected"
    FAILED = "failed"
    NEEDS_AUTH = "needs-auth"
    PENDING = "pending"
    DISABLED = "disabled"


@dataclass
class McpStdioConfig:
    """Stdio server configuration"""
    command: str
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    transport_type: TransportType = TransportType.STDIO


@dataclass
class McpSSEConfig:
    """SSE server configuration"""
    url: str
    headers: Optional[Dict[str, str]] = None
    transport_type: TransportType = TransportType.SSE


@dataclass
class McpHTTPConfig:
    """HTTP server configuration"""
    url: str
    headers: Optional[Dict[str, str]] = None
    transport_type: TransportType = TransportType.HTTP


@dataclass
class McpWSConfig:
    """WebSocket server configuration"""
    url: str
    headers: Optional[Dict[str, str]] = None
    transport_type: TransportType = TransportType.WS


@dataclass
class McpOAuthConfig:
    """OAuth configuration for MCP server"""
    client_id: Optional[str] = None
    callback_port: Optional[int] = None
    auth_server_metadata_url: Optional[str] = None


class McpServerConfig(BaseModel):
    """MCP server configuration"""
    name: str
    transport: TransportType
    command: Optional[str] = None
    args: List[str] = []
    env: Dict[str, str] = {}
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    oauth: Optional[McpOAuthConfig] = None

    class Config:
        use_enum_values = True


@dataclass
class MCPTool:
    """MCP tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str
    original_name: Optional[str] = None


@dataclass
class MCPResource:
    """MCP resource definition"""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    server: str = ""


@dataclass
class ConnectedMCPServer:
    """Connected MCP server"""
    name: str
    config: McpServerConfig
    capabilities: Dict[str, Any]
    server_info: Optional[Dict[str, str]] = None
    instructions: Optional[str] = None
    tools: List[MCPTool] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)


class MCPServerState:
    """State of an MCP server connection"""
    status: ServerConnectionStatus
    config: McpServerConfig
    error: Optional[str] = None
    reconnect_attempt: int = 0
    max_reconnect_attempts: int = 3


@dataclass
class MCPToolResult:
    """Result of an MCP tool call"""
    content: List[Dict[str, Any]]
    is_error: bool = False
    error: Optional[str] = None


@dataclass
class MCPProgress:
    """Progress callback for MCP tool execution"""
    progress_token: Optional[str] = None
    partial: bool = False


# MCP Client interface
MCPClientCallback = Callable[[str, Any], Awaitable[None]]


@dataclass
class MCPClientConfig:
    """Configuration for MCP client"""
    servers: Dict[str, McpServerConfig]
    timeout: float = 30.0
    max_retries: int = 3