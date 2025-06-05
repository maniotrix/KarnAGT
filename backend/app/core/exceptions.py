"""
Custom API Exceptions for standardized error handling
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base API exception with enhanced error details"""
    
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> None:
        super().__init__(status_code, detail, headers)
        self.error_code = error_code
        self.error_type = error_type


# Authentication Exceptions
class AuthenticationException(BaseAPIException):
    """Authentication failed"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
            error_code="AUTH_001",
            error_type="authentication_error"
        )


class InvalidCredentialsException(BaseAPIException):
    """Invalid credentials provided"""
    def __init__(self, detail: str = "Invalid email or password"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTH_002",
            error_type="invalid_credentials"
        )


class TokenExpiredException(BaseAPIException):
    """Token has expired"""
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
            error_code="AUTH_003",
            error_type="token_expired"
        )


class InvalidTokenException(BaseAPIException):
    """Invalid token provided"""
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
            error_code="AUTH_004",
            error_type="invalid_token"
        )


# Authorization Exceptions
class PermissionDeniedException(BaseAPIException):
    """Insufficient permissions"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTH_005",
            error_type="permission_denied"
        )


class AccountDisabledException(BaseAPIException):
    """User account is disabled"""
    def __init__(self, detail: str = "Account is disabled"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTH_006",
            error_type="account_disabled"
        )


class EmailNotVerifiedException(BaseAPIException):
    """Email not verified"""
    def __init__(self, detail: str = "Email address not verified"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTH_007",
            error_type="email_not_verified"
        )


class EmailAlreadyExistsException(BaseAPIException):
    """Email address already exists"""
    def __init__(self, detail: str = "Email address already registered"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="AUTH_008",
            error_type="email_already_exists"
        )


# Resource Exceptions
class ResourceNotFoundException(BaseAPIException):
    """Resource not found"""
    def __init__(self, resource: str = "Resource", detail: Optional[str] = None):
        if detail is None:
            detail = f"{resource} not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="RES_001",
            error_type="resource_not_found"
        )


class ResourceAlreadyExistsException(BaseAPIException):
    """Resource already exists"""
    def __init__(self, resource: str = "Resource", detail: Optional[str] = None):
        if detail is None:
            detail = f"{resource} already exists"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="RES_002",
            error_type="resource_already_exists"
        )


class ResourceOwnershipException(BaseAPIException):
    """User doesn't own the resource"""
    def __init__(self, detail: str = "You don't have access to this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="RES_003",
            error_type="resource_ownership_error"
        )


# Validation Exceptions
class ValidationException(BaseAPIException):
    """Validation error"""
    def __init__(self, detail: str = "Validation error", field: Optional[str] = None):
        if field:
            detail = f"Validation error in field '{field}': {detail}"
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VAL_001",
            error_type="validation_error"
        )


class InvalidFileTypeException(BaseAPIException):
    """Invalid file type"""
    def __init__(self, allowed_types: list = None, detail: Optional[str] = None):
        if detail is None:
            if allowed_types:
                detail = f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            else:
                detail = "Invalid file type"
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VAL_002",
            error_type="invalid_file_type"
        )


class FileSizeExceededException(BaseAPIException):
    """File size exceeded"""
    def __init__(self, max_size: Optional[str] = None):
        detail = "File size exceeded"
        if max_size:
            detail = f"File size exceeded. Maximum allowed: {max_size}"
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VAL_003",
            error_type="file_size_exceeded"
        )


# Rate Limiting Exceptions
class RateLimitExceededException(BaseAPIException):
    """Rate limit exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
            error_code="RATE_001",
            error_type="rate_limit_exceeded"
        )


# Quota Exceptions
class QuotaExceededException(BaseAPIException):
    """User quota exceeded"""
    def __init__(self, quota_type: str = "usage", detail: Optional[str] = None):
        if detail is None:
            detail = f"{quota_type.title()} quota exceeded"
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail,
            error_code="QUOTA_001",
            error_type="quota_exceeded"
        )


class InsufficientCreditsException(BaseAPIException):
    """Insufficient credits"""
    def __init__(self, detail: str = "Insufficient credits"):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail,
            error_code="QUOTA_002",
            error_type="insufficient_credits"
        )


# External Service Exceptions
class ExternalServiceException(BaseAPIException):
    """External service error"""
    def __init__(self, service: str, detail: str = "Service unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service}: {detail}",
            error_code="EXT_001",
            error_type="external_service_error"
        )


class OpenAIException(ExternalServiceException):
    """OpenAI API error"""
    def __init__(self, detail: str = "OpenAI API error"):
        super().__init__(service="OpenAI", detail=detail)


class VectorDBException(ExternalServiceException):
    """Vector database error"""
    def __init__(self, detail: str = "Vector database error"):
        super().__init__(service="Vector Database", detail=detail)


class GraphDBException(ExternalServiceException):
    """Graph database error"""
    def __init__(self, detail: str = "Graph database error"):
        super().__init__(service="Graph Database", detail=detail)


# Processing Exceptions
class ProcessingException(BaseAPIException):
    """Processing error"""
    def __init__(self, detail: str = "Processing error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="PROC_001",
            error_type="processing_error"
        )


class FileProcessingException(ProcessingException):
    """File processing error"""
    def __init__(self, detail: str = "File processing error"):
        super().__init__(detail=detail)


class EmbeddingGenerationException(ProcessingException):
    """Embedding generation error"""
    def __init__(self, detail: str = "Embedding generation error"):
        super().__init__(detail=detail)


class MemoryProcessingException(ProcessingException):
    """Memory processing error"""
    def __init__(self, detail: str = "Memory processing error"):
        super().__init__(detail=detail) 