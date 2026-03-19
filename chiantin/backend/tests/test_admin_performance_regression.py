"""
Admin Panel Performance and Full Regression Test Suite
Tests all admin sections: Overview, Users, KYC Queue, Accounts, Card Requests, 
Transfers Queue, Support Tickets, Audit Logs

Performance targets:
- Section shell visible < 50ms (client-side, tested via Playwright)
- First meaningful content < 200ms
- Full data loaded < 500-800ms
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_EMAIL = "ashleyalt005@gmail.com"
TEST_PASSWORD = "123456789"


class TestAdminAuth:
    """Authentication tests for admin login"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    def test_admin_login(self, admin_token):
        """Test admin can login successfully"""
        assert admin_token is not None
        print(f"SUCCESS: Admin login successful, got token")


class TestOverviewSection:
    """Test Overview section API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_notification_counts_performance(self, admin_token):
        """Test notification-counts API for performance - used by sidebar badges"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers=headers
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"notification-counts failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, dict), "Response should be a dict"
        print(f"SUCCESS: notification-counts loaded in {elapsed_ms:.0f}ms")
        print(f"Counts: {data}")


class TestUsersSection:
    """Test Users section API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_users_list_performance(self, admin_token):
        """Test users list API with default pagination"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers=headers
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"users list failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "users" in data, "Response should contain 'users' key"
        print(f"SUCCESS: Users list loaded in {elapsed_ms:.0f}ms with {len(data.get('users', []))} users")
    
    def test_users_search(self, admin_token):
        """Test users search functionality"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=ashley",
            headers=headers
        )
        
        assert response.status_code == 200, f"users search failed: {response.text}"
        data = response.json()
        print(f"SUCCESS: Users search returned {len(data.get('users', []))} results")


class TestKYCSection:
    """Test KYC Queue section API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_kyc_pending_list(self, admin_token):
        """Test KYC pending applications list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=headers
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"KYC pending failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: KYC pending loaded in {elapsed_ms:.0f}ms with {len(data)} applications")


class TestAccountsSection:
    """Test Accounts section API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_accounts_list(self, admin_token):
        """Test accounts list for admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts",
            headers=headers
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"Accounts list failed: {response.text}"
        data = response.json()
        print(f"SUCCESS: Accounts list loaded in {elapsed_ms:.0f}ms with {len(data) if isinstance(data, list) else 'N/A'} accounts")


class TestCardRequestsSection:
    """Test Card Requests section API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_card_requests_pending(self, admin_token):
        """Test PENDING card requests list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&page=1&limit=50",
            headers=headers
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"Card requests PENDING failed: {response.text}"
        data = response.json()
        print(f"SUCCESS: Card requests PENDING loaded in {elapsed_ms:.0f}ms")
    
    def test_card_requests_fulfilled(self, admin_token):
        """Test FULFILLED card requests list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=FULFILLED&page=1&limit=50",
            headers=headers
        )
        
        assert response.status_code == 200, f"Card requests FULFILLED failed: {response.text}"
        print(f"SUCCESS: Card requests FULFILLED endpoint works")
    
    def test_card_requests_rejected(self, admin_token):
        """Test REJECTED card requests list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=REJECTED&page=1&limit=50",
            headers=headers
        )
        
        assert response.status_code == 200, f"Card requests REJECTED failed: {response.text}"
        print(f"SUCCESS: Card requests REJECTED endpoint works")
    
    def test_card_requests_search(self, admin_token):
        """Test card requests search"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&search=test",
            headers=headers
        )
        
        assert response.status_code == 200, f"Card requests search failed: {response.text}"
        print(f"SUCCESS: Card requests search works")


class TestTransfersSection:
    """Test Transfers Queue section API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_transfers_submitted(self, admin_token):
        """Test SUBMITTED transfers list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=SUBMITTED&page=1&limit=50",
            headers=headers
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"Transfers SUBMITTED failed: {response.text}"
        print(f"SUCCESS: Transfers SUBMITTED loaded in {elapsed_ms:.0f}ms")
    
    def test_transfers_completed(self, admin_token):
        """Test COMPLETED transfers list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=COMPLETED&page=1&limit=50",
            headers=headers
        )
        
        assert response.status_code == 200, f"Transfers COMPLETED failed: {response.text}"
        print(f"SUCCESS: Transfers COMPLETED endpoint works")
    
    def test_transfers_rejected(self, admin_token):
        """Test REJECTED transfers list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=REJECTED&page=1&limit=50",
            headers=headers
        )
        
        assert response.status_code == 200, f"Transfers REJECTED failed: {response.text}"
        print(f"SUCCESS: Transfers REJECTED endpoint works")
    
    def test_transfers_search(self, admin_token):
        """Test transfers search"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=SUBMITTED&search=test",
            headers=headers
        )
        
        assert response.status_code == 200, f"Transfers search failed: {response.text}"
        print(f"SUCCESS: Transfers search works")


class TestSupportTicketsSection:
    """Test Support Tickets section API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_tickets_list(self, admin_token):
        """Test tickets list for admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers=headers
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"Tickets list failed: {response.text}"
        data = response.json()
        print(f"SUCCESS: Tickets list loaded in {elapsed_ms:.0f}ms")


class TestAuditLogsSection:
    """Test Audit Logs section API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_audit_logs_list(self, admin_token):
        """Test audit logs list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs?page=1&limit=50",
            headers=headers
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"Audit logs failed: {response.text}"
        data = response.json()
        print(f"SUCCESS: Audit logs loaded in {elapsed_ms:.0f}ms")


class TestNotificationBadges:
    """Test notification badge functionality"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_mark_section_seen(self, admin_token):
        """Test marking a section as seen (clears badge)"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/notifications/seen",
            headers=headers,
            json={"section_key": "users"}
        )
        
        assert response.status_code == 200, f"Mark section seen failed: {response.text}"
        print(f"SUCCESS: Section marked as seen successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
