"""Transfer service for P2P transfers."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
import uuid

from services.ledger_service import LedgerEngine
from core.ledger import EntryDirection


class TransferService:
    def __init__(self, db: AsyncIOMotorDatabase, ledger_engine: LedgerEngine):
        self.db = db
        self.ledger = ledger_engine
    
    async def p2p_transfer(
        self,
        from_user_id: str,
        to_iban: str,
        amount: int,
        reason: str = "P2P Transfer"
    ):
        """Transfer money between two customers using IBAN."""
        from bson import ObjectId
        from bson.errors import InvalidId
        
        # Normalize IBAN (remove spaces)
        normalized_iban = to_iban.replace(" ", "").upper()
        
        # Find recipient's bank account by IBAN
        to_account = await self.db.bank_accounts.find_one({"iban": normalized_iban})
        if not to_account:
            raise HTTPException(status_code=404, detail="Recipient IBAN not found")
        
        to_user_id = to_account["user_id"]
        
        if to_user_id == from_user_id:
            raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
        
        # Get recipient user details
        to_user = await self.db.users.find_one({"_id": to_user_id})
        if not to_user:
            # Try with ObjectId
            try:
                to_user = await self.db.users.find_one({"_id": ObjectId(to_user_id)})
            except:
                pass
        
        # Get sender's account
        from_account = await self.db.bank_accounts.find_one({"user_id": from_user_id})
        if not from_account:
            raise HTTPException(status_code=404, detail="Your account not found")
        
        # Check balance
        sender_balance = await self.ledger.get_balance(from_account["ledger_account_id"])
        if sender_balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        # Execute transfer
        txn = await self.ledger.post_transaction(
            transaction_type="P2P_TRANSFER",
            entries=[
                (from_account["ledger_account_id"], amount, EntryDirection.DEBIT),
                (to_account["ledger_account_id"], amount, EntryDirection.CREDIT)
            ],
            external_id=f"p2p_{uuid.uuid4()}",
            reason=reason,
            performed_by=from_user_id,
            metadata={
                "from_user": from_user_id,
                "to_user": to_user_id,
                "to_iban": normalized_iban
            }
        )
        
        # Build recipient name
        recipient_name = "Unknown"
        if to_user:
            first = to_user.get('first_name', '')
            last = to_user.get('last_name', '')
            recipient_name = f"{first} {last}".strip() or to_user.get('email', 'Unknown')
        
        return {
            "transaction_id": txn.id,
            "amount": amount,
            "recipient": recipient_name,
            "recipient_iban": normalized_iban,
            "status": "POSTED"
        }
