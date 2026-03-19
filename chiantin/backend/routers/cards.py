"""
Cards Router - User and Admin card operations.

Handles all card operations including:
- User card requests (create, list)
- User cards (list)
- Admin card request management (list, fulfill, reject, delete)

Routes: 
- /api/v1/card-requests/* (user)
- /api/v1/cards (user)
- /api/v1/admin/card-requests/* (admin)

IMPORTANT: This is a live banking application. Any changes must preserve
100% behavior parity with the original implementation.
"""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from bson import ObjectId
import re
import logging

from database import get_database
from services.banking_workflows_service import BankingWorkflowsService
from schemas.banking_workflows import CreateCardRequest, FulfillCardRequest
from utils.common import serialize_doc
from .dependencies import get_current_user, require_admin

logger = logging.getLogger(__name__)


async def check_tax_hold(user_id: str, db: AsyncIOMotorDatabase):
    """Check if user has an active tax hold."""
    return await db.tax_holds.find_one({
        "user_id": user_id,
        "is_active": True
    })


# User cards router
router = APIRouter(prefix="/api/v1", tags=["cards"])

# Admin cards router
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin-cards"])


# ==================== USER CARD ENDPOINTS ====================

@router.post("/card-requests")
async def create_card_request(
    data: CreateCardRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """User creates card request."""
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
                "formatted_message": f"Account Restricted: Your account has been temporarily suspended due to outstanding tax obligations of €{tax_amount:,.2f}. Card services are unavailable until the required amount is settled. For assistance, contact our support team at support@projectatlas.eu"
            }
        )
    
    workflows = BankingWorkflowsService(db)
    request = await workflows.create_card_request(current_user["id"], data)
    return {"ok": True, "data": request.model_dump()}


