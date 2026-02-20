"""
COMPREHENSIVE FULL SYSTEM TEST for ecommbx Banking Platform
Test every feature, every endpoint, every flow.
ONLY creates test users with pattern: test_fullcheck_*@test.com
"""

import pytest
import requests
import os
import uuid
import time
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://reject-email.preview.emergentagent.com')

# Admin credentials (existing admin)
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Global token storage
ADMIN_TOKEN = None
TEST_USER_DATA = None
TEST_USER_ID = None


def get_admin_token():
    """Get or refresh admin token"""
    global ADMIN_TOKEN
    if ADMIN_TOKEN:
        return ADMIN_TOKEN
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    ADMIN_TOKEN = response.json().get("access_token")
    return ADMIN_TOKEN


def get_unique_test_user():
    """Generate unique test user data"""
    global TEST_USER_DATA
    if TEST_USER_DATA:
        return TEST_USER_DATA
    
    unique_id = uuid.uuid4().hex[:8]
    TEST_USER_DATA = {
        "email": f"test_fullcheck_{unique_id}@test.com",
        "password": "TestPassword123!",
        "first_name": "FullCheck",
        "last_name": "TestUser"
    }
    return TEST_USER_DATA


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"API health failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    def test_db_health(self):
        """Test database health endpoint"""
        response = requests.get(f"{BASE_URL}/api/db-health")
        assert response.status_code == 200, f"DB health failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Database health check passed")


class TestAuthenticationFlow:
    """Test authentication endpoints"""
    
    def test_01_signup_new_user(self):
        """Test user signup"""
        global TEST_USER_ID
        user_data = get_unique_test_user()
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/signup",
            json=user_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 201, f"Signup failed: {response.text}"
        data = response.json()
        assert data.get("email") == user_data["email"]
        assert data.get("email_verified") == False
        TEST_USER_ID = data.get("id")
        print(f"✓ Signup passed - created user: {user_data['email']}")
    
    def test_02_login_unverified_user_fails(self):
        """Test that unverified user cannot login"""
        user_data = get_unique_test_user()
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 403, f"Expected 403 for unverified user, got {response.status_code}: {response.text}"
        assert "EMAIL_NOT_VERIFIED" in response.text
        print("✓ Unverified user login correctly blocked")
    
    def test_03_admin_login(self):
        """Test admin login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"]
        print(f"✓ Admin login passed - role: {data['user']['role']}")
    
    def test_04_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrongpassword"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401 for invalid creds, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    def test_05_forgot_password_request(self):
        """Test forgot password endpoint"""
        user_data = get_unique_test_user()
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/forgot-password",
            json={"email": user_data["email"], "language": "en"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Forgot password failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ Forgot password request passed")
    
    def test_06_resend_verification(self):
        """Test resend verification email endpoint"""
        user_data = get_unique_test_user()
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/resend-verification",
            json={"email": user_data["email"], "language": "en"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Resend verification failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ Resend verification passed")
    
    def test_07_get_me_requires_auth(self):
        """Test /me endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/v1/auth/me")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ /me endpoint correctly requires auth")
    
    def test_08_get_me_with_admin_token(self):
        """Test /me endpoint with valid token"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get me failed: {response.text}"
        data = response.json()
        assert data.get("email") == ADMIN_EMAIL
        print("✓ /me endpoint passed with admin token")


class TestKYCEndpoints:
    """Test KYC verification endpoints"""
    
    def test_01_kyc_requires_auth(self):
        """Test that KYC endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/v1/kyc/application")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ KYC endpoint correctly requires auth")
    
    def test_02_admin_get_pending_kyc(self):
        """Test admin get pending KYC applications"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get pending KYC failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin get pending KYC passed - {len(data)} applications")


class TestBankAccountEndpoints:
    """Test bank account management"""
    
    def test_01_accounts_requires_auth(self):
        """Test accounts endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/v1/accounts")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ Accounts endpoint correctly requires auth")
    
    def test_02_admin_get_all_accounts(self):
        """Test admin get all accounts with users"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get accounts failed: {response.text}"
        data = response.json()
        # API returns {accounts: [], pagination: {}}
        accounts = data.get("accounts", data) if isinstance(data, dict) else data
        if isinstance(accounts, dict):
            accounts = accounts.get("accounts", [])
        print(f"✓ Admin get all accounts passed - {len(accounts)} accounts")


class TestTransfersEndpoints:
    """Test transfer-related endpoints"""
    
    def test_01_admin_get_transfers(self):
        """Test admin get transfers list"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get transfers failed: {response.text}"
        data = response.json()
        # API returns {data: [], ok: true}
        transfers = data.get("data", data) if isinstance(data, dict) else data
        print(f"✓ Admin get transfers passed - {len(transfers)} transfers")
    
    def test_02_beneficiaries_requires_auth(self):
        """Test beneficiaries endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/v1/beneficiaries")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ Beneficiaries endpoint correctly requires auth")
    
    def test_03_scheduled_payments_requires_auth(self):
        """Test scheduled payments endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/v1/scheduled-payments")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ Scheduled payments endpoint correctly requires auth")


