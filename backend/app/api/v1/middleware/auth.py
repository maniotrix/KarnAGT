"""
Authentication Middleware for JWT Token Processing
"""
import time
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security import security
from app.core.exceptions import (
    AuthenticationException,
    InvalidTokenException,
    TokenExpiredException
)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle JWT authentication and add user context to requests"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Routes that don't require authentication
        self.public_routes = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
        }
        
        # Routes that handle their own authentication (bypass middleware auth)
        self.self_auth_routes = {
            "/api/v1/proxy/",  # File proxy routes handle service-to-service auth
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add authentication context"""
        start_time = time.time()
        
        # Skip authentication for public routes
        if request.url.path in self.public_routes:
            response = await call_next(request)
            self._add_timing_header(response, start_time)
            return response
        
        # Skip middleware auth for routes that handle their own authentication
        if any(request.url.path.startswith(route) for route in self.self_auth_routes):
            response = await call_next(request)
            self._add_timing_header(response, start_time)
            return response
        
        # Skip authentication for static files and health checks
        if (request.url.path.startswith("/static/") or 
            request.url.path.startswith("/favicon") or
            request.url.path.endswith("/health")):
            response = await call_next(request)
            self._add_timing_header(response, start_time)
            return response
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        token = None
        user_id = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Verify token and extract user ID
            try:
                payload = security.verify_token(token)
                if payload:
                    user_id = payload.get("sub")
                    # Add user context to request state
                    request.state.user_id = user_id
                    request.state.token_payload = payload
                    request.state.authenticated = True
                else:
                    request.state.authenticated = False
            except Exception:
                request.state.authenticated = False
        else:
            request.state.authenticated = False
        
        # Add token and user info to request state
        request.state.token = token
        request.state.user_id = user_id
        
        try:
            response = await call_next(request)
            self._add_timing_header(response, start_time)
            return response
        except Exception as e:
            # Handle authentication exceptions
            if isinstance(e, (AuthenticationException, InvalidTokenException, TokenExpiredException)):
                return JSONResponse(
                    status_code=e.status_code,
                    content={
                        "detail": e.detail,
                        "error_code": getattr(e, "error_code", None),
                        "error_type": getattr(e, "error_type", None)
                    },
                    headers=getattr(e, "headers", {})
                )
            
            # Re-raise other exceptions
            raise e
    
    def _add_timing_header(self, response: Response, start_time: float):
        """Add processing time header to response"""
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(f"{process_time:.4f}")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests with authentication context"""
    
    async def dispatch(self, request: Request, call_next):
        """Log request details"""
        start_time = time.time()
        
        # Get user context from request state (set by AuthenticationMiddleware)
        user_id = getattr(request.state, "user_id", None)
        authenticated = getattr(request.state, "authenticated", False)
        
        # Log request start (you can integrate with your logging system)
        print(f"Request: {request.method} {request.url.path} - User: {user_id} - Auth: {authenticated}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            print(f"Response: {response.status_code} - Time: {process_time:.4f}s")
            
            return response
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            print(f"Error: {str(e)} - Time: {process_time:.4f}s")
            raise e


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses"""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Add HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class UserContextMiddleware(BaseHTTPMiddleware):
    """Middleware to enrich user context with additional information"""
    
    async def dispatch(self, request: Request, call_next):
        """Add additional user context information"""
        
        # Get existing user context
        user_id = getattr(request.state, "user_id", None)
        
        if user_id:
            # Add additional context (IP, User-Agent, etc.)
            request.state.client_ip = self._get_client_ip(request)
            request.state.user_agent = request.headers.get("User-Agent", "")
            request.state.request_id = self._generate_request_id()
        
        response = await call_next(request)
        
        # Add request ID to response headers for debugging
        if hasattr(request.state, "request_id"):
            response.headers["X-Request-ID"] = request.state.request_id
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers first (for load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())[:8] 