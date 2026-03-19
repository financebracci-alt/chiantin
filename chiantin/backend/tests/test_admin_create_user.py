"""
Test Admin Create User Feature

Tests the following scenarios:
1. Admin login and token retrieval
2. Admin can access /api/v1/admin/users endpoint (list users)
3. Admin can create a new user via POST /api/v1/admin/users/create
4. Newly created user can login immediately
5. Created user has bank account with assigned IBAN
6. Regression: Existing user (ashleyalt005@gmail.com) can still login
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
TEST_USER_EMAIL = "ashleyalt005+test@gmail.com"
TEST_USER_PASSWORD = "Test123456!"
TEST_USER_IBAN = "MT29TEST00000000000088888888"
TEST_USER_BIC = "CFTEMTM1"
EXISTING_USER_EMAIL = "ashleyalt005@gmail.com"
EXISTING_USER_PASSWORD = "123456789"


class TestAdminCreateUser:
    """Test suite for Admin Create User feature"""
    
    admin_token = None
    created_user_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup fixture to get admin token"""
        if not BASE_URL:
            pytest.skip("REACT_APP_BACKEND_URL not set")
    
    def test_01_admin_login_success(self):
        """Test admin can login successfully"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        print(f"Admin login status: {response.status_code}")
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        
        # Store token for subsequent tests
        TestAdminCreateUser.admin_token = data["access_token"]
        print(f"✓ Admin login successful, token obtained")
    
    def test_02_admin_can_list_users(self):
        """Test admin can access users list endpoint"""
        assert TestAdminCreateUser.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreateUser.admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=headers
        )
        print(f"List users status: {response.status_code}")
        
        assert response.status_code == 200, f"Failed to list users: {response.text}"
        data = response.json()
        assert "users" in data, "No users field in response"
        print(f"✓ Admin can list users, found {len(data['users'])} users")
    
    def test_03_check_test_user_does_not_exist(self):
        """Check if test user already exists and skip creation if so"""
        assert TestAdminCreateUser.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreateUser.admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search={TEST_USER_EMAIL}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            existing_users = [u for u in data.get("users", []) if u.get("email") == TEST_USER_EMAIL]
            if existing_users:
                TestAdminCreateUser.created_user_id = existing_users[0]["id"]
                print(f"⚠ Test user already exists with ID: {TestAdminCreateUser.created_user_id}")
                pytest.skip("Test user already exists, skipping creation test")
        
        print(f"✓ Test user does not exist, proceeding with creation")
    
    def test_04_admin_create_user_success(self):
        """Test admin can create a new user"""
        assert TestAdminCreateUser.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreateUser.admin_token}"}
        payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": TEST_USER_EMAIL,
            "phone": "+35699123456",
            "password": TEST_USER_PASSWORD,
            "iban": TEST_USER_IBAN,
            "bic": TEST_USER_BIC,
            "skip_kyc": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/users/create",
            json=payload,
            headers=headers
        )
        print(f"Create user status: {response.status_code}")
        print(f"Create user response: {response.text[:500] if response.text else 'empty'}")
        
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, f"Success flag not true: {data}"
        assert "user" in data, "No user field in response"
        
        user = data["user"]
        assert user.get("email") == TEST_USER_EMAIL.lower(), "Email mismatch"
        assert user.get("status") == "ACTIVE", "Status should be ACTIVE"
        assert user.get("iban") == TEST_USER_IBAN, "IBAN mismatch"
        assert user.get("kyc_status") == "APPROVED", "KYC should be APPROVED when skip_kyc=true"
        
        TestAdminCreateUser.created_user_id = user.get("id")
        print(f"✓ User created successfully with ID: {TestAdminCreateUser.created_user_id}")
    
    def test_05_newly_created_user_can_login(self):
        """Test that the newly created user can login immediately"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        print(f"New user login status: {response.status_code}")
        
        assert response.status_code == 200, f"New user login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token for new user"
        print(f"✓ Newly created user can login successfully")
    
    def test_06_verify_user_has_bank_account_with_iban(self):
        """Verify the created user has a bank account with the assigned IBAN"""
        # Login as the new user
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        user_token = response.json()["access_token"]
        
        # Get accounts
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/accounts", headers=headers)
        print(f"Get accounts status: {response.status_code}")
        
        assert response.status_code == 200, f"Failed to get accounts: {response.text}"
        data = response.json()
        
        # Check for bank account with the IBAN
        # The API returns a list directly, not an object with accounts field
        accounts = data if isinstance(data, list) else data.get("accounts", [])
        assert len(accounts) > 0, "User should have at least one account"
        
        found_iban = False
        for acc in accounts:
            if acc.get("iban") == TEST_USER_IBAN:
                found_iban = True
                print(f"✓ Found bank account with IBAN: {acc.get('iban')}")
                break
        
        assert found_iban, f"IBAN {TEST_USER_IBAN} not found in user accounts: {accounts}"
    
    def test_07_regression_existing_user_can_login(self):
        """Regression test: Existing user can still login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": EXISTING_USER_EMAIL, "password": EXISTING_USER_PASSWORD}
        )
        print(f"Existing user login status: {response.status_code}")
        
        assert response.status_code == 200, f"Existing user login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token for existing user"
        print(f"✓ Regression test passed: Existing user can still login")
    
    def test_08_admin_can_view_created_user_details(self):
        """Verify admin can view the created user's details"""
        if not TestAdminCreateUser.created_user_id:
            pytest.skip("No created user ID available")
        
        assert TestAdminCreateUser.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreateUser.admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{TestAdminCreateUser.created_user_id}",
            headers=headers
        )
        print(f"View user details status: {response.status_code}")
        
        assert response.status_code == 200, f"Failed to get user details: {response.text}"
        data = response.json()
        
        user = data.get("user", {})
        assert user.get("email") == TEST_USER_EMAIL.lower(), "Email mismatch in details"
        assert user.get("status") == "ACTIVE", "Status should be ACTIVE"
        
        # Check KYC status
        kyc_status = data.get("kyc_status")
        assert kyc_status == "APPROVED", f"KYC should be APPROVED, got: {kyc_status}"
        
        # Check accounts
        accounts = data.get("accounts", [])
        assert len(accounts) > 0, "User should have bank account"
        
        found_iban = False
        for acc in accounts:
            if acc.get("iban") == TEST_USER_IBAN:
                found_iban = True
                break
        
        assert found_iban, f"IBAN not found in admin view: {accounts}"
        print(f"✓ Admin can view user details correctly")
    
    def test_09_duplicate_email_rejected(self):
        """Test that creating a user with duplicate email is rejected"""
        assert TestAdminCreateUser.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreateUser.admin_token}"}
        payload = {
            "first_name": "Duplicate",
            "last_name": "Test",
            "email": TEST_USER_EMAIL,  # Same email as before
            "password": "DifferentPass123!",
            "iban": "MT29TEST00000000000099999999",  # Different IBAN
            "bic": TEST_USER_BIC,
            "skip_kyc": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/users/create",
            json=payload,
            headers=headers
        )
        print(f"Duplicate email status: {response.status_code}")
        
        assert response.status_code == 400, f"Should reject duplicate email: {response.text}"
        print(f"✓ Duplicate email correctly rejected")
    
    def test_10_duplicate_iban_rejected(self):
        """Test that creating a user with duplicate IBAN is rejected"""
        assert TestAdminCreateUser.admin_token, "Admin token not available"
        
        headers = {"Authorization": f"Bearer {TestAdminCreateUser.admin_token}"}
        payload = {
            "first_name": "Another",
            "last_name": "Test",
            "email": "anothertest@example.com",  # Different email
            "password": "TestPass123!",
            "iban": TEST_USER_IBAN,  # Same IBAN as created user
            "bic": TEST_USER_BIC,
            "skip_kyc": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/users/create",
            json=payload,
            headers=headers
        )
        print(f"Duplicate IBAN status: {response.status_code}")
        
        assert response.status_code == 400, f"Should reject duplicate IBAN: {response.text}"
        print(f"✓ Duplicate IBAN correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
