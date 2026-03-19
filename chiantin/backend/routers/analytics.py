"""
Analytics Router - Admin analytics and dashboard statistics.

Handles all admin analytics operations including:
- Dashboard overview stats
- Monthly statistics charts

Routes: /api/v1/admin/analytics/*

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio
from datetime import datetime, timezone, timedelta
from calendar import month_abbr
import logging

from database import get_database
from .dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/analytics", tags=["analytics"])


@router.get("/overview")
async def get_admin_analytics_overview(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get admin dashboard analytics overview.
    
    PERFORMANCE OPTIMIZED: Uses parallel queries and aggregation pipelines
    instead of sequential count_documents() calls.
    """
    # Run all count queries in parallel using asyncio.gather
    async def get_users_count():
        return await db.users.count_documents({})
    
    async def get_active_users_count():
        return await db.users.count_documents({"status": "ACTIVE"})
    
    async def get_pending_kyc_count():
        return await db.kyc_applications.count_documents({"status": "SUBMITTED"})
    
    async def get_approved_kyc_count():
        return await db.kyc_applications.count_documents({"status": "APPROVED"})
    
    async def get_accounts_count():
        return await db.bank_accounts.count_documents({})
    
    async def get_transfer_stats():
        # Use aggregation to get all transfer counts in ONE query
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        results = await db.transfers.aggregate(pipeline).to_list(10)
        stats = {"total": 0, "pending": 0, "completed": 0, "rejected": 0}
        for r in results:
            status = r["_id"]
            count = r["count"]
            stats["total"] += count
            if status == "SUBMITTED":
                stats["pending"] = count
            elif status == "COMPLETED":
                stats["completed"] = count
            elif status == "REJECTED":
                stats["rejected"] = count
        return stats
    
    async def get_ticket_stats():
        # Use aggregation to get ticket counts in ONE query
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        results = await db.tickets.aggregate(pipeline).to_list(10)
        total = 0
        open_count = 0
        for r in results:
            status = r["_id"]
            count = r["count"]
            total += count
            if status in ["OPEN", "IN_PROGRESS", "open", "in_progress"]:
                open_count += count
        return {"total": total, "open": open_count}
    
    async def get_pending_cards_count():
        return await db.card_requests.count_documents({"status": "PENDING"})
    
    async def get_volume():
        try:
            pipeline = [
                {"$match": {"direction": "CREDIT"}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]
            result = await db.ledger_entries.aggregate(pipeline).to_list(1)
            return result[0].get("total", 0) if result else 0
        except Exception:
            return 0
    
    # Execute ALL queries in parallel
    results = await asyncio.gather(
        get_users_count(),
        get_active_users_count(),
        get_pending_kyc_count(),
        get_approved_kyc_count(),
        get_accounts_count(),
        get_transfer_stats(),
        get_ticket_stats(),
        get_pending_cards_count(),
        get_volume()
    )
    
    total_users = results[0]
    active_users = results[1]
    pending_kyc = results[2]
    approved_kyc = results[3]
    total_accounts = results[4]
    transfer_stats = results[5]
    ticket_stats = results[6]
    pending_cards = results[7]
    total_volume_cents = results[8]
    
    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "kyc": {
            "pending": pending_kyc,
            "approved": approved_kyc
        },
        "accounts": {
            "total": total_accounts
        },
        "transfers": {
            "total": transfer_stats["total"],
            "pending": transfer_stats["pending"],
            "completed": transfer_stats["completed"],
            "rejected": transfer_stats["rejected"],
            "volume_cents": total_volume_cents
        },
        "tickets": {
            "total": ticket_stats["total"],
            "open": ticket_stats["open"]
        },
        "cards": {
            "pending": pending_cards
        }
    }


@router.get("/monthly")
async def get_admin_analytics_monthly(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get real monthly statistics for admin dashboard charts.
    
    PERFORMANCE OPTIMIZED: Uses aggregation pipelines instead of sequential count queries.
    Returns actual data from the database grouped by month for the last 6 months.
    """
    # Calculate date range - last 6 months including current
    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=180)
    
    # Use aggregation to get all user counts by month in ONE query
    async def get_users_by_month():
        pipeline = [
            {"$match": {"created_at": {"$gte": six_months_ago}}},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        results = await db.users.aggregate(pipeline).to_list(12)
        return {(r["_id"]["year"], r["_id"]["month"]): r["count"] for r in results}
    
    # Use aggregation to get all transfer counts by month in ONE query
    async def get_transfers_by_month():
        pipeline = [
            {"$match": {"created_at": {"$gte": six_months_ago}}},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        results = await db.transfers.aggregate(pipeline).to_list(12)
        return {(r["_id"]["year"], r["_id"]["month"]): r["count"] for r in results}
    
    async def get_users_before_period():
        return await db.users.count_documents({"created_at": {"$lt": six_months_ago}})
    
    # Execute all queries in parallel
    users_by_month, transfers_by_month, users_before_period = await asyncio.gather(
        get_users_by_month(),
        get_transfers_by_month(),
        get_users_before_period()
    )
    
    # Generate list of last 6 months
    months_data = []
    running_total = users_before_period
    
    for i in range(5, -1, -1):  # 5 months ago to current month
        target_date = now - timedelta(days=i*30)
        year = target_date.year
        month = target_date.month
        
        users_count = users_by_month.get((year, month), 0)
        transfers_count = transfers_by_month.get((year, month), 0)
        
        running_total += users_count
        
        months_data.append({
            "month": month_abbr[month],
            "year": year,
            "users": users_count,
            "transactions": transfers_count,
            "cumulative_users": running_total
        })
    
    return {
        "monthly_data": months_data,
        "period": "last_6_months"
    }
