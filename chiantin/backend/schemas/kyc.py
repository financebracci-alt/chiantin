"""KYC models and schemas."""

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum
from bson import ObjectId


class KYCStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DocumentType(str, Enum):
    PASSPORT = "PASSPORT"
    ID_CARD = "ID_CARD"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    PROOF_OF_ADDRESS = "PROOF_OF_ADDRESS"
    SELFIE = "SELFIE"


class KYCDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    document_type: DocumentType
    file_key: str  # S3 key
    file_name: str
    file_size: int
    content_type: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class KYCApplication(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    
    # Personal details (optional for draft state)
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None  # Changed from date to str
    nationality: Optional[str] = None
    
    # Address
    street_address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Tax
    tax_residency: Optional[str] = None
    tax_id: Optional[str] = None
    
    # Documents
    documents: List[KYCDocument] = Field(default_factory=list)
    
    # Status
    status: KYCStatus = KYCStatus.DRAFT
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None  # Admin user ID
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Consents
    terms_accepted: bool = False
    terms_accepted_at: Optional[datetime] = None
    privacy_accepted: bool = False
    privacy_accepted_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class KYCSubmitRequest(BaseModel):
    full_name: str
    date_of_birth: str  # Changed from date to str to accept YYYY-MM-DD format
    nationality: str
    street_address: str
    city: str
    postal_code: str
    country: str
    tax_residency: str
    tax_id: Optional[str] = None
    terms_accepted: bool
    privacy_accepted: bool


class KYCReviewRequest(BaseModel):
    status: KYCStatus
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    assigned_iban: Optional[str] = None  # Admin enters IBAN on approval
    assigned_bic: Optional[str] = None  # Admin enters BIC/SWIFT on approval