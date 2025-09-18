"""
Resource Authorization Middleware

This middleware handles resource-level authorization (e.g., conversation ownership)
at the HTTP middleware level, before FastAPI dependencies execute.

This ensures:
1. Security-first: Unauthorized requests never reach business logic
2. Clean separation: Authorization vs Business Logic vs Resource Locking  
3. Performance: No expensive operations for unauthorized requests
4. Information security: No timing attacks or information disclosure
"""

import re
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.database import get_db
from app.logging.logger import get_logger

logger = get_logger(__name__)


class ResourceAuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle resource-level authorization before dependencies execute"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Regex pattern for conversation endpoints with UUID conversation_id
        # Matches UUID format: 8-4-4-4-12 hex digits (e.g., ac70e87f-6f96-40d0-bfac-f5d71e45b67a)
        self.conversation_pattern = re.compile(r'^/api/v1/chat/conversations/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:/.*)?$')
        
        # Paths that should NOT be validated (even if they match conversation pattern)
        self.excluded_conversation_paths = {
            "/api/v1/chat/conversations",      # Create/list conversations (no trailing slash)
            "/api/v1/chat/conversations/",     # Create/list conversations (with trailing slash)
            "/api/v1/chat/conversations/bulk", # Bulk operations
        }
        
        # Methods that require ownership validation
        self.protected_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
    
    async def dispatch(self, request: Request, call_next):
        """Check resource authorization before proceeding to dependencies"""
        
        # Skip if user is not authenticated (handled by AuthenticationMiddleware)
        if not getattr(request.state, "authenticated", False):
            return await call_next(request)
        
        # Skip if method doesn't require protection
        if request.method not in self.protected_methods:
            return await call_next(request)
        
        # Check if this is a conversation-related endpoint that needs ownership validation
        path = request.url.path
        if path not in self.excluded_conversation_paths:
            conversation_id = self._extract_conversation_id(path)
            if conversation_id:
                # Validate conversation ownership
                is_authorized = await self._validate_conversation_ownership(
                    conversation_id, 
                    request.state.user_id
                )
                
                if not is_authorized:
                    logger.warning(
                        f"User {request.state.user_id} attempted unauthorized access to conversation {conversation_id} via {path}"
                    )
                    return JSONResponse(
                        status_code=404,
                        content={
                            "detail": {
                                "message": "Conversation not found",
                                "code": "CONVERSATION_NOT_FOUND"
                            }
                        }
                    )
        
        # Authorization passed or not applicable - proceed to dependencies/endpoint
        return await call_next(request)
    
    def _extract_conversation_id(self, path: str) -> Optional[str]:
        """Extract conversation ID from URL path"""
        match = self.conversation_pattern.match(path)
        if match:
            return match.group(1)
        return None
    
    async def _validate_conversation_ownership(self, conversation_id: str, user_id: str) -> bool:
        """Validate that the user owns the conversation"""
        if not user_id or not conversation_id:
            return False
        
        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        try:
            # Import here to avoid circular dependencies
            from sqlalchemy import select
            from app.models.database.conversation import Conversation
            from app.models.database.user import User
            
            # Get user's numeric ID from user_id (UUID)
            user_result = await db.execute(
                select(User.id).where(User.user_id == user_id)
            )
            numeric_user_id = user_result.scalar_one_or_none()
            
            if not numeric_user_id:
                return False
            
            # Check if conversation exists and belongs to user
            result = await db.execute(
                select(Conversation.id).where(
                    Conversation.conversation_id == conversation_id,
                    Conversation.user_id == numeric_user_id,
                    Conversation.status == "active"
                )
            )
            conversation_exists = result.scalar_one_or_none()
            
            return conversation_exists is not None
            
        except Exception as e:
            logger.error(f"Error validating conversation ownership: {e}")
            # Fail closed - deny access on error
            return False
        finally:
            await db.close()
