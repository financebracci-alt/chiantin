"""Comprehensive POC test script for Project Atlas core systems.

Tests:
1. Double-entry ledger (invariants, append-only, derived balances)
2. Idempotency (duplicate prevention)
3. Reversals (new entries, balance restoration)
4. S3 storage adapter (upload/download)
5. JWT tokens (access token issue/verify, refresh rotation concept)
6. TOTP (generation/verification)

All tests must pass before proceeding to full app development.
"""

import sys
import os
from io import BytesIO
from datetime import datetime

# Add backend to path
sys.path.insert(0, '/app/backend')

from core.ledger import (
    LedgerEngine,
    AccountType,
    EntryDirection,
    InvariantViolation
)
from core.auth import JWTHandler, TOTPHandler, hash_password, verify_password
from core.idempotency import IdempotencyStore
from providers import LocalS3Storage


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def record_pass(self, test_name: str):
        self.passed += 1
        print(f"✓ {test_name}")
    
    def record_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"✗ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for test_name, error in self.errors:
                print(f"  - {test_name}: {error}")
        print(f"{'='*60}")
        return self.failed == 0


def test_ledger_engine(results: TestResults):
    """Test double-entry ledger core functionality."""
    print("\n=== Testing Ledger Engine ===")
    
    engine = LedgerEngine()
    
    # Test 1: Create accounts
    try:
        user_account = engine.create_account(AccountType.WALLET, user_id="user123")
        internal_account = engine.create_account(AccountType.SANDBOX_FUNDING)
        results.record_pass("Ledger: Create accounts")
    except Exception as e:
        results.record_fail("Ledger: Create accounts", str(e))
        return  # Can't continue without accounts
    
    # Test 2: Initial balance should be zero (derived)
    try:
        balance = engine.get_balance(user_account.id)
        assert balance == 0, f"Expected 0, got {balance}"
        results.record_pass("Ledger: Initial balance is zero")
    except Exception as e:
        results.record_fail("Ledger: Initial balance is zero", str(e))
    
    # Test 3: Top up (credit user, debit funding)
    try:
        txn1 = engine.top_up(
            user_account_id=user_account.id,
            amount=10000,  # €100.00 in cents
            external_id="topup_001",
            reason="Test top-up",
            performed_by="admin"
        )
        balance = engine.get_balance(user_account.id)
        assert balance == 10000, f"Expected 10000, got {balance}"
        results.record_pass("Ledger: Top-up increases balance")
    except Exception as e:
        results.record_fail("Ledger: Top-up increases balance", str(e))
    
    # Test 4: Verify double-entry invariant (debits = credits)
    try:
        # Get all entries for this transaction
        entries = [e for e in engine.entries if e.transaction_id == txn1.id]
        total_debits = sum(e.amount for e in entries if e.direction == EntryDirection.DEBIT)
        total_credits = sum(e.amount for e in entries if e.direction == EntryDirection.CREDIT)
        assert total_debits == total_credits, f"Unbalanced: debits={total_debits}, credits={total_credits}"
        results.record_pass("Ledger: Double-entry invariant holds")
    except Exception as e:
        results.record_fail("Ledger: Double-entry invariant holds", str(e))
    
    # Test 5: Idempotency - same external_id returns same transaction
    try:
        txn2 = engine.top_up(
            user_account_id=user_account.id,
            amount=10000,
            external_id="topup_001",  # Same key
            reason="Duplicate request"
        )
        assert txn2.id == txn1.id, "Should return same transaction ID"
        balance = engine.get_balance(user_account.id)
        assert balance == 10000, f"Balance should still be 10000, got {balance}"
        results.record_pass("Ledger: Idempotency prevents duplicates")
    except Exception as e:
        results.record_fail("Ledger: Idempotency prevents duplicates", str(e))
    
    # Test 6: Withdraw (debit user, credit funding)
    try:
        txn3 = engine.withdraw(
            user_account_id=user_account.id,
            amount=3000,  # €30.00
            external_id="withdraw_001",
            reason="Test withdrawal"
        )
        balance = engine.get_balance(user_account.id)
        assert balance == 7000, f"Expected 7000, got {balance}"
        results.record_pass("Ledger: Withdraw decreases balance")
    except Exception as e:
        results.record_fail("Ledger: Withdraw decreases balance", str(e))
    
    # Test 7: Fee charge
    try:
        txn4 = engine.charge_fee(
            user_account_id=user_account.id,
            amount=500,  # €5.00 fee
            external_id="fee_001",
            reason="Monthly maintenance fee"
        )
        balance = engine.get_balance(user_account.id)
        assert balance == 6500, f"Expected 6500, got {balance}"
        results.record_pass("Ledger: Fee charge works")
    except Exception as e:
        results.record_fail("Ledger: Fee charge works", str(e))
    
    # Test 8: Internal transfer
    try:
        user2_account = engine.create_account(AccountType.WALLET, user_id="user456")
        
        txn5 = engine.internal_transfer(
            from_account_id=user_account.id,
            to_account_id=user2_account.id,
            amount=2000,  # €20.00
            external_id="transfer_001",
            reason="P2P transfer"
        )
        
        balance1 = engine.get_balance(user_account.id)
        balance2 = engine.get_balance(user2_account.id)
        
        assert balance1 == 4500, f"Sender balance should be 4500, got {balance1}"
        assert balance2 == 2000, f"Recipient balance should be 2000, got {balance2}"
        results.record_pass("Ledger: Internal transfer works")
    except Exception as e:
        results.record_fail("Ledger: Internal transfer works", str(e))
    
    # Test 9: Reversal creates new entries and restores balance
    try:
        # Reverse the withdrawal (txn3: -3000)
        original_balance = engine.get_balance(user_account.id)
        
        reversal_txn = engine.reverse_transaction(
            original_txn_id=txn3.id,
            external_id="reversal_001",
            reason="Cancelling withdrawal",
            performed_by="admin"
        )
        
        new_balance = engine.get_balance(user_account.id)
        expected_balance = original_balance + 3000
        
        assert new_balance == expected_balance, f"Expected {expected_balance}, got {new_balance}"
        assert reversal_txn.reverses_txn_id == txn3.id, "Reversal should link to original"
        assert txn3.reversed_by_txn_id == reversal_txn.id, "Original should link to reversal"
        
        results.record_pass("Ledger: Reversal restores balance via new entries")
    except Exception as e:
        results.record_fail("Ledger: Reversal restores balance via new entries", str(e))
    
    # Test 10: Verify append-only (count entries never decreases)
    try:
        entry_count_before = len(engine.entries)
        
        # Do another operation
        engine.top_up(user_account.id, 1000, external_id="topup_002")
        
        entry_count_after = len(engine.entries)
        assert entry_count_after > entry_count_before, "Entries should only be appended"
        results.record_pass("Ledger: Append-only behavior verified")
    except Exception as e:
        results.record_fail("Ledger: Append-only behavior verified", str(e))
    
    # Test 11: Unbalanced transaction should fail
    try:
        try:
            # Manually create unbalanced transaction (should fail)
            engine.post_transaction(
                transaction_type="INVALID",
                entries=[
                    (user_account.id, 1000, EntryDirection.DEBIT),
                    # Missing credit entry - unbalanced!
                ],
                reason="Test invariant violation"
            )
            results.record_fail("Ledger: Reject unbalanced transactions", "Should have raised InvariantViolation")
        except InvariantViolation:
            results.record_pass("Ledger: Reject unbalanced transactions")
    except Exception as e:
        results.record_fail("Ledger: Reject unbalanced transactions", str(e))
    
    # Test 12: Calculate total system balance (should be conserved)
    try:
        total_balance = 0
        for account_id in engine.accounts.keys():
            total_balance += engine.get_balance(account_id)
        
        # In a closed system, total balance across all accounts should be zero
        # (what's credited must be debited somewhere)
        assert total_balance == 0, f"System balance should be 0, got {total_balance}"
        results.record_pass("Ledger: Conservation of value (total balance = 0)")
    except Exception as e:
        results.record_fail("Ledger: Conservation of value (total balance = 0)", str(e))


