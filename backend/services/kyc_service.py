"""KYC service."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from fastapi import HTTPException, UploadFile
from typing import List, Optional

from schemas.kyc import (
    KYCApplication,
    KYCSubmitRequest,
    KYCStatus,
    KYCDocument,
    DocumentType,
    KYCReviewRequest
)
from providers import StorageProvider
from utils.common import serialize_doc
import uuid


class KYCService:
    def __init__(self, db: AsyncIOMotorDatabase, storage: StorageProvider):
        self.db = db
        self.storage = storage
    
    async def get_or_create_application(self, user_id: str) -> KYCApplication:
        """Get existing KYC application or create new draft."""
        app_doc = await self.db.kyc_applications.find_one({"user_id": user_id})
        
        if app_doc:
            return KYCApplication(**serialize_doc(app_doc))
        
        # Create new application
        app = KYCApplication(user_id=user_id)
        app_dict = app.model_dump(by_alias=True)
        await self.db.kyc_applications.insert_one(app_dict)
        
        return app
    
    async def upload_document(
        self,
        user_id: str,
        file: UploadFile,
        document_type: DocumentType
    ) -> KYCDocument:
        """Upload a KYC document."""
        # Generate unique key
        file_id = str(uuid.uuid4())
        key = f"kyc/{user_id}/{document_type.value}_{file_id}_{file.filename}"
        
        # Upload to storage
        metadata = self.storage.upload_fileobj(
            file.file,
            key,
            content_type=file.content_type
        )
        
        # Create document record
        doc = KYCDocument(
            document_type=document_type,
            file_key=key,
            file_name=file.filename,
            file_size=metadata.size,
            content_type=file.content_type or "application/octet-stream"
        )
        
        # Add to application
        await self.db.kyc_applications.update_one(
            {"user_id": user_id},
            {"$push": {"documents": doc.model_dump()}}
        )
        
        return doc
    
    async def submit_application(
        self,
        user_id: str,
        data: KYCSubmitRequest
    ) -> KYCApplication:
        """Submit KYC application for review."""
        app = await self.get_or_create_application(user_id)
        
        # Allow resubmission for DRAFT, NEEDS_MORE_INFO, and REJECTED statuses
        if app.status not in [KYCStatus.DRAFT, KYCStatus.NEEDS_MORE_INFO, KYCStatus.REJECTED]:
            raise HTTPException(
                status_code=400,
                detail="Application cannot be modified in current status"
            )
        
        # Update application
        update_data = data.model_dump()
        update_data.update({
            "status": KYCStatus.SUBMITTED,
            "submitted_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "terms_accepted_at": datetime.utcnow() if data.terms_accepted else None,
            "privacy_accepted_at": datetime.utcnow() if data.privacy_accepted else None,
            # Clear previous rejection if resubmitting
            "rejection_reason": None,
            "review_notes": None,
            "reviewed_at": None,
            "reviewed_by": None
        })
        
        await self.db.kyc_applications.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        
        # Update user status to ACTIVE if approved
        app_doc = await self.db.kyc_applications.find_one({"user_id": user_id})
        return KYCApplication(**serialize_doc(app_doc))
    
    async def review_application(
        self,
        application_id: str,
        review: KYCReviewRequest,
        reviewer_id: str
    ) -> KYCApplication:
        """Review KYC application (admin)."""
        app_doc = await self.db.kyc_applications.find_one({"_id": application_id})
        if not app_doc:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Update application
        update_data = {
            "status": review.status,
            "reviewed_at": datetime.utcnow(),
            "reviewed_by": reviewer_id,
            "review_notes": review.review_notes,
            "rejection_reason": review.rejection_reason,
            "updated_at": datetime.utcnow()
        }
        
        await self.db.kyc_applications.update_one(
            {"_id": application_id},
            {"$set": update_data}
        )
        
        # Update user status if approved (handle both ObjectId and string)
        if review.status == KYCStatus.APPROVED:
            from bson import ObjectId
            from bson.errors import InvalidId
            
            user_id = app_doc["user_id"]
            
            # Try string first
            result = await self.db.users.update_one(
                {"_id": user_id},
                {"$set": {"status": "ACTIVE"}}
            )
            
            # If no document was modified, try as ObjectId
            if result.modified_count == 0:
                try:
                    await self.db.users.update_one(
                        {"_id": ObjectId(user_id)},
                        {"$set": {"status": "ACTIVE"}}
                    )
                except InvalidId:
                    pass
            
            # CRITICAL: Create account with IBAN or assign IBAN to existing accounts
            from utils.common import generate_sandbox_iban, generate_bic, generate_account_number
            from core.ledger import AccountType
            
            # Check if user has any accounts
            account = await self.db.bank_accounts.find_one({"user_id": user_id})
            
            # Also try ObjectId
            if not account:
                try:
                    account = await self.db.bank_accounts.find_one({"user_id": ObjectId(user_id)})
                except InvalidId:
                    pass
            
            if not account:
                # No account exists - create one WITH admin-provided IBAN (REQUIRED!)
                from services.ledger_service import LedgerEngine
                from schemas.banking import BankAccount
                
                # MUST have admin-provided IBAN - no fallback!
                if not review.assigned_iban:
                    raise HTTPException(status_code=400, detail="IBAN is required to approve KYC")
                
                # Create ledger account
                ledger_acc_id = f"ledger_acc_{user_id}"
                await self.db.ledger_accounts.insert_one({
                    "_id": ledger_acc_id,
                    "account_type": "WALLET",
                    "user_id": user_id,
                    "currency": "EUR",
                    "status": "ACTIVE",
                    "created_at": datetime.utcnow()
                })
                
                # Create bank account WITH admin-provided IBAN
                bank_acc_id = f"bank_acc_{user_id}"
                await self.db.bank_accounts.insert_one({
                    "_id": bank_acc_id,
                    "user_id": user_id,
                    "account_number": generate_account_number(),
                    "iban": review.assigned_iban,  # Use admin's IBAN only
                    "bic": generate_bic(),
                    "currency": "EUR",
                    "status": "ACTIVE",
                    "ledger_account_id": ledger_acc_id,
                    "opened_at": datetime.utcnow()
                })
            else:
                # Account exists but no IBAN - assign admin-provided IBAN (REQUIRED!)
                if not account.get("iban"):
                    if not review.assigned_iban:
                        raise HTTPException(status_code=400, detail="IBAN is required to approve KYC")
                    
                    await self.db.bank_accounts.update_one(
                        {"_id": account["_id"]},
                        {"$set": {
                            "iban": review.assigned_iban,  # Use admin's IBAN only
                            "bic": generate_bic()
                        }}
                    )
        
        app_doc = await self.db.kyc_applications.find_one({"_id": application_id})
        return KYCApplication(**serialize_doc(app_doc))
    
    async def get_pending_applications(self) -> List[KYCApplication]:
        """Get all pending KYC applications (admin)."""
        cursor = self.db.kyc_applications.find({
            "status": {"$in": [KYCStatus.SUBMITTED, KYCStatus.UNDER_REVIEW]}
        }).sort("submitted_at", 1)
        
        apps = []
        async for doc in cursor:
            apps.append(KYCApplication(**serialize_doc(doc)))
        
        return apps