"""
Transport Utilities
"""
import json
from typing import Dict, Any
from .base import StreamEvent


def format_sse_event(event: StreamEvent) -> str:
    """Format a stream event as SSE data"""
    data = json.dumps(event.data)
    return f"event: {event.type}\ndata: {data}\n\n"


def format_sse_data(data: Dict[str, Any], event_type: str = "message") -> str:
    """Format data as SSE"""
    data_str = json.dumps(data)
    return f"event: {event_type}\ndata: {data_str}\n\n"


def parse_sse_message(message: str) -> tuple[str, Dict[str, Any]]:
    """Parse SSE formatted message"""
    event_type = "message"
    data = {}

    for line in message.split('\n'):
        line = line.strip()
        if line.startswith('event:'):
            event_type = line[6:].strip()
        elif line.startswith('data:'):
            data_str = line[5:].strip()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = {"raw": data_str}

    return event_type, data


def create_keepalive_event() -> StreamEvent:
    """Create a keepalive event"""
    import time
    return StreamEvent(
        event_type="keepalive",
        data={"timestamp": time.time()}
    )