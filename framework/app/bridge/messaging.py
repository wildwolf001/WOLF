"""
Bridge Messaging
"""
import json
from typing import Dict, Any, Optional
from .types import BridgeMessage, BridgeEventType
from ..transports.base import StreamEvent


class BridgeMessaging:
    """
    Handles bridge message formatting and parsing.
    """

    @staticmethod
    def parse_message(event: StreamEvent) -> BridgeMessage:
        """Parse a transport event into a bridge message"""
        return BridgeMessage(
            type=event.type,
            data=event.data,
            timestamp=event.data.get("timestamp")
        )

    @staticmethod
    def format_message(message: BridgeMessage) -> str:
        """Format a bridge message as JSON string"""
        return json.dumps({
            "type": message.type,
            "data": message.data,
            "session_id": message.session_id,
            "timestamp": message.timestamp
        })

    @staticmethod
    def parse_inbound(raw: Dict[str, Any]) -> Optional[BridgeMessage]:
        """Parse inbound message from server"""
        try:
            msg_type = raw.get("type", "message")
            msg_data = raw.get("data", raw)

            return BridgeMessage(
                type=msg_type,
                data=msg_data,
                session_id=raw.get("session_id"),
                timestamp=raw.get("timestamp")
            )
        except Exception:
            return None

    @staticmethod
    def create_tool_call(
        tool_name: str,
        arguments: Dict[str, Any],
        call_id: str
    ) -> BridgeMessage:
        """Create a tool call message"""
        return BridgeMessage(
            type=BridgeEventType.TOOL_CALL.value,
            data={
                "tool": tool_name,
                "arguments": arguments,
                "call_id": call_id
            }
        )

    @staticmethod
    def create_tool_result(
        call_id: str,
        tool_name: str,
        result: Any,
        success: bool = True,
        error: Optional[str] = None
    ) -> BridgeMessage:
        """Create a tool result message"""
        return BridgeMessage(
            type=BridgeEventType.TOOL_RESULT.value,
            data={
                "call_id": call_id,
                "tool": tool_name,
                "result": result,
                "success": success,
                "error": error
            }
        )

    @staticmethod
    def create_content(content: str) -> BridgeMessage:
        """Create a content message"""
        return BridgeMessage(
            type=BridgeEventType.CONTENT.value,
            data={"text": content}
        )

    @staticmethod
    def create_error(error: str, details: Optional[Dict] = None) -> BridgeMessage:
        """Create an error message"""
        return BridgeMessage(
            type=BridgeEventType.ERROR.value,
            data={"error": error, "details": details or {}}
        )