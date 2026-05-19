from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    In-Memory Rate Limiter Middleware to prevent API abuse.
    Limits each unique IP address to a defined number of requests per window.
    """
    def __init__(self, app, requests_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        # Stores client IP -> list of timestamps
        self.request_history = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Exclude Swagger/OpenAPI endpoints from rate limiting for developer convenience
        path = request.url.path
        if path.startswith("/docs") or path.startswith("/openapi.json") or path.startswith("/redoc"):
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown-ip"
        current_time = time.time()
        
        # Clean up timestamps older than the rate limiting window
        timestamps = self.request_history[client_ip]
        self.request_history[client_ip] = [t for t in timestamps if current_time - t < self.window_seconds]
        
        if len(self.request_history[client_ip]) >= self.requests_limit:
            logger.warning(f"Rate limit exceeded for client: {client_ip} on path: {path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again later."
            )
            
        # Register request timestamp
        self.request_history[client_ip].append(current_time)
        
        # Proceed with request
        response = await call_next(request)
        return response
