"""
Admin Users Router.

Handles all admin user management operations including:
- User listing with search/pagination
- User details view
- User status management (enable/disable)
- Password management
- Tax hold management
- IBAN editing
- Notes management
- Session management
- User deletion

Routes: /api/v1/admin/users/*
"""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import logging
import re
import uuid

from database import get_database
from services.email_service import EmailService
from services.auth_service import AuthService
from services.notification_service import NotificationService
from schemas.notifications import NotificationType

from .dependencies import get_current_user, require_admin, create_audit_log, format_timestamp_utc

logger = logging.getLogger(__name__)

# Router definition
router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])


# ==================== Pydantic Models ====================

class UpdateNotes(BaseModel):
    notes: str

class UpdateStatus(BaseModel):
    status: str

class ChangePassword(BaseModel):
    new_password: str

class UpdateIban(BaseModel):
    iban: str
    bic: str

class SetTaxHold(BaseModel):
    tax_amount: float
    reason: str = "Outstanding tax obligations"
    beneficiary_name: Optional[str] = None
    iban: Optional[str] = None
    bic_swift: Optional[str] = None
    reference: Optional[str] = None
    crypto_wallet: Optional[str] = None


class AdminCreateUser(BaseModel):
    """Request model for admin creating a new user."""
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    password: str
    iban: str
    bic: str = "CFTEMTM1"  # Default BIC for Malta
    skip_kyc: bool = False  # If true, user won't need to do KYC


# ==================== Admin Create User ====================

