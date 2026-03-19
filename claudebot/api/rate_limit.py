# .claudebot/api/rate_limit.py
"""Rate limiting middleware"""

import time
import logging
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def _cleanup_old_requests(self, key: str, current_time: float):
        """Remove requests older than 1 minute"""
        cutoff = current_time - 60
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > cutoff
        ]

    async def check_rate_limit(self, request: Request) -> bool:
        """Check if request is within rate limit"""
        # Get config from app state
        config = getattr(request.app.state, "config", None)

        # Use configured rate limit or default
        limit = (
            config.server.rate_limit
            if config and hasattr(config.server, "rate_limit")
            else self.requests_per_minute
        )

        # Get client identifier
        client_ip = self._get_client_ip(request)

        # Check rate limit
        current_time = time.time()
        self._cleanup_old_requests(client_ip, current_time)

        request_count = len(self.requests[client_ip])

        if request_count >= limit:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {limit} requests per minute."
            )

        # Add current request
        self.requests[client_ip].append(current_time)
        return True

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded header (when behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Use client host
        if request.client:
            return request.client.host

        return "unknown"


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for health checks
    if request.url.path in ["/api/health", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)

    # Check rate limit
    await rate_limiter.check_rate_limit(request)

    response = await call_next(request)
    return response
