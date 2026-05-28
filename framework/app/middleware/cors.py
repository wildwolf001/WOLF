"""
CORS Middleware
Cross-Origin Resource Sharing configuration
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from typing import Callable


class CORSMiddleware(StarletteCORSMiddleware):
    """
    Extended CORS middleware with WOLF-specific defaults.
    """

    def __init__(
        self,
        app,
        allow_origins: list = None,
        allow_credentials: bool = True,
        allow_methods: list = None,
        allow_headers: list = None,
    ):
        # Default to allowing all origins for development
        # In production, this should be more restrictive
        super().__init__(
            app,
            allow_origins=allow_origins or ["*"],
            allow_credentials=allow_credentials,
            allow_methods=allow_methods or ["*"],
            allow_headers=allow_headers or ["*"],
        )


def setup_cors_middleware(app, config: dict = None):
    """Add CORS middleware to FastAPI app"""
    config = config or {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("allow_origins", ["*"]),
        allow_credentials=config.get("allow_credentials", True),
        allow_methods=config.get("allow_methods", ["*"]),
        allow_headers=config.get("allow_headers", ["*"]),
    )

    return app