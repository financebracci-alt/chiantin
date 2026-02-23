"""
Audit logging router.

Handles admin-only audit log retrieval.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

from database import get_database
from .dependencies import require_admin, format_timestamp_utc

router = APIRouter(prefix="/api/v1/admin", tags=["audit"])


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    entity_type: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get audit logs (admin)."""
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    
    cursor = db.audit_logs.find(query).sort("created_at", -1).limit(limit)
    logs = []
    async for doc in cursor:
        logs.append({
            "id": str(doc["_id"]),
            "performed_by": doc["performed_by"],
            "performed_by_email": doc.get("performed_by_email", ""),
            "performed_by_role": doc.get("performed_by_role", ""),
            "action": doc["action"],
            "entity_type": doc["entity_type"],
            "entity_id": doc["entity_id"],
            "description": doc.get("description", ""),
            "metadata": doc.get("metadata", {}),
            "created_at": format_timestamp_utc(doc["created_at"])
        })
    
    return logs
