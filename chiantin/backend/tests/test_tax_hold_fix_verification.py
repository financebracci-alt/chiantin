"""
Tax Hold Payment Details Fix Verification
Tests for P0 CRITICAL FIX: Reading from both nested payment_details AND top-level fields
for backwards compatibility with old DB records.

Test Scenarios:
1. Admin tax-hold endpoint returns payment details for user with nested data
2. User /me/tax-status endpoint returns payment details correctly
3. Regression tests for admin and user features
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"
USER_WITH_TAX_HOLD_NESTED = "69a6e5689f91b67119a6e52f"


class TestTaxHoldFix:
    """Tests for the tax hold payment details fix"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get test user authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"User login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_admin_tax_hold_returns_payment_details_for_nested_data(self, admin_token):
        """
        CRITICAL TEST: Admin endpoint should return payment details from nested payment_details
        User 69a6e5689f91b67119a6e52f has data stored in nested payment_details format
        """
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{USER_WITH_TAX_HOLD_NESTED}/tax-hold",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify tax hold is active
        assert data["is_blocked"] == True, "Tax hold should be blocked"
        assert data["tax_amount_due"] > 0, "Tax amount should be greater than 0"
        
        # CRITICAL: Verify payment details are returned (from nested payment_details)
        assert data["beneficiary_name"] is not None, "beneficiary_name should NOT be None"
        assert data["iban"] is not None, "iban should NOT be None"
        assert data["bic_swift"] is not None, "bic_swift should NOT be None"
        assert data["reference"] is not None, "reference should NOT be None"
        
        # Verify specific values are present (not 'Not provided')
        assert data["beneficiary_name"] != "", "beneficiary_name should not be empty"
        assert data["iban"] != "", "iban should not be empty"
        
        print(f"PASS: Payment details returned correctly:")
        print(f"  - beneficiary_name: {data['beneficiary_name']}")
        print(f"  - iban: {data['iban']}")
        print(f"  - bic_swift: {data['bic_swift']}")
        print(f"  - reference: {data['reference']}")
        print(f"  - crypto_wallet: {data['crypto_wallet']}")
    
    def test_user_tax_status_endpoint(self, user_token):
        """Test user's own tax status endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/v1/users/me/tax-status",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # User ashleyalt005@gmail.com may or may not have tax hold
        # Just verify the endpoint returns expected fields
        assert "is_blocked" in data
        assert "tax_amount_due" in data
        assert "beneficiary_name" in data
        assert "iban" in data
        assert "bic_swift" in data
        assert "reference" in data
        assert "crypto_wallet" in data
        
        print(f"PASS: User tax status endpoint returns expected fields")


class TestUserAuthentication:
    """User authentication regression tests"""
    
    def test_user_login_success(self):
        """Test user login with correct credentials"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == TEST_USER_EMAIL
        print(f"PASS: User login successful for {TEST_USER_EMAIL}")
    
    def test_user_login_wrong_password(self):
        """Test login fails with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": "wrongpassword"}
        )
        assert response.status_code in [401, 400], f"Should reject wrong password"
        print("PASS: Wrong password rejected")


class TestUserDashboard:
    """User dashboard regression tests"""
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get test user authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_user_profile(self, user_token):
        """Test user can get their profile"""
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["email"] == TEST_USER_EMAIL
        print(f"PASS: User profile retrieved")
    
    def test_user_accounts(self, user_token):
        """Test user can get their accounts"""
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts/my-accounts",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "accounts" in data
        print(f"PASS: User accounts retrieved, count: {len(data['accounts'])}")
    
    def test_user_transactions(self, user_token):
        """Test user can get their transactions"""
        response = requests.get(
            f"{BASE_URL}/api/v1/transactions/history",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"PASS: User transactions retrieved")


class TestAdminFeatures:
    """Admin panel regression tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"]
        print(f"PASS: Admin login successful")
    
    def test_admin_list_users(self, admin_token):
        """Test admin can list users"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "users" in data
        assert "pagination" in data
        print(f"PASS: Admin users list retrieved, count: {len(data['users'])}")
    
    def test_admin_support_tickets(self, admin_token):
        """Test admin can access support tickets (grouped view)"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"PASS: Admin support tickets retrieved")
    
    def test_admin_kyc_queue(self, admin_token):
        """Test admin can access KYC queue"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"PASS: Admin KYC queue retrieved")
    
    def test_admin_transfers_queue(self, admin_token):
        """Test admin can access transfers queue"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"PASS: Admin transfers queue retrieved")
    
    def test_admin_accounts_ledger(self, admin_token):
        """Test admin can access accounts/ledger"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"PASS: Admin accounts/ledger retrieved")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
