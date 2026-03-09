"""
Deployment Readiness Tests for ECOMMBX Banking Platform
Tests all critical features before production deployment
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://file-download-debug.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_01_user_login_success(self):
        """Test user can login at /login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == TEST_USER_EMAIL
        assert data["user"]["role"] == "CUSTOMER"
        print(f"✓ User login successful - {TEST_USER_EMAIL}")
    
    def test_02_admin_login_success(self):
        """Test admin can login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"]
        print(f"✓ Admin login successful - {ADMIN_EMAIL}")


class TestUserDashboard:
    """Test user dashboard endpoints"""
    
    @pytest.fixture
    def user_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_03_get_user_accounts(self, user_token):
        """Test dashboard loads with account balance"""
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "accounts" in data
        print("✓ User accounts endpoint working")
    
    def test_04_get_user_transactions(self, user_token):
        """Test transaction history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/transactions",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        print("✓ User transactions endpoint working")


class TestAdminEndpoints:
    """Test admin endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_05_admin_users_list(self, admin_token):
        """Test admin can list users at /admin?section=users"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "pagination" in data
        print(f"✓ Admin users list working - found {data['pagination']['total_users']} users")
    
    def test_06_admin_create_user_endpoint_exists(self, admin_token):
        """Test admin create user endpoint is accessible"""
        # Test with invalid data to verify endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/users/create",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "",  # Invalid - empty
                "last_name": "Test",
                "email": "invalid",  # Invalid email
                "password": "short",  # Too short
                "iban": "",
                "bic": "CFTEMTM1"
            }
        )
        # Should return 400 for validation error, not 404
        assert response.status_code in [400, 422]  # Validation error expected
        print("✓ Admin create user endpoint exists and validates input")
    
    def test_07_admin_view_user_details(self, admin_token):
        """Test admin can view user details"""
        # First get users list
        users_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        users = users_response.json()["users"]
        if users:
            user_id = users[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/users/{user_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "user" in data
            print(f"✓ Admin can view user details - {data['user']['email']}")
        else:
            pytest.skip("No users to test")
    
    def test_08_admin_overview_endpoint(self, admin_token):
        """Test admin overview/analytics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Admin overview endpoint working")
    
    def test_09_admin_kyc_queue_endpoint(self, admin_token):
        """Test admin KYC queue endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc?page=1&limit=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Admin KYC queue endpoint working")
    
    def test_10_admin_transfers_endpoint(self, admin_token):
        """Test admin transfers queue endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?page=1&limit=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Admin transfers queue endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
