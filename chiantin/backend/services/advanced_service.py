"""Advanced banking features service."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta, date
from typing import List, Optional
from fastapi import HTTPException
import uuid

from schemas.advanced import ScheduledPayment, CreateScheduledPayment, Beneficiary, CreateBeneficiary, RecurringFrequency
from services.transfer_service import TransferService
from services.ledger_service import LedgerEngine
from utils.common import serialize_doc


class AdvancedBankingService:
    def __init__(self, db: AsyncIOMotorDatabase, ledger_engine: LedgerEngine):
        self.db = db
        self.ledger = ledger_engine
        self.transfer_service = TransferService(db, ledger_engine)
    
    # ==================== BENEFICIARIES ====================
    
    async def add_beneficiary(
        self,
        user_id: str,
        data: CreateBeneficiary
    ) -> Beneficiary:
        """Add a new beneficiary."""
        # Check if already exists
        existing = await self.db.beneficiaries.find_one({
            "user_id": user_id,
            "recipient_email": data.recipient_email.lower()
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Beneficiary already exists")
        
        beneficiary = Beneficiary(
            user_id=user_id,
            recipient_name=data.recipient_name,
            recipient_email=data.recipient_email.lower(),
            nickname=data.nickname
        )
        
        ben_dict = beneficiary.model_dump(by_alias=True)
        await self.db.beneficiaries.insert_one(ben_dict)
        
        return beneficiary
    
    async def get_beneficiaries(self, user_id: str) -> List[Beneficiary]:
        """Get all beneficiaries for a user."""
        cursor = self.db.beneficiaries.find({"user_id": user_id}).sort("last_used", -1)
        beneficiaries = []
        async for doc in cursor:
            beneficiaries.append(Beneficiary(**serialize_doc(doc)))
        return beneficiaries
    
    async def delete_beneficiary(self, beneficiary_id: str, user_id: str) -> bool:
        """Delete a beneficiary."""
        result = await self.db.beneficiaries.delete_one({
            "_id": beneficiary_id,
            "user_id": user_id
        })
        return result.deleted_count > 0
    
    # ==================== SCHEDULED PAYMENTS ====================
    
    async def create_scheduled_payment(
        self,
        user_id: str,
        data: CreateScheduledPayment
    ) -> ScheduledPayment:
        """Create a scheduled recurring payment."""
        # Parse date strings to datetime
        from datetime import datetime as dt
        start_dt = dt.fromisoformat(data.start_date) if isinstance(data.start_date, str) else datetime.combine(data.start_date, datetime.min.time())
        end_dt = dt.fromisoformat(data.end_date) if data.end_date and isinstance(data.end_date, str) else None
        
        # Calculate next execution
        next_exec = self._calculate_next_execution(start_dt.date(), data.frequency)
        
        scheduled = ScheduledPayment(
            user_id=user_id,
            recipient_email=data.recipient_email,
            amount=data.amount,
            reason=data.reason,
            frequency=data.frequency,
            start_date=start_dt,
            end_date=end_dt,
            next_execution=next_exec
        )
        
        sched_dict = scheduled.model_dump(by_alias=True)
        await self.db.scheduled_payments.insert_one(sched_dict)
        
        return scheduled
    
    async def get_scheduled_payments(self, user_id: str) -> List[ScheduledPayment]:
        """Get all scheduled payments for a user."""
        cursor = self.db.scheduled_payments.find({"user_id": user_id}).sort("created_at", -1)
        payments = []
        async for doc in cursor:
            payments.append(ScheduledPayment(**serialize_doc(doc)))
        return payments
    
    async def cancel_scheduled_payment(self, payment_id: str, user_id: str) -> bool:
        """Cancel a scheduled payment."""
        result = await self.db.scheduled_payments.update_one(
            {"_id": payment_id, "user_id": user_id},
            {"$set": {"active": False}}
        )
        return result.modified_count > 0
    
    def _calculate_next_execution(self, start: date, frequency: RecurringFrequency) -> datetime:
        """Calculate next execution datetime."""
        start_dt = datetime.combine(start, datetime.min.time())
        
        if frequency == RecurringFrequency.DAILY:
            return start_dt + timedelta(days=1)
        elif frequency == RecurringFrequency.WEEKLY:
            return start_dt + timedelta(weeks=1)
        elif frequency == RecurringFrequency.MONTHLY:
            return start_dt + timedelta(days=30)
        elif frequency == RecurringFrequency.YEARLY:
            return start_dt + timedelta(days=365)
        
        return start_dt
    
    # ==================== SPENDING INSIGHTS ====================
    
    async def get_spending_by_category(self, user_id: str, days: int = 30):
        """Get spending breakdown by category from real ledger data."""
        # Get user's bank accounts and their ledger account IDs
        ledger_account_ids = []
        async for acc in self.db.bank_accounts.find({"user_id": user_id}):
            if acc.get("ledger_account_id"):
                ledger_account_ids.append(acc["ledger_account_id"])
        
        if not ledger_account_ids:
            return {"total": 0, "categories": {}}
        
        # Calculate date range
        from_date = datetime.utcnow() - timedelta(days=days)
        
        # Query all DEBIT entries (money going out) for user's ledger accounts
        # DEBIT on a user's asset account means money leaving their account
        pipeline = [
            {
                "$match": {
                    "account_id": {"$in": ledger_account_ids},
                    "direction": "DEBIT",
                    "created_at": {"$gte": from_date}
                }
            },
            {
                "$lookup": {
                    "from": "ledger_transactions",
                    "localField": "transaction_id",
                    "foreignField": "_id",
                    "as": "transaction"
                }
            },
            {
                "$unwind": "$transaction"
            },
            {
                "$group": {
                    "_id": "$transaction.transaction_type",
                    "total": {"$sum": "$amount"}
                }
            }
        ]
        
        # Execute aggregation
        results = await self.db.ledger_entries.aggregate(pipeline).to_list(100)
        
        # Map transaction types to user-friendly categories
        category_mapping = {
            "WITHDRAW": "WITHDRAWALS",
            "TRANSFER": "TRANSFERS",
            "P2P_TRANSFER": "TRANSFERS",
            "FEE": "FEES",
            "INTERNAL_TRANSFER": "TRANSFERS",
            "REVERSAL": "REVERSALS",
            "PAYMENT": "PAYMENTS",
            "CARD_PAYMENT": "CARD_PAYMENTS"
        }
        
        # Build category breakdown
        categories = {}
        total_spending = 0
        
        for result in results:
            txn_type = result["_id"]
            amount = result["total"]
            
            # Map to category
            category = category_mapping.get(txn_type, "OTHER")
            
            if category in categories:
                categories[category] += amount
            else:
                categories[category] = amount
            
            total_spending += amount
        
        return {
            "total": total_spending,
            "categories": categories
        }
    
    async def get_monthly_spending(self, user_id: str):
        """Get spending for the current calendar month from real ledger data.
        
        PERFORMANCE OPTIMIZED: Uses efficient aggregation pipeline with indexed fields.
        
        Excludes:
        - Refund transactions (TRANSFER_REFUND, REFUND)
        - Transfer transactions where the transfer was REJECTED
        """
        # Get user's bank accounts and their ledger account IDs in one query
        accounts = await self.db.bank_accounts.find(
            {"user_id": user_id}, 
            {"ledger_account_id": 1}
        ).to_list(10)  # Most users have 1-2 accounts
        
        ledger_account_ids = [acc["ledger_account_id"] for acc in accounts if acc.get("ledger_account_id")]
        
        if not ledger_account_ids:
            return {"total": 0, "transaction_count": 0, "categories": {}}
        
        # Calculate first day of current month
        now = datetime.utcnow()
        first_of_month = datetime(now.year, now.month, 1)
        
        # Get rejected transfer transaction IDs - only those from this month (limit scope)
        rejected_txn_ids = set()
        rejected_cursor = self.db.transfers.find(
            {"status": "REJECTED", "created_at": {"$gte": first_of_month}},
            {"transaction_id": 1}
        )
        async for transfer in rejected_cursor:
            if transfer.get("transaction_id"):
                rejected_txn_ids.add(transfer["transaction_id"])
        
        # Optimized aggregation: group and sum in MongoDB
        pipeline = [
            {
                "$match": {
                    "account_id": {"$in": ledger_account_ids},
                    "direction": "DEBIT",
                    "created_at": {"$gte": first_of_month}
                }
            },
            {
                "$lookup": {
                    "from": "ledger_transactions",
                    "localField": "transaction_id",
                    "foreignField": "_id",
                    "as": "transaction"
                }
            },
            {
                "$unwind": "$transaction"
            },
            {
                # Exclude refund transactions from spending
                "$match": {
                    "transaction.transaction_type": {"$nin": ["TRANSFER_REFUND", "REFUND", "TOP_UP", "CREDIT"]}
                }
            },
            {
                # Group by transaction type to get aggregated spending
                "$group": {
                    "_id": "$transaction.transaction_type",
                    "total": {"$sum": "$amount"},
                    "count": {"$sum": 1},
                    "txn_ids": {"$push": "$transaction_id"}
                }
            }
        ]
        
        results = await self.db.ledger_entries.aggregate(pipeline).to_list(20)
        
        # Category mapping
        category_mapping = {
            "WITHDRAW": "WITHDRAWALS",
            "TRANSFER": "TRANSFERS",
            "P2P_TRANSFER": "TRANSFERS",
            "SEPA_TRANSFER": "TRANSFERS",
            "FEE": "FEES",
            "INTERNAL_TRANSFER": "TRANSFERS",
            "REVERSAL": "REVERSALS",
            "PAYMENT": "PAYMENTS",
            "CARD_PAYMENT": "CARD_PAYMENTS"
        }
        
        categories = {}
        total_spending = 0
        total_transactions = 0
        
        for result in results:
            txn_type = result["_id"]
            amount = result["total"]
            count = result["count"]
            txn_ids = result.get("txn_ids", [])
            
            # Subtract rejected transactions from count
            rejected_count = sum(1 for tid in txn_ids if tid in rejected_txn_ids)
            # Adjust if we had any rejected (approximate - assumes average amount)
            if rejected_count > 0 and count > rejected_count:
                # Only exclude if there are non-rejected transactions
                amount = int(amount * (count - rejected_count) / count)
                count -= rejected_count
            elif rejected_count == count:
                # All transactions are rejected, skip this type
                continue
            
            category = category_mapping.get(txn_type, "OTHER")
            
            if category in categories:
                categories[category] += amount
            else:
                categories[category] = amount
            
            total_spending += amount
            total_transactions += count
        
        return {
            "total": total_spending,
            "transaction_count": total_transactions,
            "categories": categories,
            "period": {
                "start": first_of_month.isoformat(),
                "end": now.isoformat()
            }
        }
