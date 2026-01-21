"""Transfer schemas."""

from pydantic import BaseModel
from typing import Optional


class P2PTransferRequest(BaseModel):
    to_iban: str  # Recipient's IBAN
    amount: int  # In cents
    reason: Optional[str] = "P2P Transfer"
    recipient_name: Optional[str] = None  # Optional - for external transfers
