"""
Logging Middleware
Request/response logging for debugging
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logging import get_logger

logger = get_logger("middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details"""
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")

        # Process request
        try:
            response = await call_next(request)

            # Log response
            duration = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} "
                f"{request.method} {request.url.path} "
                f"({duration:.3f}s)"
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error: {str(e)} "
                f"{request.method} {request.url.path} "
                f"({duration:.3f}s)"
            )
            raise


def setup_logging_middleware(app):
    """Add logging middleware to FastAPI app"""
    app.add_middleware(LoggingMiddleware)
    return app