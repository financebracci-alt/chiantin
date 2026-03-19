"""Idempotency middleware and store.

Ensures exactly-once semantics for financial operations using idempotency keys.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class IdempotencyStore:
    """In-memory idempotency key store (POC - will use MongoDB in app).
    
    Stores: idempotency_key -> (response, timestamp)
    Keys expire after 24 hours.
    """
    
    def __init__(self, ttl_hours: int = 24):
        self.store: Dict[str, tuple[Any, datetime]] = {}
        self.ttl_hours = ttl_hours
    
    def get(self, key: str) -> Optional[Any]:
        """Get stored response for idempotency key.
        
        Returns:
            Stored response if key exists and not expired, None otherwise
        """
        if key not in self.store:
            return None
        
        response, timestamp = self.store[key]
        
        # Check expiry
        if datetime.utcnow() - timestamp > timedelta(hours=self.ttl_hours):
            del self.store[key]
            return None
        
        return response
    
    def set(self, key: str, response: Any) -> None:
        """Store response for idempotency key.
        
        Args:
            key: Idempotency key
            response: Response to store (will be returned for duplicate requests)
        """
        self.store[key] = (response, datetime.utcnow())
    
    def cleanup_expired(self) -> int:
        """Remove expired keys.
        
        Returns:
            Number of keys removed
        """
        expired_keys = []
        cutoff = datetime.utcnow() - timedelta(hours=self.ttl_hours)
        
        for key, (_, timestamp) in self.store.items():
            if timestamp < cutoff:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.store[key]
        
        return len(expired_keys)