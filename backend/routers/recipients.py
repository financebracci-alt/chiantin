"""
Recipients Router - User saved recipients management.

Handles all recipient operations including:
- Create saved recipient (IBAN display only)
- List user's recipients
- Delete recipient

Routes: /api/v1/recipients/*

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from database import get_database
from services.banking_workflows_service import BankingWorkflowsService
from schemas.banking_workflows import CreateRecipient
from .dependencies import get_current_user

logger = logging.getLogger(__name__)


# User recipients router
router = APIRouter(prefix="/api/v1", tags=["recipients"])


# ==================== USER RECIPIENT ENDPOINTS ====================

@router.post("/recipients")
async def create_recipient(
    data: CreateRecipient,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create saved recipient (IBAN display only)."""
    workflows = BankingWorkflowsService(db)
    recipient = await workflows.create_recipient(current_user["id"], data)
    return {"ok": True, "data": recipient.model_dump()}


@router.get("/recipients")
async def get_recipients(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's saved recipients."""
    workflows = BankingWorkflowsService(db)
    recipients = await workflows.get_user_recipients(current_user["id"])
    return {"ok": True, "data": [r.model_dump() for r in recipients]}


@router.delete("/recipients/{recipient_id}")
async def delete_recipient(
    recipient_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete saved recipient."""
    workflows = BankingWorkflowsService(db)
    success = await workflows.delete_recipient(recipient_id, current_user["id"])
    return {"ok": success}
