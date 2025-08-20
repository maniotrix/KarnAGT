"""Authentication-related Pydantic schemas"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
import re

from .common_schemas import BaseSchema, BaseResponse, SubscriptionTier


class UserRegister(BaseSchema):
    """User registration request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    confirm_password: str = Field(..., description="Password confirmation")
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    username: Optional[str] = Field(None, min_length=3, max_length=100, description="Unique username")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate password confirmation matches"""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v


class UserLogin(BaseSchema):
    """User login request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class GoogleLoginRequest(BaseSchema):
    """Google OAuth login request schema"""
    google_id_token: str = Field(..., description="Google ID token from frontend")


class TokenResponse(BaseResponse):
    """Token response schema for httpOnly cookie + CSRF authentication"""
    access_token: str = Field("", description="Empty - JWT access token is in httpOnly cookie")
    refresh_token: str = Field("", description="Empty - JWT refresh token is in httpOnly cookie")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: "UserProfile" = Field(..., description="User profile information")
    csrf_token: Optional[str] = Field(None, description="CSRF token for state-changing requests")


class TokenRefresh(BaseSchema):
    """Token refresh request schema - refresh token comes from httpOnly cookie"""
    # No fields needed - refresh token comes from httpOnly cookie
    pass


class TokenRefreshResponse(BaseResponse):
    """Token refresh response schema for httpOnly cookie + CSRF authentication"""
    access_token: str = Field("", description="Empty - new JWT access token is in httpOnly cookie")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    csrf_token: Optional[str] = Field(None, description="Updated CSRF token for state-changing requests")


class PasswordReset(BaseSchema):
    """Password reset request schema"""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetResponse(BaseResponse):
    """Password reset response schema"""
    message: str = "If the email exists, a reset link has been sent"


class PasswordResetConfirm(BaseSchema):
    """Password reset confirmation schema"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate password confirmation matches"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class EmailVerification(BaseSchema):
    """Email verification request schema"""
    token: str = Field(..., description="Email verification token")


class EmailVerificationResponse(BaseResponse):
    """Email verification response schema"""
    message: str = "Email verified successfully"


class ResendVerification(BaseSchema):
    """Resend email verification request schema"""
    email: EmailStr = Field(..., description="User email address")


class ChangePassword(BaseSchema):
    """Change password request schema"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate password confirmation matches"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class LogoutRequest(BaseSchema):
    """Logout request schema - tokens come from httpOnly cookies"""
    # No fields needed - tokens come from httpOnly cookies and are cleared by server
    pass


class UserProfile(BaseSchema):
    """User profile response schema"""
    id: int
    user_id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    subscription_tier: SubscriptionTier
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Forward reference resolution
TokenResponse.model_rebuild() 