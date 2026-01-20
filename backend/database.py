"""MongoDB database connection and utilities."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from urllib.parse import urlparse
from config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

# Global database client
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


def get_database_name_from_url(mongo_url: str) -> Optional[str]:
    """Extract database name from MongoDB URL if present."""
    try:
        parsed = urlparse(mongo_url)
        # Path contains /database_name or /database_name?options
        if parsed.path and parsed.path != '/':
            db_name = parsed.path.strip('/').split('?')[0]
            if db_name:
                return db_name
    except Exception:
        pass
    return None


async def connect_db(max_retries: int = 5, retry_delay: float = 2.0):
    """Connect to MongoDB with retry logic for production resilience."""
    global _client, _database
    
    # Try to get database name from URL first
    db_name_from_url = get_database_name_from_url(settings.MONGO_URL)
    
    # Try to extract username from MongoDB URL (often the database name matches)
    db_name_from_username = None
    try:
        if 'mongodb+srv://' in settings.MONGO_URL or 'mongodb://' in settings.MONGO_URL:
            # Extract username from URL like mongodb+srv://username:password@...
            url_part = settings.MONGO_URL.replace('mongodb+srv://', '').replace('mongodb://', '')
            if ':' in url_part and '@' in url_part:
                db_name_from_username = url_part.split(':')[0]
                logger.info(f"Extracted potential database name from username: {db_name_from_username}")
    except Exception:
        pass
    
    # List of database names to try (in order of priority)
    # 1. From DATABASE_NAME setting (user explicitly set this)
    # 2. From URL path (most reliable for managed MongoDB)
    # 3. From username (MongoDB Atlas often uses username as db name)
    # 4. 'emergent' (Emergent platform default)
    db_names_to_try = []
    
    # First priority: what user set
    if settings.DATABASE_NAME:
        db_names_to_try.append(settings.DATABASE_NAME)
    
    # Second: from URL path
    if db_name_from_url and db_name_from_url not in db_names_to_try:
        db_names_to_try.append(db_name_from_url)
    
    # Third: from username (common in MongoDB Atlas)
    if db_name_from_username and db_name_from_username not in db_names_to_try:
        db_names_to_try.append(db_name_from_username)
    
    # Fourth: emergent default
    if 'emergent' not in db_names_to_try:
        db_names_to_try.append('emergent')
    
    logger.info(f"Will try database names in order: {db_names_to_try}")
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
    
    # Try each database name until one works
    last_error = None
    for database_name in db_names_to_try:
        logger.info(f"Trying database: {database_name}")
        _database = _client[database_name]
        
        # Try to verify connection with a simple operation
        for attempt in range(max_retries):
            try:
                # Try to list collections - this will fail if not authorized
                await _database.list_collection_names()
                logger.info(f"Successfully connected to database: {database_name}")
                
                # Try to create indexes
                try:
                    await create_indexes()
                except Exception as e:
                    logger.warning(f"Index creation failed (will retry on next startup): {e}")
                
                logger.info("MongoDB startup complete")
                return  # Success!
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if 'not authorized' in error_str or 'unauthorized' in error_str:
                    logger.warning(f"Not authorized for database '{database_name}', trying next...")
                    break  # Try next database name
                elif attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.warning(f"Failed to connect to '{database_name}' after {max_retries} attempts")
                    break  # Try next database name
    
    # If we get here, none of the database names worked
    logger.error(f"Could not connect to any database. Last error: {last_error}")
    logger.warning("App will start but database operations may fail")


async def disconnect_db():
    """Disconnect from MongoDB."""
    global _client
    
    if _client:
        _client.close()
        logger.info("MongoDB disconnected")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    global _database, _client
    
    if _database is None:
        # Try to create database connection on-demand if not initialized
        logger.warning("Database not initialized during startup, attempting on-demand connection...")
        try:
            # Get database name from URL or settings
            db_name_from_url = get_database_name_from_url(settings.MONGO_URL)
            database_name = db_name_from_url or settings.DATABASE_NAME
            
            _client = AsyncIOMotorClient(
                settings.MONGO_URL,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                retryWrites=True,
                retryReads=True,
            )
            _database = _client[database_name]
            logger.info(f"On-demand database connection created: {database_name}")
        except Exception as e:
            logger.error(f"Failed to create on-demand database connection: {e}")
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
