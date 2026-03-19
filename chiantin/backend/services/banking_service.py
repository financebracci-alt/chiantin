"""Banking service."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from fastapi import HTTPException
from typing import List, Optional

from schemas.banking import BankAccount, AccountStatus, AccountResponse
from core.ledger import LedgerEngine, AccountType
from utils.common import serialize_doc, generate_account_number, generate_sandbox_iban, generate_bic


class BankingService:
    def __init__(self, db: AsyncIOMotorDatabase, ledger_engine: LedgerEngine):
        self.db = db
        self.ledger = ledger_engine
    
    async def create_account(self, user_id: str, kyc_status: str = None) -> BankAccount:
        """Create a new bank account for user."""
        # Check if user already has an account
        existing = await self.db.bank_accounts.find_one({"user_id": user_id})
        if existing:
            return BankAccount(**serialize_doc(existing))
        
        # Create ledger account
        ledger_account = await self.ledger.create_account(
            account_type=AccountType.WALLET,
            user_id=user_id
        )
        
        # Only assign IBAN if KYC is approved
        iban = None
        bic = None
        if kyc_status == 'APPROVED':
            iban = generate_sandbox_iban()
            bic = generate_bic()
        
        # Create bank account
        account = BankAccount(
            user_id=user_id,
            account_number=generate_account_number(),
            iban=iban,  # Will be None if not KYC approved
            bic=bic,
            ledger_account_id=ledger_account.id
        )
        
        account_dict = account.model_dump(by_alias=True)
        await self.db.bank_accounts.insert_one(account_dict)
        
        return account
    
    async def get_user_accounts(self, user_id: str) -> List[AccountResponse]:
        """Get all accounts for a user with balances."""
        from bson import ObjectId
        from bson.errors import InvalidId
        
        # Try to find accounts with both string and ObjectId formats
        accounts_list = []
        
        # First try as string
        cursor = self.db.bank_accounts.find({"user_id": user_id})
        async for doc in cursor:
            accounts_list.append(doc)
        
        # If no results, try as ObjectId
        if not accounts_list:
            try:
                cursor = self.db.bank_accounts.find({"user_id": ObjectId(user_id)})
                async for doc in cursor:
                    accounts_list.append(doc)
            except InvalidId:
                pass
        
        accounts = []
        for doc in accounts_list:
            account = BankAccount(**serialize_doc(doc))
            balance = await self.ledger.get_balance(account.ledger_account_id)
            
            accounts.append(AccountResponse(
                id=account.id,
                account_number=account.account_number,
                iban=account.iban,
                bic=account.bic,
                currency=account.currency,
                status=account.status,
                balance=balance,
                opened_at=account.opened_at
            ))
        
        return accounts
    
    async def get_account(self, account_id: str) -> Optional[BankAccount]:
        """Get account by ID."""
        doc = await self.db.bank_accounts.find_one({"_id": account_id})
        if not doc:
            return None
        return BankAccount(**serialize_doc(doc))