"""
Security validation utilities for input sanitization and validation.
Contains reusable functions for common security checks across Pydantic models.
"""

import re
from typing import Optional


class SecurityValidationError(ValueError):
    """Custom exception for security validation failures"""
    pass


def validate_email_security(email_str: str) -> str:
    """
    Enhanced email validation for security.
    
    Args:
        email_str: Email string to validate
        
    Returns:
        str: Validated email string
        
    Raises:
        SecurityValidationError: If email fails security checks
    """
    email_str = str(email_str)
    
    # Check for suspicious patterns
    if '..' in email_str:
        raise SecurityValidationError('Email cannot contain consecutive dots')
    if email_str.startswith('.') or email_str.endswith('.'):
        raise SecurityValidationError('Email cannot start or end with a dot')
    
    # Check domain length (prevent extremely long domains)
    domain = email_str.split('@')[-1]
    if len(domain) > 253:  # RFC domain limit
        raise SecurityValidationError('Email domain too long')
        
    return email_str


def sanitize_text_input(text: Optional[str], field_name: str = "field") -> Optional[str]:
    """
    Sanitize text input to prevent XSS and injection attacks.
    
    Args:
        text: Text to sanitize
        field_name: Name of field (for error messages)
        
    Returns:
        Optional[str]: Sanitized text or None if empty
        
    Raises:
        SecurityValidationError: If text contains dangerous characters
    """
    if text is None:
        return None
        
    text = text.strip()
    if len(text) == 0:
        return None  # Return None for empty strings after stripping
    
    # Block common XSS and injection characters
    dangerous_chars = r'[<>{}\\|`"\']'
    if re.search(dangerous_chars, text):
        raise SecurityValidationError(f'{field_name} contains invalid characters')
    
    # Check for excessive whitespace (potential formatting attacks)
    if re.search(r'\s{3,}', text):
        raise SecurityValidationError(f'{field_name} contains excessive whitespace')
    
    # Block control characters and non-printable chars
    if re.search(r'[\x00-\x1f\x7f-\x9f]', text):
        raise SecurityValidationError(f'{field_name} contains invalid characters')
        
    return text


def validate_username_security(username: Optional[str]) -> Optional[str]:
    """
    Enhanced username validation with security checks.
    
    Args:
        username: Username to validate
        
    Returns:
        Optional[str]: Validated username or None
        
    Raises:
        SecurityValidationError: If username fails security checks
    """
    if username is None:
        return None
        
    username = username.strip().lower()
    
    # Basic format check
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise SecurityValidationError('Username can only contain letters, numbers, hyphens, and underscores')
    
    # Prevent reserved/system usernames
    reserved_usernames = {
        'admin', 'administrator', 'root', 'user', 'test', 'api', 'www', 
        'mail', 'ftp', 'support', 'help', 'info', 'contact', 'null', 
        'undefined', 'system', 'service', 'public', 'private', 'static',
        'app', 'application', 'server', 'database', 'db', 'auth', 'login'
    }
    if username in reserved_usernames:
        raise SecurityValidationError('Username is reserved')
    
    # Prevent usernames that look like IDs or UUIDs
    if re.match(r'^\d+$', username):
        raise SecurityValidationError('Username cannot be all numbers')
    if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', username):
        raise SecurityValidationError('Username cannot look like a UUID')
        
    return username



def validate_secure_token(token: str, token_type: str = "token") -> str:
    """
    Validate secure token format (for password reset, email verification, etc).
    
    Args:
        token: Token to validate
        token_type: Type of token (for error messages)
        
    Returns:
        str: Validated token
        
    Raises:
        SecurityValidationError: If token fails validation
    """
    token = token.strip()
    
    # Check for valid characters (alphanumeric + URL-safe chars)
    if not re.match(r'^[A-Za-z0-9._-]+$', token):
        raise SecurityValidationError(f'Invalid {token_type} format')
    
    # Prevent obviously fake/test tokens
    if token.lower() in ('test', 'fake', 'invalid', 'demo', '123456'):
        raise SecurityValidationError(f'Invalid {token_type}')
        
    return token


def validate_password_strength(password: str) -> str:
    """
    Validate password strength requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        str: Validated password
        
    Raises:
        SecurityValidationError: If password fails strength requirements
    """
    if len(password) < 8:
        raise SecurityValidationError('Password must be at least 8 characters long')
    if not re.search(r'[A-Z]', password):
        raise SecurityValidationError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise SecurityValidationError('Password must contain at least one lowercase letter')
    if not re.search(r'\d', password):
        raise SecurityValidationError('Password must contain at least one digit')
        
    return password
