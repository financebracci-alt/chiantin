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
    
    async def get_pending_card_requests(self, status_filter: str = None) -> dict:
        """Admin: Get card requests by status with user information.
        
        PERFORMANCE OPTIMIZED: Returns user info with each request to avoid N+1 frontend queries.
        
        Args:
            status_filter: Optional status filter (PENDING, FULFILLED, REJECTED)
            
        Returns:
            Dictionary with 'requests' list (including user_name, user_email) and 'pagination' info
        """
        from bson import ObjectId
        
        query = {}
        if status_filter:
            query["status"] = status_filter
        else:
            query["status"] = "PENDING"  # Default to PENDING if no filter
        
        cursor = self.db.card_requests.find(query).sort("created_at", -1)
        request_docs = await cursor.to_list(length=500)
        
        if not request_docs:
            return {
                "requests": [],
                "pagination": {
                    "total": 0,
                    "status": status_filter or "PENDING"
                }
            }
        
        # Collect all unique user_ids for bulk lookup
        user_ids = set()
        for doc in request_docs:
            user_id = doc.get("user_id")
            if user_id:
                user_ids.add(user_id)  # Always add string version
                try:
                    user_ids.add(ObjectId(user_id))  # Also try ObjectId version
                except:
                    pass
        
        # BULK LOOKUP: Fetch all users in ONE query
        users_map = {}
        if user_ids:
            users_cursor = self.db.users.find({"_id": {"$in": list(user_ids)}})
            async for user in users_cursor:
                users_map[str(user["_id"])] = user
        
        # Build response with user info included
        requests = []
        for doc in request_docs:
            request = CardRequest(**serialize_doc(doc))
            request_dict = request.model_dump()
            
            # Add user info from pre-fetched map (O(1) lookup)
            user_id = doc.get("user_id")
            user = users_map.get(str(user_id)) if user_id else None
            
            if user:
                request_dict["user_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                request_dict["user_email"] = user.get("email", "")
            else:
                request_dict["user_name"] = f"Deleted User ({user_id[:8]}...)" if user_id else "Unknown"
                request_dict["user_email"] = ""
            
            requests.append(request_dict)
        
        return {
            "requests": requests,
            "pagination": {
                "total": len(requests),
                "status": status_filter or "PENDING"
            }
        }
    
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
        from bson import ObjectId
        from datetime import timezone
        from services.email_service import EmailService
        
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
        
        # Send transfer confirmation email with comprehensive status tracking
        email_warning = None
        try:
            # Get user details for email
            user = None
            try:
                user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            except:
                pass
            if not user:
                user = await self.db.users.find_one({"_id": user_id})
            
            if user and user.get("email"):
                email_service = EmailService()
                
                # Get user's preferred language (default to 'en')
                language = user.get("language", "en") or "en"
                
                # Get sender account IBAN
                sender_iban = account.get("iban") or "N/A"
                
                # Send the confirmation email - returns dict with success, provider_id, error
                email_result = email_service.send_transfer_confirmation_email(
                    to_email=user["email"],
                    first_name=user.get("first_name", ""),
                    reference_number=transfer.reference_number or transfer.id[:8].upper(),
                    amount_cents=data.amount,
                    beneficiary_name=data.beneficiary_name,
                    beneficiary_iban=data.beneficiary_iban,
                    sender_iban=sender_iban,
                    transfer_type="SEPA Transfer",
                    transfer_date=transfer.created_at,
                    language=language
                )
                
                now = datetime.now(timezone.utc)
                
                if email_result.get('success'):
                    # SUCCESS - Update transfer with sent status
                    await self.db.transfers.update_one(
                        {"_id": transfer.id},
                        {"$set": {
                            "confirmation_email_sent": True,
                            "confirmation_email_status": "sent",
                            "confirmation_email_sent_at": now,
                            "confirmation_email_provider_id": email_result.get('provider_id'),
                            "confirmation_email_error": None
                        }}
                    )
                    transfer.confirmation_email_sent = True
                    transfer.confirmation_email_status = "sent"
                    transfer.confirmation_email_sent_at = now
                    transfer.confirmation_email_provider_id = email_result.get('provider_id')
                else:
                    # FAILED - Update transfer with failure status
                    error_msg = email_result.get('error', 'Unknown error')
                    await self.db.transfers.update_one(
                        {"_id": transfer.id},
                        {"$set": {
                            "confirmation_email_sent": False,
                            "confirmation_email_status": "failed",
                            "confirmation_email_error": error_msg
                        }}
                    )
                    transfer.confirmation_email_status = "failed"
                    transfer.confirmation_email_error = error_msg
                    email_warning = f"Transfer submitted, but confirmation email could not be delivered: {error_msg}"
            else:
                # No user email found
                error_msg = "User email not found"
                await self.db.transfers.update_one(
                    {"_id": transfer.id},
                    {"$set": {
                        "confirmation_email_status": "failed",
                        "confirmation_email_error": error_msg
                    }}
                )
                transfer.confirmation_email_status = "failed"
                transfer.confirmation_email_error = error_msg
                
        except Exception as e:
            # Log error but don't fail the transfer
            import logging
            logger = logging.getLogger(__name__)
            error_msg = str(e)[:200]
            logger.error(f"[TRANSFER EMAIL] Exception for transfer {transfer.id}: {error_msg}")
            
            # Update transfer with failure status
            try:
                await self.db.transfers.update_one(
                    {"_id": transfer.id},
                    {"$set": {
                        "confirmation_email_status": "failed",
                        "confirmation_email_error": error_msg
                    }}
                )
                transfer.confirmation_email_status = "failed"
                transfer.confirmation_email_error = error_msg
            except:
                pass
            
            email_warning = f"Transfer submitted, but confirmation email could not be delivered: {error_msg}"
        
        # Store warning for potential UI display (not breaking the transfer)
        if email_warning:
            transfer._email_warning = email_warning
        
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
    
    async def get_admin_transfers(self, status: Optional[str] = None, page: int = 1, limit: int = 20, search: Optional[str] = None) -> dict:
        """Admin: Get transfers filtered by status with sender information.
        
        PERFORMANCE OPTIMIZED: Uses bulk lookups instead of N+1 queries.
        Added pagination and search support for better performance with large datasets.
        SOFT DELETE: Excludes soft-deleted transfers by default.
        
        Args:
            status: Optional status filter (e.g., 'SUBMITTED', 'COMPLETED', 'REJECTED')
            page: Page number (1-indexed)
            limit: Items per page (default 20, valid: 20, 50, 100)
            search: Optional search term (searches beneficiary name, sender name, email, IBAN, reference)
            
        Returns:
            Dictionary with 'transfers' list and 'pagination' info
        """
        from bson import ObjectId
        import re
        
        # Validate limit
        valid_limits = [20, 50, 100]
        if limit not in valid_limits:
            limit = 20
        
        # If search is provided, search across ALL transfers with pagination
        if search and search.strip():
            return await self._search_transfers(search.strip(), page, limit)
        
        # Build query - ALWAYS exclude soft-deleted transfers
        query = {"$or": [{"is_deleted": {"$exists": False}}, {"is_deleted": False}]}
        if status:
            query["status"] = status
        
        # Get total count for pagination
        total_count = await self.db.transfers.count_documents(query)
        
        # Calculate pagination
        total_pages = max(1, (total_count + limit - 1) // limit)
        if page > total_pages:
            page = total_pages
        if page < 1:
            page = 1
        skip = (page - 1) * limit
        
        # Fetch transfers with pagination
        cursor = self.db.transfers.find(query).sort("created_at", -1).skip(skip).limit(limit)
        transfer_docs = await cursor.to_list(length=limit)
        
        if not transfer_docs:
            return {
                "transfers": [],
                "pagination": {
                    "page": page,
                    "page_size": limit,
                    "total": total_count,
                    "total_pages": total_pages,
                    "has_next": False,
                    "has_prev": page > 1
                }
            }
        
        # Collect all unique user_ids and account_ids for bulk lookup
        user_ids = set()
        account_ids = set()
        
        for doc in transfer_docs:
            user_id = doc.get("user_id")
            if user_id:
                user_ids.add(user_id)  # Always add string version
                try:
                    user_ids.add(ObjectId(user_id))  # Also try ObjectId version
                except:
                    pass
            
            from_account_id = doc.get("from_account_id")
            if from_account_id:
                account_ids.add(from_account_id)
        
        # BULK LOOKUP: Fetch all users in ONE query
        users_map = {}
        if user_ids:
            users_cursor = self.db.users.find({"_id": {"$in": list(user_ids)}})
            async for user in users_cursor:
                users_map[str(user["_id"])] = user
        
        # BULK LOOKUP: Fetch all accounts in ONE query
        accounts_map = {}
        if account_ids:
            accounts_cursor = self.db.bank_accounts.find({"_id": {"$in": list(account_ids)}})
            async for account in accounts_cursor:
                accounts_map[str(account["_id"])] = account
        
        # Build the response using the pre-fetched data (no more N+1 queries!)
        transfers = []
        for doc in transfer_docs:
            transfer = Transfer(**serialize_doc(doc))
            transfer_dict = transfer.model_dump()
            
            # Get sender info from pre-fetched map (O(1) lookup)
            user_id = doc.get("user_id")
            user = users_map.get(str(user_id)) if user_id else None
            
            if user:
                transfer_dict["sender_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                transfer_dict["sender_email"] = user.get("email", "")
            else:
                transfer_dict["sender_name"] = f"Deleted User ({user_id[:8]}...)" if user_id else "Unknown"
                transfer_dict["sender_email"] = ""
            
            # Get sender IBAN from pre-fetched map (O(1) lookup)
            from_account_id = doc.get("from_account_id")
            account = accounts_map.get(str(from_account_id)) if from_account_id else None
            transfer_dict["sender_iban"] = account.get("iban", "N/A") if account else "N/A"
            
            transfers.append(transfer_dict)
        
        return {
            "transfers": transfers,
            "pagination": {
                "page": page,
                "page_size": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    async def get_deleted_transfers(self, page: int = 1, limit: int = 20, search: Optional[str] = None) -> dict:
        """Admin: Get soft-deleted transfers with pagination.
        
        This returns ONLY transfers that have been soft-deleted (is_deleted=True).
        Used by the admin DELETED tab to view and potentially restore deleted transfers.
        
        PERFORMANCE OPTIMIZED: Uses bulk lookups (same as get_admin_transfers).
        
        Args:
            page: Page number (1-indexed)
            limit: Items per page (20, 50, or 100)
            search: Optional search term
            
        Returns:
            Dictionary with 'transfers' list and 'pagination' info
        """
        # Build query - ONLY soft-deleted transfers
        query = {"is_deleted": True}
        
        # Add search filter if provided
        if search and search.strip():
            search_regex = {"$regex": search.strip(), "$options": "i"}
            query["$or"] = [
                {"beneficiary_name": search_regex},
                {"beneficiary_iban": search_regex},
                {"reference_number": search_regex},
                {"details": search_regex}
            ]
        
        # Get total count for pagination
        total_count = await self.db.transfers.count_documents(query)
        
        # Calculate pagination
        total_pages = max(1, (total_count + limit - 1) // limit)
        if page > total_pages:
            page = total_pages
        if page < 1:
            page = 1
        skip = (page - 1) * limit
        
        # Fetch transfers with pagination - sort by deleted_at (most recent first)
        cursor = self.db.transfers.find(query).sort("deleted_at", -1).skip(skip).limit(limit)
        transfer_docs = await cursor.to_list(length=limit)
        
        if not transfer_docs:
            return {
                "transfers": [],
                "pagination": {
                    "page": page,
                    "page_size": limit,
                    "total": total_count,
                    "total_pages": total_pages,
                    "has_next": False,
                    "has_prev": page > 1
                }
            }
        
        # Collect all unique user_ids and account_ids for bulk lookup
        user_ids = set()
        account_ids = set()
        
        for doc in transfer_docs:
            user_id = doc.get("user_id")
            if user_id:
                user_ids.add(user_id)  # Always add string version
                try:
                    user_ids.add(ObjectId(user_id))  # Also try ObjectId version
                except:
                    pass
            
            from_account_id = doc.get("from_account_id")
            if from_account_id:
                account_ids.add(from_account_id)
        
        # BULK LOOKUP: Fetch all users in ONE query
        users_map = {}
        if user_ids:
            users_cursor = self.db.users.find({"_id": {"$in": list(user_ids)}})
            async for user in users_cursor:
                users_map[str(user["_id"])] = user
        
        # BULK LOOKUP: Fetch all accounts in ONE query
        accounts_map = {}
        if account_ids:
            accounts_cursor = self.db.bank_accounts.find({"_id": {"$in": list(account_ids)}})
            async for account in accounts_cursor:
                accounts_map[account["_id"]] = account
        
        # Enrich transfer documents with sender info (using bulk lookup results)
        transfers = []
        for doc in transfer_docs:
            user = users_map.get(doc.get("user_id"))
            account = accounts_map.get(doc.get("from_account_id"))
            
            transfer_dict = {
                "id": str(doc["_id"]),
                "user_id": doc.get("user_id"),
                "amount": doc.get("amount"),
                "beneficiary_name": doc.get("beneficiary_name"),
                "beneficiary_iban": doc.get("beneficiary_iban"),
                "details": doc.get("details"),
                "status": doc.get("previous_status", doc.get("status", "UNKNOWN")),  # Show previous status
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                "reference_number": doc.get("reference_number"),
                "sender_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() if user else "Unknown",
                "sender_email": user.get("email") if user else None,
                "sender_iban": account.get("iban") if account else doc.get("sender_iban"),
                "reject_reason": doc.get("reject_reason"),
                # Deletion metadata
                "is_deleted": True,
                "deleted_at": doc.get("deleted_at").isoformat() if doc.get("deleted_at") else None,
                "deleted_by": doc.get("deleted_by"),
                "deleted_by_email": doc.get("deleted_by_email"),
                "previous_status": doc.get("previous_status")
            }
            transfers.append(transfer_dict)
        
        return {
            "transfers": transfers,
            "pagination": {
                "page": page,
                "page_size": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    async def _search_transfers(self, search_term: str, page: int = 1, limit: int = 20) -> dict:
        """Search transfers across the ENTIRE database (all statuses) with pagination.
        
        Searches by: beneficiary name, sender name, sender email, IBAN, reference number.
        SOFT DELETE: Excludes soft-deleted transfers.
        
        Args:
            search_term: The search string to match
            page: Page number (1-indexed)
            limit: Items per page
            
        Returns:
            Dictionary with 'transfers' list and 'pagination' info (search mode)
        """
        from bson import ObjectId
        import re
        
        search_regex = re.compile(re.escape(search_term), re.IGNORECASE)
        
        # First, find users matching the search
        user_query = {
            "$or": [
                {"email": {"$regex": search_regex}},
                {"first_name": {"$regex": search_regex}},
                {"last_name": {"$regex": search_regex}}
            ]
        }
        matching_users = await self.db.users.find(user_query, {"_id": 1}).to_list(100)
        matching_user_ids = [str(u["_id"]) for u in matching_users]
        
        # Build transfer query - search in transfer fields OR by user_id
        # SOFT DELETE: Always exclude soft-deleted transfers
        transfer_conditions = [
            {"beneficiary_name": {"$regex": search_regex}},
            {"beneficiary_iban": {"$regex": search_regex}},
            {"reference_number": {"$regex": search_regex}},
            {"details": {"$regex": search_regex}}
        ]
        
        if matching_user_ids:
            transfer_conditions.append({"user_id": {"$in": matching_user_ids}})
        
        # Combine search conditions with soft-delete exclusion
        transfer_query = {
            "$and": [
                {"$or": transfer_conditions},
                {"$or": [{"is_deleted": {"$exists": False}}, {"is_deleted": False}]}
            ]
        }
        
        # Get total count for pagination
        total_count = await self.db.transfers.count_documents(transfer_query)
        
        # Calculate pagination
        total_pages = max(1, (total_count + limit - 1) // limit)
        if page > total_pages:
            page = total_pages
        if page < 1:
            page = 1
        skip = (page - 1) * limit
        
        # Fetch paginated results
        all_transfer_docs = await self.db.transfers.find(transfer_query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
        
        if not all_transfer_docs:
            return {
                "transfers": [],
                "pagination": {
                    "page": page,
                    "page_size": limit,
                    "total": total_count,
                    "total_pages": total_pages,
                    "has_next": False,
                    "has_prev": page > 1,
                    "search_mode": True
                }
            }
        
        # Collect all unique user_ids and account_ids for bulk lookup
        user_ids = set()
        account_ids = set()
        
        for doc in all_transfer_docs:
            user_id = doc.get("user_id")
            if user_id:
                user_ids.add(user_id)  # Always add string version
                try:
                    user_ids.add(ObjectId(user_id))  # Also try ObjectId version
                except:
                    pass
            
            from_account_id = doc.get("from_account_id")
            if from_account_id:
                account_ids.add(from_account_id)
        
        # BULK LOOKUP: Fetch all users in ONE query
        users_map = {}
        if user_ids:
            users_cursor = self.db.users.find({"_id": {"$in": list(user_ids)}})
            async for user in users_cursor:
                users_map[str(user["_id"])] = user
        
        # BULK LOOKUP: Fetch all accounts in ONE query
        accounts_map = {}
        if account_ids:
            accounts_cursor = self.db.bank_accounts.find({"_id": {"$in": list(account_ids)}})
            async for account in accounts_cursor:
                accounts_map[str(account["_id"])] = account
        
        # Build the response
        transfers = []
        for doc in all_transfer_docs:
            transfer = Transfer(**serialize_doc(doc))
            transfer_dict = transfer.model_dump()
            
            # Get sender info from pre-fetched map
            user_id = doc.get("user_id")
            user = users_map.get(str(user_id)) if user_id else None
            
            if user:
                transfer_dict["sender_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                transfer_dict["sender_email"] = user.get("email", "")
            else:
                transfer_dict["sender_name"] = f"Deleted User ({user_id[:8]}...)" if user_id else "Unknown"
                transfer_dict["sender_email"] = ""
            
            # Get sender IBAN from pre-fetched map
            from_account_id = doc.get("from_account_id")
            account = accounts_map.get(str(from_account_id)) if from_account_id else None
            transfer_dict["sender_iban"] = account.get("iban", "N/A") if account else "N/A"
            
            transfers.append(transfer_dict)
        
        return {
            "transfers": transfers,
            "pagination": {
                "page": page,
                "page_size": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "search_mode": True
            }
        }
    
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
        """Admin rejects transfer - returns money to user's account and sends rejection email."""
        from services.ledger_service import LedgerEngine
        from services.email_service import EmailService
        from core.ledger import EntryDirection, AccountType
        from datetime import timezone
        from bson import ObjectId
        
        trans_doc = await self.db.transfers.find_one({"_id": transfer_id})
        if not trans_doc:
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        # Only reject if status is SUBMITTED
        if trans_doc.get("status") != "SUBMITTED":
            raise HTTPException(status_code=400, detail="Transfer cannot be rejected - not in SUBMITTED status")
        
        # Idempotency check: Ensure rejection email hasn't already been sent
        if trans_doc.get("rejection_email_sent", False):
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[REJECT TRANSFER] Rejection email already sent for transfer {transfer_id}, skipping email")
        
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
                from bson.errors import InvalidId
                try:
                    bank_account = await self.db.bank_accounts.find_one({"user_id": ObjectId(user_id)})
                except InvalidId:
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
                    "sender_name": "CHIANTIN",
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
        
        # Update the original transaction to show REJECTED status and rejection reason
        transaction_id = trans_doc.get("transaction_id")
        if transaction_id:
            await self.db.transactions.update_one(
                {"_id": transaction_id},
                {"$set": {
                    "status": "REJECTED",
                    "rejection_reason": reason,
                    "admin_notes": reason,
                    "updated_at": now
                }}
            )
        
        # Create notification for user
        # Use the transaction_id from the transfer record so clicking the notification opens the correct transaction
        transaction_id = trans_doc.get("transaction_id", transfer_id)
        await self._create_notification(
            user_id=user_id,
            title="Transfer Rejected",
            message=f"Your transfer of €{amount/100:.2f} to {trans_doc.get('beneficiary_name', 'Unknown')} was rejected. Reason: {reason}. The amount has been returned to your account.",
            entity_type="transfer",
            entity_id=transaction_id
        )
        
        # Send rejection email - ONLY if not already sent (idempotency)
        if not trans_doc.get("rejection_email_sent", False):
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                # Get user details for email
                user = None
                try:
                    user = await self.db.users.find_one({"_id": ObjectId(user_id)})
                except:
                    pass
                if not user:
                    user = await self.db.users.find_one({"_id": user_id})
                
                if user and user.get("email"):
                    email_service = EmailService()
                    
                    # Get user's preferred language (default to 'en')
                    language = user.get("language", "en") or "en"
                    
                    # Get reference number for email
                    reference_number = trans_doc.get("reference_number") or transfer_id[:8].upper()
                    
                    # Send the rejection email
                    email_result = email_service.send_transfer_rejected_email(
                        to_email=user["email"],
                        first_name=user.get("first_name", ""),
                        reference_number=reference_number,
                        amount_cents=amount,
                        beneficiary_name=trans_doc.get("beneficiary_name", "Unknown"),
                        beneficiary_iban=trans_doc.get("beneficiary_iban", ""),
                        rejection_timestamp=now,
                        language=language
                    )
                    
                    if email_result.get('success'):
                        # SUCCESS - Update transfer with sent status
                        await self.db.transfers.update_one(
                            {"_id": transfer_id},
                            {"$set": {
                                "rejection_email_sent": True,
                                "rejection_email_sent_at": now,
                                "rejection_email_provider_id": email_result.get('provider_id'),
                                "rejection_email_error": None
                            }}
                        )
                        logger.info(f"[REJECT TRANSFER] Rejection email sent successfully for transfer {transfer_id}")
                    else:
                        # FAILED - Log error but don't fail the rejection
                        error_msg = email_result.get('error', 'Unknown error')
                        await self.db.transfers.update_one(
                            {"_id": transfer_id},
                            {"$set": {
                                "rejection_email_sent": False,
                                "rejection_email_error": error_msg
                            }}
                        )
                        logger.error(f"[REJECT TRANSFER] Failed to send rejection email for transfer {transfer_id}: {error_msg}")
                else:
                    # No user email found
                    logger.warning(f"[REJECT TRANSFER] No email found for user {user_id}, skipping rejection email")
                    await self.db.transfers.update_one(
                        {"_id": transfer_id},
                        {"$set": {
                            "rejection_email_sent": False,
                            "rejection_email_error": "User email not found"
                        }}
                    )
                    
            except Exception as e:
                # Log error but don't fail the transfer rejection
                import logging
                logger = logging.getLogger(__name__)
                error_msg = str(e)[:200]
                logger.error(f"[REJECT TRANSFER] Exception sending rejection email for transfer {transfer_id}: {error_msg}")
                
                # Update transfer with failure status
                try:
                    await self.db.transfers.update_one(
                        {"_id": transfer_id},
                        {"$set": {
                            "rejection_email_sent": False,
                            "rejection_email_error": error_msg
                        }}
                    )
                except:
                    pass
        
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
