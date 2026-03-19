"""
Support Tickets Router.

Handles all support ticket operations for both customers and admins.

Routes:
- Customer: /api/v1/tickets/*
- Admin: /api/v1/admin/tickets/*
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
import urllib.request
import io

from database import get_database
from services.auth_service import AuthService
from services.ticket_service import TicketService, MAX_FILES_PER_MESSAGE
from services.notification_service import NotificationService
from schemas.tickets import TicketCreate, MessageCreate, TicketStatus, Ticket, MessageAttachment
from providers import CloudinaryStorage
from utils.common import serialize_doc

from .dependencies import get_current_user, require_admin, create_audit_log

# Storage provider dependency (imported from server.py pattern)
def get_storage():
    """Get the configured storage provider."""
    # Always use Cloudinary for this application
    return CloudinaryStorage()


# Router definitions
router = APIRouter(prefix="/api/v1", tags=["tickets"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin-tickets"])


# ==================== CUSTOMER TICKET ROUTES ====================

@router.post("/tickets/create")
async def create_ticket(
    data: TicketCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new support ticket."""
    auth_service = AuthService(db)
    user = await auth_service.get_user(current_user["id"])
    
    if user:
        user_name = f"{user.first_name} {user.last_name}"
    else:
        user_name = current_user.get("email", "Customer")
    
    ticket_service = TicketService(db)
    ticket = await ticket_service.create_ticket(
        user_id=current_user["id"],
        user_name=user_name,
        data=data
    )
    return ticket.model_dump()


@router.get("/tickets")
async def get_my_tickets(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get current user's tickets with unread counts."""
    ticket_service = TicketService(db)
    tickets = await ticket_service.get_user_tickets(current_user["id"])
    return tickets


# MIME type mapping for inline file viewing
MIME_TYPES = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'png': 'image/png', 'gif': 'image/gif',
    'webp': 'image/webp', 'bmp': 'image/bmp',
    'txt': 'text/plain', 'csv': 'text/csv',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
}


@router.get("/tickets/view-file")
async def view_file_inline(
    url: str = Query(..., description="Cloudinary file URL"),
    filename: str = Query(..., description="Original filename with extension"),
    current_user: dict = Depends(get_current_user)
):
    """Proxy a Cloudinary file and serve it with Content-Disposition: inline.
    
    This allows browsers to display PDFs and images inline instead of forcing download.
    Only allows proxying from the configured Cloudinary account.
    """
    from config import settings
    
    # Security: only allow proxying Cloudinary URLs from our account
    allowed_prefix = f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/"
    if not url.startswith(allowed_prefix):
        raise HTTPException(status_code=400, detail="Invalid file URL")
    
    # Determine content type from filename
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    content_type = MIME_TYPES.get(ext, 'application/octet-stream')
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            file_data = response.read()
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=86400",
            }
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch file")


@router.post("/tickets/{ticket_id}/mark-read")
async def user_mark_ticket_read(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark a ticket as read by the user (resets unread message count)."""
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket_doc["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {"user_last_read_at": datetime.now(timezone.utc)}}
    )
    
    return {"success": True, "ticket_id": ticket_id}


@router.post("/tickets/{ticket_id}/messages")
async def add_ticket_message(
    ticket_id: str,
    data: MessageCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Add a message to a ticket."""
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket_doc["user_id"] != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    auth_service = AuthService(db)
    user = await auth_service.get_user(current_user["id"])
    is_staff = current_user["role"] in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]
    
    if user:
        sender_name = f"{user.first_name} {user.last_name}"
    else:
        sender_name = current_user.get("email", "Customer")
    
    ticket_service = TicketService(db, storage)
    ticket = await ticket_service.add_message(
        ticket_id=ticket_id,
        sender_id=current_user["id"],
        sender_name=sender_name,
        is_staff=is_staff,
        data=data
    )
    
    # Create notification for user when staff replies
    if is_staff and ticket_doc["user_id"] != current_user["id"]:
        notification_service = NotificationService(db)
        await notification_service.create_or_update_support_reply_notification(
            user_id=ticket_doc["user_id"],
            ticket_id=ticket_id,
            ticket_subject=ticket_doc.get('subject', 'Support Ticket'),
            action_url="/support"
        )
    
    return ticket.model_dump()


