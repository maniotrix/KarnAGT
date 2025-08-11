"""
Core Security Module - JWT, Password Hashing, Token Validation
"""
from datetime import datetime, timedelta
from typing import Any, Union, Optional, Dict
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import hashlib
from fastapi import HTTPException, status

from .config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityService:
    """Core security service for authentication and authorization"""
    
    @staticmethod
    def create_password_hash(password: str) -> str:
        """Create password hash"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(
        subject: Union[str, Any], 
        expires_delta: Optional[timedelta] = None,
        scopes: Optional[list] = None
    ) -> str:
        """Create access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "access",
            "scopes": scopes or []
        }
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        subject: Union[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create refresh token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "refresh"
        }
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode token"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=["HS256"]
            )
            
            # Check token type
            if payload.get("type") != token_type:
                return None
                
            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                return None
                
            if datetime.utcnow() > datetime.fromtimestamp(exp):
                return None
                
            return payload
            
        except JWTError:
            return None
    
    @staticmethod
    def get_subject_from_token(token: str) -> Optional[str]:
        """Extract subject (user_id) from token"""
        payload = SecurityService.verify_token(token)
        if payload:
            return payload.get("sub")
        return None
    
    @staticmethod
    def generate_random_token(length: int = 32) -> str:
        """Generate random secure token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_api_key(user_id: str) -> str:
        """Generate API key for user"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        raw_key = f"{user_id}:{timestamp}:{secrets.token_urlsafe(16)}"
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    @staticmethod
    def create_password_reset_token(email: str) -> str:
        """Create password reset token"""
        delta = timedelta(hours=1)  # 1 hour expiry
        expire = datetime.utcnow() + delta
        
        to_encode = {
            "exp": expire,
            "sub": email,
            "type": "password_reset"
        }
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )
        return encoded_jwt
    
    @staticmethod
    def verify_password_reset_token(token: str) -> Optional[str]:
        """Verify password reset token and return email"""
        payload = SecurityService.verify_token(token, "password_reset")
        if payload:
            return payload.get("sub")
        return None

# Global security service instance
security = SecurityService()

# Token creation utilities
def create_tokens_for_user(user_id: str, scopes: Optional[list] = None) -> Dict[str, str]:
    """Create both access and refresh tokens for a user"""
    access_token = security.create_access_token(
        subject=user_id,
        scopes=scopes
    )
    refresh_token = security.create_refresh_token(subject=user_id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def get_password_hash(password: str) -> str:
    """Utility function for password hashing"""
    return security.create_password_hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Utility function for password verification"""
    return security.verify_password(plain_password, hashed_password)

# Cookie-based authentication utilities
def set_auth_cookies(response, user_id: str, settings, scopes: Optional[list] = None) -> Dict[str, str]:
    """Set httpOnly authentication cookies and CSRF token"""
    from fastapi import Response
    
    # Create tokens
    access_token = security.create_access_token(subject=user_id, scopes=scopes)
    refresh_token = security.create_refresh_token(subject=user_id)
    
    # Get cookie settings
    cookie_settings = settings.get_cookie_settings()
    
    # Set access token cookie (httpOnly)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_settings
    )
    
    # Set refresh token cookie (httpOnly)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_settings
    )
    
    # Set CSRF token cookie (NOT httpOnly - JS needs to read this)
    csrf_token = CSRFProtection.set_csrf_cookie(response, settings)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "csrf_token": csrf_token
    }

def clear_auth_cookies(response, settings):
    """Clear authentication cookies"""
    from fastapi import Response
    
    cookie_settings = settings.get_cookie_settings()
    
    # Clear cookies by setting them to expire immediately
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        **cookie_settings
    )
    
    response.set_cookie(
        key="refresh_token", 
        value="",
        max_age=0,
        **cookie_settings
    )
    
    response.set_cookie(
        key="csrf_token",
        value="",
        max_age=0,
        **cookie_settings
    )

# CSRF Protection System
class CSRFProtection:
    """CSRF token management for additional security"""
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate cryptographically secure CSRF token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def set_csrf_cookie(response, settings) -> str:
        """Set CSRF token cookie (readable by JavaScript)"""
        csrf_token = CSRFProtection.generate_csrf_token()
        
        cookie_settings = settings.get_cookie_settings()
        # CSRF cookie must NOT be httpOnly (JS needs to read it)
        csrf_settings = {**cookie_settings, "httponly": False}
        
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            **csrf_settings
        )
        return csrf_token
    
    @staticmethod
    def validate_csrf_token(request_token: str, cookie_token: str) -> bool:
        """Validate CSRF token using constant-time comparison"""
        if not request_token or not cookie_token:
            return False
        return secrets.compare_digest(request_token, cookie_token) 