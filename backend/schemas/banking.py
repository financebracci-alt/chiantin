"""Banking models and schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum
from bson import ObjectId


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class TransactionDisplayType(str, Enum):
    """How the transaction appears to the customer - like a real bank."""
    SEPA_TRANSFER = "SEPA Transfer"
    WIRE_TRANSFER = "Wire Transfer"
    INTERNAL_TRANSFER = "Internal Transfer"
    SALARY_PAYMENT = "Salary Payment"
    REFUND = "Refund"
    BANK_TRANSFER = "Bank Transfer"
    CASH_DEPOSIT = "Cash Deposit"
    INTEREST = "Interest Payment"
    BONUS = "Bonus"
    CORRECTION = "Account Correction"
    OTHER = "Other"


class AdminCreditRequest(BaseModel):
    """Request model for admin credit (top-up) with professional display options."""
    amount: int  # In cents
    
    # How it appears to the customer (professional banking display)
    display_type: TransactionDisplayType = TransactionDisplayType.BANK_TRANSFER
    sender_name: Optional[str] = None  # e.g., "Deutsche Bank AG", "ABC Company Ltd"
    sender_iban: Optional[str] = None  # e.g., "DE89370400440532013000"
    sender_bic: Optional[str] = None   # e.g., "DEUTDEDB"
    reference: Optional[str] = None    # e.g., "TRF2024011500123", "Invoice #1234"
    description: Optional[str] = None  # e.g., "Salary Payment January 2024"
    
    # Internal admin note (not shown to customer)
    admin_note: Optional[str] = None


class AdminDebitRequest(BaseModel):
    """Request model for admin debit (withdrawal) with professional display options."""
    amount: int  # In cents
    
    # How it appears to the customer
    display_type: str = "Withdrawal"
    recipient_name: Optional[str] = None
    recipient_iban: Optional[str] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    
    # Internal admin note
    admin_note: Optional[str] = None


class BankAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    
    account_number: str  # Internal account number
    iban: Optional[str] = None  # Sandbox IBAN
    bic: Optional[str] = None
    
    currency: str = "EUR"
    status: AccountStatus = AccountStatus.ACTIVE
    
    ledger_account_id: str  # Link to ledger account
    
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


class AccountResponse(BaseModel):
    id: str
    account_number: str
    iban: Optional[str] = None
    currency: str
    status: AccountStatus
    balance: int  # Derived from ledger
    opened_at: datetime