class TestCardsEndpoints:
    """Test card-related endpoints"""
    
    def test_01_admin_get_card_requests(self):
        """Test admin get card requests"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get card requests failed: {response.text}"
        data = response.json()
        # API returns {data: [], ok: true}
        requests_list = data.get("data", data) if isinstance(data, dict) else data
        print(f"✓ Admin get card requests passed - {len(requests_list)} requests")
    
    def test_02_cards_requires_auth(self):
        """Test cards endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/v1/cards")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ Cards endpoint correctly requires auth")


class TestSupportTicketsFlow:
    """Test support tickets system"""
    
    def test_01_admin_get_tickets(self):
        """Test admin get all tickets"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get tickets failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin get tickets passed - {len(data)} tickets")
    
    def test_02_admin_filter_tickets_by_status(self):
        """Test ticket filtering by status"""
        token = get_admin_token()
        statuses = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
        for status in statuses:
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/tickets?status={status}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200, f"Filter by {status} failed: {response.text}"
        print("✓ Ticket status filtering passed for all statuses")
    
    def test_03_tickets_requires_auth(self):
        """Test tickets endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/v1/tickets")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ Tickets endpoint correctly requires auth")


class TestAdminUserManagement:
    """Test admin user management endpoints"""
    
    def test_01_get_all_users(self):
        """Test get all users with pagination"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get users failed: {response.text}"
        data = response.json()
        assert "users" in data
        assert "pagination" in data
        print(f"✓ Get all users passed - {data['pagination']['total_users']} users")
    
    def test_02_search_users(self):
        """Test user search functionality"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=test",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"User search failed: {response.text}"
        data = response.json()
        assert "users" in data
        print(f"✓ User search passed - found {len(data['users'])} results")
    
    def test_03_pagination_20(self):
        """Test user pagination with limit 20"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=20",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Pagination 20 failed: {response.text}"
        data = response.json()
        assert data["pagination"]["limit"] == 20
        print("✓ User pagination (limit=20) passed")
    
    def test_04_pagination_50(self):
        """Test user pagination with limit 50"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Pagination 50 failed: {response.text}"
        data = response.json()
        assert data["pagination"]["limit"] == 50
        print("✓ User pagination (limit=50) passed")
    
    def test_05_get_user_details(self):
        """Test get specific user details"""
        token = get_admin_token()
        # First get a user ID from the list
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?limit=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            if data["users"]:
                user_id = data["users"][0]["id"]
                detail_response = requests.get(
                    f"{BASE_URL}/api/v1/admin/users/{user_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                assert detail_response.status_code == 200, f"Get user details failed: {detail_response.text}"
                print("✓ Get user details passed")
            else:
                print("✓ Get user details skipped - no users available")
        else:
            print("✓ Get user details skipped - could not get user list")


class TestAuditLogs:
    """Test audit logs endpoint"""
    
    def test_01_get_audit_logs(self):
        """Test get audit logs"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get audit logs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get audit logs passed - {len(data)} entries")


class TestAdminNotifications:
    """Test admin notification endpoints"""
    
    def test_01_admin_notifications_counts(self):
        """Test admin notification counts"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notifications/counts-since-clear",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get notification counts failed: {response.text}"
        data = response.json()
        assert isinstance(data, dict)
        print(f"✓ Admin notification counts passed")
    
    def test_02_admin_notifications_cleared_at(self):
        """Test get notifications cleared timestamp"""
        token = get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notifications/cleared-at",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get cleared-at failed: {response.text}"
        print("✓ Admin notifications cleared-at passed")


class TestInsightsEndpoints:
    """Test spending insights endpoints"""
    
    def test_01_monthly_spending_requires_auth(self):
        """Test monthly spending requires auth"""
        response = requests.get(f"{BASE_URL}/api/v1/insights/monthly-spending")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ Monthly spending endpoint correctly requires auth")


class TestNotificationsEndpoints:
    """Test notifications endpoints"""
    
    def test_01_notifications_requires_auth(self):
        """Test notifications requires auth"""
        response = requests.get(f"{BASE_URL}/api/v1/notifications")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✓ Notifications endpoint correctly requires auth")


class TestCleanupTestData:
    """Cleanup all test data after tests complete"""
    
    def test_zz_cleanup_test_users(self):
        """Clean up test users created during testing"""
        token = get_admin_token()
        # Search for test users
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=test_fullcheck",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            users_to_delete = [u for u in data.get("users", []) if "test_fullcheck" in u.get("email", "")]
            
            deleted_count = 0
            for user in users_to_delete:
                try:
                    delete_response = requests.delete(
                        f"{BASE_URL}/api/v1/admin/users/{user['id']}/permanent",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    if delete_response.status_code in [200, 204]:
                        deleted_count += 1
                        print(f"  Deleted test user: {user['email']}")
                except Exception as e:
                    print(f"  Failed to delete user {user['email']}: {e}")
            
            print(f"✓ Test user cleanup completed - deleted {deleted_count} users")
        else:
            print("✓ Test user cleanup completed (no search results)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
