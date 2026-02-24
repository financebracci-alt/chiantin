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


def format_timestamp_utc(dt: datetime) -> str:
    """Format a datetime as ISO 8601 with UTC timezone suffix.
    
    MongoDB returns naive datetimes (no timezone info) even when stored with timezone.
    This ensures all API responses include the 'Z' suffix so JavaScript parses them as UTC.
    """
    if dt is None:
        return None
    # If datetime is naive (no timezone), assume it's UTC (MongoDB returns UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to UTC and format with Z suffix
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
from services.ledger_service import LedgerEngine
from services.statement_service import StatementService
from services.ticket_service import TicketService
from services.notification_service import NotificationService
from services.transfer_service import TransferService
from services.advanced_service import AdvancedBankingService
from services.email_service import EmailService
from services.banking_workflows_service import BankingWorkflowsService
from schemas.users import (
    UserCreate, UserLogin, TokenResponse, UserResponse, MFASetupResponse, 
    MFAVerifyRequest, ResendVerificationRequest, VerifyEmailRequest,
    SignupRequest, PasswordChangeRequest, VerifyPasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest
)
from schemas.kyc import KYCSubmitRequest, KYCReviewRequest, DocumentType
from schemas.banking import AccountResponse, AdminCreditRequest, AdminDebitRequest, TransactionDisplayType
from schemas.tickets import TicketCreate, MessageCreate, TicketStatus, Ticket
from schemas.transfers import P2PTransferRequest
from schemas.advanced import CreateBeneficiary, CreateScheduledPayment
from schemas.banking_workflows import (
    CreateCardRequest, FulfillCardRequest, CreateRecipient, CreateTransfer
)
from providers import LocalS3Storage, CloudinaryStorage
from pydantic import BaseModel, Field, field_validator
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

# Include extracted routers
from routers import health as health_router
from routers import audit as audit_router
from routers import tickets as tickets_router
from routers import kyc as kyc_router
from routers import admin_users as admin_users_router
from routers import auth as auth_router

app.include_router(health_router.router)
app.include_router(audit_router.router)
app.include_router(tickets_router.router)
app.include_router(tickets_router.admin_router)
app.include_router(kyc_router.router)
app.include_router(kyc_router.admin_router)
app.include_router(admin_users_router.router)
app.include_router(auth_router.router)
from routers import analytics as analytics_router
app.include_router(analytics_router.router)


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

# NOTE: /api/v1/auth/signup moved to routers/auth.py
# @app.post("/api/v1/auth/signup", response_model=UserResponse, status_code=201)
# async def signup(...):
#     ... (see routers/auth.py)

# NOTE: /api/v1/auth/login moved to routers/auth.py
# @app.post("/api/v1/auth/login", response_model=TokenResponse)
# async def login(...):
#     ... (see routers/auth.py)


# NOTE: /api/v1/auth/logout moved to routers/auth.py
# @app.post("/api/v1/auth/logout")
# async def logout(...):
#     ... (see routers/auth.py)


# NOTE: /api/v1/auth/verify-email moved to routers/auth.py
# @app.post("/api/v1/auth/verify-email")
# async def verify_email(...):
#     ... (see routers/auth.py)

# NOTE: /api/v1/auth/resend-verification moved to routers/auth.py  
# @app.post("/api/v1/auth/resend-verification")
# async def resend_verification_email(...):
#     ... (see routers/auth.py)


# NOTE: /api/v1/auth/me moved to routers/auth.py
# @app.get("/api/v1/auth/me", response_model=UserResponse)
# async def get_me(
#     current_user: dict = Depends(get_current_user),
#     db: AsyncIOMotorDatabase = Depends(get_database)
# ):
#     """Get current user info."""
#     auth_service = AuthService(db)
#     user = await auth_service.get_user(current_user["id"])
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     
#     return UserResponse(
#         id=user.id,
#         email=user.email,
#         first_name=user.first_name,
#         last_name=user.last_name,
#         role=user.role,
#         status=user.status,
#         email_verified=user.email_verified,
#         mfa_enabled=user.mfa_enabled,
#         created_at=user.created_at,
#         last_login_at=user.last_login_at
#     )


# NOTE: /api/v1/auth/mfa/setup moved to routers/auth.py
# @app.post("/api/v1/auth/mfa/setup", response_model=MFASetupResponse)
# async def setup_mfa(...):
#     ... (see routers/auth.py)

