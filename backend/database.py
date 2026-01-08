"""MongoDB database connection and utilities."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)

# Global database client
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_db():
    """Connect to MongoDB."""
    global _client, _database
    
    logger.info(f"Connecting to MongoDB: {settings.DATABASE_NAME}")
    
    _client = AsyncIOMotorClient(
        settings.MONGO_URL,
        serverSelectionTimeoutMS=5000
    )
    
    _database = _client[settings.DATABASE_NAME]
    
    # Create indexes
    await create_indexes()
    
    logger.info("MongoDB connected successfully")


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
    """Create database indexes."""
    db = get_database()
    
    # Users
    await db.users.create_index("email", unique=True)
    await db.users.create_index("phone")
    
    # Sessions
    await db.sessions.create_index("user_id")
    await db.sessions.create_index("refresh_token_hash", unique=True, sparse=True)
    await db.sessions.create_index("expires_at", expireAfterSeconds=0)  # TTL index
    
    # KYC Applications
    await db.kyc_applications.create_index("user_id")
    await db.kyc_applications.create_index("status")
    
    # Bank Accounts
    await db.bank_accounts.create_index("user_id")
    await db.bank_accounts.create_index("iban", unique=True, sparse=True)
    
    # Ledger
    await db.ledger_accounts.create_index("user_id")
    await db.ledger_accounts.create_index("account_type")
    await db.ledger_transactions.create_index("external_id", unique=True, sparse=True)
    await db.ledger_transactions.create_index("created_at")
    await db.ledger_transactions.create_index("status")
    await db.ledger_entries.create_index("transaction_id")
    await db.ledger_entries.create_index("account_id")
    await db.ledger_entries.create_index([('account_id', 1), ('created_at', 1)])
    
    # Audit Logs
    await db.audit_logs.create_index("performed_by")
    await db.audit_logs.create_index("entity_type")
    await db.audit_logs.create_index("created_at")
    
    # Support Tickets
    await db.tickets.create_index("user_id")
    await db.tickets.create_index("status")
    
    # Idempotency
    await db.idempotency_keys.create_index(
        "key", unique=True, expireAfterSeconds=86400  # 24 hours TTL
    )
    
    logger.info("Database indexes created")