"""
Ledger Integrity Check Script

This script performs read-only verification of ledger integrity:
1. Confirms no bank_accounts have a persisted 'balance' field
2. Verifies all ledger transactions are balanced (debits = credits)
3. Checks for orphan ledger entries (entries without valid transactions)
4. Validates transfer <-> ledger transaction linkage
5. Identifies accounts with negative balances (policy violation check)
6. Generates a comprehensive integrity report

Run with: python scripts/ledger_integrity_check.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")


class LedgerIntegrityChecker:
    """Comprehensive ledger integrity verification"""
    
    def __init__(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": db_name,
            "checks": {},
            "anomalies": [],
            "summary": {},
            "statistics": {}
        }
    
    async def run_all_checks(self):
        """Execute all integrity checks"""
        print("=" * 80)
        print("LEDGER INTEGRITY CHECK - Project Atlas Banking")
        print("=" * 80)
        print(f"Database: {self.db.name}")
        print(f"Timestamp: {self.report['timestamp']}")
        print("=" * 80)
        
        # Check 1: Bank accounts should NOT have balance field
        await self.check_no_persisted_balance()
        
        # Check 2: All transactions must be balanced
        await self.check_transaction_balance()
        
        # Check 3: Check for orphan ledger entries
        await self.check_orphan_entries()
        
        # Check 4: Verify transfer -> transaction linkage
        await self.check_transfer_linkage()
        
        # Check 5: Check for negative balances
        await self.check_negative_balances()
        
        # Check 6: Verify ledger account existence
        await self.check_ledger_accounts_exist()
        
        # Generate statistics
        await self.generate_statistics()
        
        # Print summary
        self.print_summary()
        
        return self.report
    
    async def check_no_persisted_balance(self):
        """Verify no bank_accounts have a 'balance' field"""
        print("\n[CHECK 1] Verifying no persisted balance field in bank_accounts...")
        
        accounts_with_balance = []
        cursor = self.db.bank_accounts.find({"balance": {"$exists": True}})
        async for account in cursor:
            accounts_with_balance.append({
                "account_id": account.get("_id"),
                "balance_value": account.get("balance")
            })
        
        if accounts_with_balance:
            self.report["anomalies"].append({
                "type": "PERSISTED_BALANCE_FOUND",
                "severity": "CRITICAL",
                "count": len(accounts_with_balance),
                "details": accounts_with_balance[:10]  # Show first 10
            })
            print(f"  ❌ FAILED: Found {len(accounts_with_balance)} accounts with balance field")
        else:
            print(f"  ✅ PASSED: No persisted balance fields found")
        
        self.report["checks"]["no_persisted_balance"] = {
            "passed": len(accounts_with_balance) == 0,
            "accounts_with_balance": len(accounts_with_balance)
        }
    
    async def check_transaction_balance(self):
        """Verify all transactions are balanced (debits = credits)"""
        print("\n[CHECK 2] Verifying all transactions are balanced...")
        
        unbalanced_transactions = []
        
        # Get all transactions
        transactions = await self.db.ledger_transactions.find().to_list(None)
        
        for txn in transactions:
            txn_id = txn.get("_id")
            
            # Sum debits and credits for this transaction
            entries = await self.db.ledger_entries.find({"transaction_id": txn_id}).to_list(None)
            
            debits = sum(e["amount"] for e in entries if e.get("direction") == "DEBIT")
            credits = sum(e["amount"] for e in entries if e.get("direction") == "CREDIT")
            
            if debits != credits:
                unbalanced_transactions.append({
                    "transaction_id": txn_id,
                    "debits": debits,
                    "credits": credits,
                    "difference": abs(debits - credits),
                    "type": txn.get("transaction_type"),
                    "status": txn.get("status")
                })
        
        if unbalanced_transactions:
            self.report["anomalies"].append({
                "type": "UNBALANCED_TRANSACTION",
                "severity": "CRITICAL",
                "count": len(unbalanced_transactions),
                "details": unbalanced_transactions[:10]
            })
            print(f"  ❌ FAILED: Found {len(unbalanced_transactions)} unbalanced transactions")
        else:
            print(f"  ✅ PASSED: All {len(transactions)} transactions are balanced")
        
        self.report["checks"]["transaction_balance"] = {
            "passed": len(unbalanced_transactions) == 0,
            "total_transactions": len(transactions),
            "unbalanced_count": len(unbalanced_transactions)
        }
    
    async def check_orphan_entries(self):
        """Check for ledger entries without valid transactions"""
        print("\n[CHECK 3] Checking for orphan ledger entries...")
        
        # Get all unique transaction IDs from entries
        entry_txn_ids = await self.db.ledger_entries.distinct("transaction_id")
        
        # Get all transaction IDs
        txn_ids = await self.db.ledger_transactions.distinct("_id")
        txn_id_set = set(txn_ids)
        
        # Find orphans
        orphan_txn_ids = [tid for tid in entry_txn_ids if tid not in txn_id_set]
        
        if orphan_txn_ids:
            # Get sample entries
            orphan_entries = []
            for txn_id in orphan_txn_ids[:5]:
                entries = await self.db.ledger_entries.find({"transaction_id": txn_id}).to_list(None)
                orphan_entries.append({
                    "transaction_id": txn_id,
                    "entry_count": len(entries),
                    "sample_entry": entries[0] if entries else None
                })
            
            self.report["anomalies"].append({
                "type": "ORPHAN_LEDGER_ENTRIES",
                "severity": "HIGH",
                "count": len(orphan_txn_ids),
                "details": orphan_entries
            })
            print(f"  ❌ FAILED: Found {len(orphan_txn_ids)} orphan entry groups")
        else:
            print(f"  ✅ PASSED: No orphan entries found")
        
        self.report["checks"]["orphan_entries"] = {
            "passed": len(orphan_txn_ids) == 0,
            "orphan_transaction_ids": len(orphan_txn_ids)
        }
    
    async def check_transfer_linkage(self):
        """Verify all transfers link to valid ledger transactions"""
        print("\n[CHECK 4] Verifying transfer -> transaction linkage...")
        
        invalid_links = []
        
        # Get all transfers
        transfers = await self.db.transfers.find().to_list(None)
        
        for transfer in transfers:
            txn_id = transfer.get("transaction_id")
            transfer_id = transfer.get("_id")
            
            if not txn_id:
                invalid_links.append({
                    "transfer_id": transfer_id,
                    "issue": "NO_TRANSACTION_ID",
                    "status": transfer.get("status")
                })
                continue
            
            # Check if transaction exists
            txn = await self.db.ledger_transactions.find_one({"_id": txn_id})
            if not txn:
                invalid_links.append({
                    "transfer_id": transfer_id,
                    "transaction_id": txn_id,
                    "issue": "TRANSACTION_NOT_FOUND",
                    "status": transfer.get("status")
                })
        
        if invalid_links:
            self.report["anomalies"].append({
                "type": "INVALID_TRANSFER_LINKAGE",
                "severity": "HIGH",
                "count": len(invalid_links),
                "details": invalid_links[:10]
            })
            print(f"  ❌ FAILED: Found {len(invalid_links)} transfers with invalid linkage")
        else:
            print(f"  ✅ PASSED: All {len(transfers)} transfers link to valid transactions")
        
        self.report["checks"]["transfer_linkage"] = {
            "passed": len(invalid_links) == 0,
            "total_transfers": len(transfers),
            "invalid_links": len(invalid_links)
        }
    
    async def check_negative_balances(self):
        """Check for accounts with negative balances (policy check)"""
        print("\n[CHECK 5] Checking for negative balances...")
        
        negative_accounts = []
        
        # Get all ledger accounts
        accounts = await self.db.ledger_accounts.find().to_list(None)
        
        for account in accounts:
            account_id = account.get("_id")
            
            # Calculate balance
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
            
            if result:
                balance = result[0]["credits"] - result[0]["debits"]
                
                # Only flag user wallet accounts with negative balance
                if balance < 0 and account.get("account_type") == "WALLET":
                    # Get user info
                    user_id = account.get("user_id")
                    bank_account = await self.db.bank_accounts.find_one({"ledger_account_id": account_id})
                    
                    negative_accounts.append({
                        "account_id": account_id,
                        "balance": balance,
                        "balance_eur": balance / 100,
                        "user_id": user_id,
                        "bank_account_id": bank_account.get("_id") if bank_account else None
                    })
        
        if negative_accounts:
            self.report["anomalies"].append({
                "type": "NEGATIVE_USER_BALANCE",
                "severity": "MEDIUM",
                "count": len(negative_accounts),
                "details": negative_accounts
            })
            print(f"  ⚠️  WARNING: Found {len(negative_accounts)} user accounts with negative balance")
        else:
            print(f"  ✅ PASSED: No user accounts with negative balance")
        
        self.report["checks"]["negative_balances"] = {
            "passed": len(negative_accounts) == 0,
            "negative_count": len(negative_accounts)
        }
    
    async def check_ledger_accounts_exist(self):
        """Verify all bank_accounts have corresponding ledger accounts"""
        print("\n[CHECK 6] Verifying ledger account existence...")
        
        missing_ledger = []
        
        # Get all bank accounts
        bank_accounts = await self.db.bank_accounts.find().to_list(None)
        
        for ba in bank_accounts:
            ledger_id = ba.get("ledger_account_id")
            
            if not ledger_id:
                missing_ledger.append({
                    "bank_account_id": ba.get("_id"),
                    "user_id": ba.get("user_id"),
                    "issue": "NO_LEDGER_ID"
                })
                continue
            
            # Check if ledger account exists
            ledger_acc = await self.db.ledger_accounts.find_one({"_id": ledger_id})
            if not ledger_acc:
                missing_ledger.append({
                    "bank_account_id": ba.get("_id"),
                    "ledger_account_id": ledger_id,
                    "user_id": ba.get("user_id"),
                    "issue": "LEDGER_ACCOUNT_NOT_FOUND"
                })
        
        if missing_ledger:
            self.report["anomalies"].append({
                "type": "MISSING_LEDGER_ACCOUNT",
                "severity": "CRITICAL",
                "count": len(missing_ledger),
                "details": missing_ledger[:10]
            })
            print(f"  ❌ FAILED: Found {len(missing_ledger)} bank accounts without valid ledger")
        else:
            print(f"  ✅ PASSED: All {len(bank_accounts)} bank accounts have valid ledger accounts")
        
        self.report["checks"]["ledger_accounts_exist"] = {
            "passed": len(missing_ledger) == 0,
            "total_bank_accounts": len(bank_accounts),
            "missing_ledger": len(missing_ledger)
        }
    
    async def generate_statistics(self):
        """Generate overall statistics"""
        print("\n[STATISTICS] Gathering database statistics...")
        
        stats = {
            "total_users": await self.db.users.count_documents({}),
            "total_bank_accounts": await self.db.bank_accounts.count_documents({}),
            "total_ledger_accounts": await self.db.ledger_accounts.count_documents({}),
            "total_ledger_transactions": await self.db.ledger_transactions.count_documents({}),
            "total_ledger_entries": await self.db.ledger_entries.count_documents({}),
            "total_transfers": await self.db.transfers.count_documents({}),
            "completed_transfers": await self.db.transfers.count_documents({"status": "COMPLETED"}),
            "pending_transfers": await self.db.transfers.count_documents({"status": "SUBMITTED"}),
            "rejected_transfers": await self.db.transfers.count_documents({"status": "REJECTED"})
        }
        
        self.report["statistics"] = stats
        
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 80)
        print("INTEGRITY CHECK SUMMARY")
        print("=" * 80)
        
        total_checks = len(self.report["checks"])
        passed_checks = sum(1 for c in self.report["checks"].values() if c.get("passed"))
        failed_checks = total_checks - passed_checks
        
        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed: {failed_checks}")
        print(f"Anomalies Detected: {len(self.report['anomalies'])}")
        
        if failed_checks == 0 and len(self.report['anomalies']) == 0:
            print("\n✅ ALL INTEGRITY CHECKS PASSED - System is healthy!")
        else:
            print("\n⚠️  ISSUES DETECTED - Review anomalies for details")
            for anomaly in self.report["anomalies"]:
                print(f"  - {anomaly['type']}: {anomaly['severity']} ({anomaly['count']} instances)")
        
        self.report["summary"] = {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": failed_checks,
            "anomaly_count": len(self.report["anomalies"]),
            "overall_status": "HEALTHY" if failed_checks == 0 and len(self.report['anomalies']) == 0 else "ISSUES_DETECTED"
        }
        
        print("=" * 80)
    
    async def close(self):
        """Close database connection"""
        self.client.close()


async def main():
    """Run integrity check and save report"""
    
    mongo_url = os.getenv("MONGO_URL")
    db_name = os.getenv("DATABASE_NAME", "ecommbx-prod")
    
    if not mongo_url:
        print("ERROR: MONGO_URL not found in environment")
        sys.exit(1)
    
    checker = LedgerIntegrityChecker(mongo_url, db_name)
    
    try:
        report = await checker.run_all_checks()
        
        # Save report
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_path = Path(__file__).parent.parent / "test_reports" / f"ledger_integrity_{timestamp}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_path}")
        
        # Exit with appropriate code
        if report["summary"]["overall_status"] != "HEALTHY":
            sys.exit(1)
        
    finally:
        await checker.close()


if __name__ == "__main__":
    asyncio.run(main())
