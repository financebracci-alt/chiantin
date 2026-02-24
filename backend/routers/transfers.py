"""
Transfers Router - User and Admin transfer operations.

Handles all transfer operations including:
- User P2P transfers (via IBAN)
- User transfer creation and listing
- Admin transfer management (list, approve, reject, delete)
- Admin transfer email resend

Routes: 
- /api/v1/transfers/* (user)
- /api/v1/admin/transfers/* (admin)
- /api/v1/admin/ledger/internal-transfer (admin)

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.

CRITICAL PERFORMANCE NOTE: 
- The admin transfers endpoint uses BULK lookups (users_map, accounts_map)
- DO NOT replace with per-item loops - this would cause N+1 regression
- The _search_transfers method also uses bulk lookups

Transfer Restore Feature: EXPLICITLY DEFERRED - DO NOT IMPLEMENT
"""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
import uuid
import logging

from database import get_database
from services.ledger_service import LedgerEngine
from services.transfer_service import TransferService
from services.banking_workflows_service import BankingWorkflowsService
from services.email_service import EmailService
from schemas.transfers import P2PTransferRequest
from schemas.banking_workflows import CreateTransfer
from core.ledger import EntryDirection
from .dependencies import get_current_user, require_admin, create_audit_log

logger = logging.getLogger(__name__)


# ==================== REQUEST SCHEMAS ====================

class RejectTransferRequest(BaseModel):
    reason: str


class UpdateRejectReasonRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="New rejection reason")


class InternalTransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: int
    reason: str


# ==================== HELPER FUNCTIONS ====================

async def check_tax_hold(user_id: str, db: AsyncIOMotorDatabase):
    """Check if user has an active tax hold."""
    return await db.tax_holds.find_one({
        "user_id": user_id,
        "is_active": True
    })


# ==================== ROUTERS ====================

# User transfers router
router = APIRouter(prefix="/api/v1", tags=["transfers"])

# Admin transfers router
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin-transfers"])

# Admin ledger router (for internal transfer)
admin_ledger_router = APIRouter(prefix="/api/v1/admin/ledger", tags=["admin-ledger-transfers"])


# ==================== USER TRANSFER ENDPOINTS ====================

@router.post("/transfers/p2p")
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


@router.post("/transfers")
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


