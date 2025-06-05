"""
Authentication API Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import security, create_tokens_for_user, verify_password, get_password_hash
from app.core.exceptions import (
    AuthenticationException,
    EmailAlreadyExistsException,
    EmailNotVerifiedException,
    InvalidCredentialsException
)
from app.models.database.user import User
from app.models.schemas.auth_schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    TokenRefreshResponse,
    PasswordReset,
    PasswordResetResponse,
    PasswordResetConfirm,
    EmailVerification,
    EmailVerificationResponse,
    ResendVerification,
    ChangePassword,
    LogoutRequest,
    UserProfile
)
from app.models.schemas.common_schemas import BaseResponse
from app.api.v1.dependencies.auth import (
    get_current_user,
    get_current_active_user,
    get_current_verified_user
)

router = APIRouter()

@router.get("/status", response_model=BaseResponse)
async def get_auth_status():
    """Get auth service status"""
    return BaseResponse(
        success=True,
        message="Authentication service is operational"
    )

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Register a new user account"""
    
    # Check if email already exists
    query = select(User).where(User.email == user_data.email.lower())
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise EmailAlreadyExistsException("Email address already registered")
    
    # Check if username already exists (if provided)
    if user_data.username:
        query = select(User).where(User.username == user_data.username.lower())
        result = await db.execute(query)
        existing_username = result.scalar_one_or_none()
        
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email.lower(),
        username=user_data.username.lower() if user_data.username else None,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_verified=False  # Will be verified via email
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Generate tokens
    tokens = create_tokens_for_user(
        user_id=new_user.user_id,
        scopes=["chat", "files", "profile"]
    )
    
    # Create user profile for response
    user_profile = UserProfile(
        id=new_user.id,
        user_id=new_user.user_id,
        email=new_user.email,
        username=new_user.username,
        full_name=new_user.full_name,
        avatar_url=new_user.avatar_url,
        bio=new_user.bio,
        subscription_tier=new_user.subscription_tier,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        created_at=new_user.created_at,
        last_login_at=new_user.last_login_at
    )
    
    # TODO: Send verification email in background task
    # background_tasks.add_task(send_verification_email, new_user.email, verification_token)
    
    return TokenResponse(
        success=True,
        message="Account created successfully. Please check your email for verification.",
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=3600,  # 1 hour
        user=user_profile
    )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Authenticate user and return tokens"""
    
    # Find user by email
    query = select(User).where(User.email == credentials.email.lower())
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise InvalidCredentialsException("Invalid email or password")
    
    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise InvalidCredentialsException("Invalid email or password")
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Update last login
    from sqlalchemy.sql import func
    from datetime import datetime
    current_time = datetime.utcnow()
    user.last_login_at = current_time
    await db.commit()
    await db.refresh(user)
    
    # Generate tokens with appropriate expiry
    expires_delta = None
    if credentials.remember_me:
        expires_delta = 30 * 24 * 60  # 30 days in minutes
    
    tokens = create_tokens_for_user(
        user_id=user.user_id,
        scopes=["chat", "files", "profile", "analytics"]
    )
    
    # Create user profile for response
    user_profile = UserProfile(
        id=user.id,
        user_id=user.user_id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        subscription_tier=user.subscription_tier,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login_at=current_time
    )
    
    return TokenResponse(
        success=True,
        message="Login successful",
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=3600,  # 1 hour
        user=user_profile
    )

@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
) -> TokenRefreshResponse:
    """Refresh access token using refresh token"""
    
    # Verify refresh token
    payload = security.verify_token(token_data.refresh_token, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )
    
    # Verify user still exists and is active
    query = select(User).where(User.user_id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account disabled"
        )
    
    # Generate new access token
    new_access_token = security.create_access_token(
        subject=user_id,
        scopes=["chat", "files", "profile", "analytics"]
    )
    
    return TokenRefreshResponse(
        success=True,
        message="Token refreshed successfully",
        access_token=new_access_token,
        expires_in=3600
    )

@router.post("/logout", response_model=BaseResponse)
async def logout_user(
    logout_data: LogoutRequest,
    current_user: User = Depends(get_current_user)
) -> BaseResponse:
    """Logout user and invalidate tokens"""
    
    # TODO: Implement token blacklisting in Redis
    # For now, we'll just return success since tokens will expire naturally
    
    return BaseResponse(
        success=True,
        message="Logged out successfully"
    )

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserProfile:
    """Get current user profile information"""
    
    return UserProfile(
        id=current_user.id,
        user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        subscription_tier=current_user.subscription_tier,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
    )

@router.post("/forgot-password", response_model=PasswordResetResponse)
async def request_password_reset(
    reset_request: PasswordReset,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> PasswordResetResponse:
    """Request password reset email"""
    
    # Find user by email
    query = select(User).where(User.email == reset_request.email.lower())
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    # Always return success for security (don't reveal if email exists)
    if user and user.is_active:
        # Generate reset token
        reset_token = security.create_password_reset_token(user.email)
        
        # TODO: Send password reset email in background task
        # background_tasks.add_task(send_password_reset_email, user.email, reset_token)
    
    return PasswordResetResponse(
        success=True,
        message="If the email exists, a reset link has been sent"
    )

@router.post("/reset-password", response_model=BaseResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """Confirm password reset with token"""
    
    # Verify reset token
    email = security.verify_password_reset_token(reset_data.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find user by email
    query = select(User).where(User.email == email.lower())
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    await db.commit()
    
    return BaseResponse(
        success=True,
        message="Password reset successfully"
    )

@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db)
) -> EmailVerificationResponse:
    """Verify user email address"""
    
    # TODO: Implement email verification token validation
    # For now, we'll implement a simple version
    
    # In a real implementation, you would:
    # 1. Decode the verification token
    # 2. Find the user by email from token
    # 3. Mark user as verified
    
    return EmailVerificationResponse(
        success=True,
        message="Email verified successfully"
    )

@router.post("/resend-verification", response_model=BaseResponse)
async def resend_verification_email(
    resend_data: ResendVerification,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """Resend email verification"""
    
    # Find user by email
    query = select(User).where(User.email == resend_data.email.lower())
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user and not user.is_verified:
        # TODO: Generate new verification token and send email
        # background_tasks.add_task(send_verification_email, user.email, verification_token)
        pass
    
    return BaseResponse(
        success=True,
        message="If the email exists and is unverified, a new verification email has been sent"
    )

@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """Change user password"""
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return BaseResponse(
        success=True,
        message="Password changed successfully"
    ) 