"""
Authentication Middleware
JWT and session-based authentication
"""
from typing import Optional, Callable
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logging import get_logger

logger = get_logger("middleware.auth")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling authentication.
    Extracts and validates JWT tokens or session IDs.
    """

    def __init__(
        self,
        app,
        public_paths: list = None,
        jwt_secret: str = None,
    ):
        super().__init__(app)
        self._public_paths = public_paths or ["/health", "/", "/api/v1/health"]
        self._jwt_secret = jwt_secret or "default-secret-change-in-production"

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with authentication"""
        # Skip auth for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Extract token from header
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # Validate token (placeholder - would use actual JWT validation)
        if token:
            # In production, validate JWT here
            request.state.user_id = self._extract_user_id(token)
            request.state.authenticated = True
        else:
            request.state.user_id = None
            request.state.authenticated = False

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)"""
        return any(path.startswith(p) for p in self._public_paths)

    def _extract_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from token"""
        # Placeholder - would decode JWT
        return None


def optional_auth(request: Request) -> Optional[str]:
    """
    Helper function to get user ID from request.
    Returns None if not authenticated.
    """
    if hasattr(request.state, "user_id"):
        return request.state.user_id
    return None


def require_auth(request: Request) -> str:
    """
    Helper function to require authentication.
    Raises HTTPException if not authenticated.
    """
    user_id = optional_auth(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id