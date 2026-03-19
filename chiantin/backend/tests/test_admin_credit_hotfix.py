"""
P0 HOTFIX - Test Admin Credit/Debit Account Operations
Bug: Frontend sent 'amount' field but backend expected 'amount_cents'
Fix: Changed field name in frontend to amount_cents

Tests:
- Admin credit account (topup) endpoint works with amount_cents
- Admin debit account (withdraw) endpoint works with amount_cents
- Optional professional banking fields are accepted
- Audit logs are created for credit operations
- Balance is updated correctly after operations
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
TEST_CLIENT_EMAIL = "ashleyalt005@gmail.com"
TEST_CLIENT_PASSWORD = "123456789"

# Test account from requirements
TEST_ACCOUNT_ID = "bank_acc_699dcd808edd4998dcec2aa1"


class TestAdminCreditHotfix:
    """Test Admin Credit/Debit endpoints for P0 hotfix"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_client(self, admin_token):
        """Authenticated admin session"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_token}"
        })
        return session
    
    def test_admin_login(self):
        """Verify admin can login"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print("✓ Admin login successful")
    
    def test_credit_account_with_amount_cents(self, admin_client):
        """Test credit account using amount_cents field (P0 fix validation)"""
        # Get initial balance
        user_response = admin_client.get(f"{BASE_URL}/api/v1/admin/users/699dcd808edd4998dcec2aa1")
        if user_response.status_code == 200:
            initial_balance = user_response.json().get("account", {}).get("balance", 0)
        else:
            initial_balance = 0
        
        # Credit with amount_cents (the fix)
        credit_amount_cents = 100  # 1 EUR
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/topup",
            json={
                "amount_cents": credit_amount_cents,
                "description": "Test credit - P0 hotfix validation"
            }
        )
        
        assert response.status_code == 200, f"Credit failed: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        assert "transaction" in data
        assert "new_balance" in data
        
        # Verify balance increased
        assert data["new_balance"] >= initial_balance + credit_amount_cents
        print(f"✓ Credit successful with amount_cents. New balance: {data['new_balance']/100:.2f} EUR")
    
    def test_credit_account_with_professional_fields(self, admin_client):
        """Test credit account with optional professional banking fields"""
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/topup",
            json={
                "amount_cents": 500,  # 5 EUR
                "description": "Professional credit test",
                "display_type": "SEPA Transfer",
                "sender_name": "Test Bank AG",
                "sender_iban": "DE89370400440532013000",
                "sender_bic": "DEUTDEDB",
                "reference": "TRF2024TEST001",
                "admin_note": "Test transaction for hotfix validation"
            }
        )
        
        assert response.status_code == 200, f"Professional credit failed: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        print("✓ Professional credit with all optional fields successful")
    
    def test_credit_account_missing_amount_returns_error(self, admin_client):
        """Test that missing amount_cents returns proper validation error"""
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/topup",
            json={
                "description": "Test without amount"
            }
        )
        
        # Should return 422 validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Missing amount_cents correctly returns 422 validation error")
    
    def test_credit_account_old_amount_field_fails(self, admin_client):
        """Test that old 'amount' field (without _cents) fails validation"""
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/topup",
            json={
                "amount": 1000,  # Old field name - should NOT work
                "description": "Test with old field name"
            }
        )
        
        # Should return 422 since amount_cents is required
        assert response.status_code == 422, f"Expected 422 for old field name, got {response.status_code}"
        print("✓ Old 'amount' field correctly rejected - requires 'amount_cents'")
    
    def test_debit_account_with_amount_cents(self, admin_client):
        """Test debit account using amount_cents field"""
        # First credit some amount to ensure we can debit
        admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/topup",
            json={
                "amount_cents": 1000,  # 10 EUR
                "description": "Pre-debit credit for testing"
            }
        )
        
        # Now debit
        debit_amount_cents = 200  # 2 EUR
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/withdraw",
            json={
                "amount_cents": debit_amount_cents,
                "description": "Test debit - P0 hotfix validation"
            }
        )
        
        assert response.status_code == 200, f"Debit failed: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        assert "transaction" in data
        assert "new_balance" in data
        print(f"✓ Debit successful with amount_cents. New balance: {data['new_balance']/100:.2f} EUR")
    
    def test_debit_account_with_professional_fields(self, admin_client):
        """Test debit account with optional professional banking fields"""
        # First ensure there's balance
        admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/topup",
            json={
                "amount_cents": 500,
                "description": "Pre-debit credit"
            }
        )
        
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/withdraw",
            json={
                "amount_cents": 300,  # 3 EUR
                "description": "Professional debit test",
                "display_type": "Wire Transfer",
                "recipient_name": "Test Recipient",
                "recipient_iban": "FR7630006000011234567890189",
                "reference": "WDR2024TEST001",
                "admin_note": "Test withdrawal for hotfix validation"
            }
        )
        
        assert response.status_code == 200, f"Professional debit failed: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        print("✓ Professional debit with all optional fields successful")
    
    def test_debit_insufficient_balance(self, admin_client):
        """Test debit fails gracefully with insufficient balance"""
        # Try to debit a very large amount
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/withdraw",
            json={
                "amount_cents": 9999999900,  # 99,999,999 EUR - should fail
                "description": "Test insufficient balance"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for insufficient balance, got {response.status_code}"
        data = response.json()
        assert "Insufficient balance" in data.get("detail", "")
        print("✓ Insufficient balance correctly returns 400 error")
    
    def test_audit_log_created_for_credit(self, admin_client):
        """Verify audit log is created for credit operations"""
        # First do a credit
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/topup",
            json={
                "amount_cents": 100,
                "description": "Audit log test credit"
            }
        )
        assert response.status_code == 200
        
        # Check audit logs
        audit_response = admin_client.get(f"{BASE_URL}/api/v1/admin/audit-logs?limit=5")
        assert audit_response.status_code == 200
        
        audit_logs = audit_response.json()
        if isinstance(audit_logs, list) and len(audit_logs) > 0:
            # Check if recent log is a LEDGER_TOP_UP
            recent_actions = [log.get("action") for log in audit_logs[:5]]
            assert "LEDGER_TOP_UP" in recent_actions, f"Expected LEDGER_TOP_UP in recent audit logs: {recent_actions}"
            print("✓ Audit log created for credit operation")
        else:
            print("⚠ Could not verify audit log (empty or different format)")
    
    def test_invalid_account_id_returns_404(self, admin_client):
        """Test that invalid account ID returns 404"""
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/invalid_account_xyz/topup",
            json={
                "amount_cents": 100,
                "description": "Test invalid account"
            }
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid account ID correctly returns 404")


class TestErrorHandling:
    """Test error handling for validation errors"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_client(self, admin_token):
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_token}"
        })
        return session
    
    def test_validation_error_returns_proper_format(self, admin_client):
        """Verify validation errors return proper format that frontend can parse"""
        response = admin_client.post(
            f"{BASE_URL}/api/v1/admin/accounts/{TEST_ACCOUNT_ID}/topup",
            json={}  # Missing required fields
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Check that detail is in expected format (array or string)
        detail = data.get("detail")
        assert detail is not None, "Validation error should have 'detail' field"
        
        # Frontend handles both array and string formats
        if isinstance(detail, list):
            # Pydantic validation error format
            assert len(detail) > 0
            assert "msg" in detail[0] or "message" in detail[0]
            print("✓ Validation error returns array format (Pydantic)")
        else:
            # String format
            assert isinstance(detail, str)
            print("✓ Validation error returns string format")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
