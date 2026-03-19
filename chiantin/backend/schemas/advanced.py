"""Transaction categories and scheduled payments schemas."""

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional
from enum import Enum
import uuid


class TransactionCategory(str, Enum):
    FOOD_DINING = "FOOD_DINING"
    TRANSPORT = "TRANSPORT"
    SHOPPING = "SHOPPING"
    BILLS_UTILITIES = "BILLS_UTILITIES"
    ENTERTAINMENT = "ENTERTAINMENT"
    HEALTHCARE = "HEALTHCARE"
    TRANSFER = "TRANSFER"
    SALARY = "SALARY"
    OTHER = "OTHER"


class RecurringFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class ScheduledPayment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    
    recipient_email: str
    amount: int  # In cents
    reason: str
    
    frequency: RecurringFrequency
    start_date: datetime  # Changed from date to datetime for MongoDB
    end_date: Optional[datetime] = None  # Changed from date to datetime
    
    active: bool = True
    last_executed: Optional[datetime] = None
    next_execution: datetime
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class CreateScheduledPayment(BaseModel):
    recipient_email: str
    amount: int
    reason: str
    frequency: RecurringFrequency
    start_date: str  # Accept as string (YYYY-MM-DD) from frontend
    end_date: Optional[str] = None


class Beneficiary(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    
    recipient_name: str
    recipient_email: str
    
    nickname: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


class CreateBeneficiary(BaseModel):
    recipient_email: str
    recipient_name: str
    nickname: Optional[str] = None
