"""
Beneficiaries Router - User saved beneficiaries management.

Handles all beneficiary operations including:
- Add beneficiary
- List user's beneficiaries
- Delete beneficiary

Routes: /api/v1/beneficiaries/*

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from database import get_database
from services.ledger_service import LedgerEngine
from services.advanced_service import AdvancedBankingService
from schemas.advanced import CreateBeneficiary
from .dependencies import get_current_user

logger = logging.getLogger(__name__)


# User beneficiaries router
router = APIRouter(prefix="/api/v1", tags=["beneficiaries"])


# ==================== USER BENEFICIARY ENDPOINTS ====================

@router.post("/beneficiaries")
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


@router.get("/beneficiaries")
async def get_beneficiaries(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's beneficiaries."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    beneficiaries = await advanced_service.get_beneficiaries(current_user["id"])
    return [b.model_dump() for b in beneficiaries]


@router.delete("/beneficiaries/{beneficiary_id}")
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
