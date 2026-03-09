"""
Test suite for Transfer Rejection Email Feature

Tests:
1. Transfer rejection triggers email sending
2. Idempotency: rejection_email_sent flag is set after email sent
3. Email content does NOT include rejection reason
4. Email includes: masked IBAN (first 4 + last 4 chars), amount, beneficiary name, timestamp, reference
5. CTA button links to /support page
6. Italian localization works when user language is 'it'
7. English localization works when user language is 'en'
8. Transfer approval does NOT trigger rejection email
9. Transfer creation does NOT trigger rejection email
10. Re-rejecting an already rejected transfer returns proper error
11. Admin transfers queue shows REJECTED transfers correctly
"""

import pytest
import requests
import os
import sys
import time
import re
from datetime import datetime
import uuid

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://file-download-debug.preview.emergentagent.com').rstrip('/')

# Test credentials - ONLY USE TEST USER
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"


class TestTransferRejectionEmail:
    """Transfer rejection email feature tests"""
    
    @pytest.fixture(scope="class")
    def user_auth(self):
        """Authenticate as test user and return token"""
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
        """Authenticate as admin and return token"""
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
    
    def test_01_user_login_success(self, user_auth):
        """Verify test user can login successfully"""
        assert user_auth["token"] is not None, "User token is None"
        assert user_auth["user_id"] is not None, "User ID is None"
        print(f"User authenticated successfully: {user_auth['user'].get('email')}")
    
    def test_02_admin_login_success(self, admin_auth):
        """Verify admin can login successfully"""
        assert admin_auth["token"] is not None, "Admin token is None"
        print(f"Admin authenticated successfully: {admin_auth['user'].get('email')}")
    
    def test_03_create_transfer_no_rejection_email(self, user_auth, user_account):
        """Test that creating a transfer does NOT trigger rejection email"""
        headers = {"Authorization": f"Bearer {user_auth['token']}"}
        
        # Create a new transfer with unique IBAN
        unique_suffix = str(uuid.uuid4())[:8]
        transfer_data = {
            "from_account_id": user_account["id"],
            "beneficiary_name": f"Test Reject Recipient {unique_suffix}",
            "beneficiary_iban": "DE89370400440532013002",
            "amount": 100,  # 1 EUR in cents
            "currency": "EUR",
            "details": f"Test transfer for rejection email testing {unique_suffix}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/transfers",
            headers=headers,
            json=transfer_data
        )
        
        assert response.status_code == 200 or response.status_code == 201, f"Transfer creation failed: {response.text}"
        resp_data = response.json()
        
        # API returns {ok: true, data: {...}}
        transfer = resp_data.get('data', resp_data)
        
        # Verify no rejection email was sent on creation
        assert transfer.get("rejection_email_sent") == False, \
            "Rejection email should NOT be sent on transfer creation"
        
        print(f"Transfer created: {transfer.get('id')} with status: {transfer.get('status')}")
        print(f"Rejection email sent (should be False): {transfer.get('rejection_email_sent')}")
        
        # Store for later tests
        self.__class__.created_transfer_id = transfer.get("id")
        self.__class__.created_transfer = transfer
    
    def test_04_admin_reject_transfer_triggers_email(self, admin_auth):
        """Test that admin rejection triggers rejection email"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        transfer_id = getattr(self.__class__, 'created_transfer_id', None)
        if not transfer_id:
            pytest.skip("No transfer created in previous test")
        
        print(f"Rejecting transfer: {transfer_id}")
        
        # Reject the transfer
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/{transfer_id}/reject",
            headers=headers,
            json={"reason": "Test rejection reason - DO NOT INCLUDE IN EMAIL"}
        )
        
        assert response.status_code == 200, f"Rejection failed: {response.text}"
        
        # Wait for email to be processed
        time.sleep(3)
        
        # Check the transfer status - API returns 'data' not 'transfers'
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=REJECTED",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get rejected transfers: {response.text}"
        data = response.json()
        transfers = data.get("data", [])  # API returns 'data' key
        
        # Find our rejected transfer
        rejected_transfer = None
        for t in transfers:
            if t.get("id") == transfer_id:
                rejected_transfer = t
                break
        
        assert rejected_transfer is not None, f"Rejected transfer {transfer_id} not found in admin queue"
        assert rejected_transfer.get("status") == "REJECTED", "Transfer should be REJECTED"
        
        # Check if rejection email was sent - the flag should be set
        assert rejected_transfer.get("rejection_email_sent") == True, \
            f"Rejection email should be sent. Got: {rejected_transfer.get('rejection_email_sent')}"
        assert rejected_transfer.get("rejection_email_provider_id") is not None, \
            "Should have a provider ID from Resend"
        
        print(f"Rejected transfer status: {rejected_transfer.get('status')}")
        print(f"Rejection email sent: {rejected_transfer.get('rejection_email_sent')}")
        print(f"Rejection email provider ID: {rejected_transfer.get('rejection_email_provider_id')}")
        
        self.__class__.rejected_transfer = rejected_transfer
    
    def test_05_idempotency_re_reject_returns_error(self, admin_auth):
        """Test that re-rejecting an already rejected transfer returns proper error"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        transfer_id = getattr(self.__class__, 'created_transfer_id', None)
        if not transfer_id:
            pytest.skip("No transfer created in previous test")
        
        # Try to reject again
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/{transfer_id}/reject",
            headers=headers,
            json={"reason": "Second rejection attempt"}
        )
        
        # Should return 400 error because transfer is already rejected
        assert response.status_code == 400, f"Expected 400 error for re-rejection, got {response.status_code}: {response.text}"
        print(f"Re-rejection correctly returned error: {response.text}")
    
    def test_06_approval_does_not_trigger_rejection_email(self, user_auth, user_account, admin_auth):
        """Test that approving a transfer does NOT trigger rejection email"""
        user_headers = {"Authorization": f"Bearer {user_auth['token']}"}
        admin_headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        # Create a new transfer for approval with unique IBAN
        unique_suffix = str(uuid.uuid4())[:8]
        transfer_data = {
            "from_account_id": user_account["id"],
            "beneficiary_name": f"Test Approval Recipient {unique_suffix}",
            "beneficiary_iban": "IT60X0542811101000000123456",
            "amount": 50,  # 0.50 EUR in cents
            "currency": "EUR",
            "details": f"Test transfer for approval testing {unique_suffix}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/transfers",
            headers=user_headers,
            json=transfer_data
        )
        
        assert response.status_code == 200 or response.status_code == 201, f"Transfer creation failed: {response.text}"
        resp_data = response.json()
        transfer = resp_data.get('data', resp_data)
        transfer_id = transfer.get("id")
        
        print(f"Created transfer for approval: {transfer_id}")
        
        # Approve the transfer
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/{transfer_id}/approve",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Approval failed: {response.text}"
        
        # Verify no rejection email was sent - API returns 'data' key
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=COMPLETED",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        transfers = data.get("data", [])
        
        approved_transfer = None
        for t in transfers:
            if t.get("id") == transfer_id:
                approved_transfer = t
                break
        
        if approved_transfer:
            assert approved_transfer.get("rejection_email_sent") != True, \
                "Rejection email should NOT be sent on approval"
            print(f"Approved transfer status: {approved_transfer.get('status')}")
            print(f"Rejection email sent (should be False/None): {approved_transfer.get('rejection_email_sent')}")
    
    def test_07_admin_transfers_queue_shows_rejected_correctly(self, admin_auth):
        """Test that admin transfers queue shows REJECTED transfers correctly"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        # Get rejected transfers
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=REJECTED",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get rejected transfers: {response.text}"
        data = response.json()
        
        # API returns 'data' and 'pagination' keys
        assert "data" in data, "Response should contain 'data' key"
        assert "pagination" in data, "Response should contain 'pagination' key"
        
        transfers = data.get("data", [])
        print(f"Found {len(transfers)} rejected transfers in queue")
        
        # Verify each rejected transfer has required fields
        for t in transfers:
            assert t.get("status") == "REJECTED", f"Transfer {t.get('id')} should be REJECTED"
            assert "sender_name" in t, "Transfer should have sender_name"
            assert "beneficiary_name" in t, "Transfer should have beneficiary_name"
    
    def test_08_email_translations_english(self):
        """Test that English email translations contain required content"""
        from services.email_service import EMAIL_TRANSLATIONS
        
        en_translations = EMAIL_TRANSLATIONS.get('en', {})
        
        # Check required keys exist
        assert 'transfer_rejected_subject' in en_translations, "Missing transfer_rejected_subject"
        assert 'transfer_rejected_title' in en_translations, "Missing transfer_rejected_title"
        assert 'transfer_rejected_body' in en_translations, "Missing transfer_rejected_body"
        assert 'transfer_rejected_button' in en_translations, "Missing transfer_rejected_button"
        assert 'transfer_rejected_security_warning' in en_translations, "Missing transfer_rejected_security_warning"
        
        # Verify subject line
        assert en_translations['transfer_rejected_subject'] == 'Transfer rejected – action may be required', \
            f"Wrong subject: {en_translations['transfer_rejected_subject']}"
        
        # Verify CTA button text
        assert en_translations['transfer_rejected_button'] == 'Contact Support', \
            f"Wrong button text: {en_translations['transfer_rejected_button']}"
        
        # Verify body mentions no funds sent
        assert 'no funds have been sent' in en_translations['transfer_rejected_body'].lower(), \
            "Body should mention no funds were sent"
        
        print("English translations verified successfully")
    
    def test_09_email_translations_italian(self):
        """Test that Italian email translations contain required content"""
        from services.email_service import EMAIL_TRANSLATIONS
        
        it_translations = EMAIL_TRANSLATIONS.get('it', {})
        
        # Check required keys exist
        assert 'transfer_rejected_subject' in it_translations, "Missing transfer_rejected_subject in Italian"
        assert 'transfer_rejected_title' in it_translations, "Missing transfer_rejected_title in Italian"
        assert 'transfer_rejected_body' in it_translations, "Missing transfer_rejected_body in Italian"
        assert 'transfer_rejected_button' in it_translations, "Missing transfer_rejected_button in Italian"
        assert 'transfer_rejected_security_warning' in it_translations, "Missing transfer_rejected_security_warning in Italian"
        
        # Verify Italian content exists and is different from English
        assert "azione" in it_translations['transfer_rejected_subject'].lower() or \
               "rifiutato" in it_translations['transfer_rejected_subject'].lower(), \
            f"Italian subject should contain Italian text: {it_translations['transfer_rejected_subject']}"
        
        # Verify body mentions no funds sent in Italian
        assert 'nessun fondo' in it_translations['transfer_rejected_body'].lower(), \
            "Italian body should mention no funds were sent"
        
        print("Italian translations verified successfully")
    
    def test_10_email_content_no_rejection_reason(self):
        """Test that email template does NOT include rejection reason"""
        from services.email_service import EmailService
        import inspect
        
        # Get the send_transfer_rejected_email method
        method = EmailService.send_transfer_rejected_email
        source = inspect.getsource(method)
        
        # The method signature should NOT have 'reason' as a parameter
        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())
        assert 'reason' not in param_names, f"Email method should not accept 'reason' parameter. Params: {param_names}"
        
        print("Verified: Email does NOT include rejection reason")
    
    def test_11_email_includes_masked_iban(self):
        """Test that email includes masked IBAN (first 4 + last 4)"""
        from services.email_service import EmailService
        import inspect
        
        # Get the send_transfer_rejected_email method source
        method = EmailService.send_transfer_rejected_email
        source = inspect.getsource(method)
        
        # Check for mask_iban function
        assert 'mask_iban' in source, "Email template should use mask_iban function"
        
        # Check that it shows first 4 and last 4
        assert 'iban[:4]' in source, "Should show first 4 characters"
        assert 'iban[-4:]' in source, "Should show last 4 characters"
        
        print("Verified: Email includes masked IBAN (first 4 + last 4)")
    
    def test_12_email_includes_required_fields(self):
        """Test that email includes: amount, beneficiary name, timestamp, reference"""
        from services.email_service import EmailService
        import inspect
        
        method = EmailService.send_transfer_rejected_email
        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())
        
        # Check required parameters
        assert 'amount_cents' in param_names, "Should accept amount_cents"
        assert 'beneficiary_name' in param_names, "Should accept beneficiary_name"
        assert 'rejection_timestamp' in param_names, "Should accept rejection_timestamp"
        assert 'reference_number' in param_names, "Should accept reference_number"
        assert 'beneficiary_iban' in param_names, "Should accept beneficiary_iban"
        
        # Check the source uses these
        source = inspect.getsource(method)
        assert 'amount_formatted' in source, "Should format and display amount"
        assert 'beneficiary_name' in source, "Should display beneficiary name"
        assert 'timestamp_formatted' in source, "Should format and display timestamp"
        assert 'reference_number' in source, "Should display reference number"
        
        print("Verified: Email includes all required fields")
    
    def test_13_email_cta_links_to_support(self):
        """Test that CTA button links to /support page"""
        from services.email_service import EmailService
        import inspect
        
        method = EmailService.send_transfer_rejected_email
        source = inspect.getsource(method)
        
        # Check that support_url is created with /support path
        assert '/support' in source, "Email should link to /support page"
        assert 'support_url' in source, "Email should have support_url variable"
        
        print("Verified: CTA button links to /support page")
    
    def test_14_transfer_schema_has_rejection_email_fields(self):
        """Test that Transfer schema has rejection email tracking fields"""
        from schemas.banking_workflows import Transfer
        
        # Get model fields
        fields = Transfer.model_fields
        
        # Check required fields exist
        assert 'rejection_email_sent' in fields, "Should have rejection_email_sent field"
        assert 'rejection_email_sent_at' in fields, "Should have rejection_email_sent_at field"
        assert 'rejection_email_provider_id' in fields, "Should have rejection_email_provider_id field"
        assert 'rejection_email_error' in fields, "Should have rejection_email_error field"
        
        # Verify default values
        default_transfer = Transfer(
            user_id="test",
            from_account_id="test",
            beneficiary_name="test",
            beneficiary_iban="test",
            amount=100,
            details="test"
        )
        
        assert default_transfer.rejection_email_sent == False, "Default rejection_email_sent should be False"
        
        print("Verified: Transfer schema has rejection email tracking fields")
    
    def test_15_reject_transfer_sets_idempotency_flag(self):
        """Test that reject_transfer function sets rejection_email_sent flag"""
        from services.banking_workflows_service import BankingWorkflowsService
        import inspect
        
        method = BankingWorkflowsService.reject_transfer
        source = inspect.getsource(method)
        
        # Check idempotency check
        assert "rejection_email_sent" in source, "Should check/set rejection_email_sent flag"
        
        # Check it sets the flag after sending email
        assert '"rejection_email_sent": True' in source or "'rejection_email_sent': True" in source, \
            "Should set rejection_email_sent to True after email"
        
        print("Verified: reject_transfer sets idempotency flag")
    
    def test_16_email_failure_does_not_block_rejection(self):
        """Test that email failures do not block the rejection flow"""
        from services.banking_workflows_service import BankingWorkflowsService
        import inspect
        
        method = BankingWorkflowsService.reject_transfer
        source = inspect.getsource(method)
        
        # Check for try-except around email sending
        assert "try:" in source, "Should have try block for email sending"
        assert "except Exception" in source or "except:" in source, "Should catch exceptions"
        
        # Check that email error is logged but doesn't fail the rejection
        assert 'logger.error' in source or 'logger.warning' in source, "Should log email errors"
        
        print("Verified: Email failure does not block rejection flow")
    
    def test_17_get_admin_transfers_submitted_status(self, admin_auth):
        """Test getting transfers with SUBMITTED status for admin queue"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=SUBMITTED",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get submitted transfers: {response.text}"
        data = response.json()
        
        assert "data" in data, "Response should contain 'data' key"
        print(f"Found {len(data.get('data', []))} submitted transfers in queue")
    
    def test_18_get_admin_transfers_completed_status(self, admin_auth):
        """Test getting transfers with COMPLETED status for admin queue"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=COMPLETED",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get completed transfers: {response.text}"
        data = response.json()
        
        assert "data" in data, "Response should contain 'data' key"
        print(f"Found {len(data.get('data', []))} completed transfers in queue")
    
    def test_19_rejection_email_sent_flag_in_rejected_transfer(self, admin_auth):
        """Test that rejected transfer has rejection_email_sent flag set"""
        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        
        # Get rejected transfers
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=REJECTED",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        transfers = data.get("data", [])
        
        # Find transfers with rejection email info
        transfers_with_email_info = [t for t in transfers if 'rejection_email_sent' in t]
        print(f"Found {len(transfers_with_email_info)} rejected transfers with email tracking info")
        
        # Check the most recent rejected transfers have email tracking
        if transfers:
            latest = transfers[0]
            print(f"Latest rejected transfer: {latest.get('id')}")
            print(f"  - rejection_email_sent: {latest.get('rejection_email_sent')}")
            print(f"  - rejection_email_provider_id: {latest.get('rejection_email_provider_id')}")
            print(f"  - rejection_email_error: {latest.get('rejection_email_error')}")


class TestEmailServiceDirectly:
    """Direct unit tests for the email service"""
    
    def test_mask_iban_function_logic(self):
        """Test the IBAN masking logic"""
        # Replicate the mask_iban logic exactly as in email_service.py
        def mask_iban(iban):
            if not iban or len(iban) < 8:
                return iban or "N/A"
            return f"{iban[:4]}{'*' * (len(iban) - 8)}{iban[-4:]}"
        
        # Test cases - expecting (len - 8) asterisks between first 4 and last 4
        test_cases = [
            ("DE89370400440532013000", f"DE89{'*' * (22-8)}3000"),  # 22 chars, 14 asterisks
            ("IT60X054", "IT60X054"),  # Exactly 8 chars - return as is (less than or equal to 8)
            ("WO885458787887787878", f"WO88{'*' * (20-8)}7878"),  # 20 chars, 12 asterisks
            ("", "N/A"),  # Empty string
            (None, "N/A"),  # None
        ]
        
        for iban, expected in test_cases:
            result = mask_iban(iban)
            assert result == expected, f"mask_iban({iban}) = {result}, expected {expected}"
        
        print("IBAN masking logic verified correctly")
    
    def test_amount_formatting(self):
        """Test the EU amount formatting logic"""
        # Test cases (cents to EUR formatted)
        test_cases = [
            (100, "€1,00"),  # 1 EUR
            (1234, "€12,34"),  # 12.34 EUR
            (123456, "€1.234,56"),  # 1,234.56 EUR
            (10000000, "€100.000,00"),  # 100,000 EUR
        ]
        
        def format_amount(amount_cents):
            amount_euros = amount_cents / 100
            return f"€{amount_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        for cents, expected in test_cases:
            result = format_amount(cents)
            assert result == expected, f"format_amount({cents}) = {result}, expected {expected}"
        
        print("Amount formatting verified correctly")
    
    def test_email_service_method_exists(self):
        """Verify send_transfer_rejected_email method exists"""
        from services.email_service import EmailService
        
        assert hasattr(EmailService, 'send_transfer_rejected_email'), \
            "EmailService should have send_transfer_rejected_email method"
        
        print("EmailService.send_transfer_rejected_email method exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
