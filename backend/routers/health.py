"""
Health and debug endpoints router.

These are the safest endpoints to extract as they have no business logic.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
import uuid
import os

from database import get_database
from config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": "ecommbx"}


@router.get("/db-health")
async def db_health_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Database health check endpoint - shows DB status and user count."""
    try:
        # Ping database
        await db.command("ping")
        
        # Count users
        user_count = await db.users.count_documents({})
        
        # Check if admin exists
        admin = await db.users.find_one({"role": "SUPER_ADMIN"})
        
        return {
            "status": "healthy",
            "database_name": db.name,
            "user_count": user_count,
            "admin_exists": admin is not None,
            "admin_email": admin.get("email") if admin else None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/debug/db-test")
async def debug_db_test(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Debug endpoint to test database connectivity and write permissions."""
    result = {
        "database_name": db.name,
        "mongo_url_prefix": os.environ.get('MONGO_URL', 'NOT SET')[:30] + "...",
        "ping": None,
        "write_test": None,
        "read_test": None,
        "delete_test": None,
        "error": None
    }
    
    try:
        # Test ping
        ping_result = await db.command("ping")
        result["ping"] = "OK" if ping_result.get("ok") == 1.0 else "FAILED"
        
        # Test write
        test_id = f"debug_test_{uuid.uuid4()}"
        try:
            await db.debug_tests.insert_one({"_id": test_id, "test": True, "timestamp": datetime.now(timezone.utc)})
            result["write_test"] = "OK"
        except Exception as write_err:
            result["write_test"] = f"FAILED: {str(write_err)}"
            result["error"] = str(write_err)
            return result
        
        # Test read
        try:
            doc = await db.debug_tests.find_one({"_id": test_id})
            result["read_test"] = "OK" if doc else "FAILED: Document not found"
        except Exception as read_err:
            result["read_test"] = f"FAILED: {str(read_err)}"
        
        # Test delete (cleanup)
        try:
            await db.debug_tests.delete_one({"_id": test_id})
            result["delete_test"] = "OK"
        except Exception as del_err:
            result["delete_test"] = f"FAILED: {str(del_err)}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


@router.get("/debug/try-databases")
async def try_multiple_databases():
    """Try writing to different database names to find one with permissions."""
    from motor.motor_asyncio import AsyncIOMotorClient
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    
    # List of database names to try - including variations
    db_names_to_try = [
        "mongo-perf-fix",
        "mongo-perf-fix-atlas_bankii",
        "mongo-perf-fix-atlas_banking", 
        "test",
        "emergent",
        "ecommbx",
        "atlas_bankii",
        "atlas_banking",
        "default",
        "app",
        "admin",
    ]
    
    results = {}
    
    try:
        client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        
        # Test ping first
        try:
            await client.admin.command('ping')
            results["_connection"] = "OK"
        except Exception as e:
            results["_connection"] = f"FAILED: {str(e)[:100]}"
            return {"mongo_url_prefix": mongo_url[:50], "results": results}
        
        for db_name in db_names_to_try:
            try:
                db = client[db_name]
                test_id = f"test_{uuid.uuid4()}"
                await db.permission_test.insert_one({"_id": test_id, "test": True})
                await db.permission_test.delete_one({"_id": test_id})
                results[db_name] = "✅ WRITE OK"
            except Exception as e:
                error_msg = str(e)
                if "not authorized" in error_msg.lower():
                    results[db_name] = "❌ No write permission"
                else:
                    results[db_name] = f"❌ {error_msg[:60]}"
        
        client.close()
    except Exception as e:
        results["_error"] = str(e)[:200]
    
    return {"mongo_url_prefix": mongo_url[:50] + "...", "results": results}


@router.get("/debug/test-transfer/{user_email}")
async def debug_test_transfer(
    user_email: str,
    to_iban: str = "DE89370400440532013000",
    amount: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Debug endpoint to test transfer logic."""
    result = {"steps": []}
    
    # Step 1: Find user
    user = await db.users.find_one({"email": user_email})
    if not user:
        return {"error": "User not found", "steps": result["steps"]}
    result["steps"].append(f"1. User found: {user['_id']} (type: {type(user['_id']).__name__})")
    
    user_id = user["_id"]
    
    # Step 2: Find bank account
    acc = await db.bank_accounts.find_one({"user_id": user_id})
    if not acc:
        # Try as string
        acc = await db.bank_accounts.find_one({"user_id": str(user_id)})
    if not acc:
        return {"error": "Bank account not found", "steps": result["steps"]}
    result["steps"].append(f"2. Bank account found: {acc['iban']}, ledger: {acc['ledger_account_id']}")
    
    # Step 3: Check balance
    ledger_id = acc["ledger_account_id"]
    entries = await db.ledger_entries.find({"account_id": ledger_id}).to_list(1000)
    total_credit = sum(e["amount"] for e in entries if e.get("direction") == "CREDIT")
    total_debit = sum(e["amount"] for e in entries if e.get("direction") == "DEBIT")
    balance = total_credit - total_debit
    result["steps"].append(f"3. Balance: {balance} cents (€{balance/100:.2f})")
    
    if balance < amount:
        return {"error": f"Insufficient funds: {balance} < {amount}", "steps": result["steps"]}
    result["steps"].append(f"4. Balance sufficient for {amount} cents")
    
    # Step 4: Check recipient IBAN
    normalized_iban = to_iban.replace(" ", "").upper()
    to_acc = await db.bank_accounts.find_one({"iban": normalized_iban})
    if to_acc:
        result["steps"].append("5. Recipient IBAN found - INTERNAL transfer")
    else:
        result["steps"].append("5. Recipient IBAN not found - EXTERNAL transfer")
    
    result["ready"] = True
    result["transfer_type"] = "INTERNAL" if to_acc else "EXTERNAL"
    result["balance"] = balance
    result["amount"] = amount
    
    return result
