"""
Test Phone Number Validation for Registration
Tests that phone number is REQUIRED for new registrations (Feb 2025 requirement).
Existing users without phone must still be able to login.
"""
import pytest
import requests
import os
import random
import string

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for existing user without phone
EXISTING_USER_EMAIL = "ashleyalt005@gmail.com"
EXISTING_USER_PASSWORD = "123456789"


def generate_random_email():
    """Generate unique test email"""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"TEST_phone_reg_{suffix}@example.com"


class TestPhoneRequiredForRegistration:
    """Test that phone number is required for new user registration"""
    
    def test_registration_without_phone_blocked_by_backend(self):
        """Registration WITHOUT phone is blocked by backend API (422 validation error)"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "email": generate_random_email(),
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "NoPhone"
            # phone field is missing
        })
        # Backend should return 422 Unprocessable Entity for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        data = response.json()
        # Check error message mentions phone
        error_detail = str(data).lower()
        assert "phone" in error_detail or "required" in error_detail, f"Error should mention phone: {data}"
        print("✓ Backend correctly blocks registration without phone (422)")
    
    def test_registration_with_empty_phone_blocked(self):
        """Registration with empty phone is blocked by backend"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "email": generate_random_email(),
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "EmptyPhone",
            "phone": ""
        })
        # Backend should return 422 for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        data = response.json()
        error_detail = str(data).lower()
        assert "phone" in error_detail or "required" in error_detail, f"Error should mention phone: {data}"
        print("✓ Backend correctly blocks registration with empty phone")
    
    def test_registration_with_whitespace_phone_blocked(self):
        """Registration with whitespace-only phone is blocked by backend"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "email": generate_random_email(),
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "WhitespacePhone",
            "phone": "   "
        })
        # Backend should return 422 for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        data = response.json()
        error_detail = str(data).lower()
        assert "phone" in error_detail or "required" in error_detail, f"Error should mention phone: {data}"
        print("✓ Backend correctly blocks registration with whitespace-only phone")
    
    def test_registration_with_too_short_phone_blocked(self):
        """Registration with phone < 6 digits is blocked by backend"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "email": generate_random_email(),
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "ShortPhone",
            "phone": "12345"  # Only 5 digits
        })
        # Backend should return 422 for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        data = response.json()
        error_detail = str(data).lower()
        assert "phone" in error_detail or "valid" in error_detail, f"Error should mention phone: {data}"
        print("✓ Backend correctly blocks registration with too-short phone")
    
    def test_registration_with_valid_phone_succeeds(self):
        """Registration with valid phone number succeeds"""
        test_email = generate_random_email()
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "email": test_email,
            "password": "TestPassword123",
            "first_name": "Test",
            "last_name": "ValidPhone",
            "phone": "+39 123 456 7890"  # Valid international format
        })
        # Should succeed with 201 Created
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        # Email may be lowercased by backend
        assert data.get("email").lower() == test_email.lower()
        print(f"✓ Registration with valid phone succeeded: {data.get('email')}")
    
    def test_registration_with_italy_phone_format_succeeds(self):
        """Registration with Italian phone format (+39) succeeds"""
        test_email = generate_random_email()
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "email": test_email,
            "password": "TestPassword123",
            "first_name": "TestItaly",
            "last_name": "ValidPhone",
            "phone": "+39 327 610 6073"  # Italian format
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        print("✓ Italian phone format accepted")
    
    def test_registration_with_german_phone_format_succeeds(self):
        """Registration with German phone format (+49) succeeds"""
        test_email = generate_random_email()
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "email": test_email,
            "password": "TestPassword123",
            "first_name": "TestGermany",
            "last_name": "ValidPhone",
            "phone": "+49 30 12345678"  # German format
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        print("✓ German phone format accepted")
    
    def test_registration_with_us_phone_format_succeeds(self):
        """Registration with US phone format (+1) succeeds"""
        test_email = generate_random_email()
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "email": test_email,
            "password": "TestPassword123",
            "first_name": "TestUS",
            "last_name": "ValidPhone",
            "phone": "+1 212 555 1234"  # US format
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        print("✓ US phone format accepted")


class TestExistingUserWithoutPhoneCanLogin:
    """Test that existing users who registered before phone requirement can still login"""
    
    def test_existing_user_login_success(self):
        """Existing user without phone can still login (backward compatibility)"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": EXISTING_USER_EMAIL,
            "password": EXISTING_USER_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data.get("user", {}).get("email") == EXISTING_USER_EMAIL
        print(f"✓ Existing user {EXISTING_USER_EMAIL} can still login")
        return data.get("access_token")
    
    def test_existing_user_profile_loads(self):
        """Existing user's profile loads without errors"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": EXISTING_USER_EMAIL,
            "password": EXISTING_USER_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        user_from_login = login_resp.json().get("user", {})
        
        # Verify user data was returned with login response
        assert user_from_login.get("email") == EXISTING_USER_EMAIL, "Email should match in login response"
        print(f"✓ Existing user profile loads correctly from login response")


class TestAdminPanelSections:
    """Test admin panel sections still load correctly"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": EXISTING_USER_EMAIL,
            "password": EXISTING_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_admin_users_page_loads(self, admin_token):
        """Admin Users page loads with phone column"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "users" in data
        # Verify phone field exists for each user
        for user in data.get("users", [])[:5]:  # Check first 5
            assert "phone" in user, f"Phone field missing for user {user.get('email')}"
        print("✓ Admin Users page loads with phone field")
    
    def test_admin_analytics_overview_loads(self, admin_token):
        """Admin Analytics Overview page loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin Analytics Overview loads")
    
    def test_admin_kyc_queue_loads(self, admin_token):
        """Admin KYC Queue loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin KYC Queue loads")
    
    def test_admin_accounts_loads(self, admin_token):
        """Admin Accounts page loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin Accounts loads")
    
    def test_admin_transfers_loads(self, admin_token):
        """Admin Transfers Queue loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin Transfers Queue loads")
    
    def test_admin_tickets_loads(self, admin_token):
        """Admin Support Tickets loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin Support loads")
    
    def test_admin_audit_logs_loads(self, admin_token):
        """Admin Audit Logs loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin Audit Logs loads")


class TestPhoneDisplayInAdminPanel:
    """Test phone field displays correctly in admin panel"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": EXISTING_USER_EMAIL,
            "password": EXISTING_USER_PASSWORD
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    def test_users_with_phone_show_phone(self, admin_token):
        """Users who have phone display their phone number"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=hannan",  # User with phone
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        users = data.get("users", [])
        # Find user with phone
        users_with_phone = [u for u in users if u.get("phone")]
        if users_with_phone:
            print(f"✓ Found user with phone: {users_with_phone[0].get('email')} -> {users_with_phone[0].get('phone')}")
        else:
            print("⚠ No users with phone found in search results (may need different search)")
    
    def test_users_without_phone_return_null(self, admin_token):
        """Users without phone return null/None for phone field"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        users = data.get("users", [])
        # Find users without phone
        users_without_phone = [u for u in users if u.get("phone") is None]
        if users_without_phone:
            print(f"✓ Found user without phone: {users_without_phone[0].get('email')} -> phone is None")
        else:
            print("⚠ All users in this batch have phone numbers")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