def test_idempotency_store(results: TestResults):
    """Test idempotency store."""
    print("\n=== Testing Idempotency Store ===")
    
    store = IdempotencyStore(ttl_hours=24)
    
    # Test 1: Store and retrieve
    try:
        key = "test_key_001"
        response = {"transaction_id": "txn_123", "status": "posted"}
        
        store.set(key, response)
        retrieved = store.get(key)
        
        assert retrieved == response, f"Expected {response}, got {retrieved}"
        results.record_pass("Idempotency: Store and retrieve")
    except Exception as e:
        results.record_fail("Idempotency: Store and retrieve", str(e))
    
    # Test 2: Non-existent key returns None
    try:
        result = store.get("non_existent_key")
        assert result is None, f"Expected None, got {result}"
        results.record_pass("Idempotency: Non-existent key returns None")
    except Exception as e:
        results.record_fail("Idempotency: Non-existent key returns None", str(e))


def test_storage_adapter(results: TestResults):
    """Test S3-compatible storage adapter."""
    print("\n=== Testing Storage Adapter (LocalS3) ===")
    
    storage = LocalS3Storage(base_path="/tmp/test_atlas_storage")
    
    # Test 1: Upload file
    try:
        test_content = b"This is a test document for KYC"
        fileobj = BytesIO(test_content)
        
        metadata = storage.upload_fileobj(
            fileobj,
            key="kyc/user123/passport.pdf",
            content_type="application/pdf"
        )
        
        assert metadata.key == "kyc/user123/passport.pdf"
        assert metadata.size == len(test_content)
        results.record_pass("Storage: Upload file")
    except Exception as e:
        results.record_fail("Storage: Upload file", str(e))
    
    # Test 2: Check file exists
    try:
        exists = storage.exists("kyc/user123/passport.pdf")
        assert exists is True, "File should exist"
        results.record_pass("Storage: File exists check")
    except Exception as e:
        results.record_fail("Storage: File exists check", str(e))
    
    # Test 3: Download file
    try:
        download_buffer = BytesIO()
        storage.download_fileobj("kyc/user123/passport.pdf", download_buffer)
        
        downloaded_content = download_buffer.getvalue()
        assert downloaded_content == test_content, "Downloaded content should match uploaded"
        results.record_pass("Storage: Download file")
    except Exception as e:
        results.record_fail("Storage: Download file", str(e))
    
    # Test 4: Get presigned URL
    try:
        url = storage.get_presigned_url("kyc/user123/passport.pdf", expires_in=3600)
        assert url is not None and len(url) > 0
        results.record_pass("Storage: Generate presigned URL")
    except Exception as e:
        results.record_fail("Storage: Generate presigned URL", str(e))
    
    # Test 5: Delete file
    try:
        storage.delete("kyc/user123/passport.pdf")
        exists = storage.exists("kyc/user123/passport.pdf")
        assert exists is False, "File should not exist after deletion"
        results.record_pass("Storage: Delete file")
    except Exception as e:
        results.record_fail("Storage: Delete file", str(e))


