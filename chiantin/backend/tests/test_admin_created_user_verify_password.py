"""
Test suite for admin-created user password verification bug fix.

Bug: Admin-created users couldn't authorize transfers because verify-password endpoint
failed to find them. Root cause: ObjectId(user_id) succeeds for 24-char hex STRING IDs
but MongoDB lookup returns None because the _id is stored as STRING, not ObjectId.

Fix: All affected endpoints now try ObjectId first, then string lookup if result is None.

Tests:
1. Admin can create a new test user
2. Admin-created user can login successfully
3. Admin-created user can verify password (THE BUG FIX)
4. Admin-created user gets 401 with wrong password
5. Admin-created user can access bank accounts
6. Admin-created user can access dashboard data
7. Regular user (ashleyalt005@gmail.com) still works
8. Admin login/functionality still works
9. Cleanup test user after tests
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://user-alert-system-2.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
REGULAR_USER_EMAIL = "ashleyalt005@gmail.com"
REGULAR_USER_PASSWORD = "123456789"

# Generate unique test user details to avoid conflicts
TEST_USER_EMAIL = f"testbot_{uuid.uuid4().hex[:8]}@test.com"
TEST_USER_PASSWORD = "TestPassword123!"
TEST_USER_IBAN = f"IT00TEST{uuid.uuid4().hex[:18].upper()}"


class TestAdminCreatedUserVerifyPassword:
    """Tests for the admin-created user password verification bug fix."""
    
    admin_token = None
    test_user_id = None
    test_user_token = None
    
    # ==================== ADMIN TESTS ====================
    
    def test_01_admin_login(self):
        """Admin can login successfully."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        TestAdminCreatedUserVerifyPassword.admin_token = data["access_token"]
        
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"]
        print(f"Admin login successful: {data['user']['email']}, role: {data['user']['role']}")
    
    def test_02_admin_create_test_user(self):
        """Admin can create a new test user via POST /api/v1/admin/users/create."""
        assert TestAdminCreatedUserVerifyPassword.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreatedUserVerifyPassword.admin_token}"}
        
        payload = {
            "first_name": "TestBot",
            "last_name": "User",
            "email": TEST_USER_EMAIL,
            "phone": "+1234567890",
            "password": TEST_USER_PASSWORD,
            "iban": TEST_USER_IBAN,
            "bic": "CFTEMTM1",
            "skip_kyc": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/users/create",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 200, f"Admin create user failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Create user did not return success=true"
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_EMAIL
        assert data["user"]["status"] == "ACTIVE"
        
        TestAdminCreatedUserVerifyPassword.test_user_id = data["user"]["id"]
        print(f"Test user created: {TEST_USER_EMAIL}, ID: {TestAdminCreatedUserVerifyPassword.test_user_id}")
        print(f"Test user IBAN: {TEST_USER_IBAN}")
    
    # ==================== ADMIN-CREATED USER TESTS (THE BUG FIX) ====================
    
    def test_03_admin_created_user_can_login(self):
        """Admin-created user can login successfully."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        assert response.status_code == 200, f"Admin-created user login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        TestAdminCreatedUserVerifyPassword.test_user_token = data["access_token"]
        
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_EMAIL
        assert data["user"]["status"] == "ACTIVE"
        print(f"Admin-created user login successful: {data['user']['email']}")
    
    def test_04_admin_created_user_can_verify_password(self):
        """
        THE BUG FIX TEST: Admin-created user can verify password.
        
        This was the critical bug - admin-created users have STRING IDs which 
        pass ObjectId validation but don't match the STRING _id in MongoDB.
        The fix tries ObjectId first, then falls back to string lookup.
        """
        assert TestAdminCreatedUserVerifyPassword.test_user_token, "Test user token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreatedUserVerifyPassword.test_user_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/verify-password",
            json={"password": TEST_USER_PASSWORD},
            headers=headers
        )
        
        assert response.status_code == 200, f"Verify password FAILED (BUG NOT FIXED): {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "verify-password did not return success=true"
        print("BUG FIX VERIFIED: Admin-created user can verify password successfully!")
    
    def test_05_admin_created_user_wrong_password_returns_401(self):
        """Admin-created user gets 401 with wrong password on verify-password."""
        assert TestAdminCreatedUserVerifyPassword.test_user_token, "Test user token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreatedUserVerifyPassword.test_user_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/verify-password",
            json={"password": "WrongPassword123!"},
            headers=headers
        )
        
        assert response.status_code == 401, f"Expected 401 for wrong password, got: {response.status_code}"
        print("Correct: Admin-created user gets 401 with wrong password")
    
    def test_06_admin_created_user_can_access_accounts(self):
        """Admin-created user can access bank accounts (GET /api/v1/accounts)."""
        assert TestAdminCreatedUserVerifyPassword.test_user_token, "Test user token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreatedUserVerifyPassword.test_user_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers=headers
        )
        
        assert response.status_code == 200, f"Get accounts failed: {response.text}"
        
        data = response.json()
        # Should have accounts array
        assert "accounts" in data or isinstance(data, list), "No accounts in response"
        
        accounts = data.get("accounts", data) if isinstance(data, dict) else data
        assert len(accounts) >= 1, "Admin-created user should have at least one bank account"
        
        # Check the IBAN matches what we created
        found_iban = False
        for acc in accounts:
            if acc.get("iban") == TEST_USER_IBAN:
                found_iban = True
                break
        
        assert found_iban, f"Expected IBAN {TEST_USER_IBAN} not found in accounts"
        print(f"Admin-created user can access accounts, IBAN {TEST_USER_IBAN} found")
    
    def test_07_admin_created_user_can_access_dashboard(self):
        """Admin-created user can access dashboard data."""
        assert TestAdminCreatedUserVerifyPassword.test_user_token, "Test user token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreatedUserVerifyPassword.test_user_token}"}
        
        # Try /api/v1/auth/me to verify user data access
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=headers
        )
        
        assert response.status_code == 200, f"Get /auth/me failed: {response.text}"
        
        data = response.json()
        assert data.get("email") == TEST_USER_EMAIL
        print(f"Admin-created user can access dashboard/me endpoint")
    
    # ==================== REGULAR USER TESTS (REGRESSION) ====================
    
    def test_08_regular_user_can_login(self):
        """Regular user (ashleyalt005@gmail.com) can still login."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": REGULAR_USER_EMAIL, "password": REGULAR_USER_PASSWORD}
        )
        
        assert response.status_code == 200, f"Regular user login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        TestAdminCreatedUserVerifyPassword.regular_user_token = data["access_token"]
        print(f"Regular user login successful: {REGULAR_USER_EMAIL}")
    
    def test_09_regular_user_can_verify_password(self):
        """Regular user can still verify password (regression test)."""
        token = getattr(TestAdminCreatedUserVerifyPassword, 'regular_user_token', None)
        assert token, "Regular user token not available"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/verify-password",
            json={"password": REGULAR_USER_PASSWORD},
            headers=headers
        )
        
        assert response.status_code == 200, f"Regular user verify-password failed: {response.text}"
        print("Regular user can still verify password (no regression)")
    
    def test_10_regular_user_can_access_accounts(self):
        """Regular user can still access bank accounts (regression test)."""
        token = getattr(TestAdminCreatedUserVerifyPassword, 'regular_user_token', None)
        assert token, "Regular user token not available"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers=headers
        )
        
        assert response.status_code == 200, f"Regular user get accounts failed: {response.text}"
        print("Regular user can still access accounts (no regression)")
    
    # ==================== ADMIN FUNCTIONALITY TESTS ====================
    
    def test_11_admin_can_view_users_list(self):
        """Admin can view users list."""
        assert TestAdminCreatedUserVerifyPassword.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreatedUserVerifyPassword.admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=headers
        )
        
        assert response.status_code == 200, f"Admin get users failed: {response.text}"
        
        data = response.json()
        assert "users" in data, "No users in response"
        print(f"Admin can view users list, count: {len(data['users'])}")
    
    def test_12_admin_can_view_grouped_tickets(self):
        """Admin can view grouped support tickets."""
        assert TestAdminCreatedUserVerifyPassword.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreatedUserVerifyPassword.admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers=headers
        )
        
        assert response.status_code == 200, f"Admin get tickets failed: {response.text}"
        print("Admin can view grouped support tickets")
    
    # ==================== CLEANUP ====================
    
    def test_99_cleanup_test_user(self):
        """Cleanup: Delete the test user created during testing."""
        if not TestAdminCreatedUserVerifyPassword.test_user_id:
            print("No test user to cleanup")
            return
        
        if not TestAdminCreatedUserVerifyPassword.admin_token:
            print("No admin token for cleanup")
            return
        
        headers = {"Authorization": f"Bearer {TestAdminCreatedUserVerifyPassword.admin_token}"}
        
        response = requests.delete(
            f"{BASE_URL}/api/v1/admin/users/{TestAdminCreatedUserVerifyPassword.test_user_id}/permanent",
            headers=headers
        )
        
        # Accept 200 or 404 (in case already deleted)
        assert response.status_code in [200, 404], f"Cleanup failed: {response.text}"
        
        if response.status_code == 200:
            print(f"Test user {TEST_USER_EMAIL} deleted successfully")
        else:
            print(f"Test user already deleted or not found")


# Additional test class for client support functionality
class TestClientSupportAccess:
    """Tests for client support page access."""
    
    def test_client_support_ticket_page_accessible(self):
        """Client can access support ticket page."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": REGULAR_USER_EMAIL, "password": REGULAR_USER_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets",
            headers=headers
        )
        
        assert response.status_code == 200, f"Client tickets access failed: {response.text}"
        print("Client can access support tickets page")
    
    def test_tax_status_page_accessible(self):
        """Tax status endpoint is accessible."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": REGULAR_USER_EMAIL, "password": REGULAR_USER_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check if there's a tax hold endpoint for the user
        response = requests.get(
            f"{BASE_URL}/api/v1/tax-status",
            headers=headers
        )
        
        # May return 200 or 404 depending on implementation
        # Main thing is it shouldn't return 500
        assert response.status_code != 500, f"Tax status endpoint error: {response.text}"
        print(f"Tax status endpoint returned: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
