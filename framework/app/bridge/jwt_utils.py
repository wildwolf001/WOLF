"""
JWT Utilities
"""
import time
from typing import Optional, Dict, Any
import jwt


def decode_jwt(token: str, secret: str = "") -> Dict[str, Any]:
    """Decode JWT token"""
    try:
        if secret:
            return jwt.decode(token, secret, algorithms=["HS256"])
        else:
            # Decode without verification
            return jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return {}


def encode_jwt(payload: Dict[str, Any], secret: str) -> str:
    """Encode payload into JWT"""
    return jwt.encode(payload, secret, algorithm="HS256")


def is_token_expired(token: str, secret: str = "") -> bool:
    """Check if token is expired"""
    try:
        payload = decode_jwt(token, secret)
        exp = payload.get("exp", 0)
        return time.time() >= exp
    except Exception:
        return True


def get_token_expiry(token: str) -> float:
    """Get token expiry time"""
    try:
        payload = decode_jwt(token)
        return payload.get("exp", 0)
    except Exception:
        return 0


def create_access_token(
    user_id: str,
    session_id: str,
    secret: str,
    expires_in: int = 3600
) -> str:
    """Create a new access token"""
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "exp": time.time() + expires_in,
        "iat": time.time()
    }
    return encode_jwt(payload, secret)


def create_refresh_token(
    user_id: str,
    session_id: str,
    secret: str,
    expires_in: int = 86400 * 7
) -> str:
    """Create a new refresh token"""
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "type": "refresh",
        "exp": time.time() + expires_in,
        "iat": time.time()
    }
    return encode_jwt(payload, secret)