"""
Authentication Dependencies for FastAPI
"""
from typing import Optional, Dict, Any, Union
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import security
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationException,
    InvalidTokenException,
    TokenExpiredException,
    AccountDisabledException,
    EmailNotVerifiedException,
    PermissionDeniedException
)
from app.models.database.user import User
from app.logging.logger import get_logger
logger = get_logger(__name__)
class ServiceAuth:
    """Service authentication for internal service-to-service calls"""
    def __init__(self, service_name: str, has_full_access: bool = True):
        self.service_name = service_name
        self.has_full_access = has_full_access
        self.user_id = None  # Services don't have user_id
        self.is_service = True

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> str:
    """Get current user ID from JWT token (Authorization header or httpOnly cookie)"""
    token = None
    
    # Try Authorization header first
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to httpOnly cookie
        token = request.cookies.get("access_token")
    
    if not token:
        raise AuthenticationException("Authentication required")
    
    user_id = security.get_subject_from_token(token)
    
    if not user_id:
        raise InvalidTokenException("Invalid or expired token")
    
    return user_id

async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from database"""
    query = select(User).where(User.user_id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationException("User not found")
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (account must be active)"""
    if not current_user.is_active:
        raise AccountDisabledException("Account is disabled")
    
    return current_user

async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current verified user (email must be verified if required by config)"""
    settings = get_settings()
    
    # Log email verification status for debugging
    if not current_user.is_verified:
        logger.warning(f"[WARN] User {current_user.email} (ID: {current_user.user_id}) is NOT email verified")
    
    # Only check email verification if it's required in settings
    if settings.REQUIRE_EMAIL_VERIFICATION and not current_user.is_verified:
        logger.error(f"[ALERT] Email verification required but user {current_user.email} is not verified")
        raise EmailNotVerifiedException("Email address not verified")
    
    # Log successful verification check
    if settings.REQUIRE_EMAIL_VERIFICATION:
        logger.info(f"[SUCCESS] Email verification check passed for user {current_user.email}")
    else:
        logger.info(f"[INFO] Email verification not required (REQUIRE_EMAIL_VERIFICATION=False)")
    
    return current_user

async def get_current_verified_user_strict(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current verified user (email must ALWAYS be verified, ignores config)"""
    if not current_user.is_verified:
        raise EmailNotVerifiedException("Email address not verified")
    
    return current_user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user optionally (no error if not authenticated)"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user_id = security.get_subject_from_token(token)
        
        if not user_id:
            return None
        
        query = select(User).where(User.user_id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        return user
    except Exception:
        return None


async def get_current_user_or_service(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Union[User, ServiceAuth]:
    """Get current user or service authentication (supports both Authorization headers and httpOnly cookies)"""
    token = None
    settings = get_settings()
    
    # Try Authorization header first (for service authentication)
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to httpOnly cookie (for web browser users)
        token = request.cookies.get("access_token")
    
    if not token:
        raise AuthenticationException("Authentication required")
    
    # Check if it's the service token (from Authorization header)
    if token == settings.CODE_EXECUTOR_TOKEN:
        return ServiceAuth(service_name="code_executor", has_full_access=True)
    
    # Regular user authentication (from either Authorization header or httpOnly cookie)
    user_id = security.get_subject_from_token(token)
    if not user_id:
        raise InvalidTokenException("Invalid or expired token")
    
    query = select(User).where(User.user_id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationException("User not found")
    
    return user

class RequireRole:
    """Dependency class for role-based access control"""
    
    def __init__(self, required_role: str):
        self.required_role = required_role
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_verified_user)
    ) -> User:
        """Check if user has required role"""
        # For now, we'll use subscription_tier as role
        # You can extend this to a proper role system later
        if self.required_role == "admin":
            # Only enterprise users can access admin features for now
            if current_user.subscription_tier != "enterprise":
                raise PermissionDeniedException("Admin access required")
        elif self.required_role == "pro":
            # Pro and enterprise users
            if current_user.subscription_tier not in ["pro", "enterprise"]:
                raise PermissionDeniedException("Pro subscription required")
        
        return current_user

class RequireScope:
    """Dependency class for scope-based access control"""
    
    def __init__(self, required_scope: str):
        self.required_scope = required_scope
    
    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
    ) -> Dict[str, Any]:
        """Check if token has required scope"""
        if not credentials:
            raise AuthenticationException("Authentication required")
        
        token = credentials.credentials
        payload = security.verify_token(token)
        
        if not payload:
            raise InvalidTokenException("Invalid or expired token")
        
        scopes = payload.get("scopes", [])
        if self.required_scope not in scopes:
            raise PermissionDeniedException(f"Scope '{self.required_scope}' required")
        
        return payload

# Convenience dependency functions
require_admin = RequireRole("admin")
require_pro = RequireRole("pro")

# Scope-based dependencies
require_chat_scope = RequireScope("chat")
require_files_scope = RequireScope("files")
require_analytics_scope = RequireScope("analytics")

async def validate_user_ownership(
    resource_user_id: int,
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """Validate that the current user owns the resource"""
    if current_user.id != resource_user_id:
        raise PermissionDeniedException("You don't have access to this resource")
    
    return current_user

async def check_image_upload_access(
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """Check if user can upload images (pro+ feature)"""
    if not current_user.can_use_feature("file_upload"):
        raise PermissionDeniedException("Image upload requires Pro subscription")
    
    return current_user

async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[Dict[str, Any]]:
    """Get token payload without user lookup"""
    if not credentials:
        return None
    
    token = credentials.credentials
    return security.verify_token(token)

class QuotaChecker:
    """Dependency class for quota checking"""
    
    def __init__(self, operation_cost: float = 0.0):
        self.operation_cost = operation_cost
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_verified_user)
    ) -> User:
        """Check if user has sufficient quota"""
        if self.operation_cost > 0:
            # Check if user has enough remaining quota
            remaining_quota = (current_user.monthly_quota_usd or 0) - (current_user.current_usage_usd or 0)
            
            if remaining_quota < self.operation_cost:
                raise PermissionDeniedException(
                    f"Insufficient quota. Operation costs ${self.operation_cost:.4f}, "
                    f"but you only have ${remaining_quota:.4f} remaining."
                )
        
        return current_user

# Common quota checkers
check_chat_quota = QuotaChecker(0.001)  # Approximate cost per message
check_image_quota = QuotaChecker(0.005)  # Approximate cost per image upload
check_embedding_quota = QuotaChecker(0.0001)  # Approximate cost per embedding
check_file_processing_quota = QuotaChecker(0.01)  # Approximate cost per file processing

# Note: CSRF Protection is handled at middleware level for all authenticated state-changing requests 