# NOTE: /api/v1/auth/mfa/enable moved to routers/auth.py
# @app.post("/api/v1/auth/mfa/enable")
# async def enable_mfa(...):
#     ... (see routers/auth.py)


# NOTE: /api/v1/auth/change-password moved to routers/auth.py
# @app.post("/api/v1/auth/change-password")
# async def change_password(...):
#     ... (see routers/auth.py)

# NOTE: /api/v1/auth/verify-password moved to routers/auth.py
# @app.post("/api/v1/auth/verify-password")
# async def verify_user_password(...):
#     ... (see routers/auth.py)

# NOTE: /api/v1/auth/forgot-password moved to routers/auth.py
# @app.post("/api/v1/auth/forgot-password")
# async def forgot_password(...):
#     ... (see routers/auth.py)

# NOTE: /api/v1/auth/reset-password moved to routers/auth.py
# @app.post("/api/v1/auth/reset-password")
# async def reset_password(...):
#     ... (see routers/auth.py)
    
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
# ==================== ADMIN ANALYTICS ====================

# NOTE: /api/v1/admin/analytics/overview moved to routers/analytics.py
# @app.get("/api/v1/admin/analytics/overview")
# async def get_admin_analytics_overview(...):
#     ... (see routers/analytics.py)


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
        """Count transfers submitted since last seen, with status SUBMITTED.
        SOFT DELETE: Excludes soft-deleted transfers.
        """
        last_seen = last_seen_map.get('transfers', default_last_seen)
        return await db.transfers.count_documents({
            "status": "SUBMITTED",
            "created_at": {"$gt": last_seen},
            "$or": [{"is_deleted": {"$exists": False}}, {"is_deleted": False}]
        })
    
    async def get_tickets_new():
        """Count tickets with new client activity since last seen.
        
        PERFORMANCE OPTIMIZED: Uses simple count on tickets collection
        instead of expensive aggregation with $lookup.
        Counts tickets where:
        - Status is OPEN/IN_PROGRESS
        - Updated after last_seen (indicates new activity)
        """
        last_seen = last_seen_map.get('tickets', default_last_seen)
        
        # Simple and fast: count open/in-progress tickets updated after last_seen
        return await db.tickets.count_documents({
            "status": {"$in": ["OPEN", "IN_PROGRESS", "open", "in_progress"]},
            "updated_at": {"$gt": last_seen}
        })
    
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
    """Admin soft-deletes a transfer (any status).
    
    SOFT DELETE: Transfer record is NOT physically removed from the database.
    Instead, it is marked as deleted with metadata for auditability:
    - is_deleted: True
    - deleted_at: UTC timestamp
    - deleted_by: Admin user ID
    - deleted_by_email: Admin email
    - previous_status: Status before deletion (for audit trail)
    
    The transfer will be excluded from normal queries but can be found with
    explicit include_deleted=true flag if needed for investigation.
    """
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
    
    # Check if already soft-deleted (idempotent behavior)
    if transfer.get("is_deleted", False):
        return {
            "ok": True, 
            "message": "Transfer already deleted",
            "already_deleted": True
        }
    
    transfer_status = transfer.get("status", "UNKNOWN")
    transfer_amount = transfer.get("amount", 0)
    beneficiary = transfer.get("beneficiary_name", "Unknown")
    
    # SOFT DELETE: Update transfer with deletion metadata instead of removing
    soft_delete_result = await db.transfers.update_one(
        {"_id": transfer["_id"]},
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc),
                "deleted_by": current_user["id"],
                "deleted_by_email": current_user["email"],
                "previous_status": transfer_status  # Preserve status for audit trail
            }
        }
    )
    
    if soft_delete_result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete transfer")
    
    # Audit log - updated to reflect soft delete
    await create_audit_log(
        db=db,
        action="TRANSFER_SOFT_DELETED",
        entity_type="transfer",
        entity_id=str(transfer["_id"]),
        description=f"Transfer to {beneficiary} (€{transfer_amount/100:.2f}) soft-deleted. Previous status: {transfer_status}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "previous_status": transfer_status,
            "amount": transfer_amount,
            "beneficiary": beneficiary,
            "soft_delete": True
        }
    )
    
    logger.info(f"Transfer {transfer_id} soft-deleted by admin {current_user['email']} (previous status: {transfer_status})")
    
    return {"ok": True, "message": "Transfer deleted successfully"}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)

