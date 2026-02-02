"""Main FastAPI application for Project Atlas banking platform."""

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from contextlib import asynccontextmanager
from typing import Optional, List
from io import BytesIO
from datetime import datetime, timezone, timedelta
import jwt
import logging
import uuid

from config import settings
from database import connect_db, disconnect_db, get_database
from services.auth_service import AuthService
from services.kyc_service import KYCService
from services.banking_service import BankingService
from services.ledger_service import LedgerEngine
from services.statement_service import StatementService
from services.ticket_service import TicketService
from services.notification_service import NotificationService
from services.transfer_service import TransferService
from services.advanced_service import AdvancedBankingService
from services.email_service import EmailService
from services.banking_workflows_service import BankingWorkflowsService
from schemas.users import UserCreate, UserLogin, TokenResponse, UserResponse, MFASetupResponse, MFAVerifyRequest, ResendVerificationRequest, VerifyEmailRequest
from schemas.kyc import KYCSubmitRequest, KYCReviewRequest, DocumentType
from schemas.banking import AccountResponse, AdminCreditRequest, AdminDebitRequest, TransactionDisplayType
from schemas.tickets import TicketCreate, MessageCreate, TicketStatus
from schemas.transfers import P2PTransferRequest
from schemas.advanced import CreateBeneficiary, CreateScheduledPayment
from schemas.banking_workflows import (
    CreateCardRequest, FulfillCardRequest, CreateRecipient, CreateTransfer
)
from providers import LocalS3Storage, CloudinaryStorage
from pydantic import BaseModel, Field
from core.ledger import EntryDirection
from core.auth import hash_password, verify_password
from bson import ObjectId
from utils.common import serialize_doc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()


# ============== AUDIT LOGGING HELPER ==============
async def create_audit_log(
    db: AsyncIOMotorDatabase,
    action: str,
    entity_type: str,
    entity_id: str,
    description: str,
    performed_by: str = None,
    performed_by_role: str = None,
    performed_by_email: str = None,
    metadata: dict = None
):
    """
    Create an audit log entry for tracking important actions.
    This is a safe helper that won't raise exceptions to avoid breaking main flows.
    """
    try:
        await db.audit_logs.insert_one({
            "_id": str(uuid.uuid4()),
            "performed_by": performed_by or "SYSTEM",
            "performed_by_role": performed_by_role or "SYSTEM",
            "performed_by_email": performed_by_email or "",
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "description": description,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc)
        })
    except Exception as e:
        # Log error but don't break the main flow
        logger.error(f"Failed to create audit log: {e}")
# ============== END AUDIT LOGGING HELPER ==============