@router.post("/create")
async def admin_create_user(
    user_data: AdminCreateUser,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new user as admin.
    
    This endpoint allows admins to create users directly with:
    - No email verification required (email_verified=true)
    - User status set to ACTIVE (can login immediately)
    - Bank account created with admin-provided IBAN
    - KYC status based on skip_kyc flag:
      - skip_kyc=true: KYC status set to APPROVED (no KYC needed)
      - skip_kyc=false: KYC status set to NONE (user must complete KYC)
    - No verification email sent
    """
    from core.auth import hash_password
    from services.ledger_service import LedgerEngine
    from core.ledger import AccountType
    from utils.common import generate_account_number
    
    # Validate email format
    email = user_data.email.lower().strip()
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="A user with this email already exists")
    
    # Validate password length
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Capitalize names properly
    first_name = user_data.first_name.strip().title()
    last_name = user_data.last_name.strip().title()
    
    # Create user document
    user_id = str(uuid.uuid4().hex[:24])  # Generate a 24-char ID
    user_doc = {
        "_id": user_id,
        "email": email,
        "phone": user_data.phone.strip() if user_data.phone else None,
        "password_hash": password_hash,
        "password_plain": user_data.password,  # Store for admin visibility
        "first_name": first_name,
        "last_name": last_name,
        "role": "CUSTOMER",
        "status": "ACTIVE",  # User can login immediately
        "email_verified": True,  # No verification needed
        "phone_verified": False,
        "mfa_enabled": False,
        "mfa_secret": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login_at": None,
        "admin_notes": f"Account created by admin on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    }
    
    # Insert user
    await db.users.insert_one(user_doc)
    logger.info(f"Admin created user: {email}")
    
    # Create ledger account
    ledger_engine = LedgerEngine(db)
    ledger_account = await ledger_engine.create_account(
        account_type=AccountType.WALLET,
        user_id=user_id
    )
    
    # Create bank account with admin-provided IBAN
    bank_account_id = f"bank_acc_{user_id}"
    bank_account_doc = {
        "_id": bank_account_id,
        "user_id": user_id,
        "account_number": generate_account_number(),
        "iban": user_data.iban.strip(),
        "bic": user_data.bic.strip(),
        "currency": "EUR",
        "status": "ACTIVE",
        "ledger_account_id": ledger_account.id,
        "opened_at": datetime.now(timezone.utc)
    }
    await db.bank_accounts.insert_one(bank_account_doc)
    logger.info(f"Bank account created for user {email} with IBAN: {user_data.iban}")
    
    # Handle KYC status
    if user_data.skip_kyc:
        # Create approved KYC application so user doesn't need to do KYC
        kyc_doc = {
            "_id": str(uuid.uuid4().hex[:24]),
            "user_id": user_id,
            "status": "APPROVED",
            "submitted_at": datetime.now(timezone.utc),
            "reviewed_at": datetime.now(timezone.utc),
            "reviewed_by": current_user["id"],
            "admin_notes": "KYC auto-approved - account created by admin",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        await db.kyc_applications.insert_one(kyc_doc)
        logger.info(f"KYC auto-approved for admin-created user: {email}")
    
    # Audit log
    await create_audit_log(
        db=db,
        action="ADMIN_USER_CREATED",
        entity_type="user",
        entity_id=user_id,
        description=f"Admin created new user: {email}",
        performed_by=current_user["id"],
        performed_by_role=current_user.get("role", "ADMIN"),
        performed_by_email=current_user["email"],
        metadata={
            "new_user_email": email,
            "new_user_name": f"{first_name} {last_name}",
            "iban": user_data.iban,
            "skip_kyc": user_data.skip_kyc
        }
    )
    
    return {
        "success": True,
        "message": f"User {email} created successfully",
        "user": {
            "id": user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "status": "ACTIVE",
            "iban": user_data.iban,
            "kyc_status": "APPROVED" if user_data.skip_kyc else "NONE"
        }
    }


# ==================== User Listing & Search ====================

@router.get("")
async def get_all_users(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    """Get users (admin) with pagination, tax hold status and notes.
    
    Supports:
    - search: Filter by name, email, or phone number (searches ALL users in DB, not just current page)
    - page: Page number (1-indexed)
    - limit: Users per page (20, 50, or 100)
    
    When search is provided, pagination is ignored and ALL matching users are returned.
    """
    # Validate limit
    if limit not in [20, 50, 100]:
        limit = 50
    
    # Build query - if search provided, filter by name, email, or phone
    query = {}
    if search and search.strip():
        search_term = search.strip()
        escaped_term = re.escape(search_term)
        digits_only = ''.join(c for c in search_term if c.isdigit())
        
        or_conditions = [
            {"first_name": {"$regex": escaped_term, "$options": "i"}},
            {"last_name": {"$regex": escaped_term, "$options": "i"}},
            {"email": {"$regex": escaped_term, "$options": "i"}},
            {"phone": {"$regex": escaped_term, "$options": "i"}}
        ]
        
        if len(digits_only) >= 4:
            or_conditions.append({"phone": {"$regex": digits_only, "$options": "i"}})
        
        query = {"$or": or_conditions}
    
    total_count = await db.users.count_documents(query)
    
    if search and search.strip():
        cursor = db.users.find(query).sort("created_at", -1)
    else:
        skip = (page - 1) * limit
        cursor = db.users.find(query).sort("created_at", -1).skip(skip).limit(limit)
    
    user_docs = await cursor.to_list(length=limit if not (search and search.strip()) else 1000)
    
    # PERFORMANCE: Only lookup tax holds for users on THIS page
    user_ids = [str(doc["_id"]) for doc in user_docs]
    tax_hold_user_ids = set()
    if user_ids:
        tax_holds_cursor = db.tax_holds.find({
            "user_id": {"$in": user_ids},
            "is_active": True
        }, {"user_id": 1})
        async for hold in tax_holds_cursor:
            tax_hold_user_ids.add(hold["user_id"])
    
    users = []
    for doc in user_docs:
        user_id = str(doc["_id"])
        users.append({
            "id": user_id,
            "email": doc["email"],
            "first_name": doc["first_name"],
            "last_name": doc["last_name"],
            "phone": doc.get("phone"),
            "role": doc["role"],
            "status": doc["status"],
            "created_at": format_timestamp_utc(doc["created_at"]),
            "has_tax_hold": user_id in tax_hold_user_ids,
            "admin_notes": doc.get("admin_notes", "")
        })
    
    total_pages = (total_count + limit - 1) // limit if not (search and search.strip()) else 1
    
    return {
        "users": users,
        "pagination": {
            "page": 1 if (search and search.strip()) else page,
            "limit": limit,
            "total_users": total_count,
            "total_pages": total_pages,
            "has_next": False if (search and search.strip()) else page < total_pages,
            "has_prev": False if (search and search.strip()) else page > 1
        }
    }


@router.get("/search-for-ticket")
async def search_users_for_ticket(
    email: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Search for a user by email when creating a ticket (admin)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    if not email or not email.strip():
        return {"users": []}
    
    email_lower = email.strip().lower()
    users = []
    cursor = db.users.find({
        "email": {"$regex": re.escape(email_lower), "$options": "i"}
    }).limit(10)
    
    async for doc in cursor:
        users.append({
            "id": str(doc["_id"]),
            "email": doc["email"],
            "first_name": doc.get("first_name", ""),
            "last_name": doc.get("last_name", "")
        })
    
    return {"users": users}


# ==================== User Details ====================

@router.get("/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get detailed user info (admin)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user_doc = await db.users.find_one(user_query)
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user_doc["_id"])
    accounts = []
    async for acc in db.bank_accounts.find({"user_id": actual_user_id}):
        ledger_id = acc.get("ledger_account_id")
        balance = 0
        if ledger_id:
            pipeline = [
                {"$match": {"account_id": ledger_id}},
                {"$group": {
                    "_id": None,
                    "total_credit": {"$sum": {"$cond": [{"$eq": ["$direction", "CREDIT"]}, "$amount", 0]}},
                    "total_debit": {"$sum": {"$cond": [{"$eq": ["$direction", "DEBIT"]}, "$amount", 0]}}
                }}
            ]
            result = await db.ledger_entries.aggregate(pipeline).to_list(1)
            if result:
                balance = result[0]["total_credit"] - result[0]["total_debit"]
        
        accounts.append({
            "id": str(acc["_id"]),
            "account_number": acc.get("account_number"),
            "iban": acc.get("iban"),
            "bic": acc.get("bic"),
            "currency": acc.get("currency", "EUR"),
            "balance": balance,
            "ledger_account_id": ledger_id
        })
    
    kyc_app = await db.kyc_applications.find_one({"user_id": actual_user_id})
    kyc_status = kyc_app.get("status") if kyc_app else "NOT_STARTED"
    
    return {
        "user": {
            "id": actual_user_id,
            "email": user_doc["email"],
            "first_name": user_doc["first_name"],
            "last_name": user_doc["last_name"],
            "phone": user_doc.get("phone"),
            "role": user_doc["role"],
            "status": user_doc["status"],
            "email_verified": user_doc.get("email_verified", False),
            "created_at": format_timestamp_utc(user_doc["created_at"]),
            "password_plain": user_doc.get("password_plain"),
            "admin_notes": user_doc.get("admin_notes", "")
        },
        "kyc_status": kyc_status,
        "accounts": accounts
    }


# ==================== User Notes ====================

@router.patch("/{user_id}/notes")
async def update_user_notes(
    user_id: str,
    data: UpdateNotes,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update admin notes for a user."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_notes = user.get("admin_notes", "")
    
    result = await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"admin_notes": data.notes}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update notes")
    
    logger.info(f"Admin {current_user['email']} updated notes for user {user['email']}")
    
    await create_audit_log(
        db=db,
        action="USER_NOTES_UPDATED",
        entity_type="user",
        entity_id=str(user["_id"]),
        description=f"Admin notes updated for user {user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "old_notes_preview": old_notes[:100] if old_notes else "",
            "new_notes_preview": data.notes[:100] if data.notes else ""
        }
    )
    
    return {"success": True, "message": "Notes updated successfully"}


# ==================== User Status ====================

@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: str,
    data: UpdateStatus,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update user status (admin)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    if data.status not in ["ACTIVE", "PENDING", "DISABLED"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    result = await db.users.update_one(user_query, {"$set": {"status": data.status}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True}


# ==================== Email Verification ====================

@router.post("/{user_id}/verify-email")
async def admin_verify_user_email(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin manually verifies a user's email address."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("email_verified"):
        return {"success": True, "message": "Email already verified"}
    
    result = await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "email_verified": True,
                "email_verified_at": datetime.now(timezone.utc)
            },
            "$unset": {"verification_token": ""}
        }
    )
    
    logger.warning(f"ADMIN EMAIL VERIFY: Admin {current_user['email']} manually verified email for user {user['email']}")
    
    await create_audit_log(
        db=db,
        action="USER_EMAIL_VERIFIED_BY_ADMIN",
        entity_type="user",
        entity_id=str(user["_id"]),
        description=f"Admin manually verified email for user {user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"]
    )
    
    return {"success": True, "message": "Email verified successfully"}


# ==================== Password Management ====================

@router.post("/{user_id}/change-password")
async def admin_change_user_password(
    user_id: str,
    data: ChangePassword,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin changes a user's password."""
    from bson import ObjectId
    from bson.errors import InvalidId
    import bcrypt
    
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash the new password
    hashed_password = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
    
    result = await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "hashed_password": hashed_password,
                "password_plain": data.new_password,
                "password_changed_at": datetime.now(timezone.utc),
                "password_changed_by": current_user["id"]
            }
        }
    )
    
    logger.warning(f"ADMIN PASSWORD CHANGE: Admin {current_user['email']} changed password for user {user['email']}")
    
    await create_audit_log(
        db=db,
        action="USER_PASSWORD_CHANGED_BY_ADMIN",
        entity_type="user",
        entity_id=str(user["_id"]),
        description=f"Admin changed password for user {user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"]
    )
    
    return {"success": True, "message": "Password changed successfully"}


