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
        logger.info("APPLICATION STARTUP - Chiantin Banking Platform")
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
    title="Chiantin API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Use allow_origin_regex to always reflect the specific origin
# This is required because allow_origins=["*"] returns literal "*" 
# which browsers reject when allow_credentials=True (withCredentials)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
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
from routers import users as users_router
app.include_router(users_router.router)
from routers import analytics as analytics_router
app.include_router(analytics_router.router)
from routers import notifications as notifications_router
app.include_router(notifications_router.router)
app.include_router(notifications_router.admin_router)
from routers import cards as cards_router
app.include_router(cards_router.router)
app.include_router(cards_router.admin_router)
from routers import accounts as accounts_router
app.include_router(accounts_router.router)
app.include_router(accounts_router.admin_ledger_router)
app.include_router(accounts_router.admin_accounts_router)
from routers import transfers as transfers_router
app.include_router(transfers_router.router)
app.include_router(transfers_router.admin_router)
app.include_router(transfers_router.admin_ledger_router)
from routers import recipients as recipients_router
app.include_router(recipients_router.router)
from routers import beneficiaries as beneficiaries_router
app.include_router(beneficiaries_router.router)
from routers import insights as insights_router
app.include_router(insights_router.router)
from routers import scheduled_payments as scheduled_payments_router
app.include_router(scheduled_payments_router.router)


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
# All auth endpoints moved to routers/auth.py
# See: routers/auth.py for: signup, login, logout, verify-email, resend-verification,
#      me, mfa/setup, mfa/enable, change-password, verify-password, 
#      forgot-password, reset-password
    
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


# ==================== EXTRACTED ROUTERS REFERENCE ====================
# The following endpoints have been moved to dedicated router modules:
#
# Analytics:     routers/analytics.py
#   - /api/v1/admin/analytics/overview
#   - /api/v1/admin/analytics/monthly
#
# Notifications: routers/notifications.py
#   - /api/v1/notifications/*
#   - /api/v1/admin/notifications/*
#   - /api/v1/admin/notification-counts
#
# Transfers:     routers/transfers.py
#   - /api/v1/transfers/*
#   - /api/v1/admin/transfers/*
#   - /api/v1/admin/ledger/internal-transfer
#
# Recipients:    routers/recipients.py
#   - /api/v1/recipients/*
#
# Beneficiaries: routers/beneficiaries.py
#   - /api/v1/beneficiaries/*
#
# Insights:      routers/insights.py
#   - /api/v1/insights/*
#
# Scheduled:     routers/scheduled_payments.py
#   - /api/v1/scheduled-payments/*
#
# Cards:         routers/cards.py
#   - /api/v1/card-requests/*
#   - /api/v1/cards/*
#   - /api/v1/admin/card-requests/*
# ====================


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


# Health check endpoint at root path for deployment health checks
@app.get("/health")
async def root_health_check():
    """Root health check endpoint for Kubernetes/deployment."""
    return {"status": "healthy", "app": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
