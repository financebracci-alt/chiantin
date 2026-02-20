"""Main FastAPI application for Project Atlas banking platform."""

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, Response, Form
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
from schemas.tickets import TicketCreate, MessageCreate, TicketStatus, Ticket
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


# Transfer Authorization - Verify Password Schema
class VerifyPasswordRequest(BaseModel):
    password: str


@app.post("/api/v1/auth/verify-password")
async def verify_user_password(
    data: VerifyPasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify user's password for transfer authorization.
    Used to confirm identity before processing sensitive transactions.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Get user from database - handle both ObjectId and string IDs
    user_id = current_user["id"]
    user_doc = None
    
    try:
        # First try as ObjectId
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    except (InvalidId, TypeError):
        # If not a valid ObjectId, try as string
        user_doc = await db.users.find_one({"_id": user_id})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify password
    if not verify_password(data.password, user_doc["password_hash"]):
        logger.warning(f"Transfer authorization failed - incorrect password for user {current_user['email']}")
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    logger.info(f"Transfer authorization successful for user {current_user['email']}")
    return {"success": True, "message": "Password verified successfully"}


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
    download: bool = False,
    storage: CloudinaryStorage = Depends(get_storage),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """View or download uploaded KYC document. Use ?download=true to download instead of view."""
    try:
        from fastapi.responses import RedirectResponse, Response
        from urllib.parse import unquote
        import httpx
        
        # Decode URL-encoded path
        document_key = unquote(document_key)
        logger.info(f"{'Downloading' if download else 'Viewing'} document with key: {document_key}")
        
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
                        if download:
                            # Fetch the document from Cloudinary and serve with download headers
                            logger.info(f"Fetching document from Cloudinary for download: {cloudinary_url}")
                            async with httpx.AsyncClient() as client:
                                response = await client.get(cloudinary_url, timeout=30.0)
                                
                                if response.status_code != 200:
                                    raise HTTPException(status_code=502, detail="Failed to fetch document from storage")
                                
                                content = response.content
                                content_type = response.headers.get("content-type", "application/octet-stream")
                            
                            # Get filename
                            file_name = doc.get("file_name", f"document_{document_key}")
                            
                            # Return with download headers
                            return Response(
                                content=content,
                                media_type=content_type,
                                headers={
                                    "Content-Disposition": f'attachment; filename="{file_name}"',
                                    "Access-Control-Allow-Origin": "*",
                                    "Cache-Control": "no-cache"
                                }
                            )
                        else:
                            # Just redirect to Cloudinary URL for viewing
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
    logger.info(f"KYC submission started for user {current_user['id']} ({current_user['email']})")
    try:
        kyc_service = KYCService(db, storage)
        app = await kyc_service.submit_application(current_user["id"], data)
        logger.info(f"KYC submission successful for user {current_user['id']} - Status: {app.status}")
        return app.model_dump()
    except Exception as e:
        logger.error(f"KYC submission failed for user {current_user['id']}: {str(e)}")
        raise


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


class ManualKYCQueueRequest(BaseModel):
    """Request model for manually queueing a user's KYC for review."""
    user_email: str
    reason: Optional[str] = None


@app.post("/api/v1/admin/kyc/queue-user")
async def admin_queue_user_kyc(
    data: ManualKYCQueueRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Admin endpoint to manually queue a user's KYC application for review.
    This is useful when a user's KYC submission failed silently or needs to be re-queued.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    logger.info(f"Admin {current_user['email']} manually queueing KYC for user: {data.user_email}")
    
    # Find the user by email
    user_doc = await db.users.find_one({"email": data.user_email})
    if not user_doc:
        raise HTTPException(status_code=404, detail=f"User with email {data.user_email} not found")
    
    user_id = str(user_doc["_id"])
    
    # Find or create KYC application
    kyc_app = await db.kyc_applications.find_one({"user_id": user_id})
    
    if not kyc_app:
        # Create a minimal KYC application with SUBMITTED status
        from datetime import datetime
        kyc_app = {
            "_id": str(ObjectId()),
            "user_id": user_id,
            "full_name": f"{user_doc.get('first_name', '')} {user_doc.get('last_name', '')}".strip() or "Unknown",
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "documents": [],
            "terms_accepted": True,
            "privacy_accepted": True,
            "terms_accepted_at": datetime.utcnow(),
            "privacy_accepted_at": datetime.utcnow()
        }
        await db.kyc_applications.insert_one(kyc_app)
        logger.info(f"Created new KYC application for user {user_id} with SUBMITTED status")
    else:
        # Update existing KYC to SUBMITTED if it's in DRAFT state
        from datetime import datetime
        old_status = kyc_app.get("status")
        
        # Build the user's full name from registration data
        user_full_name = f"{user_doc.get('first_name', '')} {user_doc.get('last_name', '')}".strip() or None
        
        if old_status in ["DRAFT", "NEEDS_MORE_INFO", "REJECTED"]:
            update_data = {
                "status": "SUBMITTED",
                "submitted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                # Clear any rejection data
                "rejection_reason": None,
                "reviewed_at": None,
                "reviewed_by": None
            }
            
            # If full_name is missing, populate it from user registration
            if not kyc_app.get("full_name") and user_full_name:
                update_data["full_name"] = user_full_name
            
            await db.kyc_applications.update_one(
                {"_id": kyc_app["_id"]},
                {"$set": update_data}
            )
            logger.info(f"Updated KYC application for user {user_id} from {old_status} to SUBMITTED")
        elif old_status == "SUBMITTED":
            logger.info(f"KYC application for user {user_id} is already SUBMITTED")
            return {
                "success": True,
                "message": "KYC application is already in SUBMITTED status",
                "user_id": user_id,
                "kyc_status": "SUBMITTED"
            }
        elif old_status == "APPROVED":
            raise HTTPException(status_code=400, detail="KYC is already APPROVED - cannot re-queue")
        else:
            raise HTTPException(status_code=400, detail=f"Cannot queue KYC with status: {old_status}")
    
    # Audit log
    await create_audit_log(
        db=db,
        action="KYC_MANUAL_QUEUE",
        entity_type="kyc",
        entity_id=kyc_app.get("_id") or kyc_app["_id"],
        description=f"Admin manually queued KYC for user {data.user_email}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"user_email": data.user_email, "reason": data.reason, "user_id": user_id}
    )
    
    return {
        "success": True,
        "message": f"KYC application for {data.user_email} has been queued for review",
        "user_id": user_id,
        "kyc_status": "SUBMITTED"
    }


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



@app.delete("/api/v1/admin/kyc/{application_id}")
async def delete_kyc_application(
    application_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    HARD DELETE a KYC application (before approval).
    Only allowed for pending statuses: SUBMITTED, UNDER_REVIEW, NEEDS_MORE_INFO, DRAFT, REJECTED.
    User account remains - they can resubmit KYC.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find the KYC application
    kyc_app = await db.kyc_applications.find_one({"_id": application_id})
    if not kyc_app:
        try:
            kyc_app = await db.kyc_applications.find_one({"_id": ObjectId(application_id)})
        except InvalidId:
            pass
    
    if not kyc_app:
        raise HTTPException(status_code=404, detail="KYC application not found")
    
    # Check status - only allow deletion of pending/unapproved applications
    status = kyc_app.get("status")
    if status == "APPROVED":
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete approved KYC applications. This would affect verified client accounts."
        )
    
    user_id = str(kyc_app.get("user_id"))
    
    # Get user info for logging
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    user_email = user_doc.get("email", "unknown") if user_doc else "unknown"
    
    # Perform hard delete
    result = await db.kyc_applications.delete_one({"_id": kyc_app["_id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete KYC application")
    
    # Audit log
    logger.warning(
        f"KYC DELETION: Application {application_id} for user {user_email} "
        f"(status: {status}) deleted by admin {current_user['email']} "
        f"(ID: {current_user['id']})"
    )
    
    return {
        "success": True,
        "message": f"KYC application for {user_email} has been deleted",
        "application_id": application_id,
        "status_was": status
    }


@app.patch("/api/v1/admin/kyc/{application_id}")
async def edit_kyc_application(
    application_id: str,
    updates: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    EDIT a KYC application (before approval).
    Allows updating personal information and document references.
    Creates audit trail of all changes.
    Only allowed for pending statuses.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Find the KYC application
    kyc_app = await db.kyc_applications.find_one({"_id": application_id})
    if not kyc_app:
        try:
            kyc_app = await db.kyc_applications.find_one({"_id": ObjectId(application_id)})
        except InvalidId:
            pass
    
    if not kyc_app:
        raise HTTPException(status_code=404, detail="KYC application not found")
    
    # Check status - only allow editing of pending applications
    status = kyc_app.get("status")
    if status == "APPROVED":
        raise HTTPException(
            status_code=400, 
            detail="Cannot edit approved KYC applications. Contact compliance team for approved application changes."
        )
    
    # Track what changed for audit log
    changes_made = {}
    allowed_fields = [
        "full_name", "date_of_birth", "nationality", "country_of_residence",
        "address", "city", "postal_code", "tax_residency", "tax_id",
        "passport_document", "proof_of_address_document", "selfie_document"
    ]
    
    # Filter to only allowed fields and track changes
    update_data = {}
    for field, new_value in updates.items():
        if field in allowed_fields:
            old_value = kyc_app.get(field)
            if old_value != new_value:
                update_data[field] = new_value
                changes_made[field] = {"old": old_value, "new": new_value}
    
    if not update_data:
        return {
            "success": True,
            "message": "No changes detected",
            "changes": {}
        }
    
    # Add audit metadata
    update_data["edited_at"] = datetime.now(timezone.utc)
    update_data["edited_by"] = current_user["id"]
    
    # Perform update
    result = await db.kyc_applications.update_one(
        {"_id": kyc_app["_id"]},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update KYC application")
    
    # Get user email for logging
    user_doc = await db.users.find_one({"_id": kyc_app.get("user_id")})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(str(kyc_app.get("user_id")))})
        except InvalidId:
            pass
    
    user_email = user_doc.get("email", "unknown") if user_doc else "unknown"
    
    # Audit log
    logger.warning(
        f"KYC EDIT: Application {application_id} for user {user_email} "
        f"edited by admin {current_user['email']}. Changes: {list(changes_made.keys())}"
    )
    
    return {
        "success": True,
        "message": f"KYC application for {user_email} has been updated",
        "application_id": application_id,
        "changes": changes_made
    }


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
    db: AsyncIOMotorDatabase = Depends(get_database),
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    """Get users (admin) with pagination, tax hold status and notes.
    
    Supports:
    - search: Filter by name or email (searches ALL users in DB, not just current page)
    - page: Page number (1-indexed)
    - limit: Users per page (20, 50, or 100)
    
    When search is provided, pagination is ignored and ALL matching users are returned.
    This ensures admins can find any user regardless of which page they're on.
    """
    # Validate limit
    if limit not in [20, 50, 100]:
        limit = 50
    
    # Build query - if search provided, filter by name or email
    query = {}
    if search and search.strip():
        search_term = search.strip()
        query = {
            "$or": [
                {"first_name": {"$regex": search_term, "$options": "i"}},
                {"last_name": {"$regex": search_term, "$options": "i"}},
                {"email": {"$regex": search_term, "$options": "i"}}
            ]
        }
    
    # Get total count for pagination info
    total_count = await db.users.count_documents(query)
    
    # Get all active tax holds for quick lookup
    tax_holds_cursor = db.tax_holds.find({"is_active": True})
    tax_hold_user_ids = set()
    async for hold in tax_holds_cursor:
        tax_hold_user_ids.add(hold["user_id"])
    
    # When searching, return ALL matching users (no pagination)
    # This ensures the admin can find any user regardless of page
    if search and search.strip():
        cursor = db.users.find(query).sort("created_at", -1)
    else:
        # Apply pagination only when not searching
        skip = (page - 1) * limit
        cursor = db.users.find(query).sort("created_at", -1).skip(skip).limit(limit)
    
    users = []
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
    
    # Calculate pagination info
    total_pages = (total_count + limit - 1) // limit if not (search and search.strip()) else 1
    
    return {
        "users": users,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_users": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages if not (search and search.strip()) else False,
            "has_prev": page > 1 if not (search and search.strip()) else False
        }
    }


# Admin: Search users for ticket creation (must be before {user_id} route)
@app.get("/api/v1/admin/users/search-for-ticket")
async def search_users_for_ticket(
    q: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Search users by email/name/ID for admin ticket creation."""
    if not q or len(q) < 2:
        return []
    
    from bson import ObjectId
    from bson.errors import InvalidId
    
    search_query = q.strip().lower()
    
    # Build search criteria - case insensitive partial match
    search_criteria = {
        "$or": [
            {"email": {"$regex": search_query, "$options": "i"}},
            {"first_name": {"$regex": search_query, "$options": "i"}},
            {"last_name": {"$regex": search_query, "$options": "i"}}
        ]
    }
    
    # Also try to match by ID if it looks like one
    try:
        if len(search_query) == 24:
            search_criteria["$or"].append({"_id": ObjectId(search_query)})
    except (InvalidId, TypeError):
        pass
    
    # Search users
    cursor = db.users.find(
        search_criteria,
        {"_id": 1, "email": 1, "first_name": 1, "last_name": 1, "status": 1}
    ).limit(10)
    
    results = []
    async for user in cursor:
        results.append({
            "id": str(user["_id"]),
            "email": user.get("email", ""),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "status": user.get("status", "UNKNOWN")
        })
    
    return results


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
            "email_verified": user_doc.get("email_verified", False),
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


@app.post("/api/v1/admin/users/{user_id}/verify-email")
async def admin_verify_user_email(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin manually verifies a user's email (for users having trouble with verification emails)."""
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
    
    # Check if already verified
    if user_doc.get("email_verified", False):
        return {"success": True, "message": "Email already verified", "already_verified": True}
    
    # Update email_verified to True
    result = await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"email_verified": True, "updated_at": datetime.now(timezone.utc)}}
    )
    
    # Clean up any pending verification tokens for this user
    await db.email_verifications.delete_many({"user_id": str(user_doc["_id"])})
    
    # Audit: Admin email verification
    await create_audit_log(
        db=db,
        action="ADMIN_EMAIL_VERIFIED",
        entity_type="user",
        entity_id=str(user_doc["_id"]),
        description=f"Admin manually verified email for {user_doc['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"user_email": user_doc["email"], "reason": "manual_verification"}
    )
    
    logger.info(f"Admin {current_user['email']} manually verified email for user {user_doc['email']}")
    
    return {"success": True, "message": f"Email verified for {user_doc['email']}", "modified_count": result.modified_count}


# ============== ADMIN PASSWORD CHANGE ==============

class AdminChangePasswordRequest(BaseModel):
    new_password: str


@app.post("/api/v1/admin/users/{user_id}/change-password")
async def admin_change_user_password(
    user_id: str,
    data: AdminChangePasswordRequest,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Admin changes a customer's password.
    - Stores password as plaintext (as per existing system)
    - Creates audit log entry (PASSWORD_CHANGED)
    - Does NOT store the new password in audit logs
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Validate new password
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Find user (handle both string and ObjectId)
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            pass
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from changing their own password via this endpoint
    actual_user_id = str(user_doc["_id"])
    if actual_user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot change your own password via admin panel. Use the account settings.")
    
    # Update the password (plaintext storage as per existing system)
    # Also update the password_hash for authentication
    new_hash = hash_password(data.new_password)
    
    result = await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {
            "password_plain": data.new_password,
            "password_hash": new_hash,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Get client info for audit
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Audit: Password changed by admin (DO NOT log the actual password)
    await create_audit_log(
        db=db,
        action="PASSWORD_CHANGED",
        entity_type="user",
        entity_id=actual_user_id,
        description=f"Password changed for {user_doc['email']} by admin",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "target_user_email": user_doc["email"],
            "source": "admin_panel",
            "ip_address": client_ip,
            "user_agent": user_agent
        }
    )
    
    logger.info(f"Admin {current_user['email']} changed password for user {user_doc['email']}")
    
    return {"success": True, "message": "Password updated successfully"}


# ============== USER AUTH HISTORY FOR ADMIN ==============

@app.get("/api/v1/admin/users/{user_id}/auth-history")
async def get_user_auth_history(
    user_id: str,
    limit: int = 50,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get authentication history for a specific user.
    Returns login success, failed attempts, and logout events.
    """
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
    
    actual_user_id = str(user_doc["_id"])
    user_email = user_doc["email"]
    
    # Query auth events for this user
    # Look for both entity_id match and email match (for failed logins before auth)
    auth_actions = [
        "USER_LOGIN_SUCCESS", "USER_LOGIN_FAILED", "USER_LOGOUT",
        "LOGIN_SUCCESS", "LOGIN_FAILED", "LOGIN_BLOCKED", "MFA_FAILED",
        "PASSWORD_CHANGED", "EMAIL_VERIFIED"
    ]
    
    query = {
        "entity_type": "auth",
        "$or": [
            {"entity_id": actual_user_id},
            {"entity_id": user_email},
            {"performed_by": actual_user_id},
            {"performed_by_email": user_email}
        ],
        "action": {"$in": auth_actions}
    }
    
    cursor = db.audit_logs.find(query).sort("created_at", -1).limit(limit)
    
    events = []
    async for doc in cursor:
        events.append({
            "id": str(doc["_id"]),
            "action": doc["action"],
            "description": doc.get("description", ""),
            "ip_address": doc.get("metadata", {}).get("ip_address", "N/A"),
            "user_agent": doc.get("metadata", {}).get("user_agent", "N/A"),
            "source": doc.get("metadata", {}).get("source", "web"),
            "actor_email": doc.get("performed_by_email", ""),
            "actor_role": doc.get("performed_by_role", ""),
            "created_at": doc["created_at"].isoformat(),
            "metadata": doc.get("metadata", {})
        })
    
    return {
        "user_id": actual_user_id,
        "user_email": user_email,
        "events": events,
        "total": len(events)
    }


@app.delete("/api/v1/admin/users/{user_id}/permanent")
async def permanent_delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Permanently delete a user and all associated data.
    This is a destructive operation that cannot be undone.
    Only SUPER_ADMIN can perform this action.
    """
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
            "deleted": True,
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


@app.post("/api/v1/admin/users/{user_id}/demote")
async def demote_admin_to_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Demote an admin user to a regular USER role.
    Only SUPER_ADMIN can demote other admins.
    Cannot demote yourself.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Only SUPER_ADMIN can demote admins
    if current_user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403, 
            detail="Only SUPER_ADMIN can demote other administrators"
        )
    
    # Try to find user by string ID first, then ObjectId
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
    current_role = user_doc.get("role", "USER")
    
    # Prevent demoting yourself
    if actual_user_id == current_user["id"]:
        raise HTTPException(
            status_code=400, 
            detail="You cannot demote yourself. Another SUPER_ADMIN must do this."
        )
    
    # Check if user is actually an admin
    if current_role not in ["SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(
            status_code=400, 
            detail=f"User {user_email} is already a regular user (role: {current_role})"
        )
    
    # Perform the demotion
    result = await db.users.update_one(
        {"_id": user_doc["_id"]},
        {
            "$set": {
                "role": "USER",
                "demoted_at": datetime.now(timezone.utc),
                "demoted_by": current_user["id"]
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to demote user")
    
    # Log the demotion for audit trail
    logger.warning(
        f"ROLE CHANGE: User {user_email} (ID: {actual_user_id}) "
        f"demoted from {current_role} to USER by admin {current_user['email']} "
        f"(ID: {current_user['id']})"
    )
    
    return {
        "success": True,
        "message": f"User {user_email} has been demoted from {current_role} to USER",
        "user_id": actual_user_id,
        "old_role": current_role,
        "new_role": "USER"
    }


# ==================== ADMIN PROMOTE/DEMOTE ====================


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
    
    # Create notification for user in their preferred language
    user_language = user_doc.get('language', 'en')
    notification_service = NotificationService(db)
    
    if user_language == 'it':
        title = "Avviso di Restrizione Account"
        message = f"Il tuo account è stato limitato a causa di obblighi fiscali in sospeso. Importo dovuto: €{data.tax_amount:.2f}. Contatta il supporto per assistenza."
    else:  # Default to English
        title = "Account Restriction Notice"
        message = f"Your account has been restricted due to outstanding tax obligations. Amount due: €{data.tax_amount:.2f}. Please contact support for assistance."
    
    await notification_service.create_notification(
        user_id=actual_user_id,
        title=title,
        message=message,
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
    
    # Create notification for user in their preferred language
    user_language = user_doc.get('language', 'en')
    notification_service = NotificationService(db)
    
    if user_language == 'it':
        title = "Restrizioni Account Rimosse"
        message = "Le restrizioni del tuo account sono state rimosse. Ora puoi eseguire tutte le operazioni bancarie."
    else:  # Default to English
        title = "Account Restriction Lifted"
        message = "Your account restrictions have been removed. You can now perform all banking operations."
    
    await notification_service.create_notification(
        user_id=actual_user_id,
        title=title,
        message=message,
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


@app.delete("/api/v1/admin/users/{user_id}/notifications")
async def admin_clear_user_notifications(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Clear all notifications for a specific user (admin only).
    This silently removes all notifications without the user knowing.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    # Resolve user ID
    actual_user_id = user_id
    try:
        if ObjectId.is_valid(user_id):
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                actual_user_id = str(user_doc["_id"])
    except (InvalidId, TypeError):
        pass
    
    if not actual_user_id:
        user_doc = await db.users.find_one({"_id": user_id})
        if user_doc:
            actual_user_id = str(user_doc["_id"])
    
    # Verify user exists
    user_doc = await db.users.find_one({"_id": ObjectId(actual_user_id)}) if ObjectId.is_valid(actual_user_id) else await db.users.find_one({"_id": actual_user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete all notifications for this user
    result = await db.notifications.delete_many({"user_id": actual_user_id})
    
    logger.info(f"Admin {current_user['email']} cleared {result.deleted_count} notifications for user {user_doc.get('email')}")
    
    return {
        "success": True,
        "message": f"Cleared {result.deleted_count} notifications",
        "deleted_count": result.deleted_count
    }


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
    """Get current user's tickets with unread counts."""
    ticket_service = TicketService(db)
    tickets = await ticket_service.get_user_tickets(current_user["id"])
    # get_user_tickets now returns a list of dicts with unread_count
    return tickets


# Client: Mark ticket as read (resets unread counter for this user)
@app.post("/api/v1/tickets/{ticket_id}/mark-read")
async def user_mark_ticket_read(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark a ticket as read by the user (resets unread message count)."""
    from datetime import datetime, timezone
    
    # Verify ticket belongs to this user
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket_doc["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {"user_last_read_at": datetime.now(timezone.utc)}}
    )
    
    return {"success": True, "ticket_id": ticket_id}


@app.post("/api/v1/tickets/{ticket_id}/messages")
async def add_ticket_message(
    ticket_id: str,
    data: MessageCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
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
    
    ticket_service = TicketService(db, storage)
    ticket = await ticket_service.add_message(
        ticket_id=ticket_id,
        sender_id=current_user["id"],
        sender_name=sender_name,
        is_staff=is_staff,
        data=data
    )
    
    # Create or update grouped notification for the user when staff replies
    if is_staff and ticket_doc["user_id"] != current_user["id"]:
        notification_service = NotificationService(db)
        await notification_service.create_or_update_support_reply_notification(
            user_id=ticket_doc["user_id"],
            ticket_id=ticket_id,
            ticket_subject=ticket_doc.get('subject', 'Support Ticket'),
            action_url="/support"
        )
    
    return ticket.model_dump()


@app.post("/api/v1/tickets/{ticket_id}/upload")
async def upload_ticket_attachment(
    ticket_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Upload file attachments for a ticket message."""
    from services.ticket_service import MAX_FILES_PER_MESSAGE
    
    # Verify ticket access
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket_doc["user_id"] != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate number of files
    if len(files) > MAX_FILES_PER_MESSAGE:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {MAX_FILES_PER_MESSAGE} files allowed per upload"
        )
    
    ticket_service = TicketService(db, storage)
    
    uploaded_attachments = []
    for file in files:
        attachment = await ticket_service.upload_attachment(
            ticket_id=ticket_id,
            user_id=current_user["id"],
            file=file
        )
        uploaded_attachments.append(attachment.model_dump())
    
    return {"attachments": uploaded_attachments}


@app.post("/api/v1/tickets/{ticket_id}/messages/with-attachments")
async def add_ticket_message_with_attachments(
    ticket_id: str,
    content: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Add a message with optional file attachments to a ticket."""
    from services.ticket_service import MAX_FILES_PER_MESSAGE
    from schemas.tickets import MessageAttachment
    
    # Verify ticket access
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket_doc["user_id"] != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate number of files
    if len(files) > MAX_FILES_PER_MESSAGE:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {MAX_FILES_PER_MESSAGE} files allowed per message"
        )
    
    auth_service = AuthService(db)
    user = await auth_service.get_user(current_user["id"])
    is_staff = current_user["role"] in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]
    
    if user:
        sender_name = f"{user.first_name} {user.last_name}"
    else:
        sender_name = current_user.get("email", "Customer")
    
    ticket_service = TicketService(db, storage)
    
    # Upload attachments if any
    attachments = []
    for file in files:
        if file.filename:  # Skip empty file inputs
            attachment = await ticket_service.upload_attachment(
                ticket_id=ticket_id,
                user_id=current_user["id"],
                file=file
            )
            attachments.append(attachment)
    
    # Add message with attachments
    ticket = await ticket_service.add_message(
        ticket_id=ticket_id,
        sender_id=current_user["id"],
        sender_name=sender_name,
        is_staff=is_staff,
        data=MessageCreate(content=content),
        attachments=attachments
    )
    
    # Create or update grouped notification for the user when staff replies
    if is_staff and ticket_doc["user_id"] != current_user["id"]:
        notification_service = NotificationService(db)
        await notification_service.create_or_update_support_reply_notification(
            user_id=ticket_doc["user_id"],
            ticket_id=ticket_id,
            ticket_subject=ticket_doc.get('subject', 'Support Ticket'),
            action_url="/support"
        )
    
    return ticket.model_dump()


@app.get("/api/v1/admin/tickets")
async def get_all_tickets(
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all tickets (admin) with user information and unread counts.
    
    PERFORMANCE OPTIMIZED: Returns list view data only.
    Use GET /api/v1/admin/tickets/{ticket_id} for full ticket details.
    """
    ticket_service = TicketService(db)
    tickets = await ticket_service.get_all_tickets(status_filter=status, search_query=search)
    return tickets


@app.get("/api/v1/admin/tickets/{ticket_id}")
async def get_single_ticket_admin(
    ticket_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get a single ticket with full messages (admin)."""
    from bson import ObjectId
    
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = Ticket(**serialize_doc(ticket_doc))
    ticket_dict = ticket.model_dump()
    
    # Add user info
    user_id = ticket_doc.get("user_id")
    if user_id:
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                ticket_dict["user_email"] = user.get("email", "")
                ticket_dict["user_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        except:
            pass
    
    return ticket_dict


@app.get("/api/v1/tickets/{ticket_id}")
async def get_single_ticket_user(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get a single ticket with full messages (user)."""
    ticket_doc = await db.tickets.find_one({
        "_id": ticket_id,
        "user_id": current_user["id"]
    })
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = Ticket(**serialize_doc(ticket_doc))
    return ticket.model_dump()


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


@app.delete("/api/v1/admin/tickets/{ticket_id}/messages/{message_index}")
async def delete_ticket_message(
    ticket_id: str,
    message_index: int,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a specific message from a ticket (admin only)."""
    from datetime import datetime, timezone
    
    # Find the ticket
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    messages = ticket_doc.get("messages", [])
    if message_index < 0 or message_index >= len(messages):
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Store the message content for audit log
    deleted_message = messages[message_index]
    deleted_content = deleted_message.get("content", "")
    deleted_sender = deleted_message.get("sender_name", "Unknown")
    
    # Remove the message from the array
    messages.pop(message_index)
    
    # Update the ticket with the modified messages array
    await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {
            "messages": messages,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    # Audit log
    await create_audit_log(
        db=db,
        action="TICKET_MESSAGE_DELETED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Message from '{deleted_sender}' was deleted from ticket",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "message_index": message_index,
            "deleted_sender": deleted_sender,
            "deleted_content_preview": deleted_content[:100] if len(deleted_content) > 100 else deleted_content
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


# Admin: Create ticket on behalf of user
class AdminTicketCreate(BaseModel):
    user_id: str
    subject: str
    description: str


@app.post("/api/v1/admin/tickets/create-for-user")
async def admin_create_ticket_for_user(
    data: AdminTicketCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin creates a support ticket on behalf of a user."""
    from bson import ObjectId
    from bson.errors import InvalidId
    from datetime import datetime, timezone
    
    # Find the target user
    user_query = {"_id": data.user_id}
    try:
        user_query = {"$or": [{"_id": data.user_id}, {"_id": ObjectId(data.user_id)}]}
    except (InvalidId, TypeError):
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", "Customer")
    
    # Create ticket with admin flag
    ticket_service = TicketService(db)
    ticket = await ticket_service.create_ticket_by_admin(
        user_id=user_id,
        user_name=user_name,
        subject=data.subject,
        description=data.description,
        admin_id=current_user["id"],
        admin_name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip() or "Support"
    )
    
    # Create notification for the user
    notification_service = NotificationService(db)
    await notification_service.create_notification(
        user_id=user_id,
        notification_type="SUPPORT",
        title="New Support Ticket",
        message=f"A support ticket has been created for you: {data.subject}",
        action_url="/support",
        metadata={
            "ticket_id": ticket.id,
            "created_by_support": True
        }
    )
    
    # Audit log
    await create_audit_log(
        db=db,
        action="TICKET_CREATED_BY_ADMIN",
        entity_type="ticket",
        entity_id=ticket.id,
        description=f"Admin created support ticket for user {user.get('email', user_id)}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "target_user_id": user_id,
            "target_user_email": user.get("email"),
            "ticket_subject": data.subject
        }
    )
    
    return ticket.model_dump()


# Admin: Mark ticket as read (resets unread counter)
@app.post("/api/v1/admin/tickets/{ticket_id}/mark-read")
async def admin_mark_ticket_read(
    ticket_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark a ticket as read by admin (resets unread message count)."""
    from datetime import datetime, timezone
    
    result = await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {"admin_last_read_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {"success": True, "ticket_id": ticket_id}


# ==================== ADMIN ANALYTICS ====================

@app.get("/api/v1/admin/analytics/overview")
async def get_admin_analytics_overview(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get admin dashboard analytics overview.
    
    PERFORMANCE OPTIMIZED: Uses parallel queries and aggregation pipelines
    instead of sequential count_documents() calls.
    """
    import asyncio
    from datetime import datetime, timezone, timedelta
    
    # Run all count queries in parallel using asyncio.gather
    async def get_users_count():
        return await db.users.count_documents({})
    
    async def get_active_users_count():
        return await db.users.count_documents({"status": "ACTIVE"})
    
    async def get_pending_kyc_count():
        return await db.kyc_applications.count_documents({"status": "SUBMITTED"})
    
    async def get_approved_kyc_count():
        return await db.kyc_applications.count_documents({"status": "APPROVED"})
    
    async def get_accounts_count():
        return await db.bank_accounts.count_documents({})
    
    async def get_transfer_stats():
        # Use aggregation to get all transfer counts in ONE query
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        results = await db.transfers.aggregate(pipeline).to_list(10)
        stats = {"total": 0, "pending": 0, "completed": 0, "rejected": 0}
        for r in results:
            status = r["_id"]
            count = r["count"]
            stats["total"] += count
            if status == "SUBMITTED":
                stats["pending"] = count
            elif status == "COMPLETED":
                stats["completed"] = count
            elif status == "REJECTED":
                stats["rejected"] = count
        return stats
    
    async def get_ticket_stats():
        # Use aggregation to get ticket counts in ONE query
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        results = await db.tickets.aggregate(pipeline).to_list(10)
        total = 0
        open_count = 0
        for r in results:
            status = r["_id"]
            count = r["count"]
            total += count
            if status in ["OPEN", "IN_PROGRESS", "open", "in_progress"]:
                open_count += count
        return {"total": total, "open": open_count}
    
    async def get_pending_cards_count():
        return await db.card_requests.count_documents({"status": "PENDING"})
    
    async def get_volume():
        try:
            pipeline = [
                {"$match": {"direction": "CREDIT"}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]
            result = await db.ledger_entries.aggregate(pipeline).to_list(1)
            return result[0].get("total", 0) if result else 0
        except Exception:
            return 0
    
    # Execute ALL queries in parallel
    results = await asyncio.gather(
        get_users_count(),
        get_active_users_count(),
        get_pending_kyc_count(),
        get_approved_kyc_count(),
        get_accounts_count(),
        get_transfer_stats(),
        get_ticket_stats(),
        get_pending_cards_count(),
        get_volume()
    )
    
    total_users = results[0]
    active_users = results[1]
    pending_kyc = results[2]
    approved_kyc = results[3]
    total_accounts = results[4]
    transfer_stats = results[5]
    ticket_stats = results[6]
    pending_cards = results[7]
    total_volume_cents = results[8]
    
    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "kyc": {
            "pending": pending_kyc,
            "approved": approved_kyc
        },
        "accounts": {
            "total": total_accounts
        },
        "transfers": {
            "total": transfer_stats["total"],
            "pending": transfer_stats["pending"],
            "completed": transfer_stats["completed"],
            "rejected": transfer_stats["rejected"],
            "volume_cents": total_volume_cents
        },
        "tickets": {
            "total": ticket_stats["total"],
            "open": ticket_stats["open"]
        },
        "cards": {
            "pending": pending_cards
        }
    }


@app.get("/api/v1/admin/notification-counts")
async def get_admin_notification_counts(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get notification badge counts for admin sidebar.
    
    PERSISTENT ACROSS SESSIONS: Uses per-admin, per-section "last_seen_at" timestamps
    stored in database. Badges show items created/updated AFTER the admin last viewed
    that section, not just total pending items.
    
    Returns counts for:
    - users: New users created since last seen Users section
    - kyc: New KYC submissions since last seen KYC Queue
    - card_requests: New card requests since last seen Card Requests
    - transfers: New submitted transfers since last seen Transfers Queue  
    - tickets: Tickets with new client activity since last seen Support Tickets
    """
    import asyncio
    from datetime import datetime, timezone
    from bson import ObjectId
    
    admin_id = str(current_user.get("_id") or current_user.get("id"))
    
    # Section keys matching frontend
    section_keys = ['users', 'kyc', 'card_requests', 'transfers', 'tickets']
    
    # Get all last_seen timestamps for this admin in one query
    section_views = await db.admin_section_views.find(
        {"admin_id": admin_id}
    ).to_list(length=10)
    
    # Build lookup dict: section_key -> last_seen_at
    last_seen_map = {}
    for view in section_views:
        last_seen_map[view["section_key"]] = view.get("last_seen_at")
    
    # Default: if never seen, use a very old date (show all pending items)
    default_last_seen = datetime(2000, 1, 1, tzinfo=timezone.utc)
    
    async def get_users_new():
        """Count users created since last seen, with status PENDING."""
        last_seen = last_seen_map.get('users', default_last_seen)
        return await db.users.count_documents({
            "status": "PENDING",
            "created_at": {"$gt": last_seen}
        })
    
    async def get_kyc_new():
        """Count KYC applications submitted since last seen, with status PENDING."""
        last_seen = last_seen_map.get('kyc', default_last_seen)
        return await db.kyc_applications.count_documents({
            "status": "PENDING",
            "created_at": {"$gt": last_seen}
        })
    
    async def get_card_requests_new():
        """Count card requests created since last seen, with status PENDING."""
        last_seen = last_seen_map.get('card_requests', default_last_seen)
        return await db.card_requests.count_documents({
            "status": "PENDING",
            "created_at": {"$gt": last_seen}
        })
    
    async def get_transfers_new():
        """Count transfers submitted since last seen, with status SUBMITTED."""
        last_seen = last_seen_map.get('transfers', default_last_seen)
        return await db.transfers.count_documents({
            "status": "SUBMITTED",
            "created_at": {"$gt": last_seen}
        })
    
    async def get_tickets_new():
        """Count tickets with new client activity since last seen.
        
        This includes:
        1. New tickets created since last_seen
        2. Existing tickets with new client messages since last_seen
        """
        last_seen = last_seen_map.get('tickets', default_last_seen)
        
        # Use aggregation to find tickets with client activity after last_seen
        pipeline = [
            # Match open/in-progress tickets
            {"$match": {"status": {"$in": ["OPEN", "IN_PROGRESS", "open", "in_progress"]}}},
            # Lookup messages
            {"$lookup": {
                "from": "support_messages",
                "localField": "_id",
                "foreignField": "ticket_id",
                "as": "messages"
            }},
            # Filter to tickets where:
            # - Ticket created after last_seen, OR
            # - Has a client message after last_seen
            {"$match": {
                "$or": [
                    # New ticket created after last_seen
                    {"created_at": {"$gt": last_seen}},
                    # Has client message after last_seen
                    {"messages": {
                        "$elemMatch": {
                            "sender_type": {"$in": ["client", "user"]},
                            "created_at": {"$gt": last_seen}
                        }
                    }}
                ]
            }},
            {"$count": "count"}
        ]
        result = await db.support_tickets.aggregate(pipeline).to_list(1)
        return result[0]["count"] if result else 0
    
    # Execute all queries in parallel for performance
    results = await asyncio.gather(
        get_users_new(),
        get_kyc_new(),
        get_card_requests_new(),
        get_transfers_new(),
        get_tickets_new(),
        return_exceptions=True
    )
    
    # Handle any exceptions gracefully
    def safe_result(result, default=0):
        return result if isinstance(result, int) else default
    
    return {
        "users": safe_result(results[0]),
        "kyc": safe_result(results[1]),
        "card_requests": safe_result(results[2]),
        "transfers": safe_result(results[3]),
        "tickets": safe_result(results[4])
    }


@app.post("/api/v1/admin/notifications/seen")
async def mark_admin_section_seen(
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark a sidebar section as 'seen' by this admin.
    
    Updates last_seen_at timestamp for the given section. This clears the badge
    for that section and persists across logout/login.
    
    Request body: { "section_key": "users" | "kyc" | "card_requests" | "transfers" | "tickets" }
    """
    from datetime import datetime, timezone
    
    body = await request.json()
    section_key = body.get("section_key")
    
    valid_sections = ['users', 'kyc', 'card_requests', 'transfers', 'tickets']
    if section_key not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section_key. Must be one of: {valid_sections}")
    
    admin_id = str(current_user.get("_id") or current_user.get("id"))
    now = datetime.now(timezone.utc)
    
    # Upsert: update if exists, insert if not
    await db.admin_section_views.update_one(
        {"admin_id": admin_id, "section_key": section_key},
        {
            "$set": {
                "last_seen_at": now,
                "updated_at": now
            },
            "$setOnInsert": {
                "admin_id": admin_id,
                "section_key": section_key,
                "created_at": now
            }
        },
        upsert=True
    )
    
    return {"ok": True, "section_key": section_key, "last_seen_at": now.isoformat()}


@app.get("/api/v1/admin/analytics/monthly")
async def get_admin_analytics_monthly(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get real monthly statistics for admin dashboard charts.
    
    PERFORMANCE OPTIMIZED: Uses aggregation pipelines instead of sequential count queries.
    Returns actual data from the database grouped by month for the last 6 months.
    """
    import asyncio
    from datetime import datetime, timezone, timedelta
    from calendar import month_abbr
    
    # Calculate date range - last 6 months including current
    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=180)
    
    # Use aggregation to get all user counts by month in ONE query
    async def get_users_by_month():
        pipeline = [
            {"$match": {"created_at": {"$gte": six_months_ago}}},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        results = await db.users.aggregate(pipeline).to_list(12)
        return {(r["_id"]["year"], r["_id"]["month"]): r["count"] for r in results}
    
    # Use aggregation to get all transfer counts by month in ONE query
    async def get_transfers_by_month():
        pipeline = [
            {"$match": {"created_at": {"$gte": six_months_ago}}},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        results = await db.transfers.aggregate(pipeline).to_list(12)
        return {(r["_id"]["year"], r["_id"]["month"]): r["count"] for r in results}
    
    async def get_users_before_period():
        return await db.users.count_documents({"created_at": {"$lt": six_months_ago}})
    
    # Execute all queries in parallel
    users_by_month, transfers_by_month, users_before_period = await asyncio.gather(
        get_users_by_month(),
        get_transfers_by_month(),
        get_users_before_period()
    )
    
    # Generate list of last 6 months
    months_data = []
    running_total = users_before_period
    
    for i in range(5, -1, -1):  # 5 months ago to current month
        target_date = now - timedelta(days=i*30)
        year = target_date.year
        month = target_date.month
        
        users_count = users_by_month.get((year, month), 0)
        transfers_count = transfers_by_month.get((year, month), 0)
        
        running_total += users_count
        
        months_data.append({
            "month": month_abbr[month],
            "year": year,
            "users": users_count,
            "transactions": transfers_count,
            "cumulative_users": running_total
        })
    
    return {
        "monthly_data": months_data,
        "period": "last_6_months"
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
        recipient_name=data.recipient_name,
        instant_requested=data.instant_requested  # Store for future instant transfer support
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
    period: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get spending breakdown by category from real ledger data.
    
    Args:
        days: Number of days to look back (7, 30, 90). Ignored if period is set.
        period: Optional period override. Use 'this_month' for calendar month (same as Overview).
    
    When period='this_month', uses the SAME calculation as the Overview "THIS MONTH" widget
    to ensure consistency.
    """
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    
    # If period is 'this_month', use the same logic as monthly-spending for consistency
    if period == 'this_month':
        spending = await advanced_service.get_monthly_spending(current_user["id"])
        return spending
    
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
    page: int = 1,
    page_size: int = 50,
    search: str = None,
    scope: str = "tab",  # "tab" or "all" - search within tab or all statuses
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Get card requests with pagination, search, and user information.
    
    PERFORMANCE OPTIMIZED: Server-side pagination, search, and bulk user lookups.
    
    Query params:
    - status: Filter by status (PENDING, FULFILLED, REJECTED). Default: PENDING
    - page: Page number (1-indexed, default 1)
    - page_size: Items per page (20, 50, or 100, default 50)
    - search: Search term (matches user name, email, card type, request ID)
    - scope: "tab" (search current status only) or "all" (search all statuses)
    """
    from bson import ObjectId
    import re
    
    # Validate page_size
    valid_page_sizes = [20, 50, 100]
    if page_size not in valid_page_sizes:
        page_size = 50
    
    # Validate page
    if page < 1:
        page = 1
    
    # Build base query
    query = {}
    
    # Status filter (unless scope is "all" with search)
    if scope == "all" and search:
        # Search across all statuses
        pass
    elif status:
        query["status"] = status
    else:
        query["status"] = "PENDING"  # Default to PENDING
    
    # If searching, we need to do a more complex query
    search_user_ids = []
    if search:
        search = search.strip()
        search_regex = {"$regex": re.escape(search), "$options": "i"}
        
        # First, find users matching the search (for name/email search)
        user_query = {
            "$or": [
                {"first_name": search_regex},
                {"last_name": search_regex},
                {"email": search_regex}
            ]
        }
        users_cursor = db.users.find(user_query, {"_id": 1})
        async for user in users_cursor:
            search_user_ids.append(str(user["_id"]))
        
        # Build search conditions for card_requests
        search_conditions = [
            {"card_type": search_regex},
            {"_id": search_regex}
        ]
        
        if search_user_ids:
            search_conditions.append({"user_id": {"$in": search_user_ids}})
        
        # Combine with status filter
        if query.get("status"):
            query = {
                "$and": [
                    {"status": query["status"]},
                    {"$or": search_conditions}
                ]
            }
        else:
            query = {"$or": search_conditions}
    
    # Get total count for pagination
    total_count = await db.card_requests.count_documents(query)
    
    # Calculate pagination
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    
    skip = (page - 1) * page_size
    
    # Fetch paginated results
    cursor = db.card_requests.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    request_docs = await cursor.to_list(length=page_size)
    
    if not request_docs:
        return {
            "ok": True,
            "data": [],
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "status": status or "PENDING",
                "has_prev": page > 1,
                "has_next": page < total_pages
            }
        }
    
    # Collect all unique user_ids for bulk lookup
    user_ids = set()
    for doc in request_docs:
        user_id = doc.get("user_id")
        if user_id:
            try:
                user_ids.add(ObjectId(user_id))
            except:
                user_ids.add(user_id)
    
    # BULK LOOKUP: Fetch all users in ONE query
    users_map = {}
    if user_ids:
        users_cursor = db.users.find({"_id": {"$in": list(user_ids)}})
        async for user in users_cursor:
            users_map[str(user["_id"])] = user
    
    # Build response with user info included
    requests = []
    for doc in request_docs:
        request_dict = serialize_doc(doc)
        
        # Add user info from pre-fetched map (O(1) lookup)
        user_id = doc.get("user_id")
        user = users_map.get(str(user_id)) if user_id else None
        
        if user:
            request_dict["user_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            request_dict["user_email"] = user.get("email", "")
        else:
            request_dict["user_name"] = "Unknown User"
            request_dict["user_email"] = ""
        
        requests.append(request_dict)
    
    return {
        "ok": True,
        "data": requests,
        "pagination": {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "status": status or "PENDING",
            "has_prev": page > 1,
            "has_next": page < total_pages
        }
    }


@app.delete("/api/v1/admin/card-requests/{request_id}")
async def admin_delete_card_request(
    request_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Delete a card request with safety handling for fulfilled requests.
    
    CRITICAL SAFETY LOGIC:
    - If the request is FULFILLED and has an associated card, also delete the card
    - Logs all delete actions for audit purposes
    - Does not affect other user data
    
    Returns:
    - ok: True if deleted successfully
    - card_also_deleted: True if associated card was also deleted (for fulfilled requests)
    """
    from datetime import datetime, timezone
    import logging
    logger = logging.getLogger(__name__)
    
    admin_id = str(current_user.get("_id") or current_user.get("id"))
    admin_email = current_user.get("email", "unknown")
    
    # Find the card request
    request_doc = await db.card_requests.find_one({"_id": request_id})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Card request not found")
    
    request_status = request_doc.get("status")
    user_id = request_doc.get("user_id")
    card_type = request_doc.get("card_type")
    card_also_deleted = False
    deleted_card_id = None
    
    # CRITICAL: If FULFILLED, check for and delete associated card
    if request_status == "FULFILLED":
        # Find the associated card - it should have been created with a reference to this request
        # Look for card with matching user_id and card_type, created around the fulfilled time
        fulfilled_at = request_doc.get("decided_at")
        
        # Try to find the associated card
        card_query = {"user_id": user_id}
        
        # If we have the fulfilled_card_id stored, use that
        if request_doc.get("fulfilled_card_id"):
            card_doc = await db.cards.find_one({"_id": request_doc.get("fulfilled_card_id")})
        else:
            # Otherwise try to find by user and type
            # Find cards created after the request was fulfilled
            if fulfilled_at:
                card_query["created_at"] = {"$gte": fulfilled_at}
            if card_type:
                card_query["card_type"] = card_type
            
            card_doc = await db.cards.find_one(card_query)
        
        if card_doc:
            deleted_card_id = card_doc.get("_id")
            # Delete the associated card
            delete_card_result = await db.cards.delete_one({"_id": deleted_card_id})
            if delete_card_result.deleted_count > 0:
                card_also_deleted = True
                logger.warning(
                    f"[CARD REQUEST DELETE] Admin {admin_email} deleted FULFILLED request {request_id} "
                    f"- also deleted associated card {deleted_card_id} for user {user_id}"
                )
            else:
                logger.warning(
                    f"[CARD REQUEST DELETE] Admin {admin_email} deleted FULFILLED request {request_id} "
                    f"- card {deleted_card_id} was already deleted or not found"
                )
        else:
            logger.warning(
                f"[CARD REQUEST DELETE] Admin {admin_email} deleted FULFILLED request {request_id} "
                f"- no associated card found for user {user_id} (edge case)"
            )
    
    # Delete the card request
    delete_result = await db.card_requests.delete_one({"_id": request_id})
    
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete card request")
    
    # Create audit log entry
    audit_entry = {
        "_id": f"audit_{datetime.now(timezone.utc).timestamp()}_{request_id}",
        "action": "CARD_REQUEST_DELETE",
        "entity_type": "card_request",
        "entity_id": request_id,
        "admin_id": admin_id,
        "admin_email": admin_email,
        "details": {
            "request_status": request_status,
            "user_id": user_id,
            "card_type": card_type,
            "card_also_deleted": card_also_deleted,
            "deleted_card_id": deleted_card_id
        },
        "timestamp": datetime.now(timezone.utc)
    }
    
    try:
        await db.audit_logs.insert_one(audit_entry)
    except Exception as e:
        logger.error(f"[AUDIT] Failed to create audit log for card request delete: {e}")
    
    logger.info(
        f"[CARD REQUEST DELETE] Admin {admin_email} deleted card request {request_id} "
        f"(status: {request_status}, card_also_deleted: {card_also_deleted})"
    )
    
    return {
        "ok": True,
        "message": "Card request deleted successfully",
        "card_also_deleted": card_also_deleted,
        "deleted_card_id": deleted_card_id
    }


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
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Get transfers with sender information.
    
    PERFORMANCE OPTIMIZED: Uses bulk lookups and pagination.
    
    Query params:
    - status: Filter by status (SUBMITTED, COMPLETED, REJECTED)
    - page: Page number (1-indexed, default 1)
    - page_size: Items per page (20, 50, or 100, default 20)
    - search: Search term (searches beneficiary name, sender name/email, IBAN, reference across ALL statuses)
    """
    # Validate page_size
    valid_page_sizes = [20, 50, 100]
    if page_size not in valid_page_sizes:
        page_size = 20
    
    workflows = BankingWorkflowsService(db)
    result = await workflows.get_admin_transfers(status, page, page_size, search)
    # Result now includes 'transfers' list and 'pagination' info
    return {"ok": True, "data": result["transfers"], "pagination": result["pagination"]}


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


@app.post("/api/v1/admin/transfers/{transfer_id}/resend-email")
async def admin_resend_transfer_email(
    transfer_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin resends transfer confirmation email. Only available if email status is failed or pending."""
    from bson import ObjectId
    from bson.errors import InvalidId
    from services.email_service import EmailService
    from datetime import timezone
    
    # Find transfer
    transfer = await db.transfers.find_one({"_id": transfer_id})
    if not transfer:
        try:
            transfer = await db.transfers.find_one({"_id": ObjectId(transfer_id)})
        except InvalidId:
            pass
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    # Check if email already sent successfully
    email_status = transfer.get("confirmation_email_status", "pending")
    if email_status == "sent" and transfer.get("confirmation_email_sent", False):
        raise HTTPException(
            status_code=400, 
            detail=f"Email already sent successfully. Provider ID: {transfer.get('confirmation_email_provider_id', 'N/A')}"
        )
    
    # Get user details for email
    user_id = transfer.get("user_id")
    user = None
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this transfer")
    
    user_email = user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="User has no email address")
    
    # Get sender account IBAN
    account = await db.bank_accounts.find_one({"_id": transfer.get("from_account_id")})
    sender_iban = account.get("iban") if account else transfer.get("sender_iban", "N/A")
    
    # Send the email
    email_service = EmailService()
    language = user.get("language", "en") or "en"
    
    logger.info(f"[ADMIN RESEND] Attempting to resend transfer email: transferId={transfer_id}, recipient={user_email}")
    
    email_result = email_service.send_transfer_confirmation_email(
        to_email=user_email,
        first_name=user.get("first_name", ""),
        reference_number=transfer.get("reference_number") or transfer_id[:8].upper(),
        amount_cents=transfer.get("amount", 0),
        beneficiary_name=transfer.get("beneficiary_name", "Unknown"),
        beneficiary_iban=transfer.get("beneficiary_iban", ""),
        sender_iban=sender_iban or "N/A",
        transfer_type=transfer.get("transfer_type", "SEPA Transfer"),
        transfer_date=transfer.get("created_at"),
        language=language
    )
    
    now = datetime.now(timezone.utc)
    
    if email_result.get('success'):
        # Update transfer with sent status
        await db.transfers.update_one(
            {"_id": transfer["_id"]},
            {"$set": {
                "confirmation_email_sent": True,
                "confirmation_email_status": "sent",
                "confirmation_email_sent_at": now,
                "confirmation_email_provider_id": email_result.get('provider_id'),
                "confirmation_email_error": None
            }}
        )
        
        # Audit log
        await create_audit_log(
            db=db,
            action="TRANSFER_EMAIL_RESENT",
            entity_type="transfer",
            entity_id=transfer_id,
            description=f"Transfer confirmation email resent to {user_email}",
            performed_by=current_user["id"],
            performed_by_role=current_user["role"],
            performed_by_email=current_user["email"],
            metadata={
                "recipient_email": user_email,
                "provider_id": email_result.get('provider_id'),
                "reference": transfer.get("reference_number")
            }
        )
        
        return {
            "ok": True, 
            "message": f"Confirmation email resent successfully to {user_email}",
            "provider_id": email_result.get('provider_id')
        }
    else:
        # Update transfer with failure status
        error_msg = email_result.get('error', 'Unknown error')
        await db.transfers.update_one(
            {"_id": transfer["_id"]},
            {"$set": {
                "confirmation_email_status": "failed",
                "confirmation_email_error": error_msg
            }}
        )
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to send email: {error_msg}"
        )


@app.get("/api/v1/admin/accounts-with-users")
async def get_all_accounts_with_users(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    """Get all bank accounts with their user information, real ledger balances, search and pagination.
    
    PERFORMANCE OPTIMIZED: Uses bulk balance calculation instead of N+1 queries.
    
    Supports:
    - search: Filter by user name, email, IBAN, or account number (searches ALL accounts in DB)
    - page: Page number (1-indexed)
    - limit: Accounts per page (20, 50, or 100)
    
    When search is provided, pagination is ignored and ALL matching accounts are returned.
    """
    from bson import ObjectId
    
    # Validate limit
    if limit not in [20, 50, 100]:
        limit = 50
    
    # Get ledger engine for bulk balance calculation
    ledger_engine = LedgerEngine(db)
    
    # Get all bank accounts first (we need to join with users for search)
    accounts_cursor = db.bank_accounts.find({})
    all_accounts = []
    user_ids = set()
    ledger_account_ids = []
    
    async for acc in accounts_cursor:
        user_id = acc.get("user_id")
        if user_id:
            try:
                uid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id) if ObjectId.is_valid(str(user_id)) else None
                if uid:
                    user_ids.add(uid)
            except:
                pass
        
        # Collect ledger account IDs for bulk balance query
        ledger_account_id = acc.get("ledger_account_id")
        if ledger_account_id:
            ledger_account_ids.append(ledger_account_id)
        
        all_accounts.append(acc)
    
    # Fetch all users in one query
    users_map = {}
    if user_ids:
        users_cursor = db.users.find({"_id": {"$in": list(user_ids)}})
        async for user in users_cursor:
            users_map[str(user["_id"])] = user
    
    # PERFORMANCE FIX: Get ALL balances in a single bulk query instead of N queries
    balance_map = {}
    if ledger_account_ids:
        try:
            balance_map = await ledger_engine.get_bulk_balances(ledger_account_ids)
        except Exception as e:
            logger.error(f"Failed to get bulk balances: {e}")
            balance_map = {}
    
    # Combine accounts with user info and balances (no more N+1 queries!)
    enriched_accounts = []
    for acc in all_accounts:
        user_id = acc.get("user_id")
        user_id_str = str(user_id) if user_id else None
        user = users_map.get(user_id_str, {})
        
        # Get balance from the pre-fetched map (O(1) lookup)
        ledger_account_id = acc.get("ledger_account_id")
        balance = balance_map.get(ledger_account_id, 0) if ledger_account_id else 0
        
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown"
        user_email = user.get("email", "Unknown")
        account_number = acc.get("account_number", "")
        iban = acc.get("iban") or ""
        
        enriched_accounts.append({
            "id": str(acc["_id"]),
            "account_number": account_number,
            "iban": iban,
            "bic": acc.get("bic"),
            "balance": balance,  # Real ledger balance in cents
            "currency": acc.get("currency", "EUR"),
            "userId": user_id_str,
            "userName": user_name,
            "userEmail": user_email,
            "created_at": acc.get("created_at"),
            # Search fields for filtering
            "_search_text": f"{user_name} {user_email} {account_number} {iban}".lower()
        })
    
    # Apply search filter if provided
    if search and search.strip():
        search_term = search.strip().lower()
        enriched_accounts = [
            acc for acc in enriched_accounts 
            if search_term in acc["_search_text"]
        ]
    
    # Get total count before pagination
    total_count = len(enriched_accounts)
    
    # Apply pagination only when not searching
    if search and search.strip():
        # Return all matching results for search
        paginated_accounts = enriched_accounts
        total_pages = 1
    else:
        # Apply pagination
        skip = (page - 1) * limit
        paginated_accounts = enriched_accounts[skip:skip + limit]
        total_pages = (total_count + limit - 1) // limit
    
    # Remove search text field before returning
    for acc in paginated_accounts:
        acc.pop("_search_text", None)
    
    return {
        "accounts": paginated_accounts,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_accounts": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages if not (search and search.strip()) else False,
            "has_prev": page > 1 if not (search and search.strip()) else False
        }
    }


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



# ==================== ADMIN NOTIFICATION MANAGEMENT ====================

@app.post("/api/v1/admin/notifications/clear")
async def clear_admin_notifications(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark admin notifications as cleared by storing the current timestamp.
    This persists across sessions and page reloads.
    """
    from datetime import datetime, timezone
    
    cleared_at = datetime.now(timezone.utc)
    
    # Update the admin user's document with the cleared timestamp
    # Handle both string and ObjectId formats like auth code does
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_id = current_user["id"]
    
    # First try as string
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"admin_notifications_cleared_at": cleared_at}}
    )
    
    # If no match and it looks like an ObjectId, try as ObjectId
    if result.matched_count == 0:
        try:
            result = await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"admin_notifications_cleared_at": cleared_at}}
            )
        except InvalidId:
            pass
    
    if result.modified_count == 0:
        # Also handle if document doesn't exist (shouldn't happen but be safe)
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "cleared_at": cleared_at.isoformat()
    }


@app.get("/api/v1/admin/notifications/cleared-at")
async def get_admin_notifications_cleared_at(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get the timestamp when admin last cleared notifications.
    Returns None if never cleared.
    """
    # Handle both string and ObjectId formats like auth code does
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_id = current_user["id"]
    
    # First try as string
    user = await db.users.find_one(
        {"_id": user_id},
        {"admin_notifications_cleared_at": 1}
    )
    
    # If not found and it looks like an ObjectId, try as ObjectId
    if not user:
        try:
            user = await db.users.find_one(
                {"_id": ObjectId(user_id)},
                {"admin_notifications_cleared_at": 1}
            )
        except InvalidId:
            pass
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cleared_at = user.get("admin_notifications_cleared_at")
    
    return {
        "cleared_at": cleared_at.isoformat() if cleared_at else None
    }


@app.get("/api/v1/admin/notifications/counts-since-clear")
async def get_admin_notification_counts_since_clear(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get counts of pending items created AFTER the last clear timestamp.
    This allows the badge to show only NEW items while keeping old items cleared.
    
    Returns:
    - kyc: Count of pending KYC applications submitted after clear
    - cards: Count of pending card requests created after clear  
    - transfers: Count of pending transfers created after clear
    - tickets: Count of open tickets created after clear
    - total: Sum of all counts
    - cleared_at: The timestamp when notifications were last cleared (or null)
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_id = current_user["id"]
    
    # Get the cleared_at timestamp
    user = await db.users.find_one(
        {"_id": user_id},
        {"admin_notifications_cleared_at": 1}
    )
    
    if not user:
        try:
            user = await db.users.find_one(
                {"_id": ObjectId(user_id)},
                {"admin_notifications_cleared_at": 1}
            )
        except InvalidId:
            pass
    
    cleared_at = user.get("admin_notifications_cleared_at") if user else None
    
    # If never cleared, count all items
    if not cleared_at:
        kyc_count = await db.kyc_applications.count_documents({
            "status": {"$in": ["SUBMITTED", "UNDER_REVIEW", "NEEDS_MORE_INFO"]}
        })
        cards_count = await db.card_requests.count_documents({"status": "PENDING"})
        transfers_count = await db.transfers.count_documents({"status": "SUBMITTED"})
        tickets_count = await db.tickets.count_documents({
            "status": {"$in": ["OPEN", "IN_PROGRESS"]}
        })
    else:
        # Count only items created/submitted AFTER cleared_at
        # KYC: Use submitted_at field
        kyc_count = await db.kyc_applications.count_documents({
            "status": {"$in": ["SUBMITTED", "UNDER_REVIEW", "NEEDS_MORE_INFO"]},
            "submitted_at": {"$gt": cleared_at}
        })
        
        # Card requests: Use created_at field
        cards_count = await db.card_requests.count_documents({
            "status": "PENDING",
            "created_at": {"$gt": cleared_at}
        })
        
        # Transfers: Use created_at field
        transfers_count = await db.transfers.count_documents({
            "status": "SUBMITTED",
            "created_at": {"$gt": cleared_at}
        })
        
        # Tickets: Use created_at field
        tickets_count = await db.tickets.count_documents({
            "status": {"$in": ["OPEN", "IN_PROGRESS"]},
            "created_at": {"$gt": cleared_at}
        })
    
    total = kyc_count + cards_count + transfers_count + tickets_count
    
    return {
        "kyc": kyc_count,
        "cards": cards_count,
        "transfers": transfers_count,
        "tickets": tickets_count,
        "total": total,
        "cleared_at": cleared_at.isoformat() if cleared_at else None
    }



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
        result["steps"].append("5. Recipient IBAN found - INTERNAL transfer")
    else:
        result["steps"].append("5. Recipient IBAN not found - EXTERNAL transfer")
    
    result["ready"] = True
    result["transfer_type"] = "INTERNAL" if to_acc else "EXTERNAL"
    result["balance"] = balance
    result["amount"] = amount
    
    return result
