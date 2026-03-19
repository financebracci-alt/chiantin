"""Audit log models and schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    
    # Who performed the action
    performed_by: str  # User ID
    performed_by_role: str
    performed_by_email: str
    
    # What action
    action: str  # e.g., "USER_DISABLED", "KYC_APPROVED", "LEDGER_TOP_UP"
    entity_type: str  # e.g., "user", "kyc_application", "ledger_transaction"
    entity_id: str
    
    # Details
    description: str
    before_value: Optional[Dict[str, Any]] = None
    after_value: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    
    # Request metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True