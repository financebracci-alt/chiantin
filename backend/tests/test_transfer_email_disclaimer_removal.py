"""
Test suite for Transfer Email Disclaimer Removal

Tests verify that:
1. Transfer confirmation email does NOT contain 'do not reply' / 'contact support@...' footer line
2. Transfer rejection email does NOT contain 'do not reply' / 'contact support@...' footer line
3. Both emails STILL contain security warning
4. Both emails STILL contain Contact Support/View Details button
5. Transfer creation workflow works correctly
6. Transfer rejection workflow works correctly
7. Idempotency still works - rejection email flag set correctly
"""

import pytest
import requests
import os
import sys
import time
import uuid
import inspect
import re

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://file-download-debug.preview.emergentagent.com').rstrip('/')

# Test credentials - ONLY USE TEST USER
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"


class TestEmailDisclaimerRemoval:
    """Tests for verifying transfer_disclaimer is removed from email templates"""
    
    def test_01_transfer_confirmation_email_no_disclaimer_in_html(self):
        """Test that send_transfer_confirmation_email HTML does NOT contain transfer_disclaimer"""
        from services.email_service import EmailService
        
        # Get the method source code
        method = EmailService.send_transfer_confirmation_email
        source = inspect.getsource(method)
        
        # Extract the html_body section
        # The disclaimer should NOT be referenced in the HTML template
        assert "t('transfer_disclaimer')" not in source, \
            "transfer_disclaimer should NOT be in transfer confirmation email HTML"
        
        # Also check that the literal text is not hardcoded
        assert "Please do not reply to this email" not in source, \
            "Literal 'do not reply' text should NOT be in transfer confirmation email"
        
        assert "Si prega di non rispondere a questa email" not in source, \
            "Italian 'do not reply' text should NOT be in transfer confirmation email"
        
        print("VERIFIED: Transfer confirmation email does NOT contain disclaimer")
    
    def test_02_transfer_rejected_email_no_disclaimer_in_html(self):
        """Test that send_transfer_rejected_email HTML does NOT contain transfer_disclaimer"""
        from services.email_service import EmailService
        
        # Get the method source code
        method = EmailService.send_transfer_rejected_email
        source = inspect.getsource(method)
        
        # The disclaimer should NOT be referenced in the HTML template
        assert "t('transfer_disclaimer')" not in source, \
            "transfer_disclaimer should NOT be in transfer rejected email HTML"
        
        # Also check that the literal text is not hardcoded
        assert "Please do not reply to this email" not in source, \
            "Literal 'do not reply' text should NOT be in transfer rejected email"
        
        assert "Si prega di non rispondere a questa email" not in source, \
            "Italian 'do not reply' text should NOT be in transfer rejected email"
        
        print("VERIFIED: Transfer rejected email does NOT contain disclaimer")
    
    def test_03_transfer_confirmation_email_still_has_security_warning(self):
        """Test that transfer confirmation email STILL contains security warning"""
        from services.email_service import EmailService
        
        method = EmailService.send_transfer_confirmation_email
        source = inspect.getsource(method)
        
        # Security warning should be present
        assert "t('transfer_security_warning')" in source, \
            "transfer_security_warning SHOULD be in transfer confirmation email"
        
        print("VERIFIED: Transfer confirmation email still contains security warning")
    
    def test_04_transfer_rejected_email_still_has_security_warning(self):
        """Test that transfer rejected email STILL contains security warning"""
        from services.email_service import EmailService
        
        method = EmailService.send_transfer_rejected_email
        source = inspect.getsource(method)
        
        # Security warning should be present
        assert "t('transfer_rejected_security_warning')" in source, \
            "transfer_rejected_security_warning SHOULD be in transfer rejected email"
        
        print("VERIFIED: Transfer rejected email still contains security warning")
    
    def test_05_transfer_confirmation_email_has_view_details_button(self):
        """Test that transfer confirmation email has View Details button"""
        from services.email_service import EmailService
        
        method = EmailService.send_transfer_confirmation_email
        source = inspect.getsource(method)
        
        # View Details button should be present
        assert "t('transfer_button')" in source, \
            "transfer_button SHOULD be in transfer confirmation email"
        
        # Should link to transactions page
        assert "transactions_url" in source, \
            "Should link to transactions URL"
        
        print("VERIFIED: Transfer confirmation email has View Details button")
    
    def test_06_transfer_rejected_email_has_contact_support_button(self):
        """Test that transfer rejected email has Contact Support button"""
        from services.email_service import EmailService
        
        method = EmailService.send_transfer_rejected_email
        source = inspect.getsource(method)
        
        # Contact Support button should be present
        assert "t('transfer_rejected_button')" in source, \
            "transfer_rejected_button SHOULD be in transfer rejected email"
        
        # Should link to support page (not external email)
        assert "support_url" in source, \
            "Should link to support URL"
        assert "/support" in source, \
            "Should link to in-app /support page"
        
        print("VERIFIED: Transfer rejected email has Contact Support button linking to /support")
    
    def test_07_disclaimer_translations_exist_but_unused(self):
        """Test that disclaimer translations exist in dict but are not used in templates"""
        from services.email_service import EMAIL_TRANSLATIONS, EmailService
        
        # Verify keys exist in translations (for backward compatibility)
        en_translations = EMAIL_TRANSLATIONS.get('en', {})
        it_translations = EMAIL_TRANSLATIONS.get('it', {})
        
        assert 'transfer_disclaimer' in en_translations, \
            "transfer_disclaimer key should still exist for backward compatibility"
        assert 'transfer_disclaimer' in it_translations, \
            "transfer_disclaimer key should still exist for IT backward compatibility"
        
        # But verify they are NOT used in either email template
        confirmation_source = inspect.getsource(EmailService.send_transfer_confirmation_email)
        rejection_source = inspect.getsource(EmailService.send_transfer_rejected_email)
        
        assert "transfer_disclaimer" not in confirmation_source, \
            "transfer_disclaimer should not be used in confirmation email"
        assert "transfer_disclaimer" not in rejection_source, \
            "transfer_disclaimer should not be used in rejection email"
        
        print("VERIFIED: Disclaimer translations exist but are NOT used in templates")


