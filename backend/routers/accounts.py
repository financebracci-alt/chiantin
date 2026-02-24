"""
Accounts Router - User accounts, transactions, and admin ledger operations.

Handles all account operations including:
- User account creation and listing
- Transaction history and statements
- Admin ledger operations (top-up, withdraw, fee, reverse, transfer)
- Admin accounts management

Routes: 
- /api/v1/accounts/* (user)
- /api/v1/admin/ledger/* (admin)
- /api/v1/admin/accounts/* (admin)

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from io import BytesIO
import uuid
import logging

from database import get_database
from services.ledger_service import LedgerEngine
from services.banking_service import BankingService
from services.statement_service import StatementService
from schemas.banking import AccountResponse
from utils.common import serialize_doc
from .dependencies import get_current_user, require_admin, create_audit_log

logger = logging.getLogger(__name__)


# ==================== REQUEST SCHEMAS ====================

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


class ReversalRequest(BaseModel):
    transaction_id: str
    reason: str


class InternalTransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: int
    reason: str


class AdminTopUpRequest(BaseModel):
    amount_cents: int
    description: str


class AdminWithdrawRequest(BaseModel):
    amount_cents: int
    description: str


# User accounts router
router = APIRouter(prefix="/api/v1", tags=["accounts"])

# Admin ledger router
admin_ledger_router = APIRouter(prefix="/api/v1/admin/ledger", tags=["admin-ledger"])

# Admin accounts router  
admin_accounts_router = APIRouter(prefix="/api/v1/admin", tags=["admin-accounts"])


# ==================== USER ACCOUNT ENDPOINTS ====================

@router.post("/accounts/create", response_model=AccountResponse)
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
        iban=account.iban,
        currency=account.currency,
        status=account.status,
        balance=balance,
        opened_at=account.opened_at
    )


@router.get("/accounts", response_model=List[AccountResponse])
async def get_accounts(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all user accounts."""
    ledger_engine = LedgerEngine(db)
    banking_service = BankingService(db, ledger_engine)
    accounts = await banking_service.get_user_accounts(current_user["id"])
    return accounts


@router.get("/accounts/{account_id}/transactions")
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
    return transactions


@router.get("/accounts/{account_id}/statement/{year}/{month}")
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


# ==================== ADMIN LEDGER ENDPOINTS ====================

@admin_ledger_router.post("/top-up")
async def admin_top_up(
    data: TopUpRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Top up user account (admin)."""
    account = await db.bank_accounts.find_one({"_id": data.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    ledger_engine = LedgerEngine(db)
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


@admin_ledger_router.post("/withdraw")
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


@admin_ledger_router.post("/charge-fee")
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


@admin_ledger_router.post("/reverse")
async def admin_reverse_transaction(
    data: ReversalRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Reverse a posted transaction (admin)."""
    ledger_engine = LedgerEngine(db)
    txn = await ledger_engine.reverse_transaction(
        original_txn_id=data.transaction_id,
        external_id=f"admin_reversal_{uuid.uuid4()}",
        reason=data.reason,
        performed_by=current_user["id"]
    )
    
    return txn.model_dump()


@admin_ledger_router.post("/internal-transfer")
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
    txn = await ledger_engine.post_transaction(
        transaction_type="TRANSFER",
        entries=[
            {
                "account_id": from_account["ledger_account_id"],
                "amount": data.amount,
                "direction": "DEBIT"
            },
            {
                "account_id": to_account["ledger_account_id"],
                "amount": data.amount,
                "direction": "CREDIT"
            }
        ],
        external_id=f"admin_transfer_{uuid.uuid4()}",
        description=data.reason
    )
    
    # Audit: Internal transfer
    await create_audit_log(
        db=db,
        action="LEDGER_INTERNAL_TRANSFER",
        entity_type="ledger",
        entity_id=data.from_account_id,
        description=f"Admin internal transfer: €{data.amount/100:.2f} from {from_account.get('iban')} to {to_account.get('iban')}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "amount_cents": data.amount,
            "reason": data.reason,
            "from_iban": from_account.get("iban"),
            "to_iban": to_account.get("iban")
        }
    )
    
    return txn.model_dump()


# ==================== ADMIN ACCOUNTS MANAGEMENT ====================

