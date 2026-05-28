"""
Initialize REPL Bridge
"""
import asyncio
from typing import Optional

from .repl_bridge import REPLBridge
from .repl_transport import REPLBridgeTransport


async def init_repl_bridge(
    host: str = "localhost",
    port: int = 8765
) -> REPLBridge:
    """
    Initialize a REPL bridge server.
    """
    server = await asyncio.start_server(
        lambda r, w: REPLBridge(r, w),
        host,
        port
    )

    return server


async def connect_repl_bridge(
    host: str = "localhost",
    port: int = 8765
) -> REPLBridgeTransport:
    """
    Connect to a REPL bridge server.
    """
    reader, writer = await asyncio.open_connection(host, port)
    transport = REPLBridgeTransport(reader, writer)
    await transport.connect()
    return transport