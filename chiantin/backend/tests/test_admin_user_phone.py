"""
Test Admin User Phone Number Display Feature
- Tests phone field in /api/v1/admin/users endpoint
- Tests phone field in /api/v1/admin/users/{user_id} endpoint
- Tests users with and without phone numbers
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "ashleyalt005@gmail.com"
ADMIN_PASSWORD = "123456789"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestAdminUsersPhoneEndpoint:
    """Test phone field in /api/v1/admin/users list endpoint"""
    
    def test_users_list_returns_phone_field(self, admin_headers):
        """Verify users list API returns phone field"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=10",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "users" in data, "Response should contain 'users' array"
        
        users = data["users"]
        assert len(users) > 0, "Should have at least one user"
        
        # Check first user has phone field (can be None or string)
        first_user = users[0]
        assert "phone" in first_user, "User object should have 'phone' field"
    
    def test_users_list_has_user_with_phone(self, admin_headers):
        """Verify we can find a user WITH a phone number"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        users = response.json().get("users", [])
        users_with_phone = [u for u in users if u.get("phone")]
        
        assert len(users_with_phone) > 0, "Should have at least one user with phone number"
        
        # Verify phone format (should be a string)
        user_with_phone = users_with_phone[0]
        assert isinstance(user_with_phone["phone"], str), "Phone should be a string"
        assert len(user_with_phone["phone"]) > 0, "Phone should not be empty string"
        print(f"Found user with phone: {user_with_phone['email']} - {user_with_phone['phone']}")
    
    def test_users_list_has_user_without_phone(self, admin_headers):
        """Verify we can find a user WITHOUT a phone number"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        users = response.json().get("users", [])
        users_without_phone = [u for u in users if not u.get("phone")]
        
        assert len(users_without_phone) > 0, "Should have at least one user without phone number"
        
        # Verify phone is None/null for these users
        user_without_phone = users_without_phone[0]
        assert user_without_phone.get("phone") is None, "Phone should be None for users without phone"
        print(f"Found user without phone: {user_without_phone['email']}")


class TestAdminUserDetailPhoneEndpoint:
    """Test phone field in /api/v1/admin/users/{user_id} detail endpoint"""
    
    def test_user_detail_returns_phone_field(self, admin_headers):
        """Verify user detail API returns phone field"""
        # First get a user ID
        list_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=5",
            headers=admin_headers
        )
        assert list_response.status_code == 200
        
        users = list_response.json().get("users", [])
        assert len(users) > 0, "Need at least one user"
        
        user_id = users[0]["id"]
        
        # Get user detail
        detail_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}",
            headers=admin_headers
        )
        assert detail_response.status_code == 200, f"Expected 200, got {detail_response.status_code}"
        
        data = detail_response.json()
        assert "user" in data, "Response should have 'user' object"
        assert "phone" in data["user"], "User object should have 'phone' field"
    
    def test_user_detail_with_phone_shows_correct_value(self, admin_headers):
        """Verify user detail shows correct phone value for user with phone"""
        # Find a user with phone
        list_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers=admin_headers
        )
        users = list_response.json().get("users", [])
        users_with_phone = [u for u in users if u.get("phone")]
        
        assert len(users_with_phone) > 0, "Need user with phone for this test"
        
        test_user = users_with_phone[0]
        expected_phone = test_user["phone"]
        
        # Get detail
        detail_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{test_user['id']}",
            headers=admin_headers
        )
        assert detail_response.status_code == 200
        
        user_detail = detail_response.json().get("user", {})
        assert user_detail.get("phone") == expected_phone, \
            f"Expected phone '{expected_phone}', got '{user_detail.get('phone')}'"
        
        print(f"User detail phone verified: {user_detail['email']} = {user_detail['phone']}")
    
    def test_user_detail_without_phone_shows_none(self, admin_headers):
        """Verify user detail shows None for user without phone"""
        # Find a user without phone
        list_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers=admin_headers
        )
        users = list_response.json().get("users", [])
        users_without_phone = [u for u in users if not u.get("phone")]
        
        assert len(users_without_phone) > 0, "Need user without phone for this test"
        
        test_user = users_without_phone[0]
        
        # Get detail
        detail_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{test_user['id']}",
            headers=admin_headers
        )
        assert detail_response.status_code == 200
        
        user_detail = detail_response.json().get("user", {})
        assert user_detail.get("phone") is None, \
            f"Expected phone None, got '{user_detail.get('phone')}'"
        
        print(f"User detail without phone verified: {user_detail['email']} = None")


class TestAdminPanelRegressions:
    """Regression tests for admin panel features"""
    
    def test_user_search_still_works(self, admin_headers):
        """Verify user search functionality"""
        # Search by partial email
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=gmail&page=1&limit=50",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        users = response.json().get("users", [])
        # All returned users should have 'gmail' in email
        for user in users:
            assert "gmail" in user["email"].lower(), \
                f"Search result {user['email']} doesn't match 'gmail'"
        
        print(f"User search working: found {len(users)} users matching 'gmail'")
    
    def test_pagination_still_works(self, admin_headers):
        """Verify pagination returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=20",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "users" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert "total_users" in pagination
        assert "page" in pagination
        assert "total_pages" in pagination
        
        # Verify limit is respected
        assert len(data["users"]) <= 20
        print(f"Pagination working: page {pagination['page']}/{pagination['total_pages']}, {len(data['users'])} users")
    
    def test_admin_access_required(self):
        """Verify non-admin cannot access users endpoint"""
        # Try without auth
        response = requests.get(f"{BASE_URL}/api/v1/admin/users")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
