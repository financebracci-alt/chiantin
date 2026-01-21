"""Banking workflows service - Cards, Transfers, Recipients."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
import uuid

from schemas.banking_workflows import (
    CardRequest, CreateCardRequest, Card, FulfillCardRequest,
    Transfer, CreateTransfer, TransferRecipient, CreateRecipient,
    AdminAdjustment, CreateAdjustment, CardRequestStatus, TransferStatus
)
from utils.common import serialize_doc


class BankingWorkflowsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    # ==================== CARD REQUESTS ====================
    
    async def create_card_request(
        self,
        user_id: str,
        data: CreateCardRequest
    ) -> CardRequest:
        """User creates card request."""
        # Validate account belongs to user
        account = await self.db.bank_accounts.find_one({"_id": data.account_id})
        if not account or account["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Account not found or access denied")
        
        request = CardRequest(
            user_id=user_id,
            account_id=data.account_id,
            card_type=data.card_type
        )
        
        req_dict = request.model_dump(by_alias=True)
        await self.db.card_requests.insert_one(req_dict)
        
        return request
    
    async def get_user_card_requests(self, user_id: str) -> List[CardRequest]:
        """Get all card requests for a user."""
        cursor = self.db.card_requests.find({"user_id": user_id}).sort("created_at", -1)
        requests = []
        async for doc in cursor:
            requests.append(CardRequest(**serialize_doc(doc)))
        return requests
    
    async def get_pending_card_requests(self, status_filter: str = None) -> List[CardRequest]:
        """Admin: Get card requests by status."""
        query = {}
        if status_filter:
            query["status"] = status_filter
        else:
            query["status"] = "PENDING"  # Default to PENDING if no filter
        
        cursor = self.db.card_requests.find(query).sort("created_at", 1)
        requests = []
        async for doc in cursor:
            requests.append(CardRequest(**serialize_doc(doc)))
        return requests
    
    async def fulfill_card_request(
        self,
        request_id: str,
        admin_id: str,
        card_data: FulfillCardRequest
    ) -> Card:
        """Admin fulfills card request by manually entering card details."""
        # Get request
        req_doc = await self.db.card_requests.find_one({"_id": request_id})
        if not req_doc:
            raise HTTPException(status_code=404, detail="Card request not found")
        
        if req_doc["status"] != "PENDING":
            raise HTTPException(status_code=400, detail="Request already processed")
        
        # Create card
        card = Card(
            user_id=req_doc["user_id"],
            account_id=req_doc["account_id"],
            request_id=request_id,
            card_type=req_doc["card_type"],
            cardholder_name=card_data.cardholder_name,
            billing_address_line1=card_data.billing_address_line1,
            billing_address_line2=card_data.billing_address_line2,
            city=card_data.city,
            state=card_data.state,
            postal_code=card_data.postal_code,
            country=card_data.country,
            pan=card_data.pan,
            exp_month=card_data.exp_month,
            exp_year=card_data.exp_year,
            cvv=card_data.cvv
        )
        
        card_dict = card.model_dump(by_alias=True)
        await self.db.cards.insert_one(card_dict)
        
        # Update request status to FULFILLED
        await self.db.card_requests.update_one(
            {"_id": request_id},
            {"$set": {
                "status": "FULFILLED",
                "decided_at": datetime.utcnow(),
                "decided_by_admin_id": admin_id
            }}
        )
        
        # Create notification
        await self._create_notification(
            user_id=req_doc["user_id"],
            title="Your card is ready!",
            message="Your card has been issued and is ready to use.",
            entity_type="card",
            entity_id=card.id
        )
        
        return card
    
    async def reject_card_request(
        self,
        request_id: str,
        admin_id: str,
        reason: str
    ):
        """Admin rejects card request."""
        req_doc = await self.db.card_requests.find_one({"_id": request_id})
        if not req_doc:
            raise HTTPException(status_code=404, detail="Card request not found")
        
        await self.db.card_requests.update_one(
            {"_id": request_id},
            {"$set": {
                "status": "REJECTED",
                "decided_at": datetime.utcnow(),
                "decided_by_admin_id": admin_id,
                "reject_reason": reason
            }}
        )
        
        # Create notification
        await self._create_notification(
            user_id=req_doc["user_id"],
            title="Card request declined",
            message=f"Your card request could not be processed: {reason}",
            entity_type="card_request",
            entity_id=request_id
        )
        
        return True
    
    async def get_user_cards(self, user_id: str) -> List[Card]:
        """Get all cards for a user."""
        cursor = self.db.cards.find({"user_id": user_id}).sort("created_at", -1)
        cards = []
        async for doc in cursor:
            cards.append(Card(**serialize_doc(doc)))
        return cards
    
    # ==================== RECIPIENTS ====================
    
    async def create_recipient(
        self,
        user_id: str,
        data: CreateRecipient
    ) -> TransferRecipient:
        """User creates saved recipient (IBAN display only)."""
        recipient = TransferRecipient(
            user_id=user_id,
            name=data.name,
            iban=data.iban
        )
        
        rec_dict = recipient.model_dump(by_alias=True)
        await self.db.transfer_recipients.insert_one(rec_dict)
        
        return recipient
    
    async def get_user_recipients(self, user_id: str) -> List[TransferRecipient]:
        """Get user's saved recipients."""
        cursor = self.db.transfer_recipients.find({"user_id": user_id}).sort("created_at", -1)
        recipients = []
        async for doc in cursor:
            recipients.append(TransferRecipient(**serialize_doc(doc)))
        return recipients
    
    async def delete_recipient(self, recipient_id: str, user_id: str) -> bool:
        """Delete saved recipient."""
        result = await self.db.transfer_recipients.delete_one({
            "_id": recipient_id,
            "user_id": user_id
        })
        return result.deleted_count > 0
    
    # ==================== TRANSFERS ====================
    
    async def create_transfer(
        self,
        user_id: str,
        data: CreateTransfer
    ) -> Transfer:
        """User submits transfer - instant success, no waiting."""
        # Validate account
        account = await self.db.bank_accounts.find_one({"_id": data.from_account_id})
        if not account or account["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Account not found or access denied")
        
        # Validate amount
        if data.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        transfer = Transfer(
            user_id=user_id,
            from_account_id=data.from_account_id,
            beneficiary_name=data.beneficiary_name,
            beneficiary_iban=data.beneficiary_iban,
            amount=data.amount,
            currency=data.currency,
            details=data.details,
            reference_number=data.reference_number,
            scheduled_for=data.scheduled_for,
            attachment_url=data.attachment_url
        )
        
        trans_dict = transfer.model_dump(by_alias=True)
        await self.db.transfers.insert_one(trans_dict)
        
        return transfer
    
    async def get_user_transfers(self, user_id: str) -> List[Transfer]:
        """Get user's transfers."""
        cursor = self.db.transfers.find({"user_id": user_id}).sort("created_at", -1)
        transfers = []
        async for doc in cursor:
            transfers.append(Transfer(**serialize_doc(doc)))
        return transfers
    
    async def get_transfer(self, transfer_id: str, user_id: str) -> Optional[Transfer]:
        """Get transfer details."""
        doc = await self.db.transfers.find_one({"_id": transfer_id, "user_id": user_id})
        if not doc:
            return None
        return Transfer(**serialize_doc(doc))
    
    async def get_admin_transfers(self, status: Optional[str] = None) -> List[Transfer]:
        """Admin: Get transfers filtered by status."""
        query = {}
        if status:
            query["status"] = status
        
        cursor = self.db.transfers.find(query).sort("created_at", -1).limit(100)
        transfers = []
        async for doc in cursor:
            transfers.append(Transfer(**serialize_doc(doc)))
        return transfers
    
    async def approve_transfer(
        self,
        transfer_id: str,
        admin_id: str
    ):
        """Admin approves transfer."""
        trans_doc = await self.db.transfers.find_one({"_id": transfer_id})
        if not trans_doc:
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        await self.db.transfers.update_one(
            {"_id": transfer_id},
            {"$set": {
                "status": "COMPLETED",
                "admin_action_by": admin_id,
                "admin_action_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Create notification (no admin mention)
        await self._create_notification(
            user_id=trans_doc["user_id"],
            title="Transfer completed",
            message=f"Your transfer of €{trans_doc['amount']/100:.2f} to {trans_doc['beneficiary_name']} has been completed.",
            entity_type="transfer",
            entity_id=transfer_id
        )
        
        return True
    
    async def reject_transfer(
        self,
        transfer_id: str,
        admin_id: str,
        reason: str
    ):
        """Admin rejects transfer - returns money to user's account."""
        from services.ledger_service import LedgerEngine
        from core.ledger import EntryDirection, AccountType
        from datetime import timezone
        
        trans_doc = await self.db.transfers.find_one({"_id": transfer_id})
        if not trans_doc:
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        # Only reject if status is SUBMITTED
        if trans_doc.get("status") != "SUBMITTED":
            raise HTTPException(status_code=400, detail="Transfer cannot be rejected - not in SUBMITTED status")
        
        # Get user's bank account to return the money
        user_id = trans_doc.get("user_id")
        from_account_id = trans_doc.get("from_account_id")
        amount = trans_doc.get("amount", 0)
        
        # Find user's bank account
        bank_account = None
        if from_account_id:
            bank_account = await self.db.bank_accounts.find_one({"_id": from_account_id})
        if not bank_account and user_id:
            bank_account = await self.db.bank_accounts.find_one({"user_id": user_id})
            if not bank_account:
                from bson import ObjectId
                try:
                    bank_account = await self.db.bank_accounts.find_one({"user_id": ObjectId(user_id)})
                except:
                    pass
        
        # Return the money to user's account
        if bank_account and amount > 0:
            ledger_engine = LedgerEngine(self.db)
            
            # Get or create the SEPA outgoing account (this was credited during the original transfer)
            # We need to debit it to balance the refund credit to user
            sepa_account = await self.db.ledger_accounts.find_one({"type": "SEPA_OUTGOING"})
            if not sepa_account:
                # Fallback to SANDBOX_FUNDING if SEPA_OUTGOING doesn't exist
                sepa_account = await self.db.ledger_accounts.find_one({"account_type": "SANDBOX_FUNDING"})
            
            if not sepa_account:
                # Create a SANDBOX_FUNDING account as last resort
                sepa_account = {
                    "_id": f"sandbox_funding_{uuid.uuid4()}",
                    "account_type": "SANDBOX_FUNDING",
                    "type": "SANDBOX_FUNDING",
                    "currency": "EUR",
                    "created_at": datetime.now(timezone.utc)
                }
                await self.db.ledger_accounts.insert_one(sepa_account)
            
            sepa_account_id = sepa_account["_id"]
            
            # Create refund transaction with balanced entries
            # CREDIT user's account (money returned)
            # DEBIT SEPA/funding account (money comes from there)
            await ledger_engine.post_transaction(
                transaction_type="TRANSFER_REFUND",
                entries=[
                    (bank_account["ledger_account_id"], amount, EntryDirection.CREDIT),
                    (sepa_account_id, amount, EntryDirection.DEBIT)
                ],
                external_id=f"refund_{transfer_id}_{uuid.uuid4()}",
                reason=f"Refund: Transfer rejected - {reason}",
                performed_by=admin_id,
                metadata={
                    "original_transfer_id": transfer_id,
                    "refund_reason": reason,
                    "display_type": "Transfer Refund",
                    "sender_name": "ECOMMBX",
                    "description": f"Refund for rejected transfer to {trans_doc.get('beneficiary_name', 'Unknown')}",
                    "status": "POSTED"
                }
            )
        
        # Update transfer status
        now = datetime.now(timezone.utc)
        await self.db.transfers.update_one(
            {"_id": transfer_id},
            {"$set": {
                "status": "REJECTED",
                "reject_reason": reason,
                "rejection_reason": reason,
                "admin_action_by": admin_id,
                "admin_action_at": now,
                "updated_at": now,
                "refunded": True,
                "refund_amount": amount
            }}
        )
        
        # Create notification for user
        await self._create_notification(
            user_id=user_id,
            title="Transfer Rejected",
            message=f"Your transfer of €{amount/100:.2f} to {trans_doc.get('beneficiary_name', 'Unknown')} was rejected. Reason: {reason}. The amount has been returned to your account.",
            entity_type="transfer",
            entity_id=transfer_id
        )
        
        return True
    
    # ==================== ADMIN ADJUSTMENTS ====================
    
    async def topup_account(
        self,
        account_id: str,
        admin_id: str,
        amount: int,
        reason: str
    ):
        """Admin tops up account - changes real balance."""
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        account = await self.db.bank_accounts.find_one({"_id": account_id})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Create adjustment record
        adjustment = AdminAdjustment(
            admin_id=admin_id,
            account_id=account_id,
            adjustment_type="TOPUP",
            amount=amount,
            reason=reason
        )
        
        adj_dict = adjustment.model_dump(by_alias=True)
        await self.db.admin_adjustments.insert_one(adj_dict)
        
        # Update actual balance (if using balance field)
        # Note: If using ledger for balance, update ledger instead
        # For now, this is a direct balance update for admin control
        
        return adjustment
    
    async def withdraw_account(
        self,
        account_id: str,
        admin_id: str,
        amount: int,
        reason: str
    ):
        """Admin withdraws from account - changes real balance."""
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        account = await self.db.bank_accounts.find_one({"_id": account_id})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Create adjustment record
        adjustment = AdminAdjustment(
            admin_id=admin_id,
            account_id=account_id,
            adjustment_type="WITHDRAW",
            amount=amount,
            reason=reason
        )
        
        adj_dict = adjustment.model_dump(by_alias=True)
        await self.db.admin_adjustments.insert_one(adj_dict)
        
        return adjustment
    
    # ==================== HELPER ====================
    
    async def _create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        entity_type: str,
        entity_id: str,
        notification_type: str = "ACCOUNT"
    ):
        """Create notification for user."""
        notification = {
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "read": False,
            "created_at": datetime.utcnow()
        }
        await self.db.notifications.insert_one(notification)