@admin_accounts_router.get("/accounts-with-users")
async def admin_get_accounts_with_users(
    search: str = None,
    page: int = 1,
    page_size: int = 50,
    limit: int = None,  # Alias for page_size (frontend compatibility)
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Get all accounts with user information for search/selection.
    
    Used by admin panel for:
    - Account top-up
    - Account withdrawal
    - Account lookup
    
    Query params:
    - search: Search term (matches IBAN, account number, user email, user name)
    - page: Page number (1-indexed)
    - page_size/limit: Items per page (20, 50, 100)
    """
    import re
    
    # Handle 'limit' param as alias for 'page_size' (frontend compatibility)
    if limit is not None:
        page_size = limit
    
    # Validate page_size
    valid_page_sizes = [20, 50, 100]
    if page_size not in valid_page_sizes:
        page_size = 50
    
    # Build account query
    account_query = {}
    user_ids_from_search = []
    
    if search:
        search = search.strip()
        search_regex = {"$regex": re.escape(search), "$options": "i"}
        
        # First search users
        user_query = {
            "$or": [
                {"email": search_regex},
                {"first_name": search_regex},
                {"last_name": search_regex}
            ]
        }
        users_cursor = db.users.find(user_query, {"_id": 1})
        async for u in users_cursor:
            user_ids_from_search.append(str(u["_id"]))
        
        # Account search conditions
        account_conditions = [
            {"iban": search_regex},
            {"account_number": search_regex}
        ]
        
        if user_ids_from_search:
            account_conditions.append({"user_id": {"$in": user_ids_from_search}})
        
        account_query = {"$or": account_conditions}
    
    # Get total count
    total_count = await db.bank_accounts.count_documents(account_query)
    
    # Calculate pagination
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    if page < 1:
        page = 1
    
    skip = (page - 1) * page_size
    
    # Fetch accounts
    cursor = db.bank_accounts.find(account_query).sort("opened_at", -1).skip(skip).limit(page_size)
    account_docs = await cursor.to_list(length=page_size)
    
    # Collect user_ids for bulk lookup
    user_ids = set()
    ledger_account_ids = []
    for doc in account_docs:
        user_id = doc.get("user_id")
        if user_id:
            try:
                user_ids.add(ObjectId(user_id))
            except:
                user_ids.add(user_id)
        ledger_account_ids.append(doc.get("ledger_account_id"))
    
    # Bulk fetch users
    users_map = {}
    if user_ids:
        users_cursor = db.users.find({"_id": {"$in": list(user_ids)}})
        async for user in users_cursor:
            users_map[str(user["_id"])] = user
    
    # Fetch balances
    ledger_engine = LedgerEngine(db)
    balances = {}
    for ledger_id in ledger_account_ids:
        if ledger_id:
            try:
                balances[ledger_id] = await ledger_engine.get_balance(ledger_id)
            except:
                balances[ledger_id] = 0
    
    # Build response
    accounts = []
    for doc in account_docs:
        account_dict = serialize_doc(doc)
        
        user_id = doc.get("user_id")
        user = users_map.get(str(user_id)) if user_id else None
        
        if user:
            account_dict["user_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            account_dict["user_email"] = user.get("email", "")
        else:
            account_dict["user_name"] = "Unknown"
            account_dict["user_email"] = ""
        
        ledger_id = doc.get("ledger_account_id")
        account_dict["balance"] = balances.get(ledger_id, 0)
        
        accounts.append(account_dict)
    
    return {
        "ok": True,
        "data": accounts,
        "pagination": {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages
        }
    }


@admin_accounts_router.post("/accounts/{account_id}/topup")
async def admin_account_topup(
    account_id: str,
    data: AdminTopUpRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Top up a specific account."""
    account = await db.bank_accounts.find_one({"_id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    ledger_engine = LedgerEngine(db)
    txn = await ledger_engine.top_up(
        user_account_id=account["ledger_account_id"],
        amount=data.amount_cents,
        external_id=f"admin_topup_{uuid.uuid4()}",
        reason=data.description,
        performed_by=current_user["id"]
    )
    
    # Audit
    await create_audit_log(
        db=db,
        action="LEDGER_TOP_UP",
        entity_type="account",
        entity_id=account_id,
        description=f"Admin top-up: €{data.amount_cents/100:.2f} to {account.get('iban', account_id)}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"amount_cents": data.amount_cents, "description": data.description}
    )
    
    # Get new balance
    new_balance = await ledger_engine.get_balance(account["ledger_account_id"])
    
    return {
        "ok": True,
        "transaction": txn.model_dump(),
        "new_balance": new_balance
    }


@admin_accounts_router.post("/accounts/{account_id}/withdraw")
async def admin_account_withdraw(
    account_id: str,
    data: AdminWithdrawRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Withdraw from a specific account."""
    account = await db.bank_accounts.find_one({"_id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    ledger_engine = LedgerEngine(db)
    
    # Check balance
    current_balance = await ledger_engine.get_balance(account["ledger_account_id"])
    if current_balance < data.amount_cents:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Current: €{current_balance/100:.2f}")
    
    txn = await ledger_engine.withdraw(
        user_account_id=account["ledger_account_id"],
        amount=data.amount_cents,
        external_id=f"admin_withdraw_{uuid.uuid4()}",
        reason=data.description,
        performed_by=current_user["id"]
    )
    
    # Audit
    await create_audit_log(
        db=db,
        action="LEDGER_WITHDRAW",
        entity_type="account",
        entity_id=account_id,
        description=f"Admin withdrawal: €{data.amount_cents/100:.2f} from {account.get('iban', account_id)}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"amount_cents": data.amount_cents, "description": data.description}
    )
    
    # Get new balance
    new_balance = await ledger_engine.get_balance(account["ledger_account_id"])
    
    return {
        "ok": True,
        "transaction": txn.model_dump(),
        "new_balance": new_balance
    }
