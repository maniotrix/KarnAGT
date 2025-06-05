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