async def auto_seed_if_empty():
    """Auto-seed database with admin user if empty."""
    try:
        db = get_database()
        
        # CLEAR LOG: Show which database we're checking
        logger.info("=" * 60)
        logger.info(f"SEED CHECK: Connected to database '{db.name}'")
        
        user_count = await db.users.count_documents({})
        logger.info(f"SEED CHECK: Users count = {user_count}")
        
        if user_count == 0:
            logger.info("=" * 60)
            logger.info("SEED: Database is EMPTY - Creating admin user...")
            logger.info("=" * 60)
            from core.auth import hash_password
            
            # Create Super Admin
            admin = {
                "_id": "admin_super_001",
                "email": settings.SEED_SUPERADMIN_EMAIL,
                "password_hash": hash_password(settings.SEED_SUPERADMIN_PASSWORD),
                "password_plain": settings.SEED_SUPERADMIN_PASSWORD,  # Store plain text for admin visibility
                "first_name": "Super",
                "last_name": "Admin",
                "role": "SUPER_ADMIN",
                "status": "ACTIVE",
                "email_verified": True,
                "mfa_enabled": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            await db.users.insert_one(admin)
            logger.info(f"SEED: ✅ Admin user CREATED: {settings.SEED_SUPERADMIN_EMAIL}")
            logger.info(f"SEED: ✅ Password: {settings.SEED_SUPERADMIN_PASSWORD}")
            logger.info("=" * 60)
        else:
            logger.info(f"SEED: Database has {user_count} users - skipping seed")
            logger.info("=" * 60)
    except Exception as e:
        logger.error(f"SEED ERROR: Failed to seed database: {e}")
        logger.error("=" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events with error handling for production resilience."""
    try:
        logger.info("=" * 60)
        logger.info("APPLICATION STARTUP - ecommbx Banking Platform")
        logger.info("=" * 60)
        logger.info(f"MONGO_URL: {settings.MONGO_URL[:50]}...")
        logger.info(f"DATABASE_NAME: {settings.DATABASE_NAME}")
        logger.info(f"FRONTEND_URL: {settings.FRONTEND_URL}")
        logger.info(f"RESEND_API_KEY configured: {'Yes' if settings.RESEND_API_KEY else 'No'}")
        logger.info(f"DEBUG mode: {settings.DEBUG}")
        logger.info("=" * 60)
        
        await connect_db()
        
        # Auto-seed if database is empty
        await auto_seed_if_empty()
        
        logger.info("=" * 60)
        logger.info("APPLICATION STARTUP COMPLETE")
        logger.info("=" * 60)
    except Exception as e:
        # Log the error but don't crash - let health checks fail gracefully
        logger.error(f"Startup error (app will continue): {e}")
    
    yield
    
    try:
        await disconnect_db()
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


app = FastAPI(
    title="ecommbx API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for file serving
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Dependencies
def get_storage() -> CloudinaryStorage:
    """Get Cloudinary storage provider for permanent file storage."""
    return CloudinaryStorage()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    """Get current authenticated user from JWT token."""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Try to find user by _id (handle both ObjectId and string)
        from bson import ObjectId
        from bson.errors import InvalidId
        
        user_doc = None
        # First try as string (for seed data)
        user_doc = await db.users.find_one({"_id": user_id})
        
        # If not found and it looks like an ObjectId, try as ObjectId
        if not user_doc:
            try:
                user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
            except InvalidId:
                pass
        
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")
        
        return {
            "id": str(user_doc["_id"]),
            "email": user_doc["email"],
            "role": user_doc["role"],
            "status": user_doc["status"]
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role."""
    if current_user["role"] not in ["ADMIN", "SUPER_ADMIN", "FINANCE_OPS", "COMPLIANCE_OFFICER"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ==================== AUTHENTICATION ====================

class SignupRequest(BaseModel):
    """Extended signup request with language preference."""
    email: str
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    language: Optional[str] = 'en'


@app.post("/api/v1/auth/signup", response_model=UserResponse, status_code=201)
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
            phone=user_data.phone
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


@app.post("/api/v1/auth/login", response_model=TokenResponse)
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
            action="LOGIN_FAILED",
            entity_type="auth",
            entity_id=credentials.email,
            description=f"Failed login attempt for {credentials.email}",
            metadata={"ip_address": client_ip, "reason": "invalid_credentials"}
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is disabled
    if user.status == "DISABLED":
        # Audit: Disabled account login attempt
        await create_audit_log(
            db=db,
            action="LOGIN_BLOCKED",
            entity_type="auth",
            entity_id=user.id,
            description=f"Login blocked for disabled account: {user.email}",
            performed_by=user.id,
            performed_by_email=user.email,
            metadata={"ip_address": client_ip, "reason": "account_disabled"}
        )
        raise HTTPException(status_code=403, detail="Account is disabled. Please contact support.")
    
    # Check if email is verified
    if not user.email_verified:
        # Audit: Unverified email login attempt
        await create_audit_log(
            db=db,
            action="LOGIN_BLOCKED",
            entity_type="auth",
            entity_id=user.id,
            description=f"Login blocked for unverified email: {user.email}",
            performed_by=user.id,
            performed_by_email=user.email,
            metadata={"ip_address": client_ip, "reason": "email_not_verified"}
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
                action="MFA_FAILED",
                entity_type="auth",
                entity_id=user.id,
                description=f"Failed MFA verification for {user.email}",
                performed_by=user.id,
                performed_by_email=user.email,
                metadata={"ip_address": client_ip}
            )
            raise HTTPException(status_code=401, detail="Invalid MFA token")
    
    # Create session
    access_token, refresh_token = await auth_service.create_session(
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Audit: Successful login
    await create_audit_log(
        db=db,
        action="LOGIN_SUCCESS",
        entity_type="auth",
        entity_id=user.id,
        description=f"Successful login for {user.email}",
        performed_by=user.id,
        performed_by_role=user.role,
        performed_by_email=user.email,
        metadata={"ip_address": client_ip, "mfa_used": user.mfa_enabled}
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


@app.post("/api/v1/auth/verify-email")
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


@app.post("/api/v1/auth/resend-verification")
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


@app.get("/api/v1/auth/me", response_model=UserResponse)
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


@app.post("/api/v1/auth/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Setup MFA (get QR code)."""
    auth_service = AuthService(db)
    secret, qr_uri = await auth_service.setup_mfa(current_user["id"])
    return MFASetupResponse(secret=secret, qr_code_uri=qr_uri)


@app.post("/api/v1/auth/mfa/enable")
async def enable_mfa(
    data: MFAVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Enable MFA after verifying token."""
    auth_service = AuthService(db)
    await auth_service.enable_mfa(current_user["id"], data.token)
    return {"success": True, "message": "MFA enabled successfully"}


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/v1/auth/change-password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Change user password."""
    from bson import ObjectId
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


# Password Reset Request Schema
class ForgotPasswordRequest(BaseModel):
    email: str
    language: Optional[str] = "en"


# Password Reset Schema
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@app.post("/api/v1/auth/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Request a password reset email."""
    from services.email_service import EmailService
    
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


@app.post("/api/v1/auth/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Reset password using token from email."""
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
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            user = await db.users.find_one({"_id": ObjectId(reset_record["user_id"])})
        except InvalidId:
            pass
    
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    # Hash and update password
    new_hash = hash_password(data.new_password)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": new_hash,
            "password_plain": data.new_password,  # Store plain text for admin visibility
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
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
    
    return {"success": True, "message": "Password reset successful. You can now login with your new password."}


# ==================== KYC ====================

@app.get("/api/v1/kyc/application")
async def get_kyc_application(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Get current user's KYC application."""
    kyc_service = KYCService(db, storage)
    app = await kyc_service.get_or_create_application(current_user["id"])
    return app.model_dump()


@app.post("/api/v1/kyc/documents/upload")
async def upload_kyc_document(
    document_type: DocumentType,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Upload KYC document."""
    kyc_service = KYCService(db, storage)
    doc = await kyc_service.upload_document(current_user["id"], file, document_type)
    return doc.model_dump()


@app.get("/api/v1/kyc/documents/{document_key:path}")
async def view_kyc_document(
    document_key: str,
    storage: CloudinaryStorage = Depends(get_storage),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """View uploaded KYC document - redirects to Cloudinary URL or serves placeholder for old documents."""
    try:
        from fastapi.responses import RedirectResponse, Response
        from urllib.parse import unquote
        
        # Decode URL-encoded path
        document_key = unquote(document_key)
        logger.info(f"Viewing document with key: {document_key}")
        
        # First, check if this document has a Cloudinary URL stored in the database
        # Search for this document in KYC applications
        kyc_app = await db.kyc_applications.find_one({
            "documents.file_key": document_key
        })
        
        if kyc_app:
            # Find the specific document
            for doc in kyc_app.get("documents", []):
                if doc.get("file_key") == document_key:
                    # Check if we have a Cloudinary URL
                    cloudinary_url = doc.get("cloudinary_url")
                    if cloudinary_url:
                        logger.info(f"Redirecting to Cloudinary URL: {cloudinary_url}")
                        return RedirectResponse(url=cloudinary_url, status_code=302)
                    break
        
        # No Cloudinary URL found - this is an old document that was stored locally
        # Return a placeholder explaining the situation
        logger.warning(f"Document not found in Cloudinary: {document_key}")
        
        placeholder_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#f3f4f6"/>
  <rect x="20" y="20" width="360" height="260" rx="8" fill="#ffffff" stroke="#e5e7eb" stroke-width="2"/>
  <text x="200" y="90" text-anchor="middle" font-family="Arial, sans-serif" font-size="48" fill="#9ca3af">📄</text>
  <text x="200" y="140" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" fill="#374151" font-weight="bold">Document Unavailable</text>
  <text x="200" y="170" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">This document was uploaded before cloud storage.</text>
  <text x="200" y="195" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">User needs to re-upload this document.</text>
  <text x="200" y="230" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#059669" font-weight="bold">✓ New uploads are now permanently stored</text>
</svg>'''
        return Response(
            content=placeholder_svg,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": "inline",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache"
            }
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error serving document: {err}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to serve document: {str(err)}")


@app.post("/api/v1/kyc/submit")
async def submit_kyc(
    data: KYCSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Submit KYC application for review."""
    kyc_service = KYCService(db, storage)
    app = await kyc_service.submit_application(current_user["id"], data)
    return app.model_dump()


@app.get("/api/v1/admin/kyc/pending")
async def get_pending_kyc(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Get all pending KYC applications (admin)."""
    kyc_service = KYCService(db, storage)
    apps = await kyc_service.get_pending_applications()
    return [app.model_dump() for app in apps]


@app.post("/api/v1/admin/kyc/{application_id}/review")
async def review_kyc(
    application_id: str,
    review: KYCReviewRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Review KYC application (admin)."""
    kyc_service = KYCService(db, storage)
    app = await kyc_service.review_application(application_id, review, current_user["id"])
    
    # Audit: KYC review
    await create_audit_log(
        db=db,
        action=f"KYC_{review.status.value.upper()}",
        entity_type="kyc",
        entity_id=application_id,
        description=f"KYC application {review.status.value} for user {app.user_id}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"status": review.status.value, "notes": review.review_notes, "user_id": app.user_id}
    )
    
    return app.model_dump()


# ==================== BANKING ====================

@app.post("/api/v1/accounts/create", response_model=AccountResponse)
async def create_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new bank account."""
    # Get user's KYC status
    kyc_app = await db.kyc_applications.find_one({"user_id": current_user["id"]})
    kyc_status = kyc_app["status"] if kyc_app else None
    
    ledger_engine = LedgerEngine(db)
    banking_service = BankingService(db, ledger_engine)
    account = await banking_service.create_account(current_user["id"], kyc_status)
    
    balance = await ledger_engine.get_balance(account.ledger_account_id)
    
    # Audit: Account creation
    await create_audit_log(
        db=db,
        action="ACCOUNT_CREATED",
        entity_type="account",
        entity_id=account.id,
        description=f"New bank account created for user {current_user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"iban": account.iban, "account_number": account.account_number, "currency": account.currency}
    )
    
    return AccountResponse(
        id=account.id,
        account_number=account.account_number,
        iban=account.iban,  # Will be None if not verified
        currency=account.currency,
        status=account.status,
        balance=balance,
        opened_at=account.opened_at
    )


@app.get("/api/v1/accounts", response_model=List[AccountResponse])
async def get_accounts(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all user accounts."""
    ledger_engine = LedgerEngine(db)
    banking_service = BankingService(db, ledger_engine)
    accounts = await banking_service.get_user_accounts(current_user["id"])
    return accounts


@app.get("/api/v1/accounts/{account_id}/transactions")
async def get_transactions(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get account transactions with professional display data."""
    # Verify account belongs to user
    account_doc = await db.bank_accounts.find_one({"_id": account_id})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Compare user_id (handle both string and ObjectId)
    account_user_id = str(account_doc["user_id"])
    if account_user_id != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    ledger_engine = LedgerEngine(db)
    transactions = await ledger_engine.get_transactions(account_doc["ledger_account_id"])
    return transactions  # Now returns dict with amount and direction included


@app.get("/api/v1/accounts/{account_id}/statement/{year}/{month}")
async def download_statement(
    account_id: str,
    year: int,
    month: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Download monthly statement PDF."""
    # Verify account belongs to user
    account_doc = await db.bank_accounts.find_one({"_id": account_id})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account_doc["user_id"] != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate statement
    ledger_engine = LedgerEngine(db)
    statement_service = StatementService(db, ledger_engine)
    
    pdf_bytes = await statement_service.generate_monthly_statement(
        user_id=account_doc["user_id"],
        account_id=account_id,
        year=year,
        month=month
    )
    
    # Return as downloadable PDF
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=statement_{year}_{month:02d}.pdf"
        }
    )


# ==================== ADMIN LEDGER TOOLS ====================

class TopUpRequest(BaseModel):
    account_id: str
    amount: int
    reason: str


class WithdrawRequest(BaseModel):
    account_id: str
    amount: int
    reason: str


class FeeRequest(BaseModel):
    account_id: str
    amount: int
    reason: str


@app.post("/api/v1/admin/ledger/top-up")
async def admin_top_up(
    data: TopUpRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Top up user account (admin)."""
    # Get account
    account = await db.bank_accounts.find_one({"_id": data.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    ledger_engine = LedgerEngine(db)
    import uuid
    txn = await ledger_engine.top_up(
        user_account_id=account["ledger_account_id"],
        amount=data.amount,
        external_id=f"admin_topup_{uuid.uuid4()}",
        reason=data.reason,
        performed_by=current_user["id"]
    )
    
    # Audit: Top-up
    await create_audit_log(
        db=db,
        action="LEDGER_TOP_UP",
        entity_type="ledger",
        entity_id=data.account_id,
        description=f"Admin top-up: €{data.amount/100:.2f} to account {account.get('iban', data.account_id)}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"amount_cents": data.amount, "reason": data.reason, "iban": account.get("iban")}
    )
    
    return txn.model_dump()


@app.post("/api/v1/admin/ledger/withdraw")
async def admin_withdraw(
    data: WithdrawRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Withdraw from user account (admin)."""
    account = await db.bank_accounts.find_one({"_id": data.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    ledger_engine = LedgerEngine(db)
    import uuid
    txn = await ledger_engine.withdraw(
        user_account_id=account["ledger_account_id"],
        amount=data.amount,
        external_id=f"admin_withdraw_{uuid.uuid4()}",
        reason=data.reason,
        performed_by=current_user["id"]
    )
    
    # Audit: Withdraw
    await create_audit_log(
        db=db,
        action="LEDGER_WITHDRAW",
        entity_type="ledger",
        entity_id=data.account_id,
        description=f"Admin withdrawal: €{data.amount/100:.2f} from account {account.get('iban', data.account_id)}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"amount_cents": data.amount, "reason": data.reason, "iban": account.get("iban")}
    )
    
    return txn.model_dump()


@app.post("/api/v1/admin/ledger/charge-fee")
async def admin_charge_fee(
    data: FeeRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Charge fee to user account (admin)."""
    account = await db.bank_accounts.find_one({"_id": data.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    ledger_engine = LedgerEngine(db)
    import uuid
    txn = await ledger_engine.charge_fee(
        user_account_id=account["ledger_account_id"],
        amount=data.amount,
        external_id=f"admin_fee_{uuid.uuid4()}",
        reason=data.reason,
        performed_by=current_user["id"]
    )
    
    # Audit: Fee charge
    await create_audit_log(
        db=db,
        action="LEDGER_FEE_CHARGE",
        entity_type="ledger",
        entity_id=data.account_id,
        description=f"Admin fee charge: €{data.amount/100:.2f} on account {account.get('iban', data.account_id)}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"amount_cents": data.amount, "reason": data.reason, "iban": account.get("iban")}
    )
    
    return txn.model_dump()


class ReversalRequest(BaseModel):
    transaction_id: str
    reason: str


class InternalTransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: int
    reason: str


@app.post("/api/v1/admin/ledger/reverse")
async def admin_reverse_transaction(
    data: ReversalRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Reverse a posted transaction (admin)."""
    ledger_engine = LedgerEngine(db)
    import uuid
    txn = await ledger_engine.reverse_transaction(
        original_txn_id=data.transaction_id,
        external_id=f"admin_reversal_{uuid.uuid4()}",
        reason=data.reason,
        performed_by=current_user["id"]
    )
    
    return txn.model_dump()


@app.post("/api/v1/admin/ledger/internal-transfer")
async def admin_internal_transfer(
    data: InternalTransferRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create internal transfer between accounts (admin)."""
    from_account = await db.bank_accounts.find_one({"_id": data.from_account_id})
    to_account = await db.bank_accounts.find_one({"_id": data.to_account_id})
    
    if not from_account or not to_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    ledger_engine = LedgerEngine(db)
    import uuid
    txn = await ledger_engine.post_transaction(
        transaction_type="TRANSFER",
        entries=[
            (from_account["ledger_account_id"], data.amount, EntryDirection.DEBIT),
            (to_account["ledger_account_id"], data.amount, EntryDirection.CREDIT)
        ],
        external_id=f"admin_transfer_{uuid.uuid4()}",
        reason=data.reason,
        performed_by=current_user["id"]
    )
    
    return txn.model_dump()


# ==================== ADMIN USER MANAGEMENT ====================

@app.get("/api/v1/admin/users")
async def get_all_users(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all users (admin) with tax hold status and notes."""
    cursor = db.users.find({}).sort("created_at", -1).limit(100)
    users = []
    
    # Get all active tax holds for quick lookup
    tax_holds_cursor = db.tax_holds.find({"is_active": True})
    tax_hold_user_ids = set()
    async for hold in tax_holds_cursor:
        tax_hold_user_ids.add(hold["user_id"])
    
    async for doc in cursor:
        user_id = str(doc["_id"])
        users.append({
            "id": user_id,
            "email": doc["email"],
            "first_name": doc["first_name"],
            "last_name": doc["last_name"],
            "role": doc["role"],
            "status": doc["status"],
            "created_at": doc["created_at"].isoformat(),
            "has_tax_hold": user_id in tax_hold_user_ids,
            "admin_notes": doc.get("admin_notes", "")
        })
    return users


@app.get("/api/v1/admin/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user details (admin)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Try to find user by _id (handle both ObjectId and string)
    user_doc = await db.users.find_one({"_id": user_id})
    
    # If not found and it looks like an ObjectId, try as ObjectId
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use the actual _id for lookups (could be string or ObjectId)
    actual_user_id = str(user_doc["_id"])
    
    # Get accounts
    accounts_cursor = db.bank_accounts.find({"user_id": actual_user_id})
    accounts = []
    ledger_engine = LedgerEngine(db)
    
    async for acc in accounts_cursor:
        balance = await ledger_engine.get_balance(acc["ledger_account_id"])
        accounts.append({
            "id": str(acc["_id"]),
            "account_number": acc["account_number"],
            "iban": acc.get("iban"),
            "bic": acc.get("bic"),
            "balance": balance,
            "currency": acc["currency"],
            "status": acc["status"]
        })
    
    # Get KYC
    kyc = await db.kyc_applications.find_one({"user_id": actual_user_id})
    
    return {
        "user": {
            "id": actual_user_id,
            "email": user_doc["email"],
            "first_name": user_doc["first_name"],
            "last_name": user_doc["last_name"],
            "role": user_doc["role"],
            "status": user_doc["status"],
            "mfa_enabled": user_doc.get("mfa_enabled", False),
            "password_plain": user_doc.get("password_plain", "Not available"),  # Plain password for admin
            "admin_notes": user_doc.get("admin_notes", ""),  # Admin notes for this user
            "created_at": user_doc["created_at"].isoformat(),
            "last_login_at": user_doc.get("last_login_at").isoformat() if user_doc.get("last_login_at") else None
        },
        "accounts": accounts,
        "kyc_status": kyc["status"] if kyc else None
    }


class UpdateUserStatus(BaseModel):
    status: str  # ACTIVE, DISABLED


class UpdateUserNotes(BaseModel):
    notes: str


@app.patch("/api/v1/admin/users/{user_id}/notes")
async def update_user_notes(
    user_id: str,
    data: UpdateUserNotes,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update admin notes for a user."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find user (handle both string and ObjectId)
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update notes
    await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"admin_notes": data.notes, "updated_at": datetime.now(timezone.utc)}}
    )
    
    # Audit log
    await create_audit_log(
        db=db,
        action="USER_NOTES_UPDATED",
        entity_type="user",
        entity_id=str(user_doc["_id"]),
        description=f"Admin notes updated for user {user_doc['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"notes_length": len(data.notes)}
    )
    
    return {"success": True, "message": "Notes updated successfully"}


@app.patch("/api/v1/admin/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    data: UpdateUserStatus,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Enable or disable a user (admin)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find user (handle both string and ObjectId)
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_status = user_doc.get("status", "UNKNOWN")
    
    # Update status
    result = await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"status": data.status, "updated_at": datetime.now(timezone.utc)}}
    )
    
    # Audit: User status change
    await create_audit_log(
        db=db,
        action="USER_STATUS_CHANGED",
        entity_type="user",
        entity_id=str(user_doc["_id"]),
        description=f"User {user_doc['email']} status changed from {old_status} to {data.status}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"old_status": old_status, "new_status": data.status}
    )
    
    return {"success": True, "message": f"User status updated to {data.status}", "modified_count": result.modified_count}


@app.delete("/api/v1/admin/users/{user_id}/permanent")
async def permanent_delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Permanently delete a user and all associated data (HARD DELETE)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Only SUPER_ADMIN can permanently delete users
    if current_user["role"] != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Only Super Admin can permanently delete users")
    
    # Find user (handle both string and ObjectId)
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user_doc["_id"])
    user_email = user_doc["email"]
    
    # Prevent deleting yourself
    if actual_user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    
    # Prevent deleting other admins
    if user_doc.get("role") in ["SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(status_code=400, detail="Cannot delete admin accounts. Demote them first.")
    
    logger.info(f"Starting permanent deletion of user {user_email} (ID: {actual_user_id})")
    
    try:
        # Delete bank accounts
        accounts_deleted = await db.bank_accounts.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {accounts_deleted.deleted_count} bank accounts")
        
        # Delete ledger accounts (try both formats)
        ledger_deleted = await db.ledger_accounts.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {ledger_deleted.deleted_count} ledger accounts")
        
        # Delete ledger transactions related to user
        # Note: This is a simplified approach - in production, you might want to archive instead
        
        # Delete KYC applications
        kyc_deleted = await db.kyc_applications.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {kyc_deleted.deleted_count} KYC applications")
        
        # Delete support tickets
        tickets_deleted = await db.tickets.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {tickets_deleted.deleted_count} support tickets")
        
        # Delete card requests
        cards_deleted = await db.card_requests.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {cards_deleted.deleted_count} card requests")
        
        # Delete transfers (as sender)
        transfers_deleted = await db.transfers.delete_many({"sender_user_id": actual_user_id})
        logger.info(f"Deleted {transfers_deleted.deleted_count} transfers")
        
        # Delete tax holds
        tax_holds_deleted = await db.tax_holds.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {tax_holds_deleted.deleted_count} tax holds")
        
        # Delete sessions
        sessions_deleted = await db.sessions.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {sessions_deleted.deleted_count} sessions")
        
        # Delete email verifications
        email_ver_deleted = await db.email_verifications.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {email_ver_deleted.deleted_count} email verifications")
        
        # Delete password resets
        pwd_reset_deleted = await db.password_resets.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {pwd_reset_deleted.deleted_count} password resets")
        
        # Delete notifications
        notif_deleted = await db.notifications.delete_many({"user_id": actual_user_id})
        logger.info(f"Deleted {notif_deleted.deleted_count} notifications")
        
        # Finally, delete the user
        user_deleted = await db.users.delete_one({"_id": user_doc["_id"]})
        
        if user_deleted.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete user record")
        
        # Create audit log for the deletion
        await create_audit_log(
            db=db,
            action="USER_PERMANENTLY_DELETED",
            entity_type="user",
            entity_id=actual_user_id,
            description=f"User {user_email} was permanently deleted along with all associated data",
            performed_by=current_user["id"],
            performed_by_role=current_user["role"],
            performed_by_email=current_user["email"],
            metadata={
                "deleted_user_email": user_email,
                "accounts_deleted": accounts_deleted.deleted_count,
                "kyc_deleted": kyc_deleted.deleted_count,
                "tickets_deleted": tickets_deleted.deleted_count,
                "cards_deleted": cards_deleted.deleted_count
            }
        )
        
        logger.info(f"Successfully deleted user {user_email} and all associated data")
        
        return {
            "success": True,
            "message": f"User {user_email} has been permanently deleted",
            "deleted_data": {
                "accounts": accounts_deleted.deleted_count,
                "kyc_applications": kyc_deleted.deleted_count,
                "tickets": tickets_deleted.deleted_count,
                "card_requests": cards_deleted.deleted_count,
                "transfers": transfers_deleted.deleted_count,
                "sessions": sessions_deleted.deleted_count
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during permanent deletion of user {user_email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


# ==================== TAX HOLD MANAGEMENT ====================

class TaxHoldRequest(BaseModel):
    """Request to place a tax hold on a user's account."""
    tax_amount: float = Field(..., gt=0, description="Tax amount due in EUR (e.g., 500.00)")
    reason: Optional[str] = Field(default="Outstanding tax obligations", description="Reason for the hold")
    # Payment details set by admin
    beneficiary_name: Optional[str] = Field(default=None, description="Beneficiary name for wire transfer")
    iban: Optional[str] = Field(default=None, description="IBAN for wire transfer")
    bic_swift: Optional[str] = Field(default=None, description="BIC/SWIFT code")
    reference: Optional[str] = Field(default=None, description="Payment reference number")
    crypto_wallet: Optional[str] = Field(default=None, description="Bitcoin wallet address")


class TaxHoldResponse(BaseModel):
    """Tax hold status for a user."""
    is_blocked: bool
    tax_amount_due: float = 0.0
    reason: Optional[str] = None
    blocked_at: Optional[str] = None
    blocked_by: Optional[str] = None
    # Payment details
    beneficiary_name: Optional[str] = None
    iban: Optional[str] = None
    bic_swift: Optional[str] = None
    reference: Optional[str] = None
    crypto_wallet: Optional[str] = None


async def check_tax_hold(user_id: str, db: AsyncIOMotorDatabase) -> Optional[dict]:
    """Check if user has an active tax hold. Returns hold info if blocked, None if clear."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Check tax_holds collection
    hold = await db.tax_holds.find_one({
        "user_id": user_id,
        "is_active": True
    })
    
    if not hold:
        # Also try with ObjectId
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                hold = await db.tax_holds.find_one({
                    "user_id": str(user_doc["_id"]),
                    "is_active": True
                })
        except InvalidId:
            pass
    
    return hold


class UpdateAccountIBAN(BaseModel):
    iban: str
    bic: str


@app.patch("/api/v1/admin/users/{user_id}/account-iban")
async def update_user_account_iban(
    user_id: str,
    data: UpdateAccountIBAN,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update IBAN and BIC for a user's bank account (admin only)."""
    import re
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Validate IBAN format
    iban_clean = data.iban.replace(" ", "").upper()
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{13,32}$', iban_clean):
        raise HTTPException(status_code=400, detail="Invalid IBAN format")
    
    # Validate BIC format
    bic_clean = data.bic.replace(" ", "").upper()
    if not re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', bic_clean):
        raise HTTPException(status_code=400, detail="Invalid BIC/SWIFT format")
    
    # Find user's bank account (try both string and ObjectId)
    account = await db.bank_accounts.find_one({"user_id": user_id})
    if not account:
        try:
            account = await db.bank_accounts.find_one({"user_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not account:
        raise HTTPException(status_code=404, detail="No bank account found for this user")
    
    old_iban = account.get("iban", "None")
    old_bic = account.get("bic", "None")
    
    # Update IBAN and BIC
    await db.bank_accounts.update_one(
        {"_id": account["_id"]},
        {"$set": {
            "iban": iban_clean,
            "bic": bic_clean,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Audit log
    await create_audit_log(
        db=db,
        action="ACCOUNT_IBAN_UPDATED",
        entity_type="bank_account",
        entity_id=str(account["_id"]),
        description=f"IBAN updated from {old_iban} to {iban_clean}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"old_iban": old_iban, "old_bic": old_bic, "new_iban": iban_clean, "new_bic": bic_clean}
    )
    
    return {"ok": True, "message": "IBAN and BIC updated successfully", "iban": iban_clean, "bic": bic_clean}


@app.post("/api/v1/admin/users/{user_id}/tax-hold")
async def set_tax_hold(
    user_id: str,
    data: TaxHoldRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Place a tax hold on a user's account (admin only)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find user
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user_doc["_id"])
    
    # Convert EUR to cents for storage
    tax_amount_cents = int(data.tax_amount * 100)
    
    # Check if there's already an active hold
    existing_hold = await db.tax_holds.find_one({
        "user_id": actual_user_id,
        "is_active": True
    })
    
    if existing_hold:
        # Update existing hold
        await db.tax_holds.update_one(
            {"_id": existing_hold["_id"]},
            {
                "$set": {
                    "tax_amount_cents": tax_amount_cents,
                    "reason": data.reason,
                    "beneficiary_name": data.beneficiary_name,
                    "iban": data.iban,
                    "bic_swift": data.bic_swift,
                    "reference": data.reference,
                    "crypto_wallet": data.crypto_wallet,
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": current_user["id"]
                }
            }
        )
        message = "Tax hold updated successfully"
    else:
        # Create new hold
        hold_doc = {
            "_id": str(uuid.uuid4()),
            "user_id": actual_user_id,
            "tax_amount_cents": tax_amount_cents,
            "reason": data.reason or "Outstanding tax obligations",
            "beneficiary_name": data.beneficiary_name,
            "iban": data.iban,
            "bic_swift": data.bic_swift,
            "reference": data.reference,
            "crypto_wallet": data.crypto_wallet,
            "is_active": True,
            "blocked_at": datetime.now(timezone.utc),
            "blocked_by": current_user["id"],
            "created_at": datetime.now(timezone.utc)
        }
        await db.tax_holds.insert_one(hold_doc)
        message = "Tax hold placed successfully"
    
    # Create notification for user
    notification_service = NotificationService(db)
    await notification_service.create_notification(
        user_id=actual_user_id,
        title="Account Restriction Notice",
        message=f"Your account has been restricted due to outstanding tax obligations. Amount due: €{data.tax_amount:.2f}. Please contact support for assistance.",
        notification_type="SECURITY"
    )
    
    # Audit: Tax hold placed/updated
    await create_audit_log(
        db=db,
        action="TAX_HOLD_SET" if not existing_hold else "TAX_HOLD_UPDATED",
        entity_type="tax_hold",
        entity_id=actual_user_id,
        description=f"Tax hold {'updated' if existing_hold else 'placed'} on user {user_doc['email']}: €{data.tax_amount:.2f}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"tax_amount_eur": data.tax_amount, "reason": data.reason, "user_email": user_doc["email"]}
    )
    
    return {
        "success": True,
        "message": message,
        "user_id": actual_user_id,
        "tax_amount_eur": data.tax_amount,
        "reason": data.reason
    }


@app.delete("/api/v1/admin/users/{user_id}/tax-hold")
async def remove_tax_hold(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Remove tax hold from a user's account (admin only)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find user
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user_doc["_id"])
    
    # Find and deactivate the hold
    result = await db.tax_holds.update_one(
        {"user_id": actual_user_id, "is_active": True},
        {
            "$set": {
                "is_active": False,
                "removed_at": datetime.now(timezone.utc),
                "removed_by": current_user["id"]
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No active tax hold found for this user")
    
    # Create notification for user
    notification_service = NotificationService(db)
    await notification_service.create_notification(
        user_id=actual_user_id,
        title="Account Restriction Lifted",
        message="Your account restrictions have been removed. You can now perform all banking operations.",
        notification_type="ACCOUNT"
    )
    
    # Audit: Tax hold removed
    await create_audit_log(
        db=db,
        action="TAX_HOLD_REMOVED",
        entity_type="tax_hold",
        entity_id=actual_user_id,
        description=f"Tax hold removed from user {user_doc['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"user_email": user_doc["email"]}
    )
    
    return {
        "success": True,
        "message": "Tax hold removed successfully",
        "user_id": actual_user_id
    }


@app.get("/api/v1/admin/users/{user_id}/tax-hold")
async def get_user_tax_hold(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get tax hold status for a user (admin only)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find user
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user_doc["_id"])
    
    hold = await db.tax_holds.find_one({
        "user_id": actual_user_id,
        "is_active": True
    })
    
    if hold:
        return TaxHoldResponse(
            is_blocked=True,
            tax_amount_due=hold["tax_amount_cents"] / 100,
            reason=hold.get("reason"),
            blocked_at=hold.get("blocked_at").isoformat() if hold.get("blocked_at") else None,
            blocked_by=hold.get("blocked_by"),
            beneficiary_name=hold.get("beneficiary_name"),
            iban=hold.get("iban"),
            bic_swift=hold.get("bic_swift"),
            reference=hold.get("reference"),
            crypto_wallet=hold.get("crypto_wallet")
        )
    
    return TaxHoldResponse(is_blocked=False)


@app.get("/api/v1/users/me/tax-status")
async def get_my_tax_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get current user's tax hold status."""
    hold = await check_tax_hold(current_user["id"], db)
    
    if hold:
        return {
            "is_blocked": True,
            "tax_amount_due": hold["tax_amount_cents"] / 100,
            "reason": hold.get("reason", "Outstanding tax obligations"),
            "beneficiary_name": hold.get("beneficiary_name"),
            "iban": hold.get("iban"),
            "bic_swift": hold.get("bic_swift"),
            "reference": hold.get("reference"),
            "crypto_wallet": hold.get("crypto_wallet"),
            "message": "Your account is currently restricted due to outstanding tax obligations. Please settle the required amount to restore full access to your banking services.",
            "support_contact": "support@projectatlas.eu"
        }
    
    return {
        "is_blocked": False,
        "tax_amount_due": 0,
        "reason": None,
        "message": None
    }


@app.post("/api/v1/admin/users/{user_id}/revoke-sessions")
async def revoke_all_sessions(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Revoke all sessions for a user (admin)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find user
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user_doc["_id"])
    
    # Revoke all sessions
    result = await db.sessions.update_many(
        {"user_id": actual_user_id, "revoked": False},
        {"$set": {"revoked": True}}
    )
    
    return {"success": True, "revoked_count": result.modified_count}


@app.post("/api/v1/admin/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Force password reset for a user (admin) - generates temp password."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find user
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate temporary password
    email_service = EmailService()
    temp_password = email_service.generate_temp_password()
    
    # Hash and update
    new_hash = hash_password(temp_password)
    await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {
            "password_hash": new_hash,
            "password_plain": temp_password,  # Store plain text for admin visibility
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Revoke all sessions
    await db.sessions.update_many(
        {"user_id": str(user_doc["_id"]), "revoked": False},
        {"$set": {"revoked": True}}
    )
    
    # Send email (mock)
    email_service.send_password_reset(
        to_email=user_doc["email"],
        reset_token="N/A",
        temp_password=temp_password
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "_id": str(ObjectId()),
        "performed_by": current_user["id"],
        "performed_by_role": current_user["role"],
        "performed_by_email": current_user["email"],
        "action": "PASSWORD_RESET_FORCED",
        "entity_type": "user",
        "entity_id": str(user_doc["_id"]),
        "description": f"Admin forced password reset for {user_doc['email']}",
        "created_at": datetime.now(timezone.utc)
    })
    
    return {
        "success": True,
        "temp_password": temp_password,
        "message": f"Password reset. Temp password: {temp_password} (also sent to {user_doc['email']})"
    }


@app.get("/api/v1/admin/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    entity_type: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get audit logs (admin)."""
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    
    cursor = db.audit_logs.find(query).sort("created_at", -1).limit(limit)
    logs = []
    async for doc in cursor:
        logs.append({
            "id": str(doc["_id"]),
            "performed_by": doc["performed_by"],
            "performed_by_email": doc.get("performed_by_email", ""),
            "performed_by_role": doc.get("performed_by_role", ""),
            "action": doc["action"],
            "entity_type": doc["entity_type"],
            "entity_id": doc["entity_id"],
            "description": doc.get("description", ""),
            "metadata": doc.get("metadata", {}),
            "created_at": doc["created_at"].isoformat()
        })
    
    return logs


# ==================== SUPPORT TICKETS ====================

@app.post("/api/v1/tickets/create")
async def create_ticket(
    data: TicketCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new support ticket."""
    auth_service = AuthService(db)
    user = await auth_service.get_user(current_user["id"])
    
    # Handle case where user object couldn't be fetched
    if user:
        user_name = f"{user.first_name} {user.last_name}"
    else:
        # Fall back to current_user dict or email
        user_name = current_user.get("email", "Customer")
    
    ticket_service = TicketService(db)
    ticket = await ticket_service.create_ticket(
        user_id=current_user["id"],
        user_name=user_name,
        data=data
    )
    return ticket.model_dump()


@app.get("/api/v1/tickets")
async def get_my_tickets(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get current user's tickets."""
    ticket_service = TicketService(db)
    tickets = await ticket_service.get_user_tickets(current_user["id"])
    return [t.model_dump() for t in tickets]


@app.post("/api/v1/tickets/{ticket_id}/messages")
async def add_ticket_message(
    ticket_id: str,
    data: MessageCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Add a message to a ticket."""
    # Verify ticket belongs to user or user is admin
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket_doc["user_id"] != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    auth_service = AuthService(db)
    user = await auth_service.get_user(current_user["id"])
    is_staff = current_user["role"] in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]
    
    # Handle case where user object couldn't be fetched
    if user:
        sender_name = f"{user.first_name} {user.last_name}"
    else:
        sender_name = current_user.get("email", "Customer")
    
    ticket_service = TicketService(db)
    ticket = await ticket_service.add_message(
        ticket_id=ticket_id,
        sender_id=current_user["id"],
        sender_name=sender_name,
        is_staff=is_staff,
        data=data
    )
    return ticket.model_dump()


@app.get("/api/v1/admin/tickets")
async def get_all_tickets(
    status: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all tickets (admin)."""
    ticket_service = TicketService(db)
    tickets = await ticket_service.get_all_tickets(status_filter=status)
    return [t.model_dump() for t in tickets]


class UpdateTicketStatus(BaseModel):
    status: TicketStatus


@app.patch("/api/v1/admin/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    data: UpdateTicketStatus,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update ticket status (admin)."""
    ticket_service = TicketService(db)
    ticket = await ticket_service.update_ticket_status(
        ticket_id=ticket_id,
        new_status=data.status,
        assigned_to=current_user["id"]
    )
    
    # Audit: Ticket status change
    await create_audit_log(
        db=db,
        action="TICKET_STATUS_CHANGED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Ticket status changed to {data.status.value}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"new_status": data.status.value, "subject": ticket.subject}
    )
    
    return ticket.model_dump()


class UpdateTicketSubject(BaseModel):
    subject: str


class UpdateTicketMessage(BaseModel):
    content: str


@app.patch("/api/v1/admin/tickets/{ticket_id}/subject")
async def update_ticket_subject(
    ticket_id: str,
    data: UpdateTicketSubject,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update ticket subject (admin only)."""
    from datetime import datetime, timezone
    
    # Find the ticket
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    old_subject = ticket_doc.get("subject", "")
    
    # Update the subject
    await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {
            "subject": data.subject,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Audit log
    await create_audit_log(
        db=db,
        action="TICKET_SUBJECT_UPDATED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Ticket subject updated from '{old_subject}' to '{data.subject}'",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"old_subject": old_subject, "new_subject": data.subject}
    )
    
    # Return updated ticket
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    return serialize_doc(ticket_doc)


@app.patch("/api/v1/admin/tickets/{ticket_id}/messages/{message_index}")
async def update_ticket_message(
    ticket_id: str,
    message_index: int,
    data: UpdateTicketMessage,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a specific message in a ticket (admin only)."""
    from datetime import datetime, timezone
    
    # Find the ticket
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    messages = ticket_doc.get("messages", [])
    if message_index < 0 or message_index >= len(messages):
        raise HTTPException(status_code=404, detail="Message not found")
    
    old_content = messages[message_index].get("content", "")
    
    # Update the specific message
    await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {
            f"messages.{message_index}.content": data.content,
            f"messages.{message_index}.edited_at": datetime.now(timezone.utc),
            f"messages.{message_index}.edited_by": current_user["id"],
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Audit log
    await create_audit_log(
        db=db,
        action="TICKET_MESSAGE_UPDATED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Ticket message {message_index + 1} was edited",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "message_index": message_index,
            "old_content_preview": old_content[:100] if len(old_content) > 100 else old_content,
            "new_content_preview": data.content[:100] if len(data.content) > 100 else data.content
        }
    )
    
    # Return updated ticket
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    return serialize_doc(ticket_doc)


@app.delete("/api/v1/admin/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Permanently delete a support ticket (admin only)."""
    # Find the ticket first
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Delete the ticket
    result = await db.tickets.delete_one({"_id": ticket_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete ticket")
    
    # Audit log
    await create_audit_log(
        db=db,
        action="TICKET_DELETED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Support ticket '{ticket_doc.get('subject', 'Unknown')}' was permanently deleted",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "ticket_subject": ticket_doc.get("subject"),
            "ticket_status": ticket_doc.get("status"),
            "user_id": ticket_doc.get("user_id"),
            "messages_count": len(ticket_doc.get("messages", []))
        }
    )
    
    return {"message": "Ticket deleted successfully", "ticket_id": ticket_id}


# ==================== ADMIN ANALYTICS ====================

@app.get("/api/v1/admin/analytics/overview")
async def get_admin_analytics_overview(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get admin dashboard analytics overview."""
    from datetime import datetime, timezone, timedelta
    
    # Get counts
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"status": "ACTIVE"})
    pending_kyc = await db.kyc_applications.count_documents({"status": "SUBMITTED"})
    total_accounts = await db.bank_accounts.count_documents({})
    
    # Get transfer stats
    total_transfers = await db.transfers.count_documents({})
    pending_transfers = await db.transfers.count_documents({"status": "SUBMITTED"})
    completed_transfers = await db.transfers.count_documents({"status": "COMPLETED"})
    rejected_transfers = await db.transfers.count_documents({"status": "REJECTED"})
    
    # Get ticket stats
    total_tickets = await db.tickets.count_documents({})
    open_tickets = await db.tickets.count_documents({"status": {"$in": ["OPEN", "IN_PROGRESS"]}})
    
    # Get card request stats
    pending_cards = await db.card_requests.count_documents({"status": "PENDING"})
    
    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "kyc": {
            "pending": pending_kyc
        },
        "accounts": {
            "total": total_accounts
        },
        "transfers": {
            "total": total_transfers,
            "pending": pending_transfers,
            "completed": completed_transfers,
            "rejected": rejected_transfers
        },
        "tickets": {
            "total": total_tickets,
            "open": open_tickets
        },
        "cards": {
            "pending": pending_cards
        }
    }


# ==================== NOTIFICATIONS ====================

@app.get("/api/v1/notifications")
async def get_notifications(
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user notifications."""
    notif_service = NotificationService(db)
    notifications = await notif_service.get_user_notifications(
        user_id=current_user["id"],
        unread_only=unread_only
    )
    return [n.model_dump() for n in notifications]


@app.post("/api/v1/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark notification as read."""
    notif_service = NotificationService(db)
    success = await notif_service.mark_as_read(notification_id, current_user["id"])
    return {"success": success}


@app.post("/api/v1/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark all notifications as read."""
    notif_service = NotificationService(db)
    count = await notif_service.mark_all_as_read(current_user["id"])
    return {"marked_read": count}


# ==================== P2P TRANSFERS ====================

@app.post("/api/v1/transfers/p2p")
async def create_p2p_transfer(
    data: P2PTransferRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create P2P transfer between customers using IBAN."""
    # Check for tax hold
    tax_hold = await check_tax_hold(current_user["id"], db)
    if tax_hold:
        tax_amount = tax_hold["tax_amount_cents"] / 100
        raise HTTPException(
            status_code=403,
            detail={
                "code": "TAX_HOLD",
                "message": "Your account is currently restricted due to outstanding tax obligations.",
                "tax_amount_due": tax_amount,
                "formatted_message": f"Account Restricted: Your account has been temporarily suspended due to outstanding tax obligations of €{tax_amount:,.2f}. To restore full access to your banking services, please settle the required amount. For assistance, contact our support team at support@projectatlas.eu"
            }
        )
    
    ledger_engine = LedgerEngine(db)
    transfer_service = TransferService(db, ledger_engine)
    
    result = await transfer_service.p2p_transfer(
        from_user_id=current_user["id"],
        to_iban=data.to_iban,
        amount=data.amount,
        reason=data.reason,
        recipient_name=data.recipient_name
    )
    
    return result


# ==================== BENEFICIARIES ====================

@app.post("/api/v1/beneficiaries")
async def add_beneficiary(
    data: CreateBeneficiary,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Add a beneficiary."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    beneficiary = await advanced_service.add_beneficiary(current_user["id"], data)
    return beneficiary.model_dump()


@app.get("/api/v1/beneficiaries")
async def get_beneficiaries(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's beneficiaries."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    beneficiaries = await advanced_service.get_beneficiaries(current_user["id"])
    return [b.model_dump() for b in beneficiaries]


@app.delete("/api/v1/beneficiaries/{beneficiary_id}")
async def delete_beneficiary(
    beneficiary_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a beneficiary."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    success = await advanced_service.delete_beneficiary(beneficiary_id, current_user["id"])
    return {"success": success}


# ==================== SCHEDULED PAYMENTS ====================

@app.post("/api/v1/scheduled-payments")
async def create_scheduled_payment(
    data: CreateScheduledPayment,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a scheduled recurring payment."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    payment = await advanced_service.create_scheduled_payment(current_user["id"], data)
    return payment.model_dump()


@app.get("/api/v1/scheduled-payments")
async def get_scheduled_payments(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's scheduled payments."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    payments = await advanced_service.get_scheduled_payments(current_user["id"])
    return [p.model_dump() for p in payments]


@app.delete("/api/v1/scheduled-payments/{payment_id}")
async def cancel_scheduled_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Cancel a scheduled payment."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    success = await advanced_service.cancel_scheduled_payment(payment_id, current_user["id"])
    return {"success": success}


# ==================== SPENDING INSIGHTS ====================

@app.get("/api/v1/insights/spending")
async def get_spending_insights(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get spending breakdown by category from real ledger data."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    breakdown = await advanced_service.get_spending_by_category(current_user["id"], days)
    return breakdown


@app.get("/api/v1/insights/monthly-spending")
async def get_monthly_spending(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get spending for the current calendar month from real ledger data."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    spending = await advanced_service.get_monthly_spending(current_user["id"])
    return spending


# ==================== BANKING WORKFLOWS - CARDS ====================

@app.post("/api/v1/card-requests")
async def create_card_request(
    data: CreateCardRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """User creates card request."""
    # Check for tax hold
    tax_hold = await check_tax_hold(current_user["id"], db)
    if tax_hold:
        tax_amount = tax_hold["tax_amount_cents"] / 100
        raise HTTPException(
            status_code=403,
            detail={
                "code": "TAX_HOLD",
                "message": "Your account is currently restricted due to outstanding tax obligations.",
                "tax_amount_due": tax_amount,
                "formatted_message": f"Account Restricted: Your account has been temporarily suspended due to outstanding tax obligations of €{tax_amount:,.2f}. Card services are unavailable until the required amount is settled. For assistance, contact our support team at support@projectatlas.eu"
            }
        )
    
    workflows = BankingWorkflowsService(db)
    request = await workflows.create_card_request(current_user["id"], data)
    return {"ok": True, "data": request.model_dump()}


@app.get("/api/v1/card-requests")
async def get_card_requests(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's card requests."""
    workflows = BankingWorkflowsService(db)
    requests = await workflows.get_user_card_requests(current_user["id"])
    return {"ok": True, "data": [r.model_dump() for r in requests]}


@app.get("/api/v1/cards")
async def get_cards(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's cards."""
    workflows = BankingWorkflowsService(db)
    cards = await workflows.get_user_cards(current_user["id"])
    return {"ok": True, "data": [c.model_dump() for c in cards]}


# ==================== BANKING WORKFLOWS - RECIPIENTS ====================

@app.post("/api/v1/recipients")
async def create_recipient(
    data: CreateRecipient,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create saved recipient (IBAN display only)."""
    workflows = BankingWorkflowsService(db)
    recipient = await workflows.create_recipient(current_user["id"], data)
    return {"ok": True, "data": recipient.model_dump()}


@app.get("/api/v1/recipients")
async def get_recipients(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's saved recipients."""
    workflows = BankingWorkflowsService(db)
    recipients = await workflows.get_user_recipients(current_user["id"])
    return {"ok": True, "data": [r.model_dump() for r in recipients]}


@app.delete("/api/v1/recipients/{recipient_id}")
async def delete_recipient(
    recipient_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete saved recipient."""
    workflows = BankingWorkflowsService(db)
    success = await workflows.delete_recipient(recipient_id, current_user["id"])
    return {"ok": success}


# ==================== BANKING WORKFLOWS - TRANSFERS ====================

@app.post("/api/v1/transfers")
async def create_transfer(
    data: CreateTransfer,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Submit transfer - instant success, no waiting."""
    # Check for tax hold
    tax_hold = await check_tax_hold(current_user["id"], db)
    if tax_hold:
        tax_amount = tax_hold["tax_amount_cents"] / 100
        raise HTTPException(
            status_code=403,
            detail={
                "code": "TAX_HOLD",
                "message": "Your account is currently restricted due to outstanding tax obligations.",
                "tax_amount_due": tax_amount,
                "formatted_message": f"Account Restricted: Your account has been temporarily suspended due to outstanding tax obligations of €{tax_amount:,.2f}. Transfer services are unavailable until the required amount is settled. For assistance, contact our support team at support@projectatlas.eu"
            }
        )
    
    workflows = BankingWorkflowsService(db)
    transfer = await workflows.create_transfer(current_user["id"], data)
    return {"ok": True, "data": transfer.model_dump(), "message": "Transfer successful"}


@app.get("/api/v1/transfers")
async def get_transfers(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    "Get user's transfers."
    workflows = BankingWorkflowsService(db)
    transfers = await workflows.get_user_transfers(current_user["id"])
    return {"ok": True, "data": [t.model_dump() for t in transfers]}



@app.get("/api/v1/transfers/{transfer_id}")
async def get_transfer_detail(
    transfer_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get transfer details."""
    workflows = BankingWorkflowsService(db)
    transfer = await workflows.get_transfer(transfer_id, current_user["id"])
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return {"ok": True, "data": transfer.model_dump()}


@app.get("/api/v1/admin/card-requests")
async def admin_get_card_requests(
    status: str = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Get card requests filtered by status."""
    workflows = BankingWorkflowsService(db)
    requests = await workflows.get_pending_card_requests(status)
    return {"ok": True, "data": [r.model_dump() for r in requests]}


@app.post("/api/v1/admin/card-requests/{request_id}/fulfill")
async def admin_fulfill_card_request(
    request_id: str,
    card_data: FulfillCardRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin fulfills card request."""
    workflows = BankingWorkflowsService(db)
    card = await workflows.fulfill_card_request(request_id, current_user["id"], card_data)
    return {"ok": True, "data": card.model_dump()}


@app.post("/api/v1/admin/card-requests/{request_id}/reject")
async def admin_reject_card_request(
    request_id: str,
    reason: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin rejects card request."""
    if not reason:
        raise HTTPException(status_code=400, detail="Reject reason is required")
    workflows = BankingWorkflowsService(db)
    await workflows.reject_card_request(request_id, current_user["id"], reason)
    return {"ok": True}


@app.get("/api/v1/admin/transfers")
async def admin_get_transfers(
    status: str = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Get transfers."""
    workflows = BankingWorkflowsService(db)
    transfers = await workflows.get_admin_transfers(status)
    return {"ok": True, "data": [t.model_dump() for t in transfers]}


@app.post("/api/v1/admin/transfers/{transfer_id}/approve")
async def admin_approve_transfer(
    transfer_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin approves transfer."""
    workflows = BankingWorkflowsService(db)
    await workflows.approve_transfer(transfer_id, current_user["id"])
    return {"ok": True, "message": "Transfer approved"}


class RejectTransferRequest(BaseModel):
    reason: str


@app.post("/api/v1/admin/transfers/{transfer_id}/reject")
async def admin_reject_transfer(
    transfer_id: str,
    data: RejectTransferRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin rejects transfer."""
    workflows = BankingWorkflowsService(db)
    await workflows.reject_transfer(transfer_id, current_user["id"], data.reason)
    return {"ok": True, "message": "Transfer rejected"}


class UpdateRejectReasonRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="New rejection reason")


@app.patch("/api/v1/admin/transfers/{transfer_id}/reject-reason")
async def admin_update_reject_reason(
    transfer_id: str,
    data: UpdateRejectReasonRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin updates the rejection reason for a rejected transfer."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find transfer
    transfer = await db.transfers.find_one({"_id": transfer_id})
    if not transfer:
        try:
            transfer = await db.transfers.find_one({"_id": ObjectId(transfer_id)})
        except InvalidId:
            pass
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    if transfer.get("status") != "REJECTED":
        raise HTTPException(status_code=400, detail="Can only update rejection reason for rejected transfers")
    
    # Update the rejection reason
    await db.transfers.update_one(
        {"_id": transfer["_id"]},
        {"$set": {
            "reject_reason": data.reason,
            "reject_reason_updated_at": datetime.now(timezone.utc),
            "reject_reason_updated_by": current_user["id"]
        }}
    )
    
    # Audit log
    await create_audit_log(
        db=db,
        action="TRANSFER_REJECT_REASON_UPDATED",
        entity_type="transfer",
        entity_id=str(transfer["_id"]),
        description=f"Rejection reason updated for transfer {transfer_id}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"new_reason": data.reason}
    )
    
    return {"ok": True, "message": "Rejection reason updated"}


@app.delete("/api/v1/admin/transfers/{transfer_id}")
async def admin_delete_transfer(
    transfer_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin permanently deletes a transfer (any status)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Only SUPER_ADMIN can delete transfers
    if current_user["role"] != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Only Super Admin can delete transfers")
    
    # Find transfer
    transfer = await db.transfers.find_one({"_id": transfer_id})
    if not transfer:
        try:
            transfer = await db.transfers.find_one({"_id": ObjectId(transfer_id)})
        except InvalidId:
            pass
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    transfer_status = transfer.get("status", "UNKNOWN")
    transfer_amount = transfer.get("amount", 0)
    beneficiary = transfer.get("beneficiary_name", "Unknown")
    
    # Delete the transfer
    result = await db.transfers.delete_one({"_id": transfer["_id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete transfer")
    
    # Audit log
    await create_audit_log(
        db=db,
        action="TRANSFER_PERMANENTLY_DELETED",
        entity_type="transfer",
        entity_id=str(transfer["_id"]),
        description=f"Transfer to {beneficiary} (€{transfer_amount/100:.2f}) permanently deleted",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "status": transfer_status,
            "amount": transfer_amount,
            "beneficiary": beneficiary
        }
    )
    
    logger.info(f"Transfer {transfer_id} permanently deleted by admin {current_user['email']}")
    
    return {"ok": True, "message": "Transfer permanently deleted"}


@app.get("/api/v1/admin/accounts-with-users")
async def get_all_accounts_with_users(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all bank accounts with their user information (efficient single query)."""
    from bson import ObjectId
    
    # Get all bank accounts
    accounts_cursor = db.bank_accounts.find({})
    accounts = []
    user_ids = set()
    
    async for acc in accounts_cursor:
        user_id = acc.get("user_id")
        if user_id:
            user_ids.add(user_id if isinstance(user_id, ObjectId) else ObjectId(user_id) if ObjectId.is_valid(str(user_id)) else None)
        accounts.append(acc)
    
    # Remove None values
    user_ids = {uid for uid in user_ids if uid is not None}
    
    # Fetch all users in one query
    users_map = {}
    if user_ids:
        users_cursor = db.users.find({"_id": {"$in": list(user_ids)}})
        async for user in users_cursor:
            users_map[str(user["_id"])] = user
    
    # Combine accounts with user info
    result = []
    for acc in accounts:
        user_id = acc.get("user_id")
        user_id_str = str(user_id) if user_id else None
        user = users_map.get(user_id_str, {})
        
        result.append({
            "id": str(acc["_id"]),
            "account_number": acc.get("account_number", ""),
            "iban": acc.get("iban"),
            "bic": acc.get("bic"),
            "balance": acc.get("balance_in_cents", 0),
            "currency": acc.get("currency", "EUR"),
            "userId": user_id_str,
            "userName": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
            "userEmail": user.get("email", "Unknown")
        })
    
    return result


@app.post("/api/v1/admin/accounts/{account_id}/topup")
async def admin_topup_account(
    account_id: str,
    data: AdminCreditRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin tops up account with professional transaction display."""
    workflows = BankingWorkflowsService(db)
    ledger_engine = LedgerEngine(db)
    
    account = await db.bank_accounts.find_one({"_id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Build professional metadata for customer display
    metadata = {
        "display_type": data.display_type.value if hasattr(data.display_type, 'value') else data.display_type,
        "sender_name": data.sender_name,
        "sender_iban": data.sender_iban,
        "sender_bic": data.sender_bic,
        "reference": data.reference,
        "description": data.description,
        "admin_note": data.admin_note,
        "admin_id": current_user["id"]
    }
    
    # Clean None values
    metadata = {k: v for k, v in metadata.items() if v is not None}
    
    await ledger_engine.top_up(
        user_account_id=account["ledger_account_id"],
        amount=data.amount,
        external_id=f"admin_topup_{uuid.uuid4()}",
        reason=data.description or data.display_type.value if hasattr(data.display_type, 'value') else str(data.display_type),
        performed_by=current_user["id"],
        metadata=metadata
    )
    
    await workflows.topup_account(account_id, current_user["id"], data.amount, data.description or "Admin credit")
    new_balance = await ledger_engine.get_balance(account["ledger_account_id"])
    
    return {"ok": True, "message": "Credit successful", "new_balance": new_balance}


@app.post("/api/v1/admin/accounts/{account_id}/withdraw")
async def admin_withdraw_account(
    account_id: str,
    data: AdminDebitRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin withdraws from account with professional transaction display."""
    workflows = BankingWorkflowsService(db)
    ledger_engine = LedgerEngine(db)
    
    account = await db.bank_accounts.find_one({"_id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Build professional metadata for customer display
    metadata = {
        "display_type": data.display_type,
        "recipient_name": data.recipient_name,
        "recipient_iban": data.recipient_iban,
        "reference": data.reference,
        "description": data.description,
        "admin_note": data.admin_note,
        "admin_id": current_user["id"]
    }
    
    # Clean None values
    metadata = {k: v for k, v in metadata.items() if v is not None}
    
    await ledger_engine.withdraw(
        user_account_id=account["ledger_account_id"],
        amount=data.amount,
        external_id=f"admin_withdraw_{uuid.uuid4()}",
        reason=data.description or data.display_type,
        performed_by=current_user["id"],
        metadata=metadata
    )
    
    await workflows.withdraw_account(account_id, current_user["id"], data.amount, data.description or "Admin debit")
    new_balance = await ledger_engine.get_balance(account["ledger_account_id"])
    
    return {"ok": True, "message": "Debit successful", "new_balance": new_balance}


# Health check endpoint at root path for deployment health checks
@app.get("/health")
async def root_health_check():
    """Root health check endpoint for Kubernetes/deployment."""
    return {"status": "healthy", "app": settings.APP_NAME}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": "ecommbx"}


@app.get("/api/db-health")
async def db_health_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Database health check endpoint - shows DB status and user count."""
    try:
        # Ping database
        await db.command("ping")
        
        # Count users
        user_count = await db.users.count_documents({})
        
        # Check if admin exists
        admin = await db.users.find_one({"role": "SUPER_ADMIN"})
        
        return {
            "status": "healthy",
            "database_name": db.name,
            "user_count": user_count,
            "admin_exists": admin is not None,
            "admin_email": admin.get("email") if admin else None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/api/debug/db-test")
async def debug_db_test(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Debug endpoint to test database connectivity and write permissions."""
    import os
    result = {
        "database_name": db.name,
        "mongo_url_prefix": os.environ.get('MONGO_URL', 'NOT SET')[:30] + "...",
        "ping": None,
        "write_test": None,
        "read_test": None,
        "delete_test": None,
        "error": None
    }
    
    try:
        # Test ping
        ping_result = await db.command("ping")
        result["ping"] = "OK" if ping_result.get("ok") == 1.0 else "FAILED"
        
        # Test write
        test_id = f"debug_test_{uuid.uuid4()}"
        try:
            await db.debug_tests.insert_one({"_id": test_id, "test": True, "timestamp": datetime.now(timezone.utc)})
            result["write_test"] = "OK"
        except Exception as write_err:
            result["write_test"] = f"FAILED: {str(write_err)}"
            result["error"] = str(write_err)
            return result
        
        # Test read
        try:
            doc = await db.debug_tests.find_one({"_id": test_id})
            result["read_test"] = "OK" if doc else "FAILED: Document not found"
        except Exception as read_err:
            result["read_test"] = f"FAILED: {str(read_err)}"
        
        # Test delete (cleanup)
        try:
            await db.debug_tests.delete_one({"_id": test_id})
            result["delete_test"] = "OK"
        except Exception as del_err:
            result["delete_test"] = f"FAILED: {str(del_err)}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result




@app.get("/api/debug/try-databases")
async def try_multiple_databases():
    """Try writing to different database names to find one with permissions."""
    import os
    from motor.motor_asyncio import AsyncIOMotorClient
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    
    # List of database names to try - including variations
    db_names_to_try = [
        "mongo-perf-fix",
        "mongo-perf-fix-atlas_bankii",
        "mongo-perf-fix-atlas_banking", 
        "test",
        "emergent",
        "ecommbx",
        "atlas_bankii",
        "atlas_banking",
        "default",
        "app",
        "admin",
    ]
    
    results = {}
    
    try:
        client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        
        # Test ping first
        try:
            await client.admin.command('ping')
            results["_connection"] = "OK"
        except Exception as e:
            results["_connection"] = f"FAILED: {str(e)[:100]}"
            return {"mongo_url_prefix": mongo_url[:50], "results": results}
        
        for db_name in db_names_to_try:
            try:
                db = client[db_name]
                test_id = f"test_{uuid.uuid4()}"
                await db.permission_test.insert_one({"_id": test_id, "test": True})
                await db.permission_test.delete_one({"_id": test_id})
                results[db_name] = "✅ WRITE OK"
            except Exception as e:
                error_msg = str(e)
                if "not authorized" in error_msg.lower():
                    results[db_name] = "❌ No write permission"
                else:
                    results[db_name] = f"❌ {error_msg[:60]}"
        
        client.close()
    except Exception as e:
        results["_error"] = str(e)[:200]
    
    return {"mongo_url_prefix": mongo_url[:50] + "...", "results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)


@app.get("/api/debug/test-transfer/{user_email}")
async def debug_test_transfer(
    user_email: str,
    to_iban: str = "DE89370400440532013000",
    amount: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Debug endpoint to test transfer logic."""
    from bson import ObjectId
    
    result = {"steps": []}
    
    # Step 1: Find user
    user = await db.users.find_one({"email": user_email})
    if not user:
        return {"error": "User not found", "steps": result["steps"]}
    result["steps"].append(f"1. User found: {user['_id']} (type: {type(user['_id']).__name__})")
    
    user_id = user["_id"]
    
    # Step 2: Find bank account
    acc = await db.bank_accounts.find_one({"user_id": user_id})
    if not acc:
        # Try as string
        acc = await db.bank_accounts.find_one({"user_id": str(user_id)})
    if not acc:
        return {"error": "Bank account not found", "steps": result["steps"]}
    result["steps"].append(f"2. Bank account found: {acc['iban']}, ledger: {acc['ledger_account_id']}")
    
    # Step 3: Check balance
    ledger_id = acc["ledger_account_id"]
    entries = await db.ledger_entries.find({"account_id": ledger_id}).to_list(1000)
    total_credit = sum(e["amount"] for e in entries if e.get("direction") == "CREDIT")
    total_debit = sum(e["amount"] for e in entries if e.get("direction") == "DEBIT")
    balance = total_credit - total_debit
    result["steps"].append(f"3. Balance: {balance} cents (€{balance/100:.2f})")
    
    if balance < amount:
        return {"error": f"Insufficient funds: {balance} < {amount}", "steps": result["steps"]}
    result["steps"].append(f"4. Balance sufficient for {amount} cents")
    
    # Step 4: Check recipient IBAN
    normalized_iban = to_iban.replace(" ", "").upper()
    to_acc = await db.bank_accounts.find_one({"iban": normalized_iban})
    if to_acc:
        result["steps"].append(f"5. Recipient IBAN found - INTERNAL transfer")
    else:
        result["steps"].append(f"5. Recipient IBAN not found - EXTERNAL transfer")
    
    result["ready"] = True
    result["transfer_type"] = "INTERNAL" if to_acc else "EXTERNAL"
    result["balance"] = balance
    result["amount"] = amount
    
    return result
