"""
Notifications Router - User and Admin notification operations.

Handles all notification operations including:
- User notifications (get, mark read)
- Admin notification counts and badge management
- Admin section views (persistent across sessions)

Routes: 
- /api/v1/notifications/* (user)
- /api/v1/admin/notification-counts
- /api/v1/admin/notifications/* (admin)

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
import logging

from database import get_database
from services.notification_service import NotificationService
from .dependencies import get_current_user, require_admin

logger = logging.getLogger(__name__)

# User notifications router
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

# Admin notifications router
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin-notifications"])


# ==================== USER NOTIFICATIONS ====================

@router.get("")
async def get_notifications(
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user notifications."""
    notif_service = NotificationService(db)
    notifications = await notif_service.get_user_notifications(
        user_id=current_user["id"],
        unread_only=unread_only
    )
    return [n.model_dump() for n in notifications]


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark notification as read."""
    notif_service = NotificationService(db)
    success = await notif_service.mark_as_read(notification_id, current_user["id"])
    return {"success": success}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark all notifications as read."""
    notif_service = NotificationService(db)
    count = await notif_service.mark_all_as_read(current_user["id"])
    return {"marked_read": count}


# ==================== ADMIN NOTIFICATION COUNTS ====================

@admin_router.get("/notification-counts")
async def get_admin_notification_counts(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get notification badge counts for admin sidebar.
    
    PERSISTENT ACROSS SESSIONS: Uses per-admin, per-section "last_seen_at" timestamps
    stored in database. Badges show items created/updated AFTER the admin last viewed
    that section, not just total pending items.
    
    Returns counts for:
    - users: New users created since last seen Users section
    - kyc: New KYC submissions since last seen KYC Queue
    - card_requests: New card requests since last seen Card Requests
    - transfers: New submitted transfers since last seen Transfers Queue  
    - tickets: Tickets with new client activity since last seen Support Tickets
    """
    admin_id = str(current_user.get("_id") or current_user.get("id"))
    
    # Section keys matching frontend
    section_keys = ['users', 'kyc', 'card_requests', 'transfers', 'tickets']
    
    # Get all last_seen timestamps for this admin in one query
    section_views = await db.admin_section_views.find(
        {"admin_id": admin_id}
    ).to_list(length=10)
    
    # Build lookup dict: section_key -> last_seen_at
    last_seen_map = {}
    for view in section_views:
        last_seen_map[view["section_key"]] = view.get("last_seen_at")
    
    # Default: if never seen, use a very old date (show all pending items)
    default_last_seen = datetime(2000, 1, 1, tzinfo=timezone.utc)
    
    async def get_users_new():
        """Count users created since last seen, with status PENDING."""
        last_seen = last_seen_map.get('users', default_last_seen)
        return await db.users.count_documents({
            "status": "PENDING",
            "created_at": {"$gt": last_seen}
        })
    
    async def get_kyc_new():
        """Count KYC applications submitted since last seen, with status SUBMITTED.
        NOTE: KYC applications use 'SUBMITTED' status (not 'PENDING') when awaiting review.
        """
        last_seen = last_seen_map.get('kyc', default_last_seen)
        return await db.kyc_applications.count_documents({
            "status": "SUBMITTED",
            "created_at": {"$gt": last_seen}
        })
    
    async def get_card_requests_new():
        """Count card requests created since last seen, with status PENDING."""
        last_seen = last_seen_map.get('card_requests', default_last_seen)
        return await db.card_requests.count_documents({
            "status": "PENDING",
            "created_at": {"$gt": last_seen}
        })
    
    async def get_transfers_new():
        """Count transfers submitted since last seen, with status SUBMITTED.
        SOFT DELETE: Excludes soft-deleted transfers.
        """
        last_seen = last_seen_map.get('transfers', default_last_seen)
        return await db.transfers.count_documents({
            "status": "SUBMITTED",
            "created_at": {"$gt": last_seen},
            "$or": [{"is_deleted": {"$exists": False}}, {"is_deleted": False}]
        })
    
    async def get_tickets_new():
        """Count tickets with new client activity since last seen.
        
        PERFORMANCE OPTIMIZED: Uses simple count on tickets collection.
        Counts tickets where:
        - Status is OPEN/IN_PROGRESS
        - Has client message after last_seen (last_client_message_at)
        
        NOTE: Uses last_client_message_at to only count CLIENT-originated activity.
        Admin messages do NOT trigger admin notifications (admin shouldn't be notified
        for their own actions).
        """
        last_seen = last_seen_map.get('tickets', default_last_seen)
        
        # Count open/in-progress tickets with CLIENT messages after last_seen
        # Uses last_client_message_at to exclude admin-originated activity
        return await db.tickets.count_documents({
            "status": {"$in": ["OPEN", "IN_PROGRESS", "open", "in_progress"]},
            "$or": [
                # Tickets with client messages after last_seen
                {"last_client_message_at": {"$gt": last_seen}},
                # New tickets (created_at > last_seen, not created by admin)
                {"$and": [
                    {"created_at": {"$gt": last_seen}},
                    {"$or": [
                        {"created_by_admin": {"$exists": False}},
                        {"created_by_admin": False}
                    ]}
                ]}
            ]
        })
    
    # Execute all queries in parallel for performance
    results = await asyncio.gather(
        get_users_new(),
        get_kyc_new(),
        get_card_requests_new(),
        get_transfers_new(),
        get_tickets_new(),
        return_exceptions=True
    )
    
    # Handle any exceptions gracefully
    def safe_result(result, default=0):
        return result if isinstance(result, int) else default
    
    return {
        "users": safe_result(results[0]),
        "kyc": safe_result(results[1]),
        "card_requests": safe_result(results[2]),
        "transfers": safe_result(results[3]),
        "tickets": safe_result(results[4])
    }


@admin_router.post("/notifications/seen")
async def mark_admin_section_seen(
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark a sidebar section as 'seen' by this admin.
    
    Updates last_seen_at timestamp for the given section. This clears the badge
    for that section and persists across logout/login.
    
    Request body: { "section_key": "users" | "kyc" | "card_requests" | "transfers" | "tickets" }
    """
    body = await request.json()
    section_key = body.get("section_key")
    
    valid_sections = ['users', 'kyc', 'card_requests', 'transfers', 'tickets']
    if section_key not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section_key. Must be one of: {valid_sections}")
    
    admin_id = str(current_user.get("_id") or current_user.get("id"))
    now = datetime.now(timezone.utc)
    
    # Upsert: update if exists, insert if not
    await db.admin_section_views.update_one(
        {"admin_id": admin_id, "section_key": section_key},
        {
            "$set": {
                "last_seen_at": now,
                "updated_at": now
            },
            "$setOnInsert": {
                "admin_id": admin_id,
                "section_key": section_key,
                "created_at": now
            }
        },
        upsert=True
    )
    
    return {"ok": True, "section_key": section_key, "last_seen_at": now.isoformat()}


@admin_router.post("/notifications/clear")
async def clear_admin_notifications(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark admin notifications as cleared by storing the current timestamp.
    This persists across sessions and page reloads.
    """
    cleared_at = datetime.now(timezone.utc)
    
    user_id = current_user["id"]
    
    # First try as string
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"admin_notifications_cleared_at": cleared_at}}
    )
    
    # If no match and it looks like an ObjectId, try as ObjectId
    if result.matched_count == 0:
        try:
            result = await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"admin_notifications_cleared_at": cleared_at}}
            )
        except InvalidId:
            pass
    
    if result.modified_count == 0:
        # Also handle if document doesn't exist (shouldn't happen but be safe)
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "cleared_at": cleared_at.isoformat()
    }


@admin_router.get("/notifications/cleared-at")
async def get_admin_notifications_cleared_at(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get the timestamp when admin last cleared notifications.
    Returns None if never cleared.
    """
    user_id = current_user["id"]
    
    # First try as string
    user = await db.users.find_one(
        {"_id": user_id},
        {"admin_notifications_cleared_at": 1}
    )
    
    # If not found and it looks like an ObjectId, try as ObjectId
    if not user:
        try:
            user = await db.users.find_one(
                {"_id": ObjectId(user_id)},
                {"admin_notifications_cleared_at": 1}
            )
        except InvalidId:
            pass
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cleared_at = user.get("admin_notifications_cleared_at")
    
    return {
        "cleared_at": cleared_at.isoformat() if cleared_at else None
    }


@admin_router.get("/notifications/counts-since-clear")
async def get_admin_notification_counts_since_clear(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get counts of pending items created AFTER the last clear timestamp.
    This allows the badge to show only NEW items while keeping old items cleared.
    
    Returns:
    - kyc: Count of pending KYC applications submitted after clear
    - cards: Count of pending card requests created after clear  
    - transfers: Count of pending transfers created after clear
    - tickets: Count of open tickets created after clear
    - total: Sum of all counts
    - cleared_at: The timestamp when notifications were last cleared (or null)
    """
    user_id = current_user["id"]
    
    # Get the cleared_at timestamp
    user = await db.users.find_one(
        {"_id": user_id},
        {"admin_notifications_cleared_at": 1}
    )
    
    if not user:
        try:
            user = await db.users.find_one(
                {"_id": ObjectId(user_id)},
                {"admin_notifications_cleared_at": 1}
            )
        except InvalidId:
            pass
    
    cleared_at = user.get("admin_notifications_cleared_at") if user else None
    
    # If never cleared, count all items
    if not cleared_at:
        kyc_count = await db.kyc_applications.count_documents({
            "status": {"$in": ["SUBMITTED", "UNDER_REVIEW", "NEEDS_MORE_INFO"]}
        })
        cards_count = await db.card_requests.count_documents({"status": "PENDING"})
        transfers_count = await db.transfers.count_documents({"status": "SUBMITTED"})
        tickets_count = await db.tickets.count_documents({
            "status": {"$in": ["OPEN", "IN_PROGRESS"]}
        })
    else:
        # Count only items created/submitted AFTER cleared_at
        # KYC: Use submitted_at field
        kyc_count = await db.kyc_applications.count_documents({
            "status": {"$in": ["SUBMITTED", "UNDER_REVIEW", "NEEDS_MORE_INFO"]},
            "submitted_at": {"$gt": cleared_at}
        })
        
        # Card requests: Use created_at field
        cards_count = await db.card_requests.count_documents({
            "status": "PENDING",
            "created_at": {"$gt": cleared_at}
        })
        
        # Transfers: Use created_at field
        transfers_count = await db.transfers.count_documents({
            "status": "SUBMITTED",
            "created_at": {"$gt": cleared_at}
        })
        
        # Tickets: Use created_at field
        tickets_count = await db.tickets.count_documents({
            "status": {"$in": ["OPEN", "IN_PROGRESS"]},
            "created_at": {"$gt": cleared_at}
        })
    
    total = kyc_count + cards_count + transfers_count + tickets_count
    
    return {
        "kyc": kyc_count,
        "cards": cards_count,
        "transfers": transfers_count,
        "tickets": tickets_count,
        "total": total,
        "cleared_at": cleared_at.isoformat() if cleared_at else None
    }
