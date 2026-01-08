"""Ledger data models (Pydantic schemas).

Design principles:
- Amounts stored as integers in minor units (cents, not dollars)
- Append-only: no updates/deletes on entries after posting
- Double-entry: every transaction must balance (debits = credits per currency)
- Reversals create new entries, never modify originals
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId


class AccountType(str, Enum):
    """Ledger account types."""
    # User accounts
    WALLET = "WALLET"  # Customer cash account
    
    # Internal accounts
    SANDBOX_FUNDING = "SANDBOX_FUNDING"  # Source for sandbox top-ups
    FEES = "FEES"  # Fee collection account
    SETTLEMENT = "SETTLEMENT"  # Settlement/clearing account
    

class TransactionStatus(str, Enum):
    """Transaction lifecycle status."""
    PENDING = "PENDING"  # Created but not posted
    POSTED = "POSTED"   # Successfully posted to ledger
    REVERSED = "REVERSED"  # Reversed by a reversal transaction


class EntryDirection(str, Enum):
    """Entry direction (double-entry bookkeeping)."""
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerAccount(BaseModel):
    """A ledger account (customer or internal).
    
    Balances are DERIVED from entries, never stored directly here.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    account_type: AccountType
    currency: str = "EUR"  # ISO 4217
    status: str = "ACTIVE"  # ACTIVE, FROZEN, CLOSED
    user_id: Optional[str] = None  # Set for customer accounts
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class LedgerEntry(BaseModel):
    """A single ledger entry (debit or credit to an account).
    
    IMMUTABLE after creation. Never update amount or direction.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    transaction_id: str  # References LedgerTransaction
    account_id: str  # References LedgerAccount
    amount: int  # In minor units (cents), always positive
    direction: EntryDirection
    currency: str = "EUR"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('amount must be positive')
        return v
    
    class Config:
        use_enum_values = True


class LedgerTransaction(BaseModel):
    """A financial transaction (groups multiple entries).
    
    Every transaction must balance: sum(debits) = sum(credits) per currency.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    external_id: Optional[str] = None  # Idempotency key
    transaction_type: str  # TOP_UP, WITHDRAW, FEE, TRANSFER, REVERSAL
    status: TransactionStatus
    value_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Reversal tracking
    reverses_txn_id: Optional[str] = None  # Set if this is a reversal
    reversed_by_txn_id: Optional[str] = None  # Set on original when reversed
    
    # Audit/metadata
    reason: Optional[str] = None  # Required for admin actions
    performed_by: Optional[str] = None  # User/admin ID
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True