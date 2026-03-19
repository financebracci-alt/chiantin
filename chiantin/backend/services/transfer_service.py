"""Transfer service for P2P and SEPA transfers."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
import uuid
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging

from services.ledger_service import LedgerEngine
from core.ledger import EntryDirection

logger = logging.getLogger(__name__)


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
    
    async def _send_transfer_confirmation_email(
        self,
        transfer_id: str,
        user_id: str,
        reference_number: str,
        amount: int,
        beneficiary_name: str,
        beneficiary_iban: str,
        sender_iban: str,
        transfer_type: str = "SEPA Transfer",
        transfer_date: datetime = None
    ) -> dict:
        """
        Send transfer confirmation email with comprehensive status tracking.
        Updates the transfer record with email status.
        Returns dict with success, provider_id, error, and email_warning.
        """
        from services.email_service import EmailService
        
        email_warning = None
        result = {'success': False, 'provider_id': None, 'error': None, 'email_warning': None}
        
        try:
            # Get user details for email
            user = await self._get_user_details(user_id)
            
            if not user:
                error_msg = f"User not found: {user_id}"
                logger.error(f"[TRANSFER EMAIL] {error_msg}")
                await self._update_transfer_email_status(transfer_id, False, None, error_msg)
                result['error'] = error_msg
                result['email_warning'] = f"Transfer submitted, but confirmation email could not be delivered: {error_msg}"
                return result
            
            user_email = user.get("email")
            if not user_email:
                error_msg = "User email not found in record"
                logger.error(f"[TRANSFER EMAIL] {error_msg} for user {user_id}")
                await self._update_transfer_email_status(transfer_id, False, None, error_msg)
                result['error'] = error_msg
                result['email_warning'] = f"Transfer submitted, but confirmation email could not be delivered: {error_msg}"
                return result
            
            email_service = EmailService()
            
            # Get user's preferred language (default to 'en')
            language = user.get("language", "en") or "en"
            first_name = user.get("first_name", "")
            
            logger.info(f"[TRANSFER EMAIL] Sending email: transferId={transfer_id}, recipient={user_email}, lang={language}, ref={reference_number}")
            
            # Send the confirmation email - returns dict with success, provider_id, error
            email_result = email_service.send_transfer_confirmation_email(
                to_email=user_email,
                first_name=first_name,
                reference_number=reference_number,
                amount_cents=amount,
                beneficiary_name=beneficiary_name,
                beneficiary_iban=beneficiary_iban,
                sender_iban=sender_iban or "N/A",
                transfer_type=transfer_type,
                transfer_date=transfer_date or datetime.now(timezone.utc),
                language=language
            )
            
            if email_result.get('success'):
                # SUCCESS
                await self._update_transfer_email_status(
                    transfer_id, 
                    True, 
                    email_result.get('provider_id'),
                    None
                )
                result['success'] = True
                result['provider_id'] = email_result.get('provider_id')
            else:
                # FAILED
                error_msg = email_result.get('error', 'Unknown error')
                await self._update_transfer_email_status(transfer_id, False, None, error_msg)
                result['error'] = error_msg
                result['email_warning'] = f"Transfer submitted, but confirmation email could not be delivered: {error_msg}"
                
        except Exception as e:
            error_msg = str(e)[:200]
            logger.error(f"[TRANSFER EMAIL] Exception for transfer {transfer_id}: {error_msg}")
            await self._update_transfer_email_status(transfer_id, False, None, error_msg)
            result['error'] = error_msg
            result['email_warning'] = f"Transfer submitted, but confirmation email could not be delivered: {error_msg}"
        
        return result
    
    async def _update_transfer_email_status(
        self,
        transfer_id: str,
        success: bool,
        provider_id: str = None,
        error: str = None
    ):
        """Update transfer record with email status."""
        now = datetime.now(timezone.utc)
        
        if success:
            update_data = {
                "confirmation_email_sent": True,
                "confirmation_email_status": "sent",
                "confirmation_email_sent_at": now,
                "confirmation_email_provider_id": provider_id,
                "confirmation_email_error": None
            }
        else:
            update_data = {
                "confirmation_email_sent": False,
                "confirmation_email_status": "failed",
                "confirmation_email_error": error
            }
        
        try:
            await self.db.transfers.update_one(
                {"_id": transfer_id},
                {"$set": update_data}
            )
        except Exception as e:
            logger.error(f"[TRANSFER EMAIL] Failed to update email status for transfer {transfer_id}: {str(e)}")
    
    async def p2p_transfer(
        self,
        from_user_id: str,
        to_iban: str,
        amount: int,
        reason: str = "SEPA Transfer",
        recipient_name: str = None,
        instant_requested: bool = False  # For future instant transfer support
    ):
        """Transfer money to any IBAN - internal or SEPA."""
        
        # Note: instant_requested is stored for future use but currently
        # all transfers are processed as standard SEPA transfers
        
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
            reference_number = f"SEPA-{transfer_id[:8].upper()}"
            transfer_record = {
                "_id": transfer_id,
                "user_id": str(from_user_id),
                "from_account_id": from_account["_id"],
                "transaction_id": txn.id,
                "type": "SEPA_TRANSFER",
                "beneficiary_name": final_recipient_name,
                "beneficiary_iban": normalized_iban,
                "amount": amount,
                "currency": "EUR",
                "details": reason,
                "reference_number": reference_number,
                "status": "COMPLETED",  # Internal transfers complete immediately
                "transfer_type": "INTERNAL",
                "sender_name": sender_name,
                "sender_iban": from_account.get("iban"),
                "created_at": now,
                "updated_at": now,
                "completed_at": now,
                # Email status fields - initialized as pending
                "confirmation_email_sent": False,
                "confirmation_email_status": "pending"
            }
            await self.db.transfers.insert_one(transfer_record)
            
            # Send confirmation email (async, non-blocking)
            email_result = await self._send_transfer_confirmation_email(
                transfer_id=transfer_id,
                user_id=str(from_user_id),
                reference_number=reference_number,
                amount=amount,
                beneficiary_name=final_recipient_name,
                beneficiary_iban=normalized_iban,
                sender_iban=from_account.get("iban"),
                transfer_type="Internal Transfer",
                transfer_date=now
            )
            
            result = {
                "transaction_id": txn.id,
                "transfer_id": transfer_id,
                "amount": amount,
                "recipient": final_recipient_name,
                "recipient_iban": normalized_iban,
                "status": "COMPLETED",
                "transfer_type": "SEPA_TRANSFER"
            }
            
            # Add email warning if failed (non-blocking)
            if email_result.get('email_warning'):
                result["email_warning"] = email_result['email_warning']
            
            return result
        
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
            reference_number = f"SEPA-{transfer_id[:8].upper()}"
            final_beneficiary_name = recipient_name or "SEPA Recipient"
            transfer_record = {
                "_id": transfer_id,
                "user_id": str(from_user_id),
                "from_account_id": from_account["_id"],
                "transaction_id": txn.id,
                "type": "SEPA_TRANSFER",
                "beneficiary_name": final_beneficiary_name,
                "beneficiary_iban": normalized_iban,
                "amount": amount,
                "currency": "EUR",
                "details": reason,
                "reference_number": reference_number,
                "status": "SUBMITTED",  # Pending admin review
                "transfer_type": "SEPA",
                "sender_name": sender_name,
                "sender_iban": from_account.get("iban"),
                "created_at": now,
                "updated_at": now,
                # Email status fields - initialized as pending
                "confirmation_email_sent": False,
                "confirmation_email_status": "pending"
            }
            await self.db.transfers.insert_one(transfer_record)
            
            # Send confirmation email (async, non-blocking)
            email_result = await self._send_transfer_confirmation_email(
                transfer_id=transfer_id,
                user_id=str(from_user_id),
                reference_number=reference_number,
                amount=amount,
                beneficiary_name=final_beneficiary_name,
                beneficiary_iban=normalized_iban,
                sender_iban=from_account.get("iban"),
                transfer_type="SEPA Transfer",
                transfer_date=now
            )
            
            result = {
                "transaction_id": txn.id,
                "transfer_id": transfer_id,
                "amount": amount,
                "recipient": final_beneficiary_name,
                "recipient_iban": normalized_iban,
                "status": "COMPLETED",  # User sees it as completed (money deducted)
                "transfer_type": "SEPA_TRANSFER",
                "admin_status": "SUBMITTED"  # But admin will see it as submitted
            }
            
            # Add email warning if failed (non-blocking)
            if email_result.get('email_warning'):
                result["email_warning"] = email_result['email_warning']
            
            return result
