"""
Scheduled Payments Router - User scheduled/recurring payments management.

Handles all scheduled payment operations including:
- Create scheduled recurring payment
- List user's scheduled payments
- Cancel scheduled payment

Routes: /api/v1/scheduled-payments/*

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from database import get_database
from services.ledger_service import LedgerEngine
from services.advanced_service import AdvancedBankingService
from schemas.advanced import CreateScheduledPayment
from .dependencies import get_current_user

logger = logging.getLogger(__name__)


# User scheduled payments router
router = APIRouter(prefix="/api/v1", tags=["scheduled-payments"])


# ==================== USER SCHEDULED PAYMENT ENDPOINTS ====================

@router.post("/scheduled-payments")
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


@router.get("/scheduled-payments")
async def get_scheduled_payments(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's scheduled payments."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    payments = await advanced_service.get_scheduled_payments(current_user["id"])
    return [p.model_dump() for p in payments]


@router.delete("/scheduled-payments/{payment_id}")
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
