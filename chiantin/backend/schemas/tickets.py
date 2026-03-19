"""Support ticket models and schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum
from bson import ObjectId


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class MessageAttachment(BaseModel):
    """Attachment for ticket messages."""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    file_name: str
    file_size: int  # in bytes
    content_type: str
    url: str  # Cloudinary URL
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class TicketMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    sender_id: str
    sender_name: str
    is_staff: bool = False
    content: str
    attachments: List[MessageAttachment] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    
    subject: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.MEDIUM
    
    messages: List[TicketMessage] = Field(default_factory=list)
    
    assigned_to: Optional[str] = None  # Staff user ID
    
    # Track if ticket was created by admin/support
    created_by_admin: bool = False
    created_by_admin_id: Optional[str] = None
    
    # Track when admin last read the ticket (for unread message counting)
    admin_last_read_at: Optional[datetime] = None
    
    # Track when user/client last read the ticket (for unread message counting)
    user_last_read_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


class TicketCreate(BaseModel):
    subject: str
    description: str


class MessageCreate(BaseModel):
    content: str