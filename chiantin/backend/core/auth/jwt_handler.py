"""JWT token handling (access + refresh token rotation).

Implements:
- Short-lived access tokens (5-15 minutes)
- Refresh token rotation (invalidate old, issue new)
- Token metadata for session tracking
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import secrets


class JWTHandler:
    """Handle JWT access tokens and refresh token rotation."""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
    
    def create_access_token(
        self,
        subject: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a short-lived JWT access token.
        
        Args:
            subject: User ID (sub claim)
            additional_claims: Optional extra claims (roles, permissions, etc.)
        
        Returns:
            Encoded JWT string
        """
        now = datetime.utcnow()
        exp = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": subject,
            "iat": now,
            "exp": exp,
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode access token.
        
        Returns:
            Decoded payload
        
        Raises:
            jwt.ExpiredSignatureError: Token expired
            jwt.InvalidTokenError: Invalid token
        """
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm]
        )
        
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Not an access token")
        
        return payload
    
    def generate_refresh_token(self) -> str:
        """Generate a cryptographically secure random refresh token.
        
        Returns 32-byte (64 hex chars) random string.
        This is NOT a JWT - it's an opaque token stored in DB.
        """
        return secrets.token_urlsafe(32)
    
    def get_refresh_token_expiry(self) -> datetime:
        """Get expiry datetime for new refresh token."""
        return datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)