# ==================== Auth History ====================

@router.get("/{user_id}/auth-history")
async def get_user_auth_history(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's authentication/login history (admin).
    
    Queries from audit_logs collection for auth-related events.
    NOTE: After refactor, login events are stored in audit_logs (not auth_events).
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user["_id"])
    user_email = user.get("email", "")
    
    # Query audit_logs for auth-related events for this user
    # Match by performed_by (user's own actions) or entity_id (when admin acts on user)
    auth_actions = [
        "USER_LOGIN_SUCCESS", "ADMIN_LOGIN_SUCCESS", 
        "USER_LOGOUT", "ADMIN_LOGOUT",
        "LOGIN_FAILED", "MFA_ENABLED", "MFA_DISABLED",
        "PASSWORD_CHANGED", "PASSWORD_RESET"
    ]
    
    events = []
    cursor = db.audit_logs.find({
        "$and": [
            {"action": {"$in": auth_actions}},
            {"$or": [
                {"performed_by": actual_user_id},
                {"performed_by_email": user_email},
                {"entity_id": actual_user_id}
            ]}
        ]
    }).sort("created_at", -1).limit(50)
    
    async for event in cursor:
        events.append({
            "id": str(event["_id"]),
            "action": event.get("action", "UNKNOWN"),
            "description": event.get("description", ""),
            "ip_address": event.get("metadata", {}).get("ip_address", "N/A"),
            "user_agent": event.get("metadata", {}).get("user_agent", ""),
            "source": event.get("metadata", {}).get("source", ""),
            "actor_email": event.get("performed_by_email"),
            "created_at": format_timestamp_utc(event.get("created_at"))
        })
    
    return {"events": events}