def test_jwt_handler(results: TestResults):
    """Test JWT token handling."""
    print("\n=== Testing JWT Handler ===")
    
    jwt_handler = JWTHandler(
        secret_key="test_secret_key_12345",
        access_token_expire_minutes=15
    )
    
    # Test 1: Create access token
    try:
        token = jwt_handler.create_access_token(
            subject="user_123",
            additional_claims={"role": "customer"}
        )
        assert token is not None and len(token) > 0
        results.record_pass("JWT: Create access token")
    except Exception as e:
        results.record_fail("JWT: Create access token", str(e))
        return
    
    # Test 2: Verify access token
    try:
        payload = jwt_handler.verify_access_token(token)
        assert payload["sub"] == "user_123", f"Expected user_123, got {payload['sub']}"
        assert payload["role"] == "customer"
        assert payload["type"] == "access"
        results.record_pass("JWT: Verify access token")
    except Exception as e:
        results.record_fail("JWT: Verify access token", str(e))
    
    # Test 3: Generate refresh token
    try:
        refresh_token = jwt_handler.generate_refresh_token()
        assert refresh_token is not None and len(refresh_token) > 0
        # Should be opaque (not JWT)
        assert not refresh_token.count('.') == 2  # JWT has 2 dots
        results.record_pass("JWT: Generate refresh token (opaque)")
    except Exception as e:
        results.record_fail("JWT: Generate refresh token (opaque)", str(e))
    
    # Test 4: Refresh token expiry calculation
    try:
        expiry = jwt_handler.get_refresh_token_expiry()
        assert expiry > datetime.utcnow(), "Expiry should be in future"
        results.record_pass("JWT: Refresh token expiry calculation")
    except Exception as e:
        results.record_fail("JWT: Refresh token expiry calculation", str(e))