@router.get("/card-requests")
async def get_card_requests(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's card requests."""
    workflows = BankingWorkflowsService(db)
    requests = await workflows.get_user_card_requests(current_user["id"])
    return {"ok": True, "data": [r.model_dump() for r in requests]}


@router.get("/cards")
async def get_cards(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user's cards."""
    workflows = BankingWorkflowsService(db)
    cards = await workflows.get_user_cards(current_user["id"])
    return {"ok": True, "data": [c.model_dump() for c in cards]}


# ==================== ADMIN CARD ENDPOINTS ====================

@admin_router.get("/card-requests")
async def admin_get_card_requests(
    status: str = None,
    page: int = 1,
    page_size: int = 50,
    search: str = None,
    scope: str = "tab",  # "tab" or "all" - search within tab or all statuses
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Get card requests with pagination, search, and user information.
    
    PERFORMANCE OPTIMIZED: Server-side pagination, search, and bulk user lookups.
    
    Query params:
    - status: Filter by status (PENDING, FULFILLED, REJECTED). Default: PENDING
    - page: Page number (1-indexed, default 1)
    - page_size: Items per page (20, 50, or 100, default 50)
    - search: Search term (matches user name, email, card type, request ID)
    - scope: "tab" (search current status only) or "all" (search all statuses)
    """
    # Validate page_size
    valid_page_sizes = [20, 50, 100]
    if page_size not in valid_page_sizes:
        page_size = 50
    
    # Validate page
    if page < 1:
        page = 1
    
    # Build base query
    query = {}
    
    # Status filter (unless scope is "all" with search)
    if scope == "all" and search:
        # Search across all statuses
        pass
    elif status:
        query["status"] = status
    else:
        query["status"] = "PENDING"  # Default to PENDING
    
    # If searching, we need to do a more complex query
    search_user_ids = []
    if search:
        search = search.strip()
        search_regex = {"$regex": re.escape(search), "$options": "i"}
        
        # First, find users matching the search (for name/email search)
        user_query = {
            "$or": [
                {"first_name": search_regex},
                {"last_name": search_regex},
                {"email": search_regex}
            ]
        }
        users_cursor = db.users.find(user_query, {"_id": 1})
        async for user in users_cursor:
            search_user_ids.append(str(user["_id"]))
        
        # Build search conditions for card_requests
        search_conditions = [
            {"card_type": search_regex},
            {"_id": search_regex}
        ]
        
        if search_user_ids:
            search_conditions.append({"user_id": {"$in": search_user_ids}})
        
        # Combine with status filter
        if query.get("status"):
            query = {
                "$and": [
                    {"status": query["status"]},
                    {"$or": search_conditions}
                ]
            }
        else:
            query = {"$or": search_conditions}
    
    # Get total count for pagination
    total_count = await db.card_requests.count_documents(query)
    
    # Calculate pagination
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    
    skip = (page - 1) * page_size
    
    # Fetch paginated results
    cursor = db.card_requests.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    request_docs = await cursor.to_list(length=page_size)
    
    if not request_docs:
        return {
            "ok": True,
            "data": [],
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "status": status or "PENDING",
                "has_prev": page > 1,
                "has_next": page < total_pages
            }
        }
    
    # Collect all unique user_ids for bulk lookup
    user_ids = set()
    for doc in request_docs:
        user_id = doc.get("user_id")
        if user_id:
            try:
                user_ids.add(ObjectId(user_id))
            except:
                user_ids.add(user_id)
    
    # BULK LOOKUP: Fetch all users in ONE query
    users_map = {}
    if user_ids:
        users_cursor = db.users.find({"_id": {"$in": list(user_ids)}})
        async for user in users_cursor:
            users_map[str(user["_id"])] = user
    
    # Build response with user info included
    requests = []
    for doc in request_docs:
        request_dict = serialize_doc(doc)
        
        # Add user info from pre-fetched map (O(1) lookup)
        user_id = doc.get("user_id")
        user = users_map.get(str(user_id)) if user_id else None
        
        if user:
            request_dict["user_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            request_dict["user_email"] = user.get("email", "")
        else:
            request_dict["user_name"] = "Unknown User"
            request_dict["user_email"] = ""
        
        requests.append(request_dict)
    
    return {
        "ok": True,
        "data": requests,
        "pagination": {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "status": status or "PENDING",
            "has_prev": page > 1,
            "has_next": page < total_pages
        }
    }


@admin_router.delete("/card-requests/{request_id}")
async def admin_delete_card_request(
    request_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin: Delete a card request with safety handling for fulfilled requests.
    
    CRITICAL SAFETY LOGIC:
    - If the request is FULFILLED and has an associated card, also delete the card
    - Logs all delete actions for audit purposes
    - Does not affect other user data
    
    Returns:
    - ok: True if deleted successfully
    - card_also_deleted: True if associated card was also deleted (for fulfilled requests)
    """
    admin_id = str(current_user.get("_id") or current_user.get("id"))
    admin_email = current_user.get("email", "unknown")
    
    # Find the card request
    request_doc = await db.card_requests.find_one({"_id": request_id})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Card request not found")
    
    request_status = request_doc.get("status")
    user_id = request_doc.get("user_id")
    card_type = request_doc.get("card_type")
    card_also_deleted = False
    deleted_card_id = None
    
    # CRITICAL: If FULFILLED, check for and delete associated card
    if request_status == "FULFILLED":
        # Find the associated card - it should have been created with a reference to this request
        # Look for card with matching user_id and card_type, created around the fulfilled time
        fulfilled_at = request_doc.get("decided_at")
        
        # Try to find the associated card
        card_query = {"user_id": user_id}
        
        # If we have the fulfilled_card_id stored, use that
        if request_doc.get("fulfilled_card_id"):
            card_doc = await db.cards.find_one({"_id": request_doc.get("fulfilled_card_id")})
        else:
            # Otherwise try to find by user and type
            # Find cards created after the request was fulfilled
            if fulfilled_at:
                card_query["created_at"] = {"$gte": fulfilled_at}
            if card_type:
                card_query["card_type"] = card_type
            
            card_doc = await db.cards.find_one(card_query)
        
        if card_doc:
            deleted_card_id = card_doc.get("_id")
            # Delete the associated card
            delete_card_result = await db.cards.delete_one({"_id": deleted_card_id})
            if delete_card_result.deleted_count > 0:
                card_also_deleted = True
                logger.warning(
                    f"[CARD REQUEST DELETE] Admin {admin_email} deleted FULFILLED request {request_id} "
                    f"- also deleted associated card {deleted_card_id} for user {user_id}"
                )
            else:
                logger.warning(
                    f"[CARD REQUEST DELETE] Admin {admin_email} deleted FULFILLED request {request_id} "
                    f"- card {deleted_card_id} was already deleted or not found"
                )
        else:
            logger.warning(
                f"[CARD REQUEST DELETE] Admin {admin_email} deleted FULFILLED request {request_id} "
                f"- no associated card found for user {user_id} (edge case)"
            )
    
    # Delete the card request
    delete_result = await db.card_requests.delete_one({"_id": request_id})
    
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete card request")
    
    # Create audit log entry
    audit_entry = {
        "_id": f"audit_{datetime.now(timezone.utc).timestamp()}_{request_id}",
        "action": "CARD_REQUEST_DELETE",
        "entity_type": "card_request",
        "entity_id": request_id,
        "admin_id": admin_id,
        "admin_email": admin_email,
        "details": {
            "request_status": request_status,
            "user_id": user_id,
            "card_type": card_type,
            "card_also_deleted": card_also_deleted,
            "deleted_card_id": deleted_card_id
        },
        "timestamp": datetime.now(timezone.utc)
    }
    
    try:
        await db.audit_logs.insert_one(audit_entry)
    except Exception as e:
        logger.error(f"[AUDIT] Failed to create audit log for card request delete: {e}")
    
    logger.info(
        f"[CARD REQUEST DELETE] Admin {admin_email} deleted card request {request_id} "
        f"(status: {request_status}, card_also_deleted: {card_also_deleted})"
    )
    
    return {
        "ok": True,
        "message": "Card request deleted successfully",
        "card_also_deleted": card_also_deleted,
        "deleted_card_id": deleted_card_id
    }


@admin_router.post("/card-requests/{request_id}/fulfill")
async def admin_fulfill_card_request(
    request_id: str,
    card_data: FulfillCardRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin fulfills card request."""
    workflows = BankingWorkflowsService(db)
    card = await workflows.fulfill_card_request(request_id, current_user["id"], card_data)
    return {"ok": True, "data": card.model_dump()}


@admin_router.post("/card-requests/{request_id}/reject")
async def admin_reject_card_request(
    request_id: str,
    reason: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin rejects card request."""
    if not reason:
        raise HTTPException(status_code=400, detail="Reject reason is required")
    workflows = BankingWorkflowsService(db)
    await workflows.reject_card_request(request_id, current_user["id"], reason)
    return {"ok": True}
