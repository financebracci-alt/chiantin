"""
Router Extraction Regression Tests

Tests all extracted routers to ensure behavior-preserving refactor:
- health.py: Health and DB health endpoints
- audit.py: Audit logs endpoint
- tickets.py: Support tickets endpoints (customer + admin)
- kyc.py: KYC endpoints (customer + admin)
- admin_users.py: Admin user management endpoints

Uses test account: ashleyalt005@gmail.com / 123456789
"""

import pytest
import requests
import os
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-restore-build.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "ashleyalt005@gmail.com"
TEST_PASSWORD = "123456789"


class TestHealthRouter:
    """Tests for /api/health and /api/db-health endpoints"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Expected 'healthy', got {data.get('status')}"
        assert data.get("app") == "ecommbx", f"Expected 'ecommbx', got {data.get('app')}"
        print("PASS: /api/health returns healthy status")
    
    def test_db_health_endpoint(self):
        """Test /api/db-health returns database status"""
        response = requests.get(f"{BASE_URL}/api/db-health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Expected 'healthy', got {data.get('status')}"
        assert "database_name" in data, "Missing database_name"
        assert "user_count" in data, "Missing user_count"
        assert data.get("admin_exists") == True, "Admin should exist"
        print(f"PASS: /api/db-health - DB: {data.get('database_name')}, Users: {data.get('user_count')}")


class TestAuthEndpoints:
    """Tests for authentication endpoints"""
    
    def test_login_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token"
        assert "user" in data, "Missing user data"
        assert data["user"]["email"] == TEST_EMAIL, f"Email mismatch"
        print(f"PASS: Login successful for {TEST_EMAIL}")
        return data["access_token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Invalid login returns 401")


@pytest.fixture(scope="class")
def auth_token():
    """Get auth token for admin tests"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip(f"Login failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Get auth headers for authenticated requests"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestAdminUsersRouter:
    """Tests for admin user management endpoints (/api/v1/admin/users/*)"""
    
    def test_get_all_users(self, auth_headers):
        """Test GET /api/v1/admin/users returns user list with pagination"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=auth_headers,
            params={"page": 1, "limit": 20}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "users" in data, "Missing users array"
        assert "pagination" in data, "Missing pagination info"
        assert isinstance(data["users"], list), "Users should be a list"
        
        pagination = data["pagination"]
        assert "total_users" in pagination, "Missing total_users"
        assert "total_pages" in pagination, "Missing total_pages"
        
        print(f"PASS: GET /api/v1/admin/users - Found {len(data['users'])} users (total: {pagination['total_users']})")
    
    def test_search_users(self, auth_headers):
        """Test user search by name/email"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=auth_headers,
            params={"search": "ashley"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "users" in data, "Missing users array"
        # When searching, all matching results are returned
        print(f"PASS: User search - Found {len(data['users'])} users matching 'ashley'")
    
    def test_get_user_details(self, auth_headers):
        """Test GET /api/v1/admin/users/{user_id} returns user details"""
        # First get user list to get a valid user_id
        list_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=auth_headers,
            params={"limit": 1}
        )
        assert list_response.status_code == 200
        
        users = list_response.json()["users"]
        if not users:
            pytest.skip("No users in database")
        
        user_id = users[0]["id"]
        
        # Get user details
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data, "Missing user object"
        assert "kyc_status" in data, "Missing kyc_status"
        assert "accounts" in data, "Missing accounts array"
        
        user = data["user"]
        assert "id" in user, "Missing user id"
        assert "email" in user, "Missing user email"
        assert "first_name" in user, "Missing first_name"
        assert "admin_notes" in user, "Missing admin_notes field"
        
        print(f"PASS: GET user details - {user['email']}, KYC: {data['kyc_status']}")
    
    def test_get_user_tax_hold_status(self, auth_headers):
        """Test GET /api/v1/admin/users/{user_id}/tax-hold returns tax hold status"""
        # Get a user first
        list_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=auth_headers,
            params={"limit": 1}
        )
        users = list_response.json()["users"]
        if not users:
            pytest.skip("No users in database")
        
        user_id = users[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/tax-hold",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "is_blocked" in data, "Missing is_blocked field"
        assert "tax_amount_due" in data, "Missing tax_amount_due field"
        
        print(f"PASS: Tax hold status - blocked: {data['is_blocked']}, amount: {data['tax_amount_due']}")


class TestAuditRouter:
    """Tests for audit log endpoints (/api/v1/admin/audit-logs)"""
    
    def test_get_audit_logs(self, auth_headers):
        """Test GET /api/v1/admin/audit-logs returns audit entries"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs",
            headers=auth_headers,
            params={"limit": 50}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of audit logs"
        
        if data:
            log = data[0]
            assert "id" in log, "Missing id"
            assert "action" in log, "Missing action"
            assert "entity_type" in log, "Missing entity_type"
            assert "created_at" in log, "Missing created_at"
        
        print(f"PASS: GET /api/v1/admin/audit-logs - Found {len(data)} audit entries")
    
    def test_get_audit_logs_by_entity_type(self, auth_headers):
        """Test audit log filtering by entity type"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs",
            headers=auth_headers,
            params={"entity_type": "auth", "limit": 20}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # All returned logs should have entity_type="auth"
        for log in data:
            if log.get("entity_type") != "auth":
                pytest.fail(f"Expected entity_type 'auth', got {log.get('entity_type')}")
        
        print(f"PASS: Audit logs filtered by entity_type='auth' - Found {len(data)} entries")


class TestTicketsRouter:
    """Tests for support tickets endpoints"""
    
    def test_admin_get_all_tickets(self, auth_headers):
        """Test GET /api/v1/admin/tickets returns all tickets"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of tickets"
        
        if data:
            ticket = data[0]
            assert "id" in ticket, "Missing ticket id"
            assert "subject" in ticket, "Missing subject"
            assert "status" in ticket, "Missing status"
        
        print(f"PASS: GET /api/v1/admin/tickets - Found {len(data)} tickets")
    
    def test_admin_get_tickets_with_status_filter(self, auth_headers):
        """Test admin tickets with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers=auth_headers,
            params={"status": "OPEN"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        print(f"PASS: Tickets filtered by status='OPEN' - Found {len(data)} tickets")
    
    def test_customer_tickets_endpoint(self, auth_headers):
        """Test GET /api/v1/tickets returns user's tickets"""
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of tickets"
        
        print(f"PASS: GET /api/v1/tickets (customer) - Found {len(data)} tickets")


class TestKYCRouter:
    """Tests for KYC endpoints"""
    
    def test_admin_get_pending_kyc(self, auth_headers):
        """Test GET /api/v1/admin/kyc/pending returns pending applications"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of KYC applications"
        
        if data:
            app = data[0]
            assert "id" in app, "Missing application id"
            assert "user_id" in app, "Missing user_id"
            assert "status" in app, "Missing status"
        
        print(f"PASS: GET /api/v1/admin/kyc/pending - Found {len(data)} pending applications")
    
    def test_customer_get_kyc_application(self, auth_headers):
        """Test GET /api/v1/kyc/application returns user's KYC status"""
        response = requests.get(
            f"{BASE_URL}/api/v1/kyc/application",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data or "id" in data, "Expected KYC application data"
        
        print(f"PASS: GET /api/v1/kyc/application - Status: {data.get('status', 'N/A')}")


class TestSidebarNavigation:
    """Verify all admin sidebar sections have working endpoints"""
    
    def test_overview_analytics(self, auth_headers):
        """Test /api/v1/admin/analytics/overview"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/overview",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "users" in data, "Missing users stats"
        assert "kyc" in data, "Missing kyc stats"
        assert "transfers" in data, "Missing transfers stats"
        assert "tickets" in data, "Missing tickets stats"
        
        print(f"PASS: Admin analytics overview - {data['users']['total']} users, {data['kyc']['pending']} pending KYC")
    
    def test_users_section(self, auth_headers):
        """Test users section endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("PASS: Users section endpoint working")
    
    def test_kyc_queue_section(self, auth_headers):
        """Test KYC queue endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("PASS: KYC queue section endpoint working")
    
    def test_transfers_queue_section(self, auth_headers):
        """Test transfers queue endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("PASS: Transfers queue section endpoint working")
    
    def test_support_tickets_section(self, auth_headers):
        """Test support tickets endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("PASS: Support tickets section endpoint working")
    
    def test_audit_logs_section(self, auth_headers):
        """Test audit logs endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("PASS: Audit logs section endpoint working")
    
    def test_card_requests_section(self, auth_headers):
        """Test card requests endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("PASS: Card requests section endpoint working")


class TestNotes:
    """Test admin notes functionality"""
    
    def test_update_user_notes(self, auth_headers):
        """Test PATCH /api/v1/admin/users/{user_id}/notes"""
        # Get a user first
        list_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=auth_headers,
            params={"limit": 1}
        )
        users = list_response.json()["users"]
        if not users:
            pytest.skip("No users in database")
        
        user_id = users[0]["id"]
        test_note = f"Test note added at {datetime.now().isoformat()}"
        
        # Update notes
        response = requests.patch(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/notes",
            headers=auth_headers,
            json={"notes": test_note}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        
        # Verify notes were saved
        detail_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}",
            headers=auth_headers
        )
        assert detail_response.status_code == 200
        
        user_data = detail_response.json()
        assert user_data["user"]["admin_notes"] == test_note, "Notes not saved correctly"
        
        print(f"PASS: Admin notes saved and verified for user {user_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
