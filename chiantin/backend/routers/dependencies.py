"""
Shared dependencies for all routers.

Contains authentication, database access, and common utilities.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime, timezone
import jwt
import logging

from config import settings
from database import get_database

logger = logging.getLogger(__name__)
security = HTTPBearer()


def format_timestamp_utc(dt: datetime) -> str:
    """Format a datetime as ISO 8601 with UTC timezone suffix.
    
    MongoDB returns naive datetimes (no timezone info) even when stored with timezone.
    This ensures all API responses include the 'Z' suffix so JavaScript parses them as UTC.
    """
    if dt is None:
        return None
    # If datetime is naive (no timezone), assume it's UTC (MongoDB returns UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to UTC and format with Z suffix
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Validates JWT token and returns the current user.
    Used as a dependency for protected routes.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Try to find user by _id (handle both ObjectId and string)
        user_doc = None
        # First try as string (for seed data)
        user_doc = await db.users.find_one({"_id": user_id})
        
        # If not found and it looks like an ObjectId, try as ObjectId
        if not user_doc:
            try:
                user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
            except InvalidId:
                pass
        
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")
        
        return {
            "id": str(user_doc["_id"]),
            "email": user_doc["email"],
            "role": user_doc["role"],
            "status": user_doc["status"]
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_admin(user: dict = Depends(get_current_user)):
    """
    Dependency that requires the current user to be an admin.
    Returns the user if they have admin privileges.
    Includes ADMIN, SUPER_ADMIN, FINANCE_OPS, and COMPLIANCE_OFFICER roles.
    """
    if user.get("role") not in ["ADMIN", "SUPER_ADMIN", "FINANCE_OPS", "COMPLIANCE_OFFICER"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_super_admin(user: dict = Depends(get_current_user)):
    """
    Dependency that requires the current user to be a super admin.
    """
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


async def create_audit_log(
    db: AsyncIOMotorDatabase,
    action: str,
    entity_type: str,
    entity_id: str,
    description: str,
    performed_by: str = None,
    performed_by_role: str = None,
    performed_by_email: str = None,
    metadata: dict = None
):
    """
    Create an audit log entry for tracking important actions.
    This is a safe helper that won't raise exceptions to avoid breaking main flows.
    """
    try:
        audit_entry = {
            "id": str(datetime.now(timezone.utc).timestamp()).replace(".", "") + "_audit",
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "description": description,
            "performed_by": performed_by,
            "performed_by_role": performed_by_role,
            "performed_by_email": performed_by_email,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc)
        }
        await db.audit_logs.insert_one(audit_entry)
    except Exception as e:
        # Log but don't fail the main operation
        logger.error(f"Failed to create audit log: {e}")
