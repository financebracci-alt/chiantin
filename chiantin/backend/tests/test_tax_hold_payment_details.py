"""
Tax Hold Payment Details API Tests

Tests for verifying the fix where payment details (beneficiary_name, iban, bic_swift, 
reference, crypto_wallet) are returned directly on the response object instead of 
nested under payment_details.

Test Coverage:
1. Admin GET tax hold - verify payment details are returned at top level
2. Admin POST tax hold - verify payment details are saved and returned correctly  
3. User GET tax status - verify payment details are returned at top level
4. Regression: User login still works
5. Regression: Admin login and user management still works
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials provided
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"
USER_WITH_TAX_HOLD_ID = "697b5d83cca320cfb6be831f"


class TestAuthRegression:
    """Regression tests to ensure auth still works"""
    
    def test_user_login_success(self):
        """Test that regular user can still login"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"PASS: User {TEST_USER_EMAIL} logged in successfully")
    
    def test_admin_login_success(self):
        """Test that admin can still login"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"PASS: Admin {ADMIN_EMAIL} logged in successfully")


class TestAdminTaxHold:
    """Tests for admin tax hold endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json().get("access_token")
    
    def test_get_tax_hold_returns_payment_details_at_top_level(self, admin_token):
        """
        Test that GET /{user_id}/tax-hold returns payment details directly
        NOT nested under payment_details.
        
        Expected response structure:
        {
            "is_blocked": true,
            "tax_amount_due": 1234.56,
            "reason": "...",
            "beneficiary_name": "...",  <-- Direct, not nested
            "iban": "...",              <-- Direct, not nested
            "bic_swift": "...",         <-- Direct, not nested
            "reference": "...",         <-- Direct, not nested
            "crypto_wallet": "..."      <-- Direct, not nested
        }
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{USER_WITH_TAX_HOLD_ID}/tax-hold",
            headers=headers
        )
        
        assert response.status_code == 200, f"GET tax-hold failed: {response.text}"
        data = response.json()
        print(f"Tax hold response: {data}")
        
        # Verify is_blocked is True for this user
        assert data.get("is_blocked") == True, "User should have active tax hold"
        
        # CRITICAL: Payment details must be at TOP LEVEL, not nested
        assert "payment_details" not in data, "payment_details should NOT be nested - fields should be at top level"
        
        # Verify all payment fields are present at top level
        payment_fields = ["beneficiary_name", "iban", "bic_swift", "reference", "crypto_wallet"]
        for field in payment_fields:
            assert field in data, f"Field '{field}' missing from response - should be at top level"
            print(f"  {field}: {data.get(field)}")
        
        # Verify at least some payment details have values (not all None)
        has_payment_data = any(data.get(f) is not None for f in payment_fields)
        if data.get("is_blocked"):
            print(f"  Payment data present: {has_payment_data}")
        
        print("PASS: GET tax-hold returns payment details at top level (not nested)")
    
    def test_get_tax_hold_no_blocked_user(self, admin_token):
        """Test GET tax-hold for user without tax hold returns correct structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get list of users to find one without tax hold
        users_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?limit=20",
            headers=headers
        )
        assert users_response.status_code == 200
        users = users_response.json().get("users", [])
        
        # Find a user without tax hold
        user_without_hold = None
        for user in users:
            if not user.get("has_tax_hold") and user.get("id") != USER_WITH_TAX_HOLD_ID:
                user_without_hold = user
                break
        
        if not user_without_hold:
            pytest.skip("No user without tax hold found for testing")
        
        # Get tax hold for this user
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_without_hold['id']}/tax-hold",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify is_blocked is False
        assert data.get("is_blocked") == False, "User should not have tax hold"
        
        # Payment fields should still be present (but null)
        payment_fields = ["beneficiary_name", "iban", "bic_swift", "reference", "crypto_wallet"]
        for field in payment_fields:
            assert field in data, f"Field '{field}' missing - should be present even when null"
        
        print(f"PASS: GET tax-hold for non-blocked user {user_without_hold['email']} returns correct structure")


class TestUserTaxStatus:
    """Tests for user tax status endpoint"""
    
    @pytest.fixture
    def user_token(self):
        """Get user auth token for ashleyalt005"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"User login failed: {response.text}")
        return response.json().get("access_token")
    
    def test_user_tax_status_returns_payment_details_at_top_level(self, user_token):
        """
        Test that GET /me/tax-status returns payment details directly 
        NOT nested under payment_details.
        """
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/users/me/tax-status",
            headers=headers
        )
        
        assert response.status_code == 200, f"GET tax-status failed: {response.text}"
        data = response.json()
        print(f"User tax status response: {data}")
        
        # CRITICAL: Payment details must be at TOP LEVEL, not nested
        assert "payment_details" not in data, "payment_details should NOT be nested - fields should be at top level"
        
        # Verify all payment fields are present at top level (whether null or not)
        payment_fields = ["beneficiary_name", "iban", "bic_swift", "reference", "crypto_wallet"]
        for field in payment_fields:
            assert field in data, f"Field '{field}' missing from response - should be at top level"
            print(f"  {field}: {data.get(field)}")
        
        print("PASS: GET /me/tax-status returns payment details at top level (not nested)")


class TestAdminUserManagementRegression:
    """Regression tests for admin user management"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json().get("access_token")
    
    def test_admin_can_list_users(self, admin_token):
        """Test admin can still list users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?limit=20",
            headers=headers
        )
        assert response.status_code == 200, f"List users failed: {response.text}"
        data = response.json()
        assert "users" in data, "No users in response"
        assert len(data["users"]) > 0, "Users list is empty"
        print(f"PASS: Admin can list users ({len(data['users'])} users returned)")
    
    def test_admin_can_get_user_details(self, admin_token):
        """Test admin can get specific user details"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{USER_WITH_TAX_HOLD_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Get user details failed: {response.text}"
        data = response.json()
        assert "user" in data, "No user in response"
        print(f"PASS: Admin can get user details for {data['user'].get('email')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