@router.get("/transfers")
async def get_transfers(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    "Get user's transfers."
    workflows = BankingWorkflowsService(db)
    transfers = await workflows.get_user_transfers(current_user["id"])
    return {"ok": True, "data": [t.model_dump() for t in transfers]}


@router.get("/transfers/{transfer_id}")
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


# ==================== ADMIN TRANSFER ENDPOINTS ====================

@admin_router.get("/transfers")
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
    - status: Filter by status (SUBMITTED, COMPLETED, REJECTED, DELETED)
    - page: Page number (1-indexed, default 1)
    - page_size: Items per page (20, 50, or 100, default 20)
    - search: Search term (searches beneficiary name, sender name/email, IBAN, reference across ALL statuses)
    
    Note: When status=DELETED, returns soft-deleted transfers only.
    """
    # Validate page_size
    valid_page_sizes = [20, 50, 100]
    if page_size not in valid_page_sizes:
        page_size = 20
    
    workflows = BankingWorkflowsService(db)
    
    # Handle DELETED tab specially - fetch soft-deleted transfers
    if status == "DELETED":
        result = await workflows.get_deleted_transfers(page, page_size, search)
    else:
        result = await workflows.get_admin_transfers(status, page, page_size, search)
    
    # Result now includes 'transfers' list and 'pagination' info
    return {"ok": True, "data": result["transfers"], "pagination": result["pagination"]}


@admin_router.post("/transfers/{transfer_id}/approve")
async def admin_approve_transfer(
    transfer_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin approves transfer."""
    workflows = BankingWorkflowsService(db)
    await workflows.approve_transfer(transfer_id, current_user["id"])
    return {"ok": True, "message": "Transfer approved"}


@admin_router.post("/transfers/{transfer_id}/reject")
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


@admin_router.patch("/transfers/{transfer_id}/reject-reason")
async def admin_update_reject_reason(
    transfer_id: str,
    data: UpdateRejectReasonRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin updates the rejection reason for a rejected transfer."""
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


@admin_router.delete("/transfers/{transfer_id}")
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
    
    NOTE: Transfer Restore Feature is EXPLICITLY DEFERRED - not implemented.
    """
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


class RestoreTransferRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Optional reason for restoring the transfer")


@admin_router.post("/transfers/{transfer_id}/restore")
async def admin_restore_transfer(
    transfer_id: str,
    data: RestoreTransferRequest = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin restores a soft-deleted transfer.
    
    RESTORE BEHAVIOR (IMPORTANT):
    - This ONLY restores the transfer RECORD visibility in admin lists
    - This does NOT re-execute any financial transaction
    - This does NOT trigger any payment processor / settlement / ledger movement
    - The transfer returns to its previous status before deletion
    
    Eligibility:
    - Only transfers with is_deleted=True can be restored
    - Non-deleted transfers return a safe error (idempotent-safe)
    - Non-existent transfers return 404
    
    RBAC: Only SUPER_ADMIN can restore transfers (same as delete)
    """
    # Only SUPER_ADMIN can restore transfers (same permission as delete)
    if current_user["role"] != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Only Super Admin can restore transfers")
    
    # Find transfer (including soft-deleted ones)
    transfer = await db.transfers.find_one({"_id": transfer_id})
    if not transfer:
        try:
            transfer = await db.transfers.find_one({"_id": ObjectId(transfer_id)})
        except InvalidId:
            pass
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    # Check if transfer is soft-deleted
    if not transfer.get("is_deleted", False):
        # Idempotent-safe: Transfer is not deleted, nothing to restore
        return {
            "ok": True,
            "message": "Transfer is not deleted, no restore needed",
            "already_active": True
        }
    
    # Get deletion metadata for audit trail
    deleted_at = transfer.get("deleted_at")
    deleted_by = transfer.get("deleted_by")
    deleted_by_email = transfer.get("deleted_by_email")
    previous_status = transfer.get("previous_status", transfer.get("status", "UNKNOWN"))
    
    transfer_amount = transfer.get("amount", 0)
    beneficiary = transfer.get("beneficiary_name", "Unknown")
    restore_reason = data.reason if data else None
    
    # RESTORE: Remove soft-delete flags and restore previous status
    restore_result = await db.transfers.update_one(
        {"_id": transfer["_id"]},
        {
            "$set": {
                "is_deleted": False,
                "restored_at": datetime.now(timezone.utc),
                "restored_by": current_user["id"],
                "restored_by_email": current_user["email"],
                "restore_reason": restore_reason,
                # Restore to previous status if available, otherwise keep current
                "status": previous_status
            },
            "$unset": {
                # Clear deletion fields but keep them in audit via the audit log
                "deleted_at": "",
                "deleted_by": "",
                "deleted_by_email": ""
                # Keep previous_status for reference
            }
        }
    )
    
    if restore_result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to restore transfer")
    
    # Audit log - MANDATORY for traceability
    await create_audit_log(
        db=db,
        action="TRANSFER_RESTORED",
        entity_type="transfer",
        entity_id=str(transfer["_id"]),
        description=f"Transfer to {beneficiary} (€{transfer_amount/100:.2f}) restored. Status: {previous_status}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "restored_status": previous_status,
            "amount": transfer_amount,
            "beneficiary": beneficiary,
            "restore_reason": restore_reason,
            "was_deleted_at": deleted_at.isoformat() if deleted_at else None,
            "was_deleted_by": deleted_by,
            "was_deleted_by_email": deleted_by_email,
            "note": "Record visibility restored only - no financial re-execution"
        }
    )
    
    logger.info(f"Transfer {transfer_id} restored by admin {current_user['email']} (restored to status: {previous_status})")
    
    return {
        "ok": True,
        "message": "Transfer restored successfully",
        "restored_status": previous_status,
        "note": "Transfer record visibility restored. No financial transaction was re-executed."
    }


@admin_router.post("/transfers/{transfer_id}/resend-email")
async def admin_resend_transfer_email(
    transfer_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin resends transfer confirmation email. Only available if email status is failed or pending."""
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


# ==================== ADMIN LEDGER TRANSFER ENDPOINT ====================

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
            (from_account["ledger_account_id"], data.amount, EntryDirection.DEBIT),
            (to_account["ledger_account_id"], data.amount, EntryDirection.CREDIT)
        ],
        external_id=f"admin_transfer_{uuid.uuid4()}",
        reason=data.reason,
        performed_by=current_user["id"]
    )
    
    return txn.model_dump()