@router.post("/tickets/{ticket_id}/upload")
async def upload_ticket_attachment(
    ticket_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Upload file attachments for a ticket message."""
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket_doc["user_id"] != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if len(files) > MAX_FILES_PER_MESSAGE:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {MAX_FILES_PER_MESSAGE} files allowed per upload"
        )
    
    ticket_service = TicketService(db, storage)
    
    uploaded_attachments = []
    for file in files:
        attachment = await ticket_service.upload_attachment(
            ticket_id=ticket_id,
            user_id=current_user["id"],
            file=file
        )
        uploaded_attachments.append(attachment.model_dump())
    
    return {"attachments": uploaded_attachments}


@router.post("/tickets/{ticket_id}/messages/with-attachments")
async def add_ticket_message_with_attachments(
    ticket_id: str,
    content: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    storage: CloudinaryStorage = Depends(get_storage)
):
    """Add a message with optional file attachments to a ticket."""
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket_doc["user_id"] != current_user["id"] and current_user["role"] not in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if len(files) > MAX_FILES_PER_MESSAGE:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {MAX_FILES_PER_MESSAGE} files allowed per message"
        )
    
    auth_service = AuthService(db)
    user = await auth_service.get_user(current_user["id"])
    is_staff = current_user["role"] in ["ADMIN", "SUPER_ADMIN", "SUPPORT_AGENT"]
    
    if user:
        sender_name = f"{user.first_name} {user.last_name}"
    else:
        sender_name = current_user.get("email", "Customer")
    
    ticket_service = TicketService(db, storage)
    
    # Upload attachments if any
    attachments = []
    for file in files:
        if file.filename:
            attachment = await ticket_service.upload_attachment(
                ticket_id=ticket_id,
                user_id=current_user["id"],
                file=file
            )
            attachments.append(attachment)
    
    # Add message with attachments
    ticket = await ticket_service.add_message(
        ticket_id=ticket_id,
        sender_id=current_user["id"],
        sender_name=sender_name,
        is_staff=is_staff,
        data=MessageCreate(content=content),
        attachments=attachments
    )
    
    # Create notification for user when staff replies
    if is_staff and ticket_doc["user_id"] != current_user["id"]:
        notification_service = NotificationService(db)
        await notification_service.create_or_update_support_reply_notification(
            user_id=ticket_doc["user_id"],
            ticket_id=ticket_id,
            ticket_subject=ticket_doc.get('subject', 'Support Ticket'),
            action_url="/support"
        )
    
    return ticket.model_dump()


@router.get("/tickets/{ticket_id}")
async def get_single_ticket_user(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get a single ticket with full messages (user)."""
    ticket_doc = await db.tickets.find_one({
        "_id": ticket_id,
        "user_id": current_user["id"]
    })
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = Ticket(**serialize_doc(ticket_doc))
    return ticket.model_dump()


# ==================== ADMIN TICKET ROUTES ====================

@admin_router.get("/tickets")
async def get_all_tickets(
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all tickets (admin) with user information and unread counts."""
    ticket_service = TicketService(db)
    tickets = await ticket_service.get_all_tickets(status_filter=status, search_query=search)
    return tickets


@admin_router.get("/tickets/{ticket_id}")
async def get_single_ticket_admin(
    ticket_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get a single ticket with full messages (admin)."""
    from bson import ObjectId
    
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = Ticket(**serialize_doc(ticket_doc))
    ticket_dict = ticket.model_dump()
    
    # Add user info
    user_id = ticket_doc.get("user_id")
    if user_id:
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            user = None
        if not user:
            user = await db.users.find_one({"_id": user_id})
        if user:
            ticket_dict["user_email"] = user.get("email", "")
            ticket_dict["user_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    
    return ticket_dict


class UpdateTicketStatus(BaseModel):
    status: TicketStatus


@admin_router.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    data: UpdateTicketStatus,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update ticket status (admin)."""
    ticket_service = TicketService(db)
    ticket = await ticket_service.update_ticket_status(
        ticket_id=ticket_id,
        new_status=data.status,
        assigned_to=current_user["id"]
    )
    
    await create_audit_log(
        db=db,
        action="TICKET_STATUS_CHANGED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Ticket status changed to {data.status.value}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"new_status": data.status.value, "subject": ticket.subject}
    )
    
    return ticket.model_dump()


class UpdateTicketSubject(BaseModel):
    subject: str


class UpdateTicketMessage(BaseModel):
    content: str


@admin_router.patch("/tickets/{ticket_id}/subject")
async def update_ticket_subject(
    ticket_id: str,
    data: UpdateTicketSubject,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update ticket subject (admin only)."""
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    old_subject = ticket_doc.get("subject", "")
    
    await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {
            "subject": data.subject,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    await create_audit_log(
        db=db,
        action="TICKET_SUBJECT_UPDATED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Ticket subject updated from '{old_subject}' to '{data.subject}'",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={"old_subject": old_subject, "new_subject": data.subject}
    )
    
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    return serialize_doc(ticket_doc)


@admin_router.patch("/tickets/{ticket_id}/messages/{message_index}")
async def update_ticket_message(
    ticket_id: str,
    message_index: int,
    data: UpdateTicketMessage,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a specific message in a ticket (admin only)."""
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    messages = ticket_doc.get("messages", [])
    if message_index < 0 or message_index >= len(messages):
        raise HTTPException(status_code=404, detail="Message not found")
    
    old_content = messages[message_index].get("content", "")
    
    await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {
            f"messages.{message_index}.content": data.content,
            f"messages.{message_index}.edited_at": datetime.now(timezone.utc),
            f"messages.{message_index}.edited_by": current_user["id"],
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    await create_audit_log(
        db=db,
        action="TICKET_MESSAGE_UPDATED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Ticket message {message_index + 1} was edited",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "message_index": message_index,
            "old_content_preview": old_content[:100] if len(old_content) > 100 else old_content,
            "new_content_preview": data.content[:100] if len(data.content) > 100 else data.content
        }
    )
    
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    return serialize_doc(ticket_doc)


@admin_router.delete("/tickets/{ticket_id}/messages/{message_index}")
async def delete_ticket_message(
    ticket_id: str,
    message_index: int,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a specific message from a ticket (admin only)."""
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    messages = ticket_doc.get("messages", [])
    if message_index < 0 or message_index >= len(messages):
        raise HTTPException(status_code=404, detail="Message not found")
    
    deleted_message = messages[message_index]
    deleted_content = deleted_message.get("content", "")
    deleted_sender = deleted_message.get("sender_name", "Unknown")
    
    messages.pop(message_index)
    
    await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {
            "messages": messages,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    await create_audit_log(
        db=db,
        action="TICKET_MESSAGE_DELETED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Message from '{deleted_sender}' was deleted from ticket",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "message_index": message_index,
            "deleted_sender": deleted_sender,
            "deleted_content_preview": deleted_content[:100] if len(deleted_content) > 100 else deleted_content
        }
    )
    
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    return serialize_doc(ticket_doc)


@admin_router.delete("/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Permanently delete a support ticket (admin only)."""
    ticket_doc = await db.tickets.find_one({"_id": ticket_id})
    if not ticket_doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    result = await db.tickets.delete_one({"_id": ticket_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete ticket")
    
    await create_audit_log(
        db=db,
        action="TICKET_DELETED",
        entity_type="ticket",
        entity_id=ticket_id,
        description=f"Support ticket '{ticket_doc.get('subject', 'Unknown')}' was permanently deleted",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "ticket_subject": ticket_doc.get("subject"),
            "ticket_status": ticket_doc.get("status"),
            "user_id": ticket_doc.get("user_id"),
            "messages_count": len(ticket_doc.get("messages", []))
        }
    )
    
    return {"message": "Ticket deleted successfully", "ticket_id": ticket_id}


class AdminTicketCreate(BaseModel):
    user_id: str
    subject: str
    description: str


@admin_router.post("/tickets/create-for-user")
async def admin_create_ticket_for_user(
    data: AdminTicketCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Admin creates a support ticket on behalf of a user."""
    from bson import ObjectId
    from bson.errors import InvalidId
    
    user_query = {"_id": data.user_id}
    try:
        user_query = {"$or": [{"_id": data.user_id}, {"_id": ObjectId(data.user_id)}]}
    except (InvalidId, TypeError):
        pass
    
    user = await db.users.find_one(user_query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", "Customer")
    
    ticket_service = TicketService(db)
    ticket = await ticket_service.create_ticket_by_admin(
        user_id=user_id,
        user_name=user_name,
        subject=data.subject,
        description=data.description,
        admin_id=current_user["id"],
        admin_name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip() or "Support"
    )
    
    notification_service = NotificationService(db)
    await notification_service.create_notification(
        user_id=user_id,
        notification_type="SUPPORT",
        title="New Support Ticket",
        message=f"A support ticket has been created for you: {data.subject}",
        action_url="/support",
        metadata={
            "ticket_id": ticket.id,
            "created_by_support": True
        }
    )
    
    await create_audit_log(
        db=db,
        action="TICKET_CREATED_BY_ADMIN",
        entity_type="ticket",
        entity_id=ticket.id,
        description=f"Admin created support ticket for user {user.get('email', user_id)}",
        performed_by=current_user["id"],
        performed_by_role=current_user["role"],
        performed_by_email=current_user["email"],
        metadata={
            "target_user_id": user_id,
            "target_user_email": user.get("email"),
            "ticket_subject": data.subject
        }
    )
    
    return ticket.model_dump()


@admin_router.post("/tickets/{ticket_id}/mark-read")
async def admin_mark_ticket_read(
    ticket_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark a ticket as read by admin (resets unread message count)."""
    result = await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {"admin_last_read_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {"success": True, "ticket_id": ticket_id}