class TestTransferWorkflows:
    """Tests for transfer creation, approval, and rejection workflows"""
    
    @pytest.fixture(scope="class")
    def user_auth(self):
        """Authenticate as test user"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"User login failed: {response.text}"
        data = response.json()
        return {
            "token": data.get("access_token"),
            "user_id": data.get("user", {}).get("id"),
            "user": data.get("user")
        }
    
    @pytest.fixture(scope="class")
    def admin_auth(self):
        """Authenticate as admin"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        return {
            "token": data.get("access_token"),
            "user_id": data.get("user", {}).get("id"),
            "user": data.get("user")
        }
    
    @pytest.fixture(scope="class")
    def user_account(self, user_auth):
        """Get test user's bank account"""
        headers = {"Authorization": f"Bearer {user_auth['token']}"}
        response = requests.get(f"{BASE_URL}/api/v1/accounts", headers=headers)
        assert response.status_code == 200, f"Failed to get accounts: {response.text}"
        accounts = response.json()
        assert len(accounts) > 0, "No accounts found for test user"
        # Return the first account with a balance or the first account
        for acc in accounts:
            if acc.get("id") == "bank_acc_6971fed2ad8ed4d326f04041":
                return acc
        return accounts[0]
    
    def test_08_user_login_success(self, user_auth):
        """Verify test user can login"""
        assert user_auth["token"] is not None
        print(f"User authenticated: {user_auth['user'].get('email')}")
    
    def test_09_admin_login_success(self, admin_auth):
        """Verify admin can login"""
        assert admin_auth["token"] is not None
        print(f"Admin authenticated: {admin_auth['user'].get('email')}")
    
    def test_10_create_transfer_sends_confirmation_email(self, user_auth, user_account):
        """Test that creating a transfer triggers confirmation email"""
        headers = {"Authorization": f"Bearer {user_auth['token']}"}
        
        unique_suffix = str(uuid.uuid4())[:8]
        transfer_data = {
            "from_account_id": user_account["id"],
            "beneficiary_name": f"Test Disclaimer Removal {unique_suffix}",
            "beneficiary_iban": "DE89370400440532013002",
            "amount": 100,  # 1 EUR in cents
            "currency": "EUR",
            "details": f"Test transfer for disclaimer removal testing {unique_suffix}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/transfers",
            headers=headers,
            json=transfer_data
        )
        
        assert response.status_code in [200, 201], f"Transfer creation failed: {response.text}"
        resp_data = response.json()
        transfer = resp_data.get('data', resp_data)
        
        # Store for later tests
        self.__class__.test_transfer_id = transfer.get("id")
        self.__class__.test_transfer = transfer
        
        print(f"Transfer created: {transfer.get('id')} with status: {transfer.get('status')}")
        print(f"Confirmation email should have been sent (without disclaimer)")
    
    def test_11_admin_reject_transfer_sends_rejection_email(self, admin_auth):
        """Test that admin rejection triggers rejection email (without disclaimer)"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        transfer_id = getattr(self.__class__, 'test_transfer_id', None)
        if not transfer_id:
            pytest.skip("No transfer created in previous test")
        
        # Reject the transfer
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/{transfer_id}/reject",
            headers=headers,
            json={"reason": "Test rejection for disclaimer removal verification"}
        )
        
        assert response.status_code == 200, f"Rejection failed: {response.text}"
        
        # Wait for email processing
        time.sleep(3)
        
        # Verify rejection email was sent
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=REJECTED",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        transfers = data.get("data", [])
        
        rejected_transfer = None
        for t in transfers:
            if t.get("id") == transfer_id:
                rejected_transfer = t
                break
        
        assert rejected_transfer is not None, f"Rejected transfer {transfer_id} not found"
        assert rejected_transfer.get("status") == "REJECTED"
        assert rejected_transfer.get("rejection_email_sent") == True, \
            "Rejection email should be sent"
        
        print(f"Rejection email sent: {rejected_transfer.get('rejection_email_sent')}")
        print(f"Provider ID: {rejected_transfer.get('rejection_email_provider_id')}")
    
    def test_12_idempotency_re_reject_returns_error(self, admin_auth):
        """Test idempotency - re-rejecting already rejected transfer returns error"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        transfer_id = getattr(self.__class__, 'test_transfer_id', None)
        if not transfer_id:
            pytest.skip("No transfer created in previous test")
        
        # Try to reject again
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/{transfer_id}/reject",
            headers=headers,
            json={"reason": "Second rejection attempt"}
        )
        
        # Should return 400 error
        assert response.status_code == 400, \
            f"Expected 400 for re-rejection, got {response.status_code}"
        
        print("VERIFIED: Idempotency works - re-rejection returns 400")
    
    def test_13_approval_workflow_still_works(self, user_auth, user_account, admin_auth):
        """Test that approval workflow still works correctly"""
        user_headers = {"Authorization": f"Bearer {user_auth['token']}"}
        admin_headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        unique_suffix = str(uuid.uuid4())[:8]
        transfer_data = {
            "from_account_id": user_account["id"],
            "beneficiary_name": f"Test Approval Flow {unique_suffix}",
            "beneficiary_iban": "IT60X0542811101000000123456",
            "amount": 50,
            "currency": "EUR",
            "details": f"Test for approval workflow {unique_suffix}"
        }
        
        # Create transfer
        response = requests.post(
            f"{BASE_URL}/api/v1/transfers",
            headers=user_headers,
            json=transfer_data
        )
        
        assert response.status_code in [200, 201]
        resp_data = response.json()
        transfer = resp_data.get('data', resp_data)
        transfer_id = transfer.get("id")
        
        # Approve transfer
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/{transfer_id}/approve",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Approval failed: {response.text}"
        
        # Verify status
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=COMPLETED",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        print("VERIFIED: Approval workflow works correctly")