def test_totp_handler(results: TestResults):
    """Test TOTP (MFA) handling."""
    print("\n=== Testing TOTP Handler ===")
    
    totp_handler = TOTPHandler()
    
    # Test 1: Generate secret
    try:
        secret = totp_handler.generate_secret()
        assert secret is not None and len(secret) > 0
        results.record_pass("TOTP: Generate secret")
    except Exception as e:
        results.record_fail("TOTP: Generate secret", str(e))
        return
    
    # Test 2: Get provisioning URI
    try:
        uri = totp_handler.get_provisioning_uri(
            secret=secret,
            account_email="test@example.com",
            issuer_name="Project Atlas"
        )
        assert uri.startswith("otpauth://totp/"), f"Invalid URI: {uri}"
        assert "Project Atlas" in uri
        results.record_pass("TOTP: Generate provisioning URI")
    except Exception as e:
        results.record_fail("TOTP: Generate provisioning URI", str(e))
    
    # Test 3: Get current token and verify it
    try:
        current_token = totp_handler.get_current_token(secret)
        assert len(current_token) == 6, f"Token should be 6 digits, got {len(current_token)}"
        
        # Verify the token we just generated
        is_valid = totp_handler.verify_token(secret, current_token)
        assert is_valid is True, "Current token should be valid"
        results.record_pass("TOTP: Generate and verify token")
    except Exception as e:
        results.record_fail("TOTP: Generate and verify token", str(e))
    
    # Test 4: Invalid token should fail
    try:
        is_valid = totp_handler.verify_token(secret, "000000")
        assert is_valid is False, "Invalid token should not verify"
        results.record_pass("TOTP: Reject invalid token")
    except Exception as e:
        results.record_fail("TOTP: Reject invalid token", str(e))


def test_password_hashing(results: TestResults):
    """Test password hashing."""
    print("\n=== Testing Password Hashing ===")
    
    # Test 1: Hash password
    try:
        password = "SecureP@ssw0rd123"
        hashed = hash_password(password)
        assert hashed is not None and len(hashed) > 0
        assert hashed != password, "Hash should differ from password"
        results.record_pass("Password: Hash password")
    except Exception as e:
        results.record_fail("Password: Hash password", str(e))
        return
    
    # Test 2: Verify correct password
    try:
        is_valid = verify_password(password, hashed)
        assert is_valid is True, "Correct password should verify"
        results.record_pass("Password: Verify correct password")
    except Exception as e:
        results.record_fail("Password: Verify correct password", str(e))
    
    # Test 3: Reject incorrect password
    try:
        is_valid = verify_password("WrongPassword", hashed)
        assert is_valid is False, "Wrong password should not verify"
        results.record_pass("Password: Reject incorrect password")
    except Exception as e:
        results.record_fail("Password: Reject incorrect password", str(e))


def main():
    """Run all POC tests."""
    print("=" * 60)
    print("Project Atlas - Core POC Test Suite")
    print("=" * 60)
    
    results = TestResults()
    
    # Run all test suites
    test_ledger_engine(results)
    test_idempotency_store(results)
    test_storage_adapter(results)
    test_jwt_handler(results)
    test_totp_handler(results)
    test_password_hashing(results)
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n✓✓✓ All POC tests passed! Core is proven. Ready for app development. ✓✓✓")
        return 0
    else:
        print("\n✗✗✗ Some tests failed. Fix core issues before proceeding. ✗✗✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
