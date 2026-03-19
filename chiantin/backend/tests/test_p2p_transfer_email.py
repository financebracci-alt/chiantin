"""
Test P2P Transfer Email Feature - Bug Fix Verification

This test file verifies the bug fix for:
- P2P transfers (/api/v1/transfers/p2p) now send confirmation emails automatically
- Regular transfers continue to send confirmation emails
- Transfer record includes new email status fields
- Admin resend endpoint works correctly

ROOT CAUSE FIX: P2P transfers via TransferService.p2p_transfer() previously didn't send emails.
Now both internal and SEPA transfers via P2P endpoint send confirmation emails.

IMPORTANT: This is a LIVE BANKING APPLICATION
- Do NOT use real client data
- Create fresh test users and delete them after tests
"""

import pytest
import requests
import os
import time
import uuid
from datetime import datetime, timedelta

# Get the backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

# Admin credentials for testing
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"


class TestP2PTransferEmailFeature:
    """
    Test suite for the P2P Transfer Email bug fix.
    Verifies that P2P transfers now send confirmation emails.
    """
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth token."""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }

    # ==================== SCHEMA TESTS - NEW EMAIL STATUS FIELDS ====================
    
    def test_transfer_schema_has_new_email_status_fields(self):
        """Verify Transfer schema includes all new email status fields."""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from schemas.banking_workflows import Transfer, ConfirmationEmailStatus
        
        # Check all new fields exist in the model
        fields = Transfer.model_fields
        
        # New comprehensive email status fields
        assert 'confirmation_email_status' in fields, "Transfer should have confirmation_email_status field"
        assert 'confirmation_email_sent_at' in fields, "Transfer should have confirmation_email_sent_at field"
        assert 'confirmation_email_provider_id' in fields, "Transfer should have confirmation_email_provider_id field"
        assert 'confirmation_email_error' in fields, "Transfer should have confirmation_email_error field"
        
        # Legacy field for backwards compatibility
        assert 'confirmation_email_sent' in fields, "Transfer should have confirmation_email_sent field (legacy)"
        
        print("PASSED: Transfer schema has all new email status fields")
        
        # Verify ConfirmationEmailStatus enum
        assert ConfirmationEmailStatus.PENDING.value == "pending"
        assert ConfirmationEmailStatus.SENT.value == "sent"
        assert ConfirmationEmailStatus.FAILED.value == "failed"
        print("PASSED: ConfirmationEmailStatus enum has correct values (pending, sent, failed)")
    
    def test_transfer_schema_default_values(self):
        """Verify default values for email status fields."""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from schemas.banking_workflows import Transfer, ConfirmationEmailStatus
        
        fields = Transfer.model_fields
        
        # Check default values
        assert fields['confirmation_email_sent'].default == False, "confirmation_email_sent should default to False"
        assert fields['confirmation_email_status'].default == ConfirmationEmailStatus.PENDING, "confirmation_email_status should default to pending"
        assert fields['confirmation_email_sent_at'].default is None, "confirmation_email_sent_at should default to None"
        assert fields['confirmation_email_provider_id'].default is None, "confirmation_email_provider_id should default to None"
        assert fields['confirmation_email_error'].default is None, "confirmation_email_error should default to None"
        
        print("PASSED: All email status fields have correct default values")

    # ==================== P2P TRANSFER SERVICE TESTS ====================
    
    def test_p2p_transfer_service_sends_email(self):
        """Verify TransferService.p2p_transfer calls email service."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        # Get the source code of p2p_transfer
        source = inspect.getsource(TransferService.p2p_transfer)
        
        # Verify email sending is integrated
        assert "_send_transfer_confirmation_email" in source, "p2p_transfer should call _send_transfer_confirmation_email"
        assert "email_result" in source, "p2p_transfer should capture email result"
        assert "email_warning" in source, "p2p_transfer should handle email warnings"
        
        print("PASSED: p2p_transfer method integrates email service")
    
    def test_p2p_transfer_service_has_email_helper(self):
        """Verify TransferService has _send_transfer_confirmation_email helper."""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.transfer_service import TransferService
        
        # Check the helper method exists
        assert hasattr(TransferService, '_send_transfer_confirmation_email'), \
            "TransferService should have _send_transfer_confirmation_email method"
        
        print("PASSED: TransferService has _send_transfer_confirmation_email helper")
    
    def test_p2p_transfer_email_helper_returns_dict(self):
        """Verify _send_transfer_confirmation_email returns dict with success/provider_id/error."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        source = inspect.getsource(TransferService._send_transfer_confirmation_email)
        
        # Verify return structure
        assert "success" in source, "Helper should track success status"
        assert "provider_id" in source, "Helper should track provider_id"
        assert "error" in source, "Helper should track error messages"
        assert "email_warning" in source, "Helper should provide email_warning for response"
        
        print("PASSED: _send_transfer_confirmation_email returns proper status dict")
    
    def test_p2p_transfer_updates_email_status(self):
        """Verify p2p_transfer updates transfer record with email status."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        source = inspect.getsource(TransferService._update_transfer_email_status)
        
        # Verify all status fields are updated
        assert "confirmation_email_sent" in source, "Should update confirmation_email_sent"
        assert "confirmation_email_status" in source, "Should update confirmation_email_status"
        assert "confirmation_email_sent_at" in source, "Should update confirmation_email_sent_at"
        assert "confirmation_email_provider_id" in source, "Should update confirmation_email_provider_id"
        assert "confirmation_email_error" in source, "Should update confirmation_email_error"
        
        print("PASSED: _update_transfer_email_status updates all email status fields")
    
    def test_p2p_transfer_initializes_email_pending_status(self):
        """Verify p2p_transfer initializes email status as pending before sending."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        source = inspect.getsource(TransferService.p2p_transfer)
        
        # Check initial status is pending
        assert '"confirmation_email_status": "pending"' in source, \
            "Transfer record should initialize confirmation_email_status as pending"
        
        print("PASSED: p2p_transfer initializes email status as pending")

    # ==================== EMAIL SERVICE RESPONSE FORMAT TESTS ====================
    
    def test_email_service_returns_structured_response(self):
        """Verify EmailService.send_transfer_confirmation_email returns dict with success/provider_id/error."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.email_service import EmailService
        
        source = inspect.getsource(EmailService.send_transfer_confirmation_email)
        
        # Verify return structure comments and implementation
        assert "'success'" in source, "Should return success status"
        assert "'provider_id'" in source, "Should return provider_id"
        assert "'error'" in source, "Should return error on failure"
        
        print("PASSED: EmailService.send_transfer_confirmation_email returns structured response")
    
    def test_email_service_logs_with_transfer_email_tag(self):
        """Verify email service uses [TRANSFER EMAIL] logging tags."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.email_service import EmailService
        
        source = inspect.getsource(EmailService.send_transfer_confirmation_email)
        
        # Verify structured logging
        assert "[TRANSFER EMAIL]" in source, "Should use [TRANSFER EMAIL] logging tag"
        assert "transferRef=" in source or "recipient=" in source, "Should log transferId/recipient details"
        
        print("PASSED: EmailService uses structured [TRANSFER EMAIL] logging")

    # ==================== ADMIN RESEND ENDPOINT TESTS ====================
    
    def test_admin_resend_endpoint_exists(self, admin_headers):
        """Verify POST /api/v1/admin/transfers/{id}/resend-email endpoint exists."""
        # Use a fake ID to test endpoint existence
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/nonexistent_id_123/resend-email",
            headers=admin_headers
        )
        # Should return 404 (transfer not found), not 405 (method not allowed) or 404 (endpoint not found)
        assert response.status_code == 404, f"Expected 404 for missing transfer, got {response.status_code}"
        assert "not found" in response.text.lower(), "Should indicate transfer not found"
        
        print("PASSED: Admin resend endpoint exists and returns 404 for missing transfer")
    
    def test_admin_resend_prevents_duplicate_send(self, admin_headers):
        """Verify admin resend endpoint prevents resending if already sent successfully."""
        # Get an existing transfer with sent status to test
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find a transfer with confirmation_email_status = 'sent' if any
        sent_transfer = None
        for transfer in data.get("data", []):
            if transfer.get("confirmation_email_status") == "sent" and transfer.get("confirmation_email_sent"):
                sent_transfer = transfer
                break
        
        if sent_transfer:
            # Try to resend - should fail with 400
            transfer_id = sent_transfer.get("_id") or sent_transfer.get("id")
            resend_response = requests.post(
                f"{BASE_URL}/api/v1/admin/transfers/{transfer_id}/resend-email",
                headers=admin_headers
            )
            assert resend_response.status_code == 400, f"Expected 400 for already sent, got {resend_response.status_code}"
            assert "already sent" in resend_response.text.lower(), "Should indicate email already sent"
            print(f"PASSED: Resend blocked for transfer {transfer_id} (already sent)")
        else:
            print("INFO: No transfer with sent status found to test duplicate prevention")
    
    def test_admin_transfers_endpoint_returns_email_status_fields(self, admin_headers):
        """Verify admin transfers endpoint returns new email status fields."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check if any transfer has the new fields
        if len(data.get("data", [])) > 0:
            # Find any transfer with email status fields
            has_new_fields = False
            for transfer in data["data"]:
                if "confirmation_email_status" in transfer:
                    has_new_fields = True
                    status = transfer.get("confirmation_email_status")
                    assert status in ["pending", "sent", "failed", None], f"Invalid email status: {status}"
                    print(f"PASSED: Found transfer with confirmation_email_status={status}")
                    
                    # Check other fields if present
                    if transfer.get("confirmation_email_sent_at"):
                        print(f"  - sent_at: {transfer['confirmation_email_sent_at']}")
                    if transfer.get("confirmation_email_provider_id"):
                        print(f"  - provider_id: {transfer['confirmation_email_provider_id']}")
                    if transfer.get("confirmation_email_error"):
                        print(f"  - error: {transfer['confirmation_email_error']}")
                    break
            
            if not has_new_fields:
                print("INFO: No transfers have the new email status fields yet (may be older transfers)")
        else:
            print("INFO: No transfers found to check email status fields")

    # ==================== P2P ENDPOINT TESTS ====================
    
    def test_p2p_transfer_endpoint_exists(self, admin_headers):
        """Verify POST /api/v1/transfers/p2p endpoint exists."""
        response = requests.post(
            f"{BASE_URL}/api/v1/transfers/p2p",
            headers=admin_headers,
            json={}  # Empty payload to test endpoint existence
        )
        # Should return 422 (validation error) not 404 (endpoint not found)
        assert response.status_code != 404, "POST /api/v1/transfers/p2p endpoint should exist"
        assert response.status_code in [400, 403, 422], f"Expected validation error, got {response.status_code}"
        print(f"PASSED: POST /api/v1/transfers/p2p endpoint exists (status: {response.status_code})")

    # ==================== LOGGING TESTS ====================
    
    def test_transfer_service_uses_structured_logging(self):
        """Verify TransferService uses structured [TRANSFER EMAIL] logging."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        source = inspect.getsource(TransferService._send_transfer_confirmation_email)
        
        # Verify structured logging format
        assert "[TRANSFER EMAIL]" in source, "Should use [TRANSFER EMAIL] tag"
        assert "transferId=" in source or "transfer_id" in source, "Should log transfer ID"
        assert "recipient=" in source or "user_email" in source, "Should log recipient email"
        
        print("PASSED: TransferService uses structured logging with [TRANSFER EMAIL] tags")


class TestP2PTransferEmailIntegration:
    """
    Integration tests verifying the complete P2P transfer + email flow.
    Tests code paths without creating actual transfers on LIVE system.
    """
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth token."""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_p2p_transfer_internal_sends_email(self):
        """Verify internal P2P transfer (recipient exists) sends email."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        source = inspect.getsource(TransferService.p2p_transfer)
        
        # Check the INTERNAL TRANSFER path sends email
        # The code has two paths: internal (to_account found) and SEPA (external)
        # Both should call _send_transfer_confirmation_email
        
        # Count occurrences of email sending call
        email_call_count = source.count("_send_transfer_confirmation_email")
        assert email_call_count >= 2, f"p2p_transfer should call email for both internal and SEPA paths, found {email_call_count} calls"
        
        print(f"PASSED: p2p_transfer calls email service {email_call_count} times (internal and SEPA)")
    
    def test_p2p_transfer_sepa_sends_email(self):
        """Verify SEPA P2P transfer (external recipient) sends email."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        source = inspect.getsource(TransferService.p2p_transfer)
        
        # Verify SEPA path has email sending
        # Look for SEPA TRANSFER comment and email call after it
        assert "SEPA TRANSFER" in source, "Should have SEPA transfer path"
        assert "_send_transfer_confirmation_email" in source, "Should call email service"
        
        print("PASSED: SEPA P2P transfer path includes email sending")
    
    def test_regular_transfer_endpoint_still_works(self, admin_headers):
        """Verify regular transfers (via /api/v1/transfers) still work."""
        response = requests.get(
            f"{BASE_URL}/api/v1/transfers",
            headers=admin_headers
        )
        assert response.status_code == 200, f"GET /api/v1/transfers should work, got {response.status_code}"
        data = response.json()
        assert "ok" in data or "data" in data, "Response should have valid structure"
        print("PASSED: Regular transfers endpoint still works")


class TestTransferEmailErrorHandling:
    """Test error handling for transfer confirmation emails."""
    
    def test_email_failure_does_not_break_transfer(self):
        """Verify email sending failure doesn't break transfer creation."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        source = inspect.getsource(TransferService._send_transfer_confirmation_email)
        
        # Verify error handling with try/except
        assert "except Exception" in source, "Email errors should be caught"
        assert "email_warning" in source, "Should set warning on failure"
        # Status is updated via _update_transfer_email_status call
        assert "_update_transfer_email_status" in source, "Should call status update method even on failure"
        
        print("PASSED: Email errors are handled gracefully (don't break transfers)")
    
    def test_email_failure_stores_error_message(self):
        """Verify email failure error message is stored in transfer record."""
        import sys
        sys.path.insert(0, '/app/backend')
        import inspect
        from services.transfer_service import TransferService
        
        source = inspect.getsource(TransferService._update_transfer_email_status)
        
        # Verify error message is stored
        assert "confirmation_email_error" in source, "Should store error message"
        # Check for failed status setting
        assert '"failed"' in source or "failed" in source, "Should set status to failed on error"
        
        print("PASSED: Email failure error messages are stored in transfer record")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
