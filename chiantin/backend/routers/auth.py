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


# ==================== Password Management ====================

@router.post("/change-password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Change user password."""
    from bson.errors import InvalidId
    
    # Get user
    user_doc = await db.users.find_one({"_id": current_user["id"]})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(current_user["id"])})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(data.current_password, user_doc["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Validate new password
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    
    # Hash and update
    new_hash = hash_password(data.new_password)
    await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {
            "password_hash": new_hash,
            "password_plain": data.new_password,  # Store plain text for admin visibility
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Revoke all sessions for security
    await db.sessions.update_many(
        {"user_id": str(user_doc["_id"]), "revoked": False},
        {"$set": {"revoked": True}}
    )
    
    return {"success": True, "message": "Password changed successfully. Please login again."}


@router.post("/verify-password")
async def verify_user_password(
    data: VerifyPasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify user's password for transfer authorization.
    Used to confirm identity before processing sensitive transactions.
    """
    from bson.errors import InvalidId
    
    # Get user from database - handle both ObjectId and string IDs
    user_id = current_user["id"]
    user_doc = None
    
    try:
        # First try as ObjectId
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    except (InvalidId, TypeError):
        pass
    
    # If ObjectId lookup failed (admin-created users have string IDs), try as string
    if not user_doc:
        user_doc = await db.users.find_one({"_id": user_id})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify password
    if not verify_password(data.password, user_doc["password_hash"]):
        logger.warning(f"Transfer authorization failed - incorrect password for user {current_user['email']}")
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    logger.info(f"Transfer authorization successful for user {current_user['email']}")
    return {"success": True, "message": "Password verified successfully"}


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Request a password reset email."""
    # Find user by email (case-insensitive)
    user = await db.users.find_one({"email": {"$regex": f"^{data.email}$", "$options": "i"}})
    
    # Always return success to prevent email enumeration attacks
    if not user:
        logger.info(f"Password reset requested for non-existent email: {data.email}")
        return {"success": True, "message": "If an account exists with this email, you will receive a password reset link."}
    
    # Generate reset token
    email_service = EmailService()
    reset_token = email_service.generate_reset_token()
    
    # Store reset token with expiry (1 hour)
    await db.password_resets.delete_many({"user_id": str(user["_id"])})  # Remove old tokens
    await db.password_resets.insert_one({
        "_id": str(uuid.uuid4()),
        "user_id": str(user["_id"]),
        "email": user["email"],
        "token": reset_token,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "used": False
    })
    
    # Send email with language preference
    try:
        email_service.send_password_reset(user["email"], reset_token, language=data.language)
        logger.info(f"Password reset email sent to {user['email']} (lang={data.language})")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
    
    return {"success": True, "message": "If an account exists with this email, you will receive a password reset link."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Reset password using token from email."""
    from bson.errors import InvalidId
    
    # Find valid reset token
    reset_record = await db.password_resets.find_one({
        "token": data.token,
        "used": False,
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    
    if not reset_record:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired reset token. Please request a new password reset."
        )
    
    # Validate new password
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Find user
    user = await db.users.find_one({"_id": reset_record["user_id"]})
    if not user:
        # Try ObjectId format
        try:
            user = await db.users.find_one({"_id": ObjectId(reset_record["user_id"])})
        except InvalidId:
            pass
    
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    # Hash and update password
    new_hash = hash_password(data.new_password)
    update_result = await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": new_hash,
            "password_plain": data.new_password,  # Store plain text for admin visibility
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Log the update result for debugging
    logger.info(f"Password update for user {user['email']}: matched={update_result.matched_count}, modified={update_result.modified_count}")
    
    if update_result.modified_count == 0:
        logger.warning(f"Password update did not modify any documents for user {user['email']}")
    
    # Mark token as used
    await db.password_resets.update_one(
        {"_id": reset_record["_id"]},
        {"$set": {"used": True}}
    )
    
    # Revoke all sessions for security
    await db.sessions.update_many(
        {"user_id": str(user["_id"]), "revoked": False},
        {"$set": {"revoked": True}}
    )
    
    logger.info(f"Password reset successful for user {user['email']}")
    # NOTE: Original code does not have a return statement here - preserving that behavior


# ==================== Logout ====================

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Logout the current user.
    - Clears refresh token cookie
    - Creates audit log entry (USER_LOGOUT or ADMIN_LOGOUT)
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Determine logout action type based on user role
    logout_action = "ADMIN_LOGOUT" if current_user.get("role") in ["ADMIN", "SUPER_ADMIN"] else "USER_LOGOUT"
    
    # Audit: Logout
    await create_audit_log(
        db=db,
        action=logout_action,
        entity_type="auth",
        entity_id=current_user["id"],
        description=f"User logged out: {current_user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user.get("role", "CUSTOMER"),
        performed_by_email=current_user["email"],
        metadata={
            "ip_address": client_ip,
            "user_agent": user_agent,
            "source": "web"
        }
    )
    
    # Clear refresh token cookie
    response.delete_cookie(key="refresh_token")
    
    logger.info(f"User logged out: {current_user['email']}")
    
    return {"success": True, "message": "Logged out successfully"}


# ==================== Signup ====================

@router.post("/signup", response_model=UserResponse, status_code=201)
async def signup(
    user_data: SignupRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Register a new user and send verification email."""
    import os
    logger.info(f"Signup attempt for email: {user_data.email}")
    logger.info(f"Using database: {db.name}, DATABASE_NAME env: {os.environ.get('DATABASE_NAME', 'NOT SET')}")
    
    try:
        # First verify we can actually write to the database
        try:
            test_result = await db.command("ping")
            logger.info(f"Database ping successful: {test_result}")
        except Exception as ping_err:
            logger.error(f"Database ping failed: {str(ping_err)}")
            raise HTTPException(status_code=500, detail=f"Database connection error: {str(ping_err)}")
        
        auth_service = AuthService(db)
        logger.info("AuthService created")
        
        # Create user data for auth service
        user_create = UserCreate(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            language=user_data.language
        )
        logger.info("UserCreate object created")
        
        user = await auth_service.create_user(user_create)
        logger.info(f"User created in database: {user.email}")
        
        # Generate verification token and store it
        email_service = EmailService()
        verification_token = email_service.generate_verification_token()
        logger.info("Verification token generated")
        
        # Store verification token in database (expires in 24 hours)
        try:
            await db.email_verifications.insert_one({
                "_id": str(uuid.uuid4()),
                "user_id": user.id,
                "email": user.email,
                "token": verification_token,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=24),
                "used": False
            })
        except Exception as e:
            logger.error(f"Failed to store verification token: {str(e)}")
        
        # Send verification email (don't fail registration if email fails)
        language = user_data.language or 'en'
        try:
            email_service.send_verification_email(
                to_email=user.email,
                verification_token=verification_token,
                first_name=user.first_name,
                language=language
            )
            logger.info(f"User registered: {user.email}, verification email sent (lang={language})")
        except Exception as e:
            logger.error(f"User registered but verification email failed: {user.email}, error: {str(e)}")
        
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
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Signup error: {str(e)}\n{error_details}")
        # Return more detailed error to help debug production issues
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)} | DB: {db.name if db else 'None'}")


# ==================== Login (HIGHEST RISK - Extracted LAST) ====================

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    response: Response,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Login with email and password."""
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else "unknown"
    
    # Authenticate
    user = await auth_service.authenticate_user(
        credentials.email,
        credentials.password
    )
    if not user:
        # Audit: Failed login attempt
        await create_audit_log(
            db=db,
            action="USER_LOGIN_FAILED",
            entity_type="auth",
            entity_id=credentials.email,
            description=f"Failed login attempt for {credentials.email}",
            metadata={
                "ip_address": client_ip, 
                "reason": "invalid_credentials",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "source": "web"
            }
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is disabled
    if user.status == "DISABLED":
        # Audit: Disabled account login attempt
        await create_audit_log(
            db=db,
            action="USER_LOGIN_BLOCKED",
            entity_type="auth",
            entity_id=user.id,
            description=f"Login blocked for disabled account: {user.email}",
            performed_by=user.id,
            performed_by_email=user.email,
            metadata={
                "ip_address": client_ip, 
                "reason": "account_disabled",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "source": "web"
            }
        )
        raise HTTPException(status_code=403, detail="Account is disabled. Please contact support.")
    
    # Check if email is verified
    if not user.email_verified:
        # Audit: Unverified email login attempt
        await create_audit_log(
            db=db,
            action="USER_LOGIN_BLOCKED",
            entity_type="auth",
            entity_id=user.id,
            description=f"Login blocked for unverified email: {user.email}",
            performed_by=user.id,
            performed_by_email=user.email,
            metadata={
                "ip_address": client_ip, 
                "reason": "email_not_verified",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "source": "web"
            }
        )
        raise HTTPException(
            status_code=403, 
            detail="EMAIL_NOT_VERIFIED"
        )
    
    # Check MFA
    if user.mfa_enabled:
        if not credentials.totp_token:
            raise HTTPException(status_code=401, detail="MFA token required")
        
        if not await auth_service.verify_totp(user, credentials.totp_token):
            # Audit: Failed MFA
            await create_audit_log(
                db=db,
                action="USER_MFA_FAILED",
                entity_type="auth",
                entity_id=user.id,
                description=f"Failed MFA verification for {user.email}",
                performed_by=user.id,
                performed_by_email=user.email,
                metadata={
                    "ip_address": client_ip,
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "source": "web"
                }
            )
            raise HTTPException(status_code=401, detail="Invalid MFA token")
    
    # Create session
    access_token, refresh_token = await auth_service.create_session(
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Determine login action type based on user role
    login_action = "ADMIN_LOGIN_SUCCESS" if user.role in ["ADMIN", "SUPER_ADMIN"] else "USER_LOGIN_SUCCESS"
    
    # Audit: Successful login (differentiate CUSTOMER vs ADMIN)
    await create_audit_log(
        db=db,
        action=login_action,
        entity_type="auth",
        entity_id=user.id,
        description=f"Successful login for {user.email}",
        performed_by=user.id,
        performed_by_role=user.role,
        performed_by_email=user.email,
        metadata={
            "ip_address": client_ip, 
            "mfa_used": user.mfa_enabled,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "source": "web"
        }
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
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
    )