# ==================== User Deletion ====================

@router.delete("/{user_id}/permanent")
async def delete_user_permanently(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Permanently delete a user and ALL their data."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("role") in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Cannot delete admin users. Demote first.")
    
    actual_user_id = str(user["_id"])
    user_email = user.get("email", "unknown")
    
    deleted_data = {"user_email": user_email, "deleted_items": {}}
    
    # Delete in order of dependencies
    accounts = await db.bank_accounts.find({"user_id": actual_user_id}).to_list(100)
    for acc in accounts:
        ledger_id = acc.get("ledger_account_id")
        if ledger_id:
            ledger_result = await db.ledger_entries.delete_many({"account_id": ledger_id})
            deleted_data["deleted_items"]["ledger_entries"] = deleted_data["deleted_items"].get("ledger_entries", 0) + ledger_result.deleted_count
    
    acc_result = await db.bank_accounts.delete_many({"user_id": actual_user_id})
    deleted_data["deleted_items"]["bank_accounts"] = acc_result.deleted_count
    
    kyc_result = await db.kyc_applications.delete_many({"user_id": actual_user_id})
    deleted_data["deleted_items"]["kyc_applications"] = kyc_result.deleted_count
    
    tickets_result = await db.tickets.delete_many({"user_id": actual_user_id})
    deleted_data["deleted_items"]["tickets"] = tickets_result.deleted_count
    
    transfers_result = await db.transfers.delete_many({"user_id": actual_user_id})
    deleted_data["deleted_items"]["transfers"] = transfers_result.deleted_count
    
    notif_result = await db.notifications.delete_many({"user_id": actual_user_id})
    deleted_data["deleted_items"]["notifications"] = notif_result.deleted_count
    
    tax_result = await db.tax_holds.delete_many({"user_id": actual_user_id})
    deleted_data["deleted_items"]["tax_holds"] = tax_result.deleted_count
    
    user_result = await db.users.delete_one({"_id": user["_id"]})
    deleted_data["deleted_items"]["user"] = user_result.deleted_count
    
    logger.warning(f"USER DELETED: Admin {current_user['email']} permanently deleted user {user_email}. Items deleted: {deleted_data['deleted_items']}")
    
    await create_audit_log(
        db=db,
        action="USER_PERMANENTLY_DELETED",
        entity_type="user",
        entity_id=actual_user_id,
        description=f"User {user_email} was permanently deleted",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata=deleted_data
    )
    
    return {
        "success": True,
        "deleted": True,
        "message": f"User {user_email} has been permanently deleted",
        "deleted_items": deleted_data["deleted_items"]
    }


