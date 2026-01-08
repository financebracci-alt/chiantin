"""Main FastAPI application for Project Atlas banking platform."""

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from contextlib import asynccontextmanager
from typing import Optional, List
import jwt
import logging

from config import settings
from database import connect_db, disconnect_db, get_database
from services.auth_service import AuthService
from services.kyc_service import KYCService
from services.banking_service import BankingService
from services.ledger_service import LedgerEngine
from schemas.users import UserCreate, UserLogin, TokenResponse, UserResponse, MFASetupResponse, MFAVerifyRequest
from schemas.kyc import KYCSubmitRequest, KYCReviewRequest, DocumentType
from schemas.banking import AccountResponse
from providers import LocalS3Storage
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="Project Atlas API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependencies
def get_storage() -> LocalS3Storage:
    return LocalS3Storage(base_path=settings.STORAGE_BASE_PATH)


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
        
        user_doc = await db.users.find_one({"_id": user_id})
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

@app.post("/api/v1/auth/signup", response_model=UserResponse, status_code=201)
async def signup(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Register a new user."""
    auth_service = AuthService(db)
    user = await auth_service.create_user(user_data)
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


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    response: Response,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Login with email and password."""
    auth_service = AuthService(db)
    
    # Authenticate
    user = await auth_service.authenticate_user(
        credentials.email,
        credentials.password
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check MFA
    if user.mfa_enabled:
        if not credentials.totp_token:
            raise HTTPException(status_code=401, detail="MFA token required")
        
        if not await auth_service.verify_totp(user, credentials.totp_token):
            raise HTTPException(status_code=401, detail="Invalid MFA token")
    
    # Create session
    access_token, refresh_token = await auth_service.create_session(
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
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


# ==================== KYC ====================

@app.get("/api/v1/kyc/application")
async def get_kyc_application(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: LocalS3Storage = Depends(get_storage)
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
    storage: LocalS3Storage = Depends(get_storage)
):
    """Upload KYC document."""
    kyc_service = KYCService(db, storage)
    doc = await kyc_service.upload_document(current_user["id"], file, document_type)
    return doc.model_dump()


@app.post("/api/v1/kyc/submit")
async def submit_kyc(
    data: KYCSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: LocalS3Storage = Depends(get_storage)
):
    """Submit KYC application for review."""
    kyc_service = KYCService(db, storage)
    app = await kyc_service.submit_application(current_user["id"], data)
    return app.model_dump()


@app.get("/api/v1/admin/kyc/pending")
async def get_pending_kyc(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: LocalS3Storage = Depends(get_storage)
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
    storage: LocalS3Storage = Depends(get_storage)
):
    """Review KYC application (admin)."""
    kyc_service = KYCService(db, storage)
    app = await kyc_service.review_application(application_id, review, current_user["id"])
    return app.model_dump()


# ==================== BANKING ====================

@app.post("/api/v1/accounts/create", response_model=AccountResponse)
async def create_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new bank account."""
    ledger_engine = LedgerEngine(db)
    banking_service = BankingService(db, ledger_engine)
    account = await banking_service.create_account(current_user["id"])
    
    balance = await ledger_engine.get_balance(account.ledger_account_id)
    
    return AccountResponse(
        id=account.id,
        account_number=account.account_number,
        iban=account.iban,
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
    """Get account transactions."""
    # Verify account belongs to user
    account_doc = await db.bank_accounts.find_one({"_id": account_id})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account_doc["user_id"] != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    ledger_engine = LedgerEngine(db)
    transactions = await ledger_engine.get_transactions(account_doc["ledger_account_id"])
    return [txn.model_dump() for txn in transactions]


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
    
    return txn.model_dump()


# ==================== ADMIN USER MANAGEMENT ====================

@app.get("/api/v1/admin/users")
async def get_all_users(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all users (admin)."""
    cursor = db.users.find({}).sort("created_at", -1).limit(100)
    users = []
    async for doc in cursor:
        users.append({
            "id": str(doc["_id"]),
            "email": doc["email"],
            "first_name": doc["first_name"],
            "last_name": doc["last_name"],
            "role": doc["role"],
            "status": doc["status"],
            "created_at": doc["created_at"].isoformat()
        })
    return users


@app.get("/api/v1/admin/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user details (admin)."""
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get accounts
    accounts_cursor = db.bank_accounts.find({"user_id": user_id})
    accounts = []
    ledger_engine = LedgerEngine(db)
    
    async for acc in accounts_cursor:
        balance = await ledger_engine.get_balance(acc["ledger_account_id"])
        accounts.append({
            "id": str(acc["_id"]),
            "account_number": acc["account_number"],
            "iban": acc.get("iban"),
            "balance": balance,
            "currency": acc["currency"],
            "status": acc["status"]
        })
    
    # Get KYC
    kyc = await db.kyc_applications.find_one({"user_id": user_id})
    
    return {
        "user": {
            "id": str(user_doc["_id"]),
            "email": user_doc["email"],
            "first_name": user_doc["first_name"],
            "last_name": user_doc["last_name"],
            "role": user_doc["role"],
            "status": user_doc["status"],
            "mfa_enabled": user_doc.get("mfa_enabled", False),
            "created_at": user_doc["created_at"].isoformat(),
            "last_login_at": user_doc.get("last_login_at").isoformat() if user_doc.get("last_login_at") else None
        },
        "accounts": accounts,
        "kyc_status": kyc["status"] if kyc else None
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