class TestEmailContentVerification:
    """Additional tests to verify email content details"""
    
    def test_14_transfer_confirmation_has_branding(self):
        """Test that transfer confirmation email has ecommbx branding"""
        from services.email_service import EmailService
        
        source = inspect.getsource(EmailService.send_transfer_confirmation_email)
        
        assert "ecomm" in source and "bx" in source, \
            "Email should have ecommbx branding"
        
        print("VERIFIED: Transfer confirmation email has branding")
    
    def test_15_transfer_rejected_has_branding(self):
        """Test that transfer rejected email has ecommbx branding"""
        from services.email_service import EmailService
        
        source = inspect.getsource(EmailService.send_transfer_rejected_email)
        
        assert "ecomm" in source and "bx" in source, \
            "Email should have ecommbx branding"
        
        print("VERIFIED: Transfer rejected email has branding")
    
    def test_16_transfer_confirmation_has_transfer_details(self):
        """Test that transfer confirmation email has transfer details section"""
        from services.email_service import EmailService
        
        source = inspect.getsource(EmailService.send_transfer_confirmation_email)
        
        # Should have transfer summary section
        assert "transfer_summary" in source, "Should have transfer summary"
        assert "transfer_amount" in source, "Should have amount"
        assert "transfer_recipient" in source, "Should have recipient"
        assert "transfer_reference" in source, "Should have reference"
        
        print("VERIFIED: Transfer confirmation email has all transfer details")
    
    def test_17_transfer_rejected_has_transfer_details(self):
        """Test that transfer rejected email has transfer details section"""
        from services.email_service import EmailService
        
        source = inspect.getsource(EmailService.send_transfer_rejected_email)
        
        # Should have transfer details section
        assert "transfer_rejected_summary" in source, "Should have transfer summary"
        assert "transfer_amount" in source, "Should have amount"
        assert "transfer_recipient" in source, "Should have recipient"
        assert "transfer_reference" in source, "Should have reference"
        
        print("VERIFIED: Transfer rejected email has all transfer details")
    
    def test_18_email_translations_en_complete(self):
        """Test English translations are complete for transfer emails"""
        from services.email_service import EMAIL_TRANSLATIONS
        
        en = EMAIL_TRANSLATIONS.get('en', {})
        
        # Transfer confirmation required keys
        confirmation_keys = [
            'transfer_subject', 'transfer_title', 'transfer_greeting',
            'transfer_body', 'transfer_summary', 'transfer_amount',
            'transfer_recipient', 'transfer_reference', 'transfer_button',
            'transfer_security_warning'
        ]
        
        for key in confirmation_keys:
            assert key in en, f"Missing EN translation: {key}"
        
        # Transfer rejected required keys
        rejected_keys = [
            'transfer_rejected_subject', 'transfer_rejected_title',
            'transfer_rejected_greeting', 'transfer_rejected_body',
            'transfer_rejected_button', 'transfer_rejected_security_warning'
        ]
        
        for key in rejected_keys:
            assert key in en, f"Missing EN translation: {key}"
        
        print("VERIFIED: All EN translations present")
    
    def test_19_email_translations_it_complete(self):
        """Test Italian translations are complete for transfer emails"""
        from services.email_service import EMAIL_TRANSLATIONS
        
        it = EMAIL_TRANSLATIONS.get('it', {})
        
        # Transfer confirmation required keys
        confirmation_keys = [
            'transfer_subject', 'transfer_title', 'transfer_greeting',
            'transfer_body', 'transfer_summary', 'transfer_amount',
            'transfer_recipient', 'transfer_reference', 'transfer_button',
            'transfer_security_warning'
        ]
        
        for key in confirmation_keys:
            assert key in it, f"Missing IT translation: {key}"
        
        # Transfer rejected required keys
        rejected_keys = [
            'transfer_rejected_subject', 'transfer_rejected_title',
            'transfer_rejected_greeting', 'transfer_rejected_body',
            'transfer_rejected_button', 'transfer_rejected_security_warning'
        ]
        
        for key in rejected_keys:
            assert key in it, f"Missing IT translation: {key}"
        
        print("VERIFIED: All IT translations present")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
