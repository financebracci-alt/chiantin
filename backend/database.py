"""MongoDB database connection and utilities."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

# Global database client
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_db(max_retries: int = 5, retry_delay: float = 2.0):
    """Connect to MongoDB with retry logic for production resilience."""
    global _client, _database
    
    logger.info(f"Connecting to MongoDB: {settings.DATABASE_NAME}")
    logger.info(f"MongoDB URL: {settings.MONGO_URL[:50]}...")
    
    # Create client with production-ready settings
    _client = AsyncIOMotorClient(
        settings.MONGO_URL,
        serverSelectionTimeoutMS=10000,  # 10 second timeout
        connectTimeoutMS=10000,
        socketTimeoutMS=30000,
        retryWrites=True,
        retryReads=True,
    )
    
    _database = _client[settings.DATABASE_NAME]
    
    # Try to verify connection with retries
    for attempt in range(max_retries):
        try:
            # Ping the database to verify connection
            await _client.admin.command('ping')
            logger.info("MongoDB connection verified successfully")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"MongoDB connection failed after {max_retries} attempts: {e}")
                # Don't crash - let the app start and handle DB errors gracefully
                logger.warning("App will start but database operations may fail")
    
    # Try to create indexes (non-blocking, with error handling)
    try:
        await create_indexes()
    except Exception as e:
        logger.warning(f"Index creation failed (will retry on next startup): {e}")
    
    logger.info("MongoDB startup complete")


async def disconnect_db():
    """Disconnect from MongoDB."""
    global _client
    
    if _client:
        _client.close()
        logger.info("MongoDB disconnected")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    if _database is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _database


async def create_indexes():
    """Create database indexes with error handling."""
    db = get_database()
    
    indexes = [
        # Users
        ("users", "email", {"unique": True}),
        ("users", "phone", {}),
        
        # Sessions
        ("sessions", "user_id", {}),
        ("sessions", "refresh_token_hash", {"unique": True, "sparse": True}),
        ("sessions", "expires_at", {"expireAfterSeconds": 0}),
        
        # KYC Applications
        ("kyc_applications", "user_id", {}),
        ("kyc_applications", "status", {}),
        
        # Bank Accounts
        ("bank_accounts", "user_id", {}),
        ("bank_accounts", "iban", {"unique": True, "sparse": True}),
        
        # Ledger
        ("ledger_accounts", "user_id", {}),
        ("ledger_accounts", "account_type", {}),
        ("ledger_transactions", "external_id", {"unique": True, "sparse": True}),
        ("ledger_transactions", "created_at", {}),
        ("ledger_transactions", "status", {}),
        ("ledger_entries", "transaction_id", {}),
        ("ledger_entries", "account_id", {}),
        
        # Audit Logs
        ("audit_logs", "performed_by", {}),
        ("audit_logs", "entity_type", {}),
        ("audit_logs", "created_at", {}),
        
        # Support Tickets
        ("tickets", "user_id", {}),
        ("tickets", "status", {}),
        
        # Idempotency
        ("idempotency_keys", "key", {"unique": True, "expireAfterSeconds": 86400}),
    ]
    
    # Also create compound indexes
    compound_indexes = [
        ("ledger_entries", [('account_id', 1), ('created_at', 1)], {}),
    ]
    
    created = 0
    failed = 0
    
    for collection, field, options in indexes:
        try:
            await db[collection].create_index(field, **options)
            created += 1
        except Exception as e:
            # Index might already exist or there could be a conflict - log but continue
            logger.debug(f"Index {collection}.{field}: {e}")
            failed += 1
    
    for collection, fields, options in compound_indexes:
        try:
            await db[collection].create_index(fields, **options)
            created += 1
        except Exception as e:
            logger.debug(f"Compound index {collection}.{fields}: {e}")
            failed += 1
    
    logger.info(f"Database indexes: {created} created/verified, {failed} skipped")