# ==================== Demote Admin ====================

@router.post("/{user_id}/demote")
async def demote_admin_to_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Demote an admin user to regular USER role."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("role") not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=400, detail="User is not an admin")
    
    if str(user["_id"]) == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")
    
    old_role = user.get("role")
    
    result = await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"role": "CUSTOMER"}}
    )
    
    logger.warning(f"ADMIN DEMOTED: Admin {current_user['email']} demoted user {user['email']} from {old_role} to CUSTOMER")
    
    await create_audit_log(
        db=db,
        action="ADMIN_DEMOTED",
        entity_type="user",
        entity_id=str(user["_id"]),
        description=f"User {user['email']} demoted from {old_role} to CUSTOMER",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"old_role": old_role, "new_role": "CUSTOMER"}
    )
    
    return {
        "success": True,
        "message": f"User {user['email']} has been demoted from {old_role} to CUSTOMER"
    }


# ==================== IBAN Management ====================

@router.patch("/{user_id}/account-iban")
async def update_user_account_iban(
    user_id: str,
    data: UpdateIban,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update the IBAN and BIC for a user's bank account."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user["_id"])
    
    account = await db.bank_accounts.find_one({"user_id": actual_user_id})
    if not account:
        raise HTTPException(status_code=404, detail="User has no bank account")
    
    old_iban = account.get("iban", "Not set")
    old_bic = account.get("bic", "Not set")
    
    result = await db.bank_accounts.update_one(
        {"_id": account["_id"]},
        {"$set": {
            "iban": data.iban.upper(),
            "bic": data.bic.upper(),
            "iban_updated_at": datetime.now(timezone.utc),
            "iban_updated_by": current_user["id"]
        }}
    )
    
    logger.warning(f"IBAN UPDATE: Admin {current_user['email']} changed IBAN for user {user['email']} from {old_iban} to {data.iban.upper()}")
    
    await create_audit_log(
        db=db,
        action="IBAN_BIC_UPDATED",
        entity_type="bank_account",
        entity_id=str(account["_id"]),
        description=f"IBAN/BIC updated for user {user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "user_email": user["email"],
            "old_iban": old_iban,
            "new_iban": data.iban.upper(),
            "old_bic": old_bic,
            "new_bic": data.bic.upper()
        }
    )
    
    return {"success": True, "message": "IBAN and BIC updated successfully"}


