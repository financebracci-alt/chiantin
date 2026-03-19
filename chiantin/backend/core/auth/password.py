"""Password hashing using Argon2 (OWASP recommended)."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Use default secure parameters
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        hashed: Previously hashed password
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        ph.verify(hashed, password)
        
        # Check if rehash is needed (parameters changed)
        if ph.check_needs_rehash(hashed):
            # In real app, update DB with new hash
            pass
        
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False