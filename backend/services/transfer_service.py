"""Transfer service for P2P and SEPA transfers."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
import uuid
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from services.ledger_service import LedgerEngine
from core.ledger import EntryDirection


class TransferService:
    def __init__(self, db: AsyncIOMotorDatabase, ledger_engine: LedgerEngine):
        self.db = db
        self.ledger = ledger_engine
    
    async def _find_bank_account_by_user(self, user_id: str):
        """Find bank account by user_id, handling both string and ObjectId formats."""
        # Try as string first
        account = await self.db.bank_accounts.find_one({"user_id": user_id})
        if account:
            return account
        
        # Try as ObjectId
        try:
            account = await self.db.bank_accounts.find_one({"user_id": ObjectId(user_id)})
            if account:
                return account
        except:
            pass
        
        # Try converting ObjectId to string match
        try:
            account = await self.db.bank_accounts.find_one({"user_id": str(user_id)})
            if account:
                return account
        except:
            pass
        
        return None
    
    async def _get_user_details(self, user_id):
        """Get user details, handling ObjectId/string formats."""
        user = await self.db.users.find_one({"_id": user_id})
        if not user:
            try:
                user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            except:
                pass
        if not user:
            user = await self.db.users.find_one({"_id": str(user_id)})
        return user
    
    async def p2p_transfer(
        self,
        from_user_id: str,
        to_iban: str,
        amount: int,
        reason: str = "SEPA Transfer",
        recipient_name: str = None
    ):
        """Transfer money to any IBAN - internal or SEPA."""
        
        # Normalize IBAN (remove spaces)
        normalized_iban = to_iban.replace(" ", "").upper()
        
        # Get sender's account
        from_account = await self._find_bank_account_by_user(from_user_id)
        if not from_account:
            raise HTTPException(status_code=404, detail="Your account not found")
        
        # Get sender user details
        from_user = await self._get_user_details(from_user_id)
        sender_name = "Unknown"
        if from_user:
            first = from_user.get('first_name', '')
            last = from_user.get('last_name', '')
            sender_name = f"{first} {last}".strip() or from_user.get('email', 'Unknown')
        
        # Check if sender is trying to send to themselves
        if from_account.get("iban") == normalized_iban:
            raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
        
        # Check sender's balance
        sender_balance = await self.ledger.get_balance(from_account["ledger_account_id"])
        if sender_balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        # Try to find recipient's bank account by IBAN (internal transfer)
        to_account = await self.db.bank_accounts.find_one({"iban": normalized_iban})
        
        # Current time with correct timezone (UTC+1 for Europe)
        now = datetime.now(timezone.utc)
        
        if to_account:
            # INTERNAL TRANSFER - recipient exists in our system
            to_user_id = to_account["user_id"]
            
            # Check not sending to self
            if str(to_user_id) == str(from_user_id):
                raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
            
            # Get recipient user details
            to_user = await self._get_user_details(to_user_id)
            final_recipient_name = "Unknown"
            if to_user:
                first = to_user.get('first_name', '')
                last = to_user.get('last_name', '')
                final_recipient_name = f"{first} {last}".strip() or to_user.get('email', 'Unknown')
            
            # Execute internal transfer immediately (debit sender, credit recipient)
            txn = await self.ledger.post_transaction(
                transaction_type="SEPA_TRANSFER",
                entries=[
                    (from_account["ledger_account_id"], amount, EntryDirection.DEBIT),
                    (to_account["ledger_account_id"], amount, EntryDirection.CREDIT)
                ],
                external_id=f"sepa_{uuid.uuid4()}",
                reason=reason,
                performed_by=str(from_user_id),
                metadata={
                    "from_user": str(from_user_id),
                    "to_user": str(to_user_id),
                    "to_iban": normalized_iban,
                    "transfer_type": "INTERNAL"
                }
            )
            
            # Store in transfers collection for admin visibility
            transfer_id = str(uuid.uuid4())
            transfer_record = {
                "_id": transfer_id,
                "user_id": str(from_user_id),
                "transaction_id": txn.id,
                "type": "SEPA_TRANSFER",
                "beneficiary_name": final_recipient_name,
                "beneficiary_iban": normalized_iban,
                "amount": amount,
                "details": reason,
                "reference_number": f"SEPA-{transfer_id[:8].upper()}",
                "status": "COMPLETED",  # Internal transfers complete immediately
                "transfer_type": "INTERNAL",
                "sender_name": sender_name,
                "sender_iban": from_account.get("iban"),
                "created_at": now,
                "updated_at": now,
                "completed_at": now
            }
            await self.db.transfers.insert_one(transfer_record)
            
            return {
                "transaction_id": txn.id,
                "transfer_id": transfer_id,
                "amount": amount,
                "recipient": final_recipient_name,
                "recipient_iban": normalized_iban,
                "status": "COMPLETED",
                "transfer_type": "SEPA_TRANSFER"
            }
        
        else:
            # SEPA TRANSFER - recipient IBAN not in our system
            # Deduct from sender's balance, but mark as SUBMITTED for admin review
            
            # Create SEPA outgoing ledger account if it doesn't exist
            sepa_account = await self.db.ledger_accounts.find_one({"type": "SEPA_OUTGOING"})
            if not sepa_account:
                sepa_account = {
                    "_id": f"sepa_outgoing_{uuid.uuid4()}",
                    "type": "SEPA_OUTGOING",
                    "name": "SEPA Outgoing Transfers",
                    "currency": "EUR",
                    "created_at": now
                }
                await self.db.ledger_accounts.insert_one(sepa_account)
            
            # Execute SEPA transfer (debit sender, credit SEPA account)
            txn = await self.ledger.post_transaction(
                transaction_type="SEPA_TRANSFER",
                entries=[
                    (from_account["ledger_account_id"], amount, EntryDirection.DEBIT),
                    (sepa_account["_id"], amount, EntryDirection.CREDIT)
                ],
                external_id=f"sepa_{uuid.uuid4()}",
                reason=reason,
                performed_by=str(from_user_id),
                metadata={
                    "from_user": str(from_user_id),
                    "to_iban": normalized_iban,
                    "recipient_name": recipient_name or "SEPA Recipient",
                    "transfer_type": "SEPA"
                }
            )
            
            # Store in transfers collection for admin panel
            transfer_id = str(uuid.uuid4())
            transfer_record = {
                "_id": transfer_id,
                "user_id": str(from_user_id),
                "transaction_id": txn.id,
                "type": "SEPA_TRANSFER",
                "beneficiary_name": recipient_name or "SEPA Recipient",
                "beneficiary_iban": normalized_iban,
                "amount": amount,
                "details": reason,
                "reference_number": f"SEPA-{transfer_id[:8].upper()}",
                "status": "SUBMITTED",  # Pending admin review
                "transfer_type": "SEPA",
                "sender_name": sender_name,
                "sender_iban": from_account.get("iban"),
                "created_at": now,
                "updated_at": now
            }
            await self.db.transfers.insert_one(transfer_record)
            
            return {
                "transaction_id": txn.id,
                "transfer_id": transfer_id,
                "amount": amount,
                "recipient": recipient_name or "SEPA Recipient",
                "recipient_iban": normalized_iban,
                "status": "COMPLETED",  # User sees it as completed (money deducted)
                "transfer_type": "SEPA_TRANSFER",
                "admin_status": "SUBMITTED"  # But admin will see it as submitted
            }
