"""Notification models and schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum
from bson import ObjectId


class NotificationType(str, Enum):
    KYC_UPDATE = "KYC_UPDATE"
    TRANSACTION = "TRANSACTION"
    SECURITY = "SECURITY"
    ACCOUNT = "ACCOUNT"
    SUPPORT = "SUPPORT"


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    
    notification_type: NotificationType
    title: str
    message: str
    
    read: bool = False
    read_at: Optional[datetime] = None
    
    action_url: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    
    # Entity tracking for navigation
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    
    # Counter for grouped notifications (e.g., multiple ticket replies)
    reply_count: int = 1
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True