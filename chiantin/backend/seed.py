"""Seed script for Project Atlas - Create initial data."""

import asyncio
import sys
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from core.auth import hash_password
from datetime import datetime, date

async def seed_database():
    """Seed initial data."""
    print(f"Connecting to MongoDB: {settings.DATABASE_NAME}")
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.DATABASE_NAME]
    
    # Create Super Admin
    print("Creating Super Admin...")
    admin_email = settings.SEED_SUPERADMIN_EMAIL
    existing_admin = await db.users.find_one({"email": admin_email})
    
    if not existing_admin:
        admin = {
            "_id": "admin_super_001",
            "email": admin_email,
            "password_hash": hash_password(settings.SEED_SUPERADMIN_PASSWORD),
            "first_name": "Super",
            "last_name": "Admin",
            "role": "SUPER_ADMIN",
            "status": "ACTIVE",
            "email_verified": True,
            "mfa_enabled": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.users.insert_one(admin)
        print(f"✓ Super Admin created: {admin_email}")
    else:
        print(f"✓ Super Admin already exists: {admin_email}")
    
    # Create demo customer
    print("Creating demo customer...")
    demo_email = "customer@demo.com"
    existing_customer = await db.users.find_one({"email": demo_email})
    
    if not existing_customer:
        customer = {
            "_id": "customer_001",
            "email": demo_email,
            "password_hash": hash_password("Demo@123456"),
            "first_name": "John",
            "last_name": "Doe",
            "role": "CUSTOMER",
            "status": "ACTIVE",
            "email_verified": True,
            "mfa_enabled": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.users.insert_one(customer)
        print(f"✓ Demo customer created: {demo_email} / Demo@123456")
        
        # Create KYC application (approved)
        kyc = {
            "_id": "kyc_001",
            "user_id": "customer_001",
            "full_name": "John Doe",
            "date_of_birth": date(1990, 1, 1),
            "nationality": "DE",
            "street_address": "Berliner Strasse 123",
            "city": "Berlin",
            "postal_code": "10115",
            "country": "Germany",
            "tax_residency": "DE",
            "documents": [],
            "status": "APPROVED",
            "submitted_at": datetime.utcnow(),
            "reviewed_at": datetime.utcnow(),
            "reviewed_by": "admin_super_001",
            "review_notes": "Demo user - auto-approved",
            "terms_accepted": True,
            "terms_accepted_at": datetime.utcnow(),
            "privacy_accepted": True,
            "privacy_accepted_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.kyc_applications.insert_one(kyc)
        print("✓ Demo KYC application created (approved)")
        
        # Create bank account
        ledger_account = {
            "_id": "ledger_acc_customer_001",
            "account_type": "WALLET",
            "user_id": "customer_001",
            "currency": "EUR",
            "status": "ACTIVE",
            "created_at": datetime.utcnow()
        }
        await db.ledger_accounts.insert_one(ledger_account)
        
        bank_account = {
            "_id": "bank_acc_001",
            "user_id": "customer_001",
            "account_number": "ACC000000001",
            "iban": "DE99123456789012345678",
            "bic": "ATLASDE99XXX",
            "currency": "EUR",
            "status": "ACTIVE",
            "ledger_account_id": "ledger_acc_customer_001",
            "opened_at": datetime.utcnow()
        }
        await db.bank_accounts.insert_one(bank_account)
        print("✓ Demo bank account created with IBAN")
        
        # Add some balance
        txn_id = "txn_seed_001"
        sandbox_funding = {
            "_id": "ledger_acc_sandbox",
            "account_type": "SANDBOX_FUNDING",
            "currency": "EUR",
            "status": "ACTIVE",
            "created_at": datetime.utcnow()
        }
        await db.ledger_accounts.update_one(
            {"_id": "ledger_acc_sandbox"},
            {"$setOnInsert": sandbox_funding},
            upsert=True
        )
        
        txn = {
            "_id": txn_id,
            "external_id": "seed_topup_001",
            "transaction_type": "TOP_UP",
            "status": "POSTED",
            "value_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "reason": "Initial seed balance",
            "performed_by": "system",
            "metadata": {}
        }
        await db.ledger_transactions.insert_one(txn)
        
        # Entries
        entries = [
            {
                "_id": "entry_001",
                "transaction_id": txn_id,
                "account_id": "ledger_acc_customer_001",
                "amount": 100000,  # €1000
                "direction": "CREDIT",
                "currency": "EUR",
                "created_at": datetime.utcnow()
            },
            {
                "_id": "entry_002",
                "transaction_id": txn_id,
                "account_id": "ledger_acc_sandbox",
                "amount": 100000,
                "direction": "DEBIT",
                "currency": "EUR",
                "created_at": datetime.utcnow()
            }
        ]
        await db.ledger_entries.insert_many(entries)
        print("✓ Initial balance added: €1000.00")
    else:
        print(f"✓ Demo customer already exists: {demo_email}")
    
    # Create internal ledger accounts
    print("Creating internal ledger accounts...")
    await db.ledger_accounts.update_one(
        {"_id": "ledger_acc_fees"},
        {"$setOnInsert": {
            "_id": "ledger_acc_fees",
            "account_type": "FEES",
            "currency": "EUR",
            "status": "ACTIVE",
            "created_at": datetime.utcnow()
        }},
        upsert=True
    )
    print("✓ Internal ledger accounts ready")
    
    print("\n" + "="*60)
    print("✓✓✓ Database seeded successfully!")
    print("="*60)
    print(f"\nAdmin Login:")
    print(f"  Email: {settings.SEED_SUPERADMIN_EMAIL}")
    print(f"  Password: {settings.SEED_SUPERADMIN_PASSWORD}")
    print(f"\nDemo Customer Login:")
    print(f"  Email: customer@demo.com")
    print(f"  Password: Demo@123456")
    print("="*60)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