# ==================== Tax Hold Management ====================

@router.post("/{user_id}/tax-hold")
async def set_user_tax_hold(
    user_id: str,
    data: SetTaxHold,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Place a tax hold on a user's account."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user["_id"])
    
    existing = await db.tax_holds.find_one({"user_id": actual_user_id, "is_active": True})
    if existing:
        await db.tax_holds.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "tax_amount_cents": int(data.tax_amount * 100),
                "reason": data.reason,
                "beneficiary_name": data.beneficiary_name,
                "iban": data.iban,
                "bic_swift": data.bic_swift,
                "reference": data.reference,
                "crypto_wallet": data.crypto_wallet,
                "updated_at": datetime.now(timezone.utc),
                "updated_by": current_user["id"]
            }}
        )
        action = "TAX_HOLD_UPDATED"
        message = "Tax hold updated successfully"
    else:
        tax_hold_doc = {
            "_id": str(uuid.uuid4()),
            "user_id": actual_user_id,
            "is_active": True,
            "tax_amount_cents": int(data.tax_amount * 100),
            "reason": data.reason,
            "beneficiary_name": data.beneficiary_name,
            "iban": data.iban,
            "bic_swift": data.bic_swift,
            "reference": data.reference,
            "crypto_wallet": data.crypto_wallet,
            "blocked_at": datetime.now(timezone.utc),
            "blocked_by": current_user["id"],
            "created_at": datetime.now(timezone.utc)
        }
        await db.tax_holds.insert_one(tax_hold_doc)
        action = "TAX_HOLD_PLACED"
        message = "Tax hold placed successfully"
    
    logger.warning(f"TAX HOLD: Admin {current_user['email']} {action.lower().replace('_', ' ')} on user {user['email']}, amount: €{data.tax_amount}")
    
    await create_audit_log(
        db=db,
        action=action,
        entity_type="user",
        entity_id=actual_user_id,
        description=f"{action.replace('_', ' ').title()} on user {user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "user_email": user["email"],
            "tax_amount": data.tax_amount,
            "reason": data.reason
        }
    )
    
    # Create notification for the client about the tax hold
    notification_service = NotificationService(db)
    if action == "TAX_HOLD_PLACED":
        await notification_service.create_notification(
            user_id=actual_user_id,
            notification_type=NotificationType.ACCOUNT,
            title="Account Restricted",
            message=f"Your account has been restricted due to: {data.reason}. Tax amount due: €{data.tax_amount:,.2f}. Please contact support for assistance.",
            action_url="/support",
            metadata={
                "type": "tax_hold",
                "tax_amount": data.tax_amount,
                "reason": data.reason
            }
        )
    elif action == "TAX_HOLD_UPDATED":
        await notification_service.create_notification(
            user_id=actual_user_id,
            notification_type=NotificationType.ACCOUNT,
            title="Tax Hold Updated",
            message=f"Your tax hold has been updated. New amount due: €{data.tax_amount:,.2f}.",
            action_url="/support",
            metadata={
                "type": "tax_hold_update",
                "tax_amount": data.tax_amount,
                "reason": data.reason
            }
        )
    
    return {"success": True, "message": message}


