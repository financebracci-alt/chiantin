"""
KYC (Know Your Customer) Router.

Handles all KYC operations for both customers and admins.

Routes:
- Customer: /api/v1/kyc/*
- Admin: /api/v1/admin/kyc/*
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import logging
import httpx

from database import get_database
from services.kyc_service import KYCService
from services.notification_service import NotificationService
from schemas.kyc import DocumentType, KYCStatus
from providers import CloudinaryStorage

from .dependencies import get_current_user, require_admin, format_timestamp_utc

logger = logging.getLogger(__name__)

# Storage provider dependency
def get_storage():
    """Get the configured storage provider."""
    # Always use Cloudinary for this application
    return CloudinaryStorage()


# Router definitions
router = APIRouter(prefix="/api/v1/kyc", tags=["kyc"])
admin_router = APIRouter(prefix="/api/v1/admin/kyc", tags=["admin-kyc"])


# ==================== CUSTOMER KYC ROUTES ====================

@router.get("/application")
async def get_kyc_application(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Get current user's KYC application."""
    kyc_service = KYCService(db, storage)
    app = await kyc_service.get_or_create_application(current_user["id"])
    return app.model_dump()


@router.post("/documents/upload")
async def upload_kyc_document(
    document_type: DocumentType,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Upload KYC document."""
    kyc_service = KYCService(db, storage)
    doc = await kyc_service.upload_document(current_user["id"], file, document_type)
    return doc.model_dump()


@router.get("/documents/{document_key:path}")
async def view_kyc_document(
    document_key: str,
    download: bool = False,
    storage: CloudinaryStorage = Depends(get_storage),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """View or download uploaded KYC document. Use ?download=true to download instead of view."""
    try:
        from urllib.parse import unquote
        
        # Decode URL-encoded path
        document_key = unquote(document_key)
        logger.info(f"{'Downloading' if download else 'Viewing'} document with key: {document_key}")
        
        # First, check if this document has a Cloudinary URL stored in the database
        kyc_app = await db.kyc_applications.find_one({
            "documents.file_key": document_key
        })
        
        if kyc_app:
            for doc in kyc_app.get("documents", []):
                if doc.get("file_key") == document_key:
                    cloudinary_url = doc.get("cloudinary_url")
                    if cloudinary_url:
                        if download:
                            logger.info(f"Fetching document from Cloudinary for download: {cloudinary_url}")
                            async with httpx.AsyncClient() as client:
                                response = await client.get(cloudinary_url, timeout=30.0)
                                
                                if response.status_code != 200:
                                    raise HTTPException(status_code=502, detail="Failed to fetch document from storage")
                                
                                content = response.content
                                content_type = response.headers.get("content-type", "application/octet-stream")
                            
                            file_name = doc.get("file_name", f"document_{document_key}")
                            
                            return Response(
                                content=content,
                                media_type=content_type,
                                headers={
                                    "Content-Disposition": f'attachment; filename="{file_name}"',
                                    "Access-Control-Allow-Origin": "*",
                                    "Cache-Control": "no-cache"
                                }
                            )
                        else:
                            logger.info(f"Redirecting to Cloudinary URL: {cloudinary_url}")
                            return RedirectResponse(url=cloudinary_url, status_code=302)
                    break
        
        # No Cloudinary URL found
        logger.warning(f"Document not found in Cloudinary: {document_key}")
        
        placeholder_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#f3f4f6"/>
  <text x="50%" y="40%" text-anchor="middle" font-family="Arial" font-size="18" fill="#6b7280">Document Migrated</text>
  <text x="50%" y="55%" text-anchor="middle" font-family="Arial" font-size="14" fill="#9ca3af">This document was uploaded before</text>
  <text x="50%" y="65%" text-anchor="middle" font-family="Arial" font-size="14" fill="#9ca3af">the cloud storage migration.</text>
  <text x="50%" y="80%" text-anchor="middle" font-family="Arial" font-size="12" fill="#6366f1">Please re-upload if needed.</text>
</svg>'''
        
        return Response(
            content=placeholder_svg.encode(),
            media_type="image/svg+xml",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing document {document_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error viewing document: {str(e)}")


@router.post("/submit")
async def submit_kyc_application(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Submit KYC application for review."""
    kyc_service = KYCService(db, storage)
    app = await kyc_service.submit_application(current_user["id"])
    return app.model_dump()


# ==================== ADMIN KYC ROUTES ====================

@admin_router.get("/pending")
async def get_pending_kyc(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all pending KYC applications with user info."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    applications = []
    cursor = db.kyc_applications.find({"status": "SUBMITTED"})
    
    async for app_doc in cursor:
        user_id = app_doc.get("user_id")
        user_doc = None
        
        if user_id:
            user_doc = await db.users.find_one({"_id": user_id})
            if not user_doc:
                try:
                    user_doc = await db.users.find_one({"_id": ObjectId(str(user_id))})
                except InvalidId:
                    pass
        
        applications.append({
            "id": str(app_doc["_id"]),
            "user_id": str(user_id) if user_id else None,
            "user_email": user_doc.get("email") if user_doc else None,
            "user_name": f"{user_doc.get('first_name', '')} {user_doc.get('last_name', '')}".strip() if user_doc else None,
            "status": app_doc.get("status"),
            "documents": app_doc.get("documents", []),
            "created_at": format_timestamp_utc(app_doc.get("created_at")),
            "submitted_at": format_timestamp_utc(app_doc.get("submitted_at"))
        })
    
    return applications


class QueueUserKYC(BaseModel):
    user_id: str


@admin_router.post("/queue-user")
async def queue_user_kyc(
    data: QueueUserKYC,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    PUT A USER IN THE KYC QUEUE (Admin Override).
    Creates a new KYC application in SUBMITTED status so the user appears in the KYC queue.
    This is for when an admin wants to manually process a user's KYC without the user submitting.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    import uuid
    
    # Find the user
    user = await db.users.find_one({"_id": data.user_id})
    if not user:
        try:
            user = await db.users.find_one({"_id": ObjectId(data.user_id)})
        except InvalidId:
            pass
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    
    # Check if user already has a KYC application
    existing_app = await db.kyc_applications.find_one({"user_id": user_id})
    if existing_app:
        if existing_app.get("status") == "SUBMITTED":
            return {
                "success": True,
                "message": "User is already in KYC queue",
                "application_id": str(existing_app["_id"])
            }
        elif existing_app.get("status") == "APPROVED":
            raise HTTPException(
                status_code=400,
                detail="User KYC is already approved"
            )
        else:
            # Update existing application to SUBMITTED
            await db.kyc_applications.update_one(
                {"_id": existing_app["_id"]},
                {
                    "$set": {
                        "status": "SUBMITTED",
                        "submitted_at": datetime.now(timezone.utc),
                        "admin_queued": True,
                        "admin_queued_by": current_user["id"]
                    }
                }
            )
            
            logger.info(f"KYC ADMIN QUEUE: User {user.get('email')} queued for KYC review by admin {current_user['email']}")
            
            return {
                "success": True,
                "message": f"User {user.get('email')} has been added to KYC queue",
                "application_id": str(existing_app["_id"])
            }
    
    # Create new KYC application with SUBMITTED status
    new_application = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "status": "SUBMITTED",
        "documents": [],
        "created_at": datetime.now(timezone.utc),
        "submitted_at": datetime.now(timezone.utc),
        "admin_queued": True,
        "admin_queued_by": current_user["id"]
    }
    
    await db.kyc_applications.insert_one(new_application)
    
    logger.info(f"KYC ADMIN QUEUE: New application created for user {user.get('email')} by admin {current_user['email']}")
    
    return {
        "success": True,
        "message": f"User {user.get('email')} has been added to KYC queue",
        "application_id": new_application["_id"]
    }


class ReviewKYC(BaseModel):
    status: KYCStatus
    rejection_reason: Optional[str] = None


@admin_router.post("/{application_id}/review")
async def review_kyc(
    application_id: str,
    data: ReviewKYC,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Review KYC application (admin)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    kyc_app = await db.kyc_applications.find_one({"_id": application_id})
    if not kyc_app:
        try:
            kyc_app = await db.kyc_applications.find_one({"_id": ObjectId(application_id)})
        except InvalidId:
            pass
    
    if not kyc_app:
        raise HTTPException(status_code=404, detail="KYC application not found")
    
    update_data = {
        "status": data.status.value,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.now(timezone.utc)
    }
    
    if data.status == ApplicationStatus.REJECTED and data.rejection_reason:
        update_data["rejection_reason"] = data.rejection_reason
    
    await db.kyc_applications.update_one(
        {"_id": kyc_app["_id"]},
        {"$set": update_data}
    )
    
    user_id = kyc_app.get("user_id")
    
    # Update user KYC status if approved
    if data.status == KYCStatus.APPROVED:
        if user_id:
            user_query = {"_id": user_id}
            try:
                user_query = {"$or": [{"_id": user_id}, {"_id": ObjectId(str(user_id))}]}
            except (InvalidId, TypeError):
                pass
            await db.users.update_one(user_query, {"$set": {"kyc_verified": True}})
            
            # Create notification for user
            notification_service = NotificationService(db)
            await notification_service.create_notification(
                user_id=str(user_id),
                notification_type="KYC",
                title="KYC Approved",
                message="Your KYC verification has been approved. You can now use all banking features.",
                action_url="/dashboard"
            )
    elif data.status == KYCStatus.REJECTED:
        # Create notification for rejected KYC
        if user_id:
            notification_service = NotificationService(db)
            await notification_service.create_notification(
                user_id=str(user_id),
                notification_type="KYC",
                title="KYC Requires Attention",
                message=f"Your KYC verification needs attention. {data.rejection_reason or 'Please review and resubmit your documents.'}",
                action_url="/settings/kyc"
            )
    
    # Get user email for logging
    user_doc = await db.users.find_one({"_id": user_id}) if user_id else None
    if not user_doc and user_id:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(str(user_id))})
        except InvalidId:
            pass
    
    user_email = user_doc.get("email", "unknown") if user_doc else "unknown"
    logger.warning(
        f"KYC REVIEW: Application {application_id} for user {user_email} "
        f"was {data.status.value} by admin {current_user['email']}"
    )
    
    return {"message": f"KYC application {data.status.value}"}


@admin_router.delete("/{application_id}")
async def delete_kyc_application(
    application_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    DELETE a KYC application entirely (Admin only).
    This removes the KYC application so the user can start fresh.
    DANGEROUS: Use with caution. Creates audit trail.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    kyc_app = await db.kyc_applications.find_one({"_id": application_id})
    if not kyc_app:
        try:
            kyc_app = await db.kyc_applications.find_one({"_id": ObjectId(application_id)})
        except InvalidId:
            pass
    
    if not kyc_app:
        raise HTTPException(status_code=404, detail="KYC application not found")
    
    user_id = kyc_app.get("user_id")
    status = kyc_app.get("status")
    
    # Get user info for audit
    user_doc = await db.users.find_one({"_id": user_id}) if user_id else None
    if not user_doc and user_id:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(str(user_id))})
        except InvalidId:
            pass
    
    user_email = user_doc.get("email", "unknown") if user_doc else "unknown"
    
    # Delete the application
    result = await db.kyc_applications.delete_one({"_id": kyc_app["_id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete KYC application")
    
    # If user was KYC verified, revert that
    if status == "APPROVED" and user_doc:
        await db.users.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {"kyc_verified": False}}
        )
        logger.warning(f"KYC DELETE: User {user_email} kyc_verified status reverted to False")
    
    # Audit log
    logger.warning(
        f"KYC DELETE: Application {application_id} for user {user_email} "
        f"(status was {status}) deleted by admin {current_user['email']}"
    )
    
    return {
        "success": True,
        "message": f"KYC application for {user_email} has been deleted",
        "application_id": application_id,
        "status_was": status
    }


