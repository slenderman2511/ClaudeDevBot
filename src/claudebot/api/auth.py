# .claudebot/api/auth.py
"""API authentication and authorization"""

import logging
from typing import Optional

from fastapi import HTTPException, Request, Depends
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# Header name for API key
API_KEY_HEADER = "X-API-Key"

# Optional API key header (for development)
optional_api_key = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def verify_api_key(request: Request, api_key: Optional[str] = Depends(optional_api_key)) -> bool:
    """Verify API key for non-localhost requests"""
    # Get config from app state
    config = getattr(request.app.state, "config", None)

    # If no config or no API key required, allow
    if not config or not config.server.api_key:
        # In development, allow if no key configured
        return True

    # If request is from localhost, allow without key
    client_host = request.client.host if request.client else ""
    if client_host in ["127.0.0.1", "localhost", "::1"]:
        return True

    # Check API key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Add X-API-Key header."
        )

    if api_key != config.server.api_key:
        logger.warning(f"Invalid API key attempt from {client_host}")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return True


async def verify_telegram_webhook(request: Request, x_telegram_bot_api_secret_token: Optional[str] = None) -> bool:
    """Verify Telegram webhook request"""
    # Get config
    config = getattr(request.app.state, "config", None)

    # If no secret configured, skip verification (development mode)
    if not config or not hasattr(config.server, "telegram_webhook_secret"):
        return True

    # Verify secret token
    expected_token = getattr(config.server, "telegram_webhook_secret", None)
    if expected_token and x_telegram_bot_api_secret_token != expected_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid Telegram webhook token"
        )

    return True
