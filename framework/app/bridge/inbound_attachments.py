"""
Inbound Attachments Handler
"""
import json
import base64
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class Attachment:
    """File attachment"""
    filename: str
    content_type: str
    data: bytes
    size: int


class InboundAttachments:
    """
    Handles inbound file attachments.
    """

    def __init__(self, max_size: int = 10 * 1024 * 1024):  # 10MB default
        self._max_size = max_size
        self._attachments: Dict[str, Attachment] = {}

    async def receive_attachment(
        self,
        attachment_id: str,
        filename: str,
        content_type: str,
        data: bytes
    ) -> Optional[Attachment]:
        """Receive and store an attachment"""
        if len(data) > self._max_size:
            return None

        attachment = Attachment(
            filename=filename,
            content_type=content_type,
            data=data,
            size=len(data)
        )
        self._attachments[attachment_id] = attachment
        return attachment

    def get_attachment(self, attachment_id: str) -> Optional[Attachment]:
        """Get an attachment by ID"""
        return self._attachments.get(attachment_id)

    def remove_attachment(self, attachment_id: str) -> None:
        """Remove an attachment"""
        if attachment_id in self._attachments:
            del self._attachments[attachment_id]

    def parse_base64_attachment(
        self,
        b64_data: str,
        filename: str,
        content_type: str = "application/octet-stream"
    ) -> Optional[Attachment]:
        """Parse a base64-encoded attachment"""
        try:
            data = base64.b64decode(b64_data)
            return Attachment(
                filename=filename,
                content_type=content_type,
                data=data,
                size=len(data)
            )
        except Exception:
            return None


import asyncio