@admin_router.patch("/{application_id}")
async def edit_kyc_application(
    application_id: str,
    updates: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    EDIT a KYC application (before approval).
    Allows updating personal information and document references.
    Creates audit trail of all changes.
    Only allowed for pending statuses.
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    
    kyc_app = await db.kyc_applications.find_one({"_id": application_id})
    if not kyc_app:
        try:
            kyc_app = await db.kyc_applications.find_one({"_id": ObjectId(application_id)})
        except InvalidId:
            pass
    
    if not kyc_app:
        raise HTTPException(status_code=404, detail="KYC application not found")
    
    status = kyc_app.get("status")
    if status == "APPROVED":
        raise HTTPException(
            status_code=400, 
            detail="Cannot edit approved KYC applications. Contact compliance team for approved application changes."
        )
    
    changes_made = {}
    allowed_fields = [
        "full_name", "date_of_birth", "nationality", "country_of_residence",
        "address", "city", "postal_code", "tax_residency", "tax_id",
        "passport_document", "proof_of_address_document", "selfie_document"
    ]
    
    update_data = {}
    for field, new_value in updates.items():
        if field in allowed_fields:
            old_value = kyc_app.get(field)
            if old_value != new_value:
                update_data[field] = new_value
                changes_made[field] = {"old": old_value, "new": new_value}
    
    if not update_data:
        return {
            "success": True,
            "message": "No changes detected",
            "changes": {}
        }
    
    update_data["edited_at"] = datetime.now(timezone.utc)
    update_data["edited_by"] = current_user["id"]
    
    result = await db.kyc_applications.update_one(
        {"_id": kyc_app["_id"]},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update KYC application")
    
    user_doc = await db.users.find_one({"_id": kyc_app.get("user_id")})
    if not user_doc:
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(str(kyc_app.get("user_id")))})
        except InvalidId:
            pass
    
    user_email = user_doc.get("email", "unknown") if user_doc else "unknown"
    
    logger.warning(
        f"KYC EDIT: Application {application_id} for user {user_email} "
        f"edited by admin {current_user['email']}. Changes: {list(changes_made.keys())}"
    )
    
    return {
        "success": True,
        "message": f"KYC application for {user_email} has been updated",
        "application_id": application_id,
        "changes": changes_made
    }
