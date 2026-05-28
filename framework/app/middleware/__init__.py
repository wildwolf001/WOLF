"""
Middleware Module
Provides middleware components for request processing
"""
from app.middleware.logging import LoggingMiddleware, setup_logging_middleware
from app.middleware.cors import CORSMiddleware
from app.middleware.auth import AuthMiddleware, optional_auth

__all__ = [
    'LoggingMiddleware',
    'setup_logging_middleware',
    'AuthMiddleware',
    'optional_auth',
]