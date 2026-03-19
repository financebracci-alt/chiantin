"""
Users Router - Customer-facing user endpoints.

Handles customer user operations including:
- Tax hold status check

Routes: /api/v1/users/*

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone

from database import get_database
from .dependencies import get_current_user, format_timestamp_utc

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me/tax-status")
async def get_my_tax_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get current user's tax hold status."""
    user_id = current_user["id"]
    
    # Check for active tax hold
    tax_hold = await db.tax_holds.find_one({
        "user_id": user_id,
        "is_active": True
    })
    
    if not tax_hold:
        return {
            "is_blocked": False,
            "tax_amount_due": 0,
            "reason": None,
            "blocked_at": None,
            "beneficiary_name": None,
            "iban": None,
            "bic_swift": None,
            "reference": None,
            "crypto_wallet": None
        }
    
    # Support both old format (nested payment_details) and new format (top-level fields)
    # Old format: payment_details: {beneficiary_name, iban, bic_swift, reference, crypto_wallet}
    # New format: beneficiary_name, iban, bic_swift, reference, crypto_wallet at top level
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
        "bic_swift": bic_swift.strip() if bic_swift else None,  # Clean up any trailing spaces
        "reference": reference,
        "crypto_wallet": crypto_wallet
    }