@router.delete("/{user_id}/tax-hold")
async def remove_user_tax_hold(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Remove a tax hold from a user's account."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user["_id"])
    
    existing = await db.tax_holds.find_one({"user_id": actual_user_id, "is_active": True})
    if not existing:
        return {"success": True, "message": "No active tax hold found"}
    
    await db.tax_holds.update_one(
        {"_id": existing["_id"]},
        {"$set": {
            "is_active": False,
            "removed_at": datetime.now(timezone.utc),
            "removed_by": current_user["id"]
        }}
    )
    
    logger.warning(f"TAX HOLD REMOVED: Admin {current_user['email']} removed tax hold from user {user['email']}")
    
    await create_audit_log(
        db=db,
        action="TAX_HOLD_REMOVED",
        entity_type="user",
        entity_id=actual_user_id,
        description=f"Tax hold removed from user {user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"user_email": user["email"]}
    )
    
    # Notify client that restriction is removed
    notification_service = NotificationService(db)
    await notification_service.create_notification(
        user_id=actual_user_id,
        notification_type=NotificationType.ACCOUNT,
        title="Account Restriction Lifted",
        message="Your account restriction has been removed. You can now perform all banking operations.",
        action_url="/dashboard",
        metadata={
            "type": "tax_hold_removed"
        }
    )
    
    return {"success": True, "message": "Tax hold removed successfully"}


@router.get("/{user_id}/tax-hold")
async def get_user_tax_hold(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get tax hold status for a user."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user["_id"])
    
    tax_hold = await db.tax_holds.find_one({"user_id": actual_user_id, "is_active": True})
    
    if not tax_hold:
        return {
            "is_blocked": False,
            "tax_amount_due": 0,
            "reason": None,
            "beneficiary_name": None,
            "iban": None,
            "bic_swift": None,
            "reference": None,
            "crypto_wallet": None
        }
    
    # Support both old format (nested payment_details) and new format (top-level fields)
    payment_details = tax_hold.get("payment_details", {}) or {}
    
    # Read from top-level first, fall back to nested payment_details
    beneficiary_name = tax_hold.get("beneficiary_name") or payment_details.get("beneficiary_name")
    iban = tax_hold.get("iban") or payment_details.get("iban")
    bic_swift = tax_hold.get("bic_swift") or payment_details.get("bic_swift")
    reference = tax_hold.get("reference") or payment_details.get("reference")
    crypto_wallet = tax_hold.get("crypto_wallet") or payment_details.get("crypto_wallet")
    
    return {
        "is_blocked": True,
        "tax_amount_due": (tax_hold.get("tax_amount_cents", 0) or 0) / 100,
        "reason": tax_hold.get("reason"),
        "blocked_at": format_timestamp_utc(tax_hold.get("blocked_at")),
        "beneficiary_name": beneficiary_name,
        "iban": iban,
        "bic_swift": bic_swift.strip() if bic_swift else None,  # Clean trailing spaces
        "reference": reference,
        "crypto_wallet": crypto_wallet
    }


# ==================== Notifications Management ====================

@router.delete("/{user_id}/notifications")
async def clear_user_notifications(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Clear all notifications for a user (admin)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    actual_user_id = str(user["_id"])
    
    result = await db.notifications.delete_many({"user_id": actual_user_id})
    
    logger.info(f"Admin {current_user['email']} cleared {result.deleted_count} notifications for user {user['email']}")
    
    await create_audit_log(
        db=db,
        action="USER_NOTIFICATIONS_CLEARED",
        entity_type="user",
        entity_id=actual_user_id,
        description=f"Cleared {result.deleted_count} notifications for user {user['email']}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"cleared_count": result.deleted_count}
    )
    
    return {"success": True, "deleted_count": result.deleted_count}


# ==================== Session Management ====================

@router.post("/{user_id}/revoke-sessions")
async def revoke_user_sessions(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Revoke all active sessions for a user (force logout everywhere)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"sessions_revoked_at": datetime.now(timezone.utc)}}
    )
    
    logger.warning(f"SESSION REVOKE: Admin {current_user['email']} revoked all sessions for user {user['email']}")
    
    return {"success": True, "message": "All sessions revoked"}


# ==================== Password Reset ====================

@router.post("/{user_id}/reset-password")
async def admin_reset_user_password(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin forces a password reset for a user (generates temporary password)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    import bcrypt
    import secrets
    import string
    
    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass
    
    user_doc = await db.users.find_one(user_query)
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    hashed_password = bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt()).decode()
    
    await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {
            "hashed_password": hashed_password,
            "password_plain": temp_password,
            "must_change_password": True,
            "password_reset_at": datetime.now(timezone.utc),
            "password_reset_by": current_user["id"]
        }}
    )
    
    logger.warning(f"ADMIN PASSWORD RESET: Admin {current_user['email']} reset password for user {user_doc['email']}")
    
    # Try to send email
    try:
        email_service = EmailService()
        await email_service.send_password_reset_email(
            to_email=user_doc["email"],
            temp_password=temp_password,
            reset_by_admin=True
        )
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
    
    await db.audit_logs.insert_one({
        "_id": str(uuid.uuid4()),
        "action": "ADMIN_PASSWORD_RESET",
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



class DomainChangeRequest(BaseModel):
    new_domain: str


@router.post("/send-domain-change-all")
async def send_domain_change_to_all(
    data: DomainChangeRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Send domain change notification email to all non-admin users."""
    users = await db.users.find({"role": {"$nin": ["ADMIN", "SUPER_ADMIN"]}}).to_list(length=10000)
    new_domain = data.new_domain.strip().replace("https://", "").replace("http://", "").rstrip("/")

    email_service = EmailService()
    sent = 0
    failed = 0

    for user_doc in users:
        email = user_doc.get("email")
        if not email:
            continue
        success = email_service.send_domain_change_email(
            to_email=email,
            first_name=user_doc.get("first_name", ""),
            new_domain=new_domain,
            language=user_doc.get("language", "en")
        )
        if success:
            sent += 1
        else:
            failed += 1

    logger.info(f"DOMAIN CHANGE NOTIFICATION: Admin {current_user['email']} sent to all users. Sent: {sent}, Failed: {failed}")

    await create_audit_log(
        db=db,
        action="DOMAIN_CHANGE_NOTIFICATION_ALL",
        entity_type="system",
        entity_id="all_users",
        description=f"Domain change notification sent to all users. New domain: {new_domain}. Sent: {sent}, Failed: {failed}",
        performed_by=current_user["id"],
        performed_by_role=current_user.get("role", "ADMIN"),
        performed_by_email=current_user["email"],
        metadata={"new_domain": new_domain, "sent": sent, "failed": failed, "total": len(users)}
    )

    return {
        "success": True,
        "message": f"Domain change emails sent: {sent} successful, {failed} failed",
        "sent": sent,
        "failed": failed,
        "total": len(users)
    }


@router.post("/{user_id}/send-domain-change")
async def send_domain_change_to_user(
    user_id: str,
    data: DomainChangeRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Send domain change notification email to a single user."""
    from bson import ObjectId
    from bson.errors import InvalidId

    user_query = {"_id": user_id}
    try:
        user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(user_id)}]}
    except InvalidId:
        pass

    user_doc = await db.users.find_one(user_query)
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    email_service = EmailService()
    new_domain = data.new_domain.strip().replace("https://", "").replace("http://", "").rstrip("/")
    success = email_service.send_domain_change_email(
        to_email=user_doc["email"],
        first_name=user_doc.get("first_name", ""),
        new_domain=new_domain,
        language=user_doc.get("language", "en")
    )

    if success:
        logger.info(f"DOMAIN CHANGE NOTIFICATION: Admin {current_user['email']} sent to {user_doc['email']}. New domain: {new_domain}")
        await create_audit_log(
            db=db,
            action="DOMAIN_CHANGE_NOTIFICATION_SINGLE",
            entity_type="user",
            entity_id=str(user_doc["_id"]),
            description=f"Domain change notification sent to {user_doc['email']}. New domain: {new_domain}",
            performed_by=current_user["id"],
            performed_by_role=current_user.get("role", "ADMIN"),
            performed_by_email=current_user["email"],
            metadata={"new_domain": new_domain, "target_email": user_doc["email"]}
        )
        return {"success": True, "message": f"Domain change email sent to {user_doc['email']}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")
