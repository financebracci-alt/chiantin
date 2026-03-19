"""
Insights Router - User spending insights and analytics.

Handles all insights operations including:
- Get spending breakdown by category
- Get monthly spending summary

Routes: /api/v1/insights/*

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from database import get_database
from services.ledger_service import LedgerEngine
from services.advanced_service import AdvancedBankingService
from .dependencies import get_current_user

logger = logging.getLogger(__name__)


# User insights router
router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


# ==================== USER INSIGHTS ENDPOINTS ====================

@router.get("/spending")
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


@router.get("/monthly-spending")
async def get_monthly_spending(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get spending for the current calendar month from real ledger data."""
    ledger_engine = LedgerEngine(db)
    advanced_service = AdvancedBankingService(db, ledger_engine)
    spending = await advanced_service.get_monthly_spending(current_user["id"])
    return spending
