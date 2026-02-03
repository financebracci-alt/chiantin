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
        """Upload a KYC document to Cloudinary."""
        # Ensure KYC application exists
        await self.get_or_create_application(user_id)
        
        # Generate unique key
        file_id = str(uuid.uuid4())
        key = f"kyc/{user_id}/{document_type.value}_{file_id}_{file.filename}"
        
        # Upload to Cloudinary storage
        metadata = self.storage.upload_fileobj(
            file.file,
            key,
            content_type=file.content_type
        )
        
        # Create document record with Cloudinary URL
        doc = KYCDocument(
            document_type=document_type,
            file_key=key,
            file_name=file.filename,
            file_size=metadata.size,
            content_type=file.content_type or "application/octet-stream"
        )
        
        # Add Cloudinary URL to the document data
        doc_data = doc.model_dump()
        doc_data["cloudinary_url"] = metadata.url  # Store the Cloudinary URL
        
        # Add to application
        await self.db.kyc_applications.update_one(
            {"user_id": user_id},
            {"$push": {"documents": doc_data}}
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
        
        # CRITICAL VALIDATION: Ensure required documents are uploaded
        # Get the latest application data to check documents
        app_doc = await self.db.kyc_applications.find_one({"user_id": user_id})
        documents = app_doc.get("documents", []) if app_doc else []
        
        # Check for required document types
        doc_types = {doc.get("document_type") for doc in documents}
        required_docs = {"PASSPORT", "PROOF_OF_ADDRESS"}  # Minimum required
        missing_docs = required_docs - doc_types
        
        if missing_docs:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required documents: {', '.join(missing_docs)}. Please upload all required documents before submitting."
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
        
        # STRICT VALIDATION: If approving, IBAN and BIC are ALWAYS required
        if review.status == KYCStatus.APPROVED:
            if not review.assigned_iban or not review.assigned_iban.strip():
                raise HTTPException(status_code=400, detail="IBAN is required to approve KYC")
            if not review.assigned_bic or not review.assigned_bic.strip():
                raise HTTPException(status_code=400, detail="BIC/SWIFT is required to approve KYC")
            
            # Basic IBAN format validation
            import re
            iban_clean = review.assigned_iban.replace(" ", "").upper()
            if not re.match(r'^[A-Z]{2}[A-Z0-9]{13,32}$', iban_clean):
                raise HTTPException(status_code=400, detail="Invalid IBAN format. Must start with 2 letters followed by 13-32 alphanumeric characters")
            
            # Basic BIC format validation (8 or 11 characters)
            bic_clean = review.assigned_bic.replace(" ", "").upper()
            if not re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', bic_clean):
                raise HTTPException(status_code=400, detail="Invalid BIC/SWIFT format. Must be 8 or 11 characters (e.g., ATLASLT21 or ATLASLT21XXX)")
        
        # For APPROVED status, create/update account FIRST before updating KYC status
        if review.status == KYCStatus.APPROVED:
            from bson import ObjectId
            from bson.errors import InvalidId
            from utils.common import generate_account_number
            
            user_id = app_doc["user_id"]
            iban_clean = review.assigned_iban.replace(" ", "").upper()
            bic_clean = review.assigned_bic.replace(" ", "").upper()
            
            # Check if user has any accounts (try both string and ObjectId)
            account = await self.db.bank_accounts.find_one({"user_id": user_id})
            if not account:
                try:
                    account = await self.db.bank_accounts.find_one({"user_id": ObjectId(user_id)})
                except InvalidId:
                    pass
            
            try:
                if not account:
                    # No account exists - create ledger account and bank account
                    ledger_acc_id = f"ledger_acc_{user_id}"
                    bank_acc_id = f"bank_acc_{user_id}"
                    
                    # Check if ledger account already exists (avoid duplicate key error)
                    existing_ledger = await self.db.ledger_accounts.find_one({"_id": ledger_acc_id})
                    if not existing_ledger:
                        await self.db.ledger_accounts.insert_one({
                            "_id": ledger_acc_id,
                            "account_type": "WALLET",
                            "user_id": user_id,
                            "currency": "EUR",
                            "status": "ACTIVE",
                            "created_at": datetime.utcnow()
                        })
                    
                    # Check if bank account already exists (avoid duplicate key error)
                    existing_bank = await self.db.bank_accounts.find_one({"_id": bank_acc_id})
                    if not existing_bank:
                        await self.db.bank_accounts.insert_one({
                            "_id": bank_acc_id,
                            "user_id": user_id,
                            "account_number": generate_account_number(),
                            "iban": iban_clean,
                            "bic": bic_clean,
                            "currency": "EUR",
                            "status": "ACTIVE",
                            "ledger_account_id": ledger_acc_id,
                            "opened_at": datetime.utcnow()
                        })
                    else:
                        # Bank account exists but may not have IBAN - update it
                        await self.db.bank_accounts.update_one(
                            {"_id": bank_acc_id},
                            {"$set": {"iban": iban_clean, "bic": bic_clean}}
                        )
                else:
                    # Account exists - update IBAN and BIC
                    await self.db.bank_accounts.update_one(
                        {"_id": account["_id"]},
                        {"$set": {"iban": iban_clean, "bic": bic_clean}}
                    )
            except Exception as e:
                # If account creation fails, don't approve the KYC
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to create/update bank account: {str(e)}. Please try again."
                )
            
            # Update user status to ACTIVE
            result = await self.db.users.update_one(
                {"_id": user_id},
                {"$set": {"status": "ACTIVE"}}
            )
            if result.modified_count == 0:
                try:
                    await self.db.users.update_one(
                        {"_id": ObjectId(user_id)},
                        {"$set": {"status": "ACTIVE"}}
                    )
                except InvalidId:
                    pass
        
        # NOW update the KYC application status (after account is created/updated)
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
        
        app_doc = await self.db.kyc_applications.find_one({"_id": application_id})
        return KYCApplication(**serialize_doc(app_doc))
    
    async def get_pending_applications(self) -> List[KYCApplication]:
        """Get all pending KYC applications (admin)."""
        cursor = self.db.kyc_applications.find({
            "status": {"$in": [KYCStatus.SUBMITTED, KYCStatus.UNDER_REVIEW, KYCStatus.NEEDS_MORE_INFO]}
        }).sort("submitted_at", 1)
        
        apps = []
        async for doc in cursor:
            apps.append(KYCApplication(**serialize_doc(doc)))
        
        return apps