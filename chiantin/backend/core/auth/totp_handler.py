"""TOTP (Time-based One-Time Password) handler for MFA.

Uses standard TOTP (RFC 6238) compatible with Google Authenticator, Authy, etc.
"""

import pyotp
import secrets
from typing import Tuple


class TOTPHandler:
    """Handle TOTP generation and verification for MFA."""
    
    def generate_secret(self) -> str:
        """Generate a new random TOTP secret (base32 encoded).
        
        Returns:
            Base32-encoded secret string
        """
        return pyotp.random_base32()
    
    def get_provisioning_uri(
        self,
        secret: str,
        account_email: str,
        issuer_name: str = "Chiantin"
    ) -> str:
        """Get provisioning URI for QR code generation.
        
        Args:
            secret: Base32 TOTP secret
            account_email: User's email
            issuer_name: App name shown in authenticator
        
        Returns:
            otpauth:// URI for QR code
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=account_email,
            issuer_name=issuer_name
        )
    
    def verify_token(
        self,
        secret: str,
        token: str,
        valid_window: int = 1
    ) -> bool:
        """Verify a TOTP token.
        
        Args:
            secret: Base32 TOTP secret
            token: 6-digit code from authenticator app
            valid_window: Accept tokens from +/- N time windows (default 1 = 30 sec drift)
        
        Returns:
            True if valid, False otherwise
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=valid_window)
    
    def get_current_token(self, secret: str) -> str:
        """Get current TOTP token (for testing/debugging only).
        
        Args:
            secret: Base32 TOTP secret
        
        Returns:
            Current 6-digit token
        """
        totp = pyotp.TOTP(secret)
        return totp.now()