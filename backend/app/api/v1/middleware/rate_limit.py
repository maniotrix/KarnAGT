"""
Rate Limiting Middleware for API endpoints
"""
import time
import json
from typing import Dict, Optional, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions import RateLimitExceededException


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis for distributed rate limiting"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.redis_client = None
        
        # Rate limit configurations by endpoint pattern
        self.rate_limits = {
            "auth": {"requests": 10, "window": 60},  # 10 requests per minute for auth
            "chat": {"requests": 100, "window": 60},  # 100 requests per minute for chat
            "files": {"requests": 20, "window": 60},  # 20 requests per minute for files
            "default": {"requests": 60, "window": 60},  # 60 requests per minute default
        }
        
        # Routes that are exempt from rate limiting
        self.exempt_routes = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
    
    async def get_redis_client(self):
        """Get Redis client for rate limiting"""
        if self.redis_client is None:
            try:
                # Parse Redis URL from settings
                redis_url = settings.REDIS_URL
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                await self.redis_client.ping()  # Test connection
            except Exception as e:
                print(f"Redis connection failed: {e}")
                # Fallback to in-memory rate limiting (not recommended for production)
                self.redis_client = InMemoryRateLimit()
        
        return self.redis_client
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests"""
        
        # Skip rate limiting for exempt routes
        if request.url.path in self.exempt_routes:
            return await call_next(request)
        
        # Get rate limit configuration for this endpoint
        rate_limit_config = self._get_rate_limit_config(request.url.path)
        
        # Get client identifier (user ID or IP)
        client_id = self._get_client_identifier(request)
        
        # Check rate limit
        is_allowed, retry_after = await self._check_rate_limit(
            client_id,
            request.url.path,
            rate_limit_config
        )
        
        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "error_code": "RATE_001",
                    "error_type": "rate_limit_exceeded",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        remaining, reset_time = await self._get_rate_limit_status(
            client_id,
            request.url.path,
            rate_limit_config
        )
        
        response.headers["X-RateLimit-Limit"] = str(rate_limit_config["requests"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_rate_limit_config(self, path: str) -> Dict[str, int]:
        """Get rate limit configuration for a path"""
        if "/auth/" in path:
            return self.rate_limits["auth"]
        elif "/chat/" in path:
            return self.rate_limits["chat"]
        elif "/files/" in path:
            return self.rate_limits["files"]
        else:
            return self.rate_limits["default"]
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Prefer user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fallback to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limit(
        self,
        client_id: str,
        endpoint: str,
        config: Dict[str, int]
    ) -> Tuple[bool, int]:
        """Check if request is within rate limit"""
        redis_client = await self.get_redis_client()
        
        window = config["window"]
        limit = config["requests"]
        
        # Use sliding window rate limiting
        now = int(time.time())
        window_start = now - window
        
        # Redis key for this client and endpoint
        key = f"rate_limit:{client_id}:{endpoint}"
        
        try:
            # Use Redis pipeline for atomic operations
            async with redis_client.pipeline() as pipe:
                # Remove expired entries
                await pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current requests in window
                await pipe.zcard(key)
                
                # Add current request
                await pipe.zadd(key, {str(now): now})
                
                # Set expiry
                await pipe.expire(key, window)
                
                results = await pipe.execute()
                
                current_requests = results[1]
                
                if current_requests >= limit:
                    # Rate limit exceeded
                    retry_after = window - (now % window)
                    return False, retry_after
                
                return True, 0
                
        except Exception as e:
            print(f"Rate limiting error: {e}")
            # On error, allow the request (fail open)
            return True, 0
    
    async def _get_rate_limit_status(
        self,
        client_id: str,
        endpoint: str,
        config: Dict[str, int]
    ) -> Tuple[int, int]:
        """Get current rate limit status"""
        redis_client = await self.get_redis_client()
        
        window = config["window"]
        limit = config["requests"]
        
        now = int(time.time())
        window_start = now - window
        
        key = f"rate_limit:{client_id}:{endpoint}"
        
        try:
            # Remove expired entries and count
            async with redis_client.pipeline() as pipe:
                await pipe.zremrangebyscore(key, 0, window_start)
                await pipe.zcard(key)
                results = await pipe.execute()
                
                current_requests = results[1]
                remaining = max(0, limit - current_requests)
                reset_time = now + window
                
                return remaining, reset_time
                
        except Exception as e:
            print(f"Rate limiting status error: {e}")
            return limit, now + window


class InMemoryRateLimit:
    """Fallback in-memory rate limiting (not recommended for production)"""
    
    def __init__(self):
        self.data = {}
    
    async def ping(self):
        """Mock ping method"""
        return "PONG"
    
    async def pipeline(self):
        """Mock pipeline context manager"""
        return InMemoryPipeline(self.data)
    
    async def zremrangebyscore(self, key: str, min_score: int, max_score: int):
        """Remove items by score range"""
        if key in self.data:
            self.data[key] = {k: v for k, v in self.data[key].items() if not (min_score <= v <= max_score)}
    
    async def zcard(self, key: str) -> int:
        """Count items in sorted set"""
        return len(self.data.get(key, {}))
    
    async def zadd(self, key: str, mapping: Dict[str, float]):
        """Add items to sorted set"""
        if key not in self.data:
            self.data[key] = {}
        self.data[key].update(mapping)
    
    async def expire(self, key: str, seconds: int):
        """Set expiry (no-op in memory implementation)"""
        pass


class InMemoryPipeline:
    """In-memory pipeline for rate limiting operations"""
    
    def __init__(self, data: dict):
        self.data = data
        self.operations = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def zremrangebyscore(self, key: str, min_score: int, max_score: int):
        self.operations.append(("zremrangebyscore", key, min_score, max_score))
    
    async def zcard(self, key: str):
        self.operations.append(("zcard", key))
    
    async def zadd(self, key: str, mapping: Dict[str, float]):
        self.operations.append(("zadd", key, mapping))
    
    async def expire(self, key: str, seconds: int):
        self.operations.append(("expire", key, seconds))
    
    async def execute(self):
        """Execute pipeline operations"""
        results = []
        
        for op in self.operations:
            if op[0] == "zremrangebyscore":
                _, key, min_score, max_score = op
                if key in self.data:
                    original_len = len(self.data[key])
                    self.data[key] = {k: v for k, v in self.data[key].items() if not (min_score <= v <= max_score)}
                    results.append(original_len - len(self.data[key]))
                else:
                    results.append(0)
            
            elif op[0] == "zcard":
                _, key = op
                results.append(len(self.data.get(key, {})))
            
            elif op[0] == "zadd":
                _, key, mapping = op
                if key not in self.data:
                    self.data[key] = {}
                self.data[key].update(mapping)
                results.append(len(mapping))
            
            elif op[0] == "expire":
                # No-op for in-memory implementation
                results.append(True)
        
        return results 