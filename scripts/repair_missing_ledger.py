"""
Repair Missing Ledger Account

This script safely creates missing ledger accounts for bank accounts.
It will NOT modify any existing ledger entries or transactions.

Run with: python scripts/repair_missing_ledger.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")


async def repair_missing_ledger_accounts():
    """Create missing ledger accounts for bank accounts"""
    
    mongo_url = os.getenv("MONGO_URL")
    db_name = os.getenv("DATABASE_NAME", "ecommbx-prod")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("=" * 80)
    print("LEDGER ACCOUNT REPAIR SCRIPT")
    print("=" * 80)
    
    # Find all bank accounts with missing ledger accounts
    bank_accounts = await db.bank_accounts.find().to_list(None)
    
    missing_count = 0
    repaired_count = 0
    
    for ba in bank_accounts:
        ledger_id = ba.get("ledger_account_id")
        
        if not ledger_id:
            print(f"\n⚠️  Bank account {ba.get('_id')} has no ledger_account_id - skipping (needs manual review)")
            missing_count += 1
            continue
        
        # Check if ledger account exists
        ledger_acc = await db.ledger_accounts.find_one({"_id": ledger_id})
        
        if not ledger_acc:
            print(f"\n🔧 Creating missing ledger account: {ledger_id}")
            print(f"   Bank account: {ba.get('_id')}")
            print(f"   User ID: {ba.get('user_id')}")
            
            # Create the ledger account
            new_ledger = {
                "_id": ledger_id,
                "account_type": "WALLET",
                "user_id": str(ba.get("user_id")),
                "currency": ba.get("currency", "EUR"),
                "created_at": ba.get("opened_at", datetime.now(timezone.utc))
            }
            
            try:
                await db.ledger_accounts.insert_one(new_ledger)
                print(f"   ✅ Successfully created ledger account")
                repaired_count += 1
            except Exception as e:
                print(f"   ❌ Error creating ledger account: {e}")
                missing_count += 1
    
    print("\n" + "=" * 80)
    print("REPAIR COMPLETE")
    print("=" * 80)
    print(f"Total bank accounts checked: {len(bank_accounts)}")
    print(f"Ledger accounts created: {repaired_count}")
    print(f"Issues remaining: {missing_count}")
    
    client.close()
    
    return repaired_count > 0


if __name__ == "__main__":
    result = asyncio.run(repair_missing_ledger_accounts())
    if result:
        print("\n✅ Repair completed - run ledger_integrity_check.py to verify")
