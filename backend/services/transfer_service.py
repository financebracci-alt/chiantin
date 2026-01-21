"""Transfer service for P2P transfers."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
import uuid
from datetime import datetime, timezone

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
        reason: str = "P2P Transfer",
        recipient_name: str = None  # Optional recipient name for external transfers
    ):
        """Transfer money to any IBAN - internal or external."""
        from bson import ObjectId
        
        # Normalize IBAN (remove spaces)
        normalized_iban = to_iban.replace(" ", "").upper()
        
        # Get sender's account first
        from_account = await self.db.bank_accounts.find_one({"user_id": from_user_id})
        if not from_account:
            raise HTTPException(status_code=404, detail="Your account not found")
        
        # Check if sender is trying to send to themselves
        if from_account.get("iban") == normalized_iban:
            raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
        
        # Check sender's balance
        sender_balance = await self.ledger.get_balance(from_account["ledger_account_id"])
        if sender_balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        # Try to find recipient's bank account by IBAN (internal transfer)
        to_account = await self.db.bank_accounts.find_one({"iban": normalized_iban})
        
        if to_account:
            # INTERNAL TRANSFER - recipient exists in our system
            to_user_id = to_account["user_id"]
            
            if to_user_id == from_user_id:
                raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
            
            # Get recipient user details
            to_user = await self.db.users.find_one({"_id": to_user_id})
            if not to_user:
                try:
                    to_user = await self.db.users.find_one({"_id": ObjectId(to_user_id)})
                except:
                    pass
            
            # Execute internal transfer (debit sender, credit recipient)
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
                    "to_iban": normalized_iban,
                    "transfer_type": "INTERNAL"
                }
            )
            
            # Build recipient name from user data
            final_recipient_name = "Unknown"
            if to_user:
                first = to_user.get('first_name', '')
                last = to_user.get('last_name', '')
                final_recipient_name = f"{first} {last}".strip() or to_user.get('email', 'Unknown')
            
            return {
                "transaction_id": txn.id,
                "amount": amount,
                "recipient": final_recipient_name,
                "recipient_iban": normalized_iban,
                "status": "POSTED",
                "transfer_type": "INTERNAL"
            }
        
        else:
            # EXTERNAL TRANSFER - recipient IBAN not in our system
            # Just deduct from sender's balance and log the transfer
            
            # Create external outgoing ledger account if it doesn't exist
            external_account = await self.db.ledger_accounts.find_one({"type": "EXTERNAL_OUTGOING"})
            if not external_account:
                external_account = {
                    "_id": f"external_outgoing_{uuid.uuid4()}",
                    "type": "EXTERNAL_OUTGOING",
                    "name": "External Outgoing Transfers",
                    "created_at": datetime.now(timezone.utc)
                }
                await self.db.ledger_accounts.insert_one(external_account)
            
            # Execute external transfer (debit sender, credit external account)
            txn = await self.ledger.post_transaction(
                transaction_type="EXTERNAL_TRANSFER",
                entries=[
                    (from_account["ledger_account_id"], amount, EntryDirection.DEBIT),
                    (external_account["_id"], amount, EntryDirection.CREDIT)
                ],
                external_id=f"ext_{uuid.uuid4()}",
                reason=reason,
                performed_by=from_user_id,
                metadata={
                    "from_user": from_user_id,
                    "to_iban": normalized_iban,
                    "recipient_name": recipient_name or "External Account",
                    "transfer_type": "EXTERNAL"
                }
            )
            
            # Also store in a separate external_transfers collection for tracking
            external_transfer_record = {
                "_id": str(uuid.uuid4()),
                "transaction_id": txn.id,
                "from_user_id": from_user_id,
                "from_iban": from_account.get("iban"),
                "to_iban": normalized_iban,
                "recipient_name": recipient_name or "External Account",
                "amount": amount,
                "reason": reason,
                "status": "COMPLETED",
                "created_at": datetime.now(timezone.utc)
            }
            await self.db.external_transfers.insert_one(external_transfer_record)
            
            return {
                "transaction_id": txn.id,
                "amount": amount,
                "recipient": recipient_name or "External Account",
                "recipient_iban": normalized_iban,
                "status": "POSTED",
                "transfer_type": "EXTERNAL"
            }
