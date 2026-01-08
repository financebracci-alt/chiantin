"""Ledger service with MongoDB persistence."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import HTTPException

from core.ledger import (
    LedgerAccount,
    LedgerTransaction,
    LedgerEntry,
    AccountType,
    EntryDirection,
    TransactionStatus
)
from utils.common import serialize_doc
from bson import ObjectId


class LedgerEngine:
    """MongoDB-backed ledger engine."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_account(
        self,
        account_type: AccountType,
        user_id: Optional[str] = None,
        currency: str = "EUR"
    ) -> LedgerAccount:
        """Create a new ledger account."""
        account = LedgerAccount(
            account_type=account_type,
            user_id=user_id,
            currency=currency
        )
        account_dict = account.model_dump()
        account_dict["_id"] = account.id
        await self.db.ledger_accounts.insert_one(account_dict)
        return account
    
    async def get_balance(self, account_id: str) -> int:
        """Calculate derived balance for an account."""
        pipeline = [
            {"$match": {"account_id": account_id}},
            {
                "$group": {
                    "_id": None,
                    "credits": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$direction", "CREDIT"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "debits": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$direction", "DEBIT"]},
                                "$amount",
                                0
                            ]
                        }
                    }
                }
            }
        ]
        
        result = await self.db.ledger_entries.aggregate(pipeline).to_list(1)
        
        if not result:
            return 0
        
        return result[0]["credits"] - result[0]["debits"]
    
    async def post_transaction(
        self,
        transaction_type: str,
        entries: List[Tuple[str, int, EntryDirection]],
        external_id: Optional[str] = None,
        reason: Optional[str] = None,
        performed_by: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> LedgerTransaction:
        """Post a transaction with entries."""
        # Check idempotency
        if external_id:
            existing = await self.db.ledger_transactions.find_one({"external_id": external_id})
            if existing:
                return LedgerTransaction(**serialize_doc(existing))
        
        # Validate entries balance
        by_currency = {}
        for account_id, amount, direction in entries:
            account = await self.db.ledger_accounts.find_one({"_id": account_id})
            if not account:
                raise HTTPException(status_code=400, detail=f"Account {account_id} not found")
            
            currency = account["currency"]
            if currency not in by_currency:
                by_currency[currency] = {"debits": 0, "credits": 0}
            
            if direction == EntryDirection.DEBIT:
                by_currency[currency]["debits"] += amount
            else:
                by_currency[currency]["credits"] += amount
        
        # Check balance
        for currency, totals in by_currency.items():
            if totals["debits"] != totals["credits"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unbalanced transaction for {currency}: debits={totals['debits']}, credits={totals['credits']}"
                )
        
        # Create transaction
        txn = LedgerTransaction(
            transaction_type=transaction_type,
            status=TransactionStatus.POSTED,
            external_id=external_id,
            reason=reason,
            performed_by=performed_by,
            metadata=metadata or {}
        )
        
        txn_dict = txn.model_dump()
        txn_dict["_id"] = txn.id
        await self.db.ledger_transactions.insert_one(txn_dict)
        
        # Create entries
        entry_docs = []
        for account_id, amount, direction in entries:
            account = await self.db.ledger_accounts.find_one({"_id": account_id})
            entry = LedgerEntry(
                transaction_id=txn.id,
                account_id=account_id,
                amount=amount,
                direction=direction,
                currency=account["currency"]
            )
            entry_dict = entry.model_dump()
            entry_dict["_id"] = entry.id
            entry_docs.append(entry_dict)
        
        if entry_docs:
            await self.db.ledger_entries.insert_many(entry_docs)
        
        return txn
    
    async def top_up(
        self,
        user_account_id: str,
        amount: int,
        external_id: Optional[str] = None,
        reason: str = "Sandbox top-up",
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Add funds to user account."""
        # Get or create sandbox funding account
        funding = await self.db.ledger_accounts.find_one({"account_type": "SANDBOX_FUNDING"})
        if not funding:
            acc = await self.create_account(AccountType.SANDBOX_FUNDING)
            funding_id = acc.id
        else:
            funding_id = str(funding["_id"])
        
        return await self.post_transaction(
            transaction_type="TOP_UP",
            entries=[
                (user_account_id, amount, EntryDirection.CREDIT),
                (funding_id, amount, EntryDirection.DEBIT)
            ],
            external_id=external_id,
            reason=reason,
            performed_by=performed_by
        )
    
    async def withdraw(
        self,
        user_account_id: str,
        amount: int,
        external_id: Optional[str] = None,
        reason: str = "Withdrawal",
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Remove funds from user account."""
        funding = await self.db.ledger_accounts.find_one({"account_type": "SANDBOX_FUNDING"})
        if not funding:
            acc = await self.create_account(AccountType.SANDBOX_FUNDING)
            funding_id = acc.id
        else:
            funding_id = str(funding["_id"])
        
        return await self.post_transaction(
            transaction_type="WITHDRAW",
            entries=[
                (user_account_id, amount, EntryDirection.DEBIT),
                (funding_id, amount, EntryDirection.CREDIT)
            ],
            external_id=external_id,
            reason=reason,
            performed_by=performed_by
        )
    
    async def charge_fee(
        self,
        user_account_id: str,
        amount: int,
        external_id: Optional[str] = None,
        reason: str = "Fee",
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Charge fee to user account."""
        fees = await self.db.ledger_accounts.find_one({"account_type": "FEES"})
        if not fees:
            acc = await self.create_account(AccountType.FEES)
            fees_id = acc.id
        else:
            fees_id = str(fees["_id"])
        
        return await self.post_transaction(
            transaction_type="FEE",
            entries=[
                (user_account_id, amount, EntryDirection.DEBIT),
                (fees_id, amount, EntryDirection.CREDIT)
            ],
            external_id=external_id,
            reason=reason,
            performed_by=performed_by
        )
    
    async def get_transactions(self, account_id: str, limit: int = 50) -> List[LedgerTransaction]:
        """Get transactions for an account."""
        # Get entries for this account
        entry_cursor = self.db.ledger_entries.find(
            {"account_id": account_id}
        ).sort("created_at", -1).limit(limit)
        
        txn_ids = set()
        async for entry in entry_cursor:
            txn_ids.add(entry["transaction_id"])
        
        # Get transactions
        txn_cursor = self.db.ledger_transactions.find(
            {"_id": {"$in": list(txn_ids)}}
        ).sort("created_at", -1)
        
        txns = []
        async for doc in txn_cursor:
            txns.append(LedgerTransaction(**serialize_doc(doc)))
        
        return txns