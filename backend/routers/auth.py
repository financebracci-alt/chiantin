"""
Auth Router - Authentication endpoints.

Handles all authentication operations including:
- User signup/registration
- Login/logout
- Email verification
- Password management
- MFA setup/enable

Routes: /api/v1/auth/*

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from bson import ObjectId
import logging
import uuid

from database import get_database
from config import settings
from services.auth_service import AuthService
from services.email_service import EmailService
from core.auth import hash_password, verify_password
from schemas.users import (
    UserCreate, UserLogin, TokenResponse, UserResponse, 
    MFASetupResponse, MFAVerifyRequest, ResendVerificationRequest, VerifyEmailRequest,
    SignupRequest, PasswordChangeRequest, VerifyPasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest
)

from .dependencies import get_current_user, require_admin, create_audit_log

logger = logging.getLogger(__name__)

# Router definition - NO prefix here, we'll add it when including
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ==================== /auth/me ====================

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get current user info."""
    auth_service = AuthService(db)
    user = await auth_service.get_user(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        status=user.status,
        email_verified=user.email_verified,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )


# ==================== Email Verification ====================

@router.post("/verify-email")
async def verify_email(
    request_data: VerifyEmailRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Verify email address using token from email."""
    # Find the verification record
    verification = await db.email_verifications.find_one({
        "token": request_data.token,
        "used": False
    })
    
    if not verification:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired verification link. Please request a new one."
        )
    
    # Check if token is expired
    if verification["expires_at"] < datetime.utcnow():
        raise HTTPException(
            status_code=400, 
            detail="Verification link has expired. Please request a new one."
        )
    
    # Get user_id and convert to ObjectId if needed
    user_id = verification["user_id"]
    try:
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
    except Exception:
        user_id_obj = user_id
    
    # Mark email as verified (try both ObjectId and string formats)
    result = await db.users.update_one(
        {"_id": user_id_obj},
        {"$set": {"email_verified": True, "updated_at": datetime.utcnow()}}
    )
    
    # If ObjectId didn't work, try string
    if result.matched_count == 0:
        result = await db.users.update_one(
            {"_id": user_id},
            {"$set": {"email_verified": True, "updated_at": datetime.utcnow()}}
        )
    
    # Mark verification token as used
    await db.email_verifications.update_one(
        {"_id": verification["_id"]},
        {"$set": {"used": True, "verified_at": datetime.utcnow()}}
    )
    
    # Audit log
    await create_audit_log(
        db=db,
        action="EMAIL_VERIFIED",
        entity_type="auth",
        entity_id=verification["user_id"],
        description=f"Email verified for {verification['email']}",
        performed_by=verification["user_id"],
        performed_by_email=verification["email"],
        metadata={"email": verification["email"]}
    )
    
    logger.info(f"Email verified successfully for: {verification['email']}")
    
    return {"message": "Email verified successfully. You can now log in.", "success": True}


@router.post("/resend-verification")
async def resend_verification_email(
    request_data: ResendVerificationRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Resend email verification email."""
    # Find the user
    user = await db.users.find_one({"email": request_data.email.lower()})
    
    if not user:
        # Don't reveal if email exists - return success anyway for security
        return {"message": "If an account exists with this email, a verification link will be sent.", "success": True}
    
    # Check if already verified
    if user.get("email_verified", False):
        raise HTTPException(
            status_code=400, 
            detail="Email is already verified. You can proceed to login."
        )
    
    # Invalidate any existing verification tokens for this user
    await db.email_verifications.update_many(
        {"user_id": str(user["_id"]), "used": False},
        {"$set": {"used": True, "invalidated_at": datetime.utcnow()}}
    )
    
    # Generate new verification token
    email_service = EmailService()
    verification_token = email_service.generate_verification_token()
    
    # Store new verification token
    await db.email_verifications.insert_one({
        "_id": str(uuid.uuid4()),
        "user_id": str(user["_id"]),
        "email": user["email"],
        "token": verification_token,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24),
        "used": False
    })
    
    # Send verification email (don't fail if email fails)
    language = request_data.language or 'en'
    try:
        email_service.send_verification_email(
            to_email=user["email"],
            verification_token=verification_token,
            first_name=user.get("first_name", ""),
            language=language
        )
        logger.info(f"Verification email resent to: {user['email']} (lang={language})")
    except Exception as e:
        logger.error(f"Failed to resend verification email to {user['email']}: {str(e)}")
    
    return {"message": "Verification email sent. Please check your inbox.", "success": True}


# ==================== MFA ====================

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Setup MFA (get QR code)."""
    auth_service = AuthService(db)
    secret, qr_uri = await auth_service.setup_mfa(current_user["id"])
    return MFASetupResponse(secret=secret, qr_code_uri=qr_uri)


@router.post("/mfa/enable")
async def enable_mfa(
    data: MFAVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Enable MFA after verifying token."""
    auth_service = AuthService(db)
    await auth_service.enable_mfa(current_user["id"], data.token)
    return {"success": True, "message": "MFA enabled successfully"}


# NOTE: More endpoints will be moved here incrementally in subsequent phases
