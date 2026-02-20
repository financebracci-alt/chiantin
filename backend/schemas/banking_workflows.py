"""Complete banking workflows schemas - Cards, Transfers, Recipients."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid


# ==================== CARD REQUESTS ====================

class CardType(str, Enum):
    DEBIT_PHYSICAL = "DEBIT_PHYSICAL"
    VIRTUAL = "VIRTUAL"


class CardRequestStatus(str, Enum):
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class CardStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class CardRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    account_id: str
    card_type: CardType
    status: CardRequestStatus = CardRequestStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = None
    decided_by_admin_id: Optional[str] = None
    reject_reason: Optional[str] = None
    
    class Config:
        populate_by_name = True


class CreateCardRequest(BaseModel):
    account_id: str
    card_type: CardType


class Card(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    account_id: str
    request_id: str
    card_type: CardType
    status: CardStatus = CardStatus.ACTIVE
    
    cardholder_name: str
    billing_address_line1: str
    billing_address_line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    
    pan: str  # Plain text for prototype
    exp_month: int
    exp_year: int
    cvv: str  # Plain text for prototype
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class FulfillCardRequest(BaseModel):
    cardholder_name: str
    billing_address_line1: str
    billing_address_line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    pan: str
    exp_month: int
    exp_year: int
    cvv: str


# ==================== TRANSFERS ====================

class TransferStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class TransferRecipient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    name: str
    iban: str  # Not used for internal crediting, display only
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class CreateRecipient(BaseModel):
    name: str
    iban: str


class ConfirmationEmailStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Transfer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    from_account_id: str
    beneficiary_name: str
    beneficiary_iban: str  # Display only
    amount: int  # In cents
    currency: str = "EUR"
    details: str
    reference_number: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    attachment_url: Optional[str] = None
    
    status: TransferStatus = TransferStatus.SUBMITTED
    reject_reason: Optional[str] = None
    
    # Email confirmation tracking - comprehensive status
    confirmation_email_sent: bool = False  # Legacy field for backwards compatibility
    confirmation_email_status: ConfirmationEmailStatus = ConfirmationEmailStatus.PENDING
    confirmation_email_sent_at: Optional[datetime] = None
    confirmation_email_provider_id: Optional[str] = None  # Resend message ID
    confirmation_email_error: Optional[str] = None  # Error message if failed
    
    # Rejection email tracking - for idempotency
    rejection_email_sent: bool = False
    rejection_email_sent_at: Optional[datetime] = None
    rejection_email_provider_id: Optional[str] = None
    rejection_email_error: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    admin_action_by: Optional[str] = None
    admin_action_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


class CreateTransfer(BaseModel):
    from_account_id: str
    beneficiary_name: str
    beneficiary_iban: str
    amount: int
    currency: str = "EUR"
    details: str
    reference_number: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    attachment_url: Optional[str] = None


# ==================== ADMIN ADJUSTMENTS ====================

class AdjustmentType(str, Enum):
    TOPUP = "TOPUP"
    WITHDRAW = "WITHDRAW"


class AdminAdjustment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    admin_id: str
    account_id: str
    adjustment_type: AdjustmentType
    amount: int  # In cents
    currency: str = "EUR"
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class CreateAdjustment(BaseModel):
    account_id: str
    adjustment_type: AdjustmentType
    amount: int
    reason: str
