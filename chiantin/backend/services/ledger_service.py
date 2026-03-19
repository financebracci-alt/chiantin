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
    
    async def get_bulk_balances(self, account_ids: List[str]) -> dict:
        """Calculate derived balances for multiple accounts in a single query.
        
        This is a performance-optimized method that replaces N individual 
        get_balance() calls with a single aggregation pipeline.
        
        Args:
            account_ids: List of ledger account IDs to get balances for
            
        Returns:
            Dictionary mapping account_id -> balance (in cents)
        """
        if not account_ids:
            return {}
        
        pipeline = [
            {"$match": {"account_id": {"$in": account_ids}}},
            {
                "$group": {
                    "_id": "$account_id",
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
        
        results = await self.db.ledger_entries.aggregate(pipeline).to_list(None)
        
        # Build the balance map
        balance_map = {}
        for result in results:
            account_id = result["_id"]
            balance = result["credits"] - result["debits"]
            balance_map[account_id] = balance
        
        # For accounts with no entries, set balance to 0
        for account_id in account_ids:
            if account_id not in balance_map:
                balance_map[account_id] = 0
        
        return balance_map
    
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
        performed_by: Optional[str] = None,
        metadata: Optional[dict] = None
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
            performed_by=performed_by,
            metadata=metadata
        )
    
    async def withdraw(
        self,
        user_account_id: str,
        amount: int,
        external_id: Optional[str] = None,
        reason: str = "Withdrawal",
        performed_by: Optional[str] = None,
        metadata: Optional[dict] = None
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
            performed_by=performed_by,
            metadata=metadata
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
    
    async def get_transactions(self, account_id: str, limit: int = 50) -> List[dict]:
        """Get transactions for an account with amounts, direction, and transfer status."""
        # Get entries for this account with amounts
        entries_by_txn = {}
        entry_cursor = self.db.ledger_entries.find(
            {"account_id": account_id}
        ).sort("created_at", -1).limit(limit)
        
        async for entry in entry_cursor:
            txn_id = entry.get("transaction_id")
            if not txn_id:
                # Skip entries without transaction_id (legacy data)
                continue
            entries_by_txn[txn_id] = {
                "amount": entry.get("amount", 0),
                "direction": entry.get("direction", "DEBIT")
            }
        
        if not entries_by_txn:
            return []
        
        # Get transactions
        txn_cursor = self.db.ledger_transactions.find(
            {"_id": {"$in": list(entries_by_txn.keys())}}
        ).sort("created_at", -1)
        
        txns = []
        async for doc in txn_cursor:
            txn_data = serialize_doc(doc)
            txn_id = txn_data.get("id")
            
            # Add amount and direction from entry
            if txn_id in entries_by_txn:
                txn_data["amount"] = entries_by_txn[txn_id]["amount"]
                txn_data["direction"] = entries_by_txn[txn_id]["direction"]
            
            txns.append(txn_data)
        
        # Enrich transfer-related transactions with status from transfers collection
        await self._enrich_transactions_with_transfer_status(txns)
        
        return txns
    
    async def _enrich_transactions_with_transfer_status(self, txns: List[dict]) -> None:
        """Enrich transactions with transfer status and rejection info from transfers collection."""
        if not txns:
            return
        
        # Collect all transaction IDs
        txn_ids = [txn.get("id") for txn in txns if txn.get("id")]
        
        if not txn_ids:
            return
        
        # Find all transfers that reference these transaction IDs
        transfer_cursor = self.db.transfers.find(
            {"transaction_id": {"$in": txn_ids}}
        )
        
        # Build a map of transaction_id -> transfer data
        transfer_map = {}
        async for transfer in transfer_cursor:
            txn_id = transfer.get("transaction_id")
            if txn_id:
                transfer_map[txn_id] = {
                    "transfer_id": transfer.get("_id"),
                    "status": transfer.get("status"),
                    "rejection_reason": transfer.get("rejection_reason") or transfer.get("reject_reason"),
                    "beneficiary_name": transfer.get("beneficiary_name"),
                    "beneficiary_iban": transfer.get("beneficiary_iban"),
                    "transfer_type": transfer.get("transfer_type"),
                    "reference_number": transfer.get("reference_number")
                }
        
        # Enrich transactions with transfer data
        for txn in txns:
            txn_id = txn.get("id")
            if txn_id and txn_id in transfer_map:
                transfer_data = transfer_map[txn_id]
                
                # Update transaction status based on transfer status
                transfer_status = transfer_data.get("status")
                if transfer_status:
                    txn["status"] = transfer_status
                
                # Add rejection reason if available
                rejection_reason = transfer_data.get("rejection_reason")
                if rejection_reason:
                    txn["rejection_reason"] = rejection_reason
                    # Also add to metadata for frontend compatibility
                    if "metadata" not in txn:
                        txn["metadata"] = {}
                    txn["metadata"]["rejection_reason"] = rejection_reason
                
                # Update metadata with transfer info for better display
                if "metadata" not in txn:
                    txn["metadata"] = {}
                
                if transfer_data.get("beneficiary_name"):
                    txn["metadata"]["recipient_name"] = transfer_data["beneficiary_name"]
                if transfer_data.get("beneficiary_iban"):
                    txn["metadata"]["recipient_iban"] = transfer_data["beneficiary_iban"]
                if transfer_data.get("transfer_type"):
                    # Set proper display type based on transfer type
                    if transfer_data["transfer_type"] == "SEPA":
                        txn["metadata"]["display_type"] = "SEPA Transfer"
                    elif transfer_data["transfer_type"] == "INTERNAL":
                        txn["metadata"]["display_type"] = "SEPA Transfer"
                if transfer_data.get("reference_number"):
                    txn["metadata"]["reference"] = transfer_data["reference_number"]
                if transfer_data.get("transfer_id"):
                    txn["metadata"]["transfer_id"] = transfer_data["transfer_id"]
    
    async def reverse_transaction(
        self,
        original_txn_id: str,
        external_id: Optional[str] = None,
        reason: Optional[str] = None,
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Reverse a posted transaction by creating mirror entries."""
        # Check idempotency
        if external_id:
            existing = await self.db.ledger_transactions.find_one({"external_id": external_id})
            if existing:
                return LedgerTransaction(**serialize_doc(existing))
        
        # Get original transaction
        original_txn_doc = await self.db.ledger_transactions.find_one({"_id": original_txn_id})
        if not original_txn_doc:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        if original_txn_doc["status"] == "REVERSED":
            raise HTTPException(status_code=400, detail="Transaction already reversed")
        
        # Get original entries
        original_entries = []
        entry_cursor = self.db.ledger_entries.find({"transaction_id": original_txn_id})
        async for entry in entry_cursor:
            original_entries.append(entry)
        
        # Create reversal transaction
        reversal_txn = LedgerTransaction(
            transaction_type="REVERSAL",
            status=TransactionStatus.POSTED,
            external_id=external_id,
            reverses_txn_id=original_txn_id,
            reason=reason or f"Reversal of {original_txn_id}",
            performed_by=performed_by,
            metadata={"original_txn_type": original_txn_doc["transaction_type"]}
        )
        
        reversal_dict = reversal_txn.model_dump()
        reversal_dict["_id"] = reversal_txn.id
        await self.db.ledger_transactions.insert_one(reversal_dict)
        
        # Create mirror entries (swap direction)
        reversal_entries = []
        for orig_entry in original_entries:
            reversed_direction = (
                EntryDirection.CREDIT if orig_entry["direction"] == "DEBIT"
                else EntryDirection.DEBIT
            )
            entry = LedgerEntry(
                transaction_id=reversal_txn.id,
                account_id=orig_entry["account_id"],
                amount=orig_entry["amount"],
                direction=reversed_direction,
                currency=orig_entry["currency"]
            )
            entry_dict = entry.model_dump()
            entry_dict["_id"] = entry.id
            reversal_entries.append(entry_dict)
        
        if reversal_entries:
            await self.db.ledger_entries.insert_many(reversal_entries)
        
        # Mark original as reversed
        await self.db.ledger_transactions.update_one(
            {"_id": original_txn_id},
            {
                "$set": {
                    "status": "REVERSED",
                    "reversed_by_txn_id": reversal_txn.id
                }
            }
        )
        
        return reversal_txn