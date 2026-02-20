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


async def connect_db(max_retries: int = 3, retry_delay: float = 2.0):
    """Connect to MongoDB using DATABASE_NAME setting directly."""
    global _client, _database
    
    # Use DATABASE_NAME from settings - this is what the user configures
    database_name = settings.DATABASE_NAME
    
    logger.info(f"Connecting to MongoDB...")
    logger.info(f"DATABASE_NAME setting: {database_name}")
    logger.info(f"MongoDB URL prefix: {settings.MONGO_URL[:50]}...")
    
    # Create client with production-ready settings
    _client = AsyncIOMotorClient(
        settings.MONGO_URL,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=30000,
        retryWrites=True,
        retryReads=True,
    )
    
    # Connect to the specified database
    _database = _client[database_name]
    logger.info(f"Using database: {database_name}")
    
    # Verify connection works
    for attempt in range(max_retries):
        try:
            # Try a simple ping command first
            await _client.admin.command('ping')
            logger.info("MongoDB ping successful")
            
            # Try to access the database
            await _database.list_collection_names()
            logger.info(f"Successfully connected to database: {database_name}")
            
            # Try to create indexes
            try:
                await create_indexes()
            except Exception as e:
                logger.warning(f"Index creation warning (non-fatal): {e}")
            
            logger.info("MongoDB startup complete")
            return  # Success!
            
        except Exception as e:
            error_str = str(e).lower()
            if 'not authorized' in error_str or 'unauthorized' in error_str:
                logger.error(f"DATABASE AUTHORIZATION ERROR: Not authorized for database '{database_name}'")
                logger.error(f"Please check your DATABASE_NAME secret matches the database your MongoDB user has access to")
                logger.error(f"Full error: {e}")
                # Don't retry auth errors - they won't fix themselves
                break
            elif attempt < max_retries - 1:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect after {max_retries} attempts: {e}")
    
    logger.warning("App started but database connection has issues - operations may fail")


async def disconnect_db():
    """Disconnect from MongoDB."""
    global _client
    
    if _client:
        _client.close()
        logger.info("MongoDB disconnected")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance - always uses DATABASE_NAME from settings."""
    global _database, _client
    
    # If database is set, verify it's using the correct name
    if _database is not None:
        # Check if the database name matches current settings
        if _database.name != settings.DATABASE_NAME:
            logger.warning(f"Database name mismatch! Connected: {_database.name}, Settings: {settings.DATABASE_NAME}")
            logger.warning("Reconnecting to correct database...")
            _database = _client[settings.DATABASE_NAME] if _client else None
    
    if _database is None:
        # Create connection on-demand
        logger.warning("Database not initialized, creating on-demand connection...")
        try:
            _client = AsyncIOMotorClient(
                settings.MONGO_URL,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                retryWrites=True,
                retryReads=True,
            )
            _database = _client[settings.DATABASE_NAME]
            logger.info(f"On-demand database connection created: {settings.DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise RuntimeError(f"Database not available: {e}")
    
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
        # IBAN index removed - duplicate IBANs are now allowed
        # ("bank_accounts", "iban", {"unique": True, "sparse": True}),
        
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
        
        # Transfers (PERFORMANCE: for admin panel queries)
        ("transfers", "status", {}),
        ("transfers", "created_at", {}),
        ("transfers", "user_id", {}),
        
        # Card Requests (PERFORMANCE: for admin panel queries)
        ("card_requests", "status", {}),
        ("card_requests", "user_id", {}),
        ("card_requests", "created_at", {}),
    ]
    
    # Also create compound indexes
    compound_indexes = [
        ("ledger_entries", [('account_id', 1), ('created_at', 1)], {}),
        # PERFORMANCE: Compound index for transfers admin queries
        ("transfers", [('status', 1), ('created_at', -1)], {}),
        # PERFORMANCE: Compound index for card requests admin queries
        ("card_requests", [('status', 1), ('created_at', -1)], {}),
    ]
    
    created = 0
    failed = 0
    
    for collection, field, options in indexes:
        try:
            await db[collection].create_index(field, **options)
            created += 1
        except Exception as e:
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
