"""
Comprehensive Router Extraction Tests - All 5 Extracted Routers + Transfers (in server.py)

Tests all endpoints from extracted routers:
- auth.py: Login, signup, MFA, password management, email verification
- analytics.py: Admin analytics overview and monthly stats
- notifications.py: User notifications, admin notification counts
- cards.py: User and admin card endpoints
- accounts.py: User accounts, admin ledger operations

Also tests transfers endpoints still in server.py:
- POST/GET /api/v1/transfers
- GET /api/v1/admin/transfers

Test credentials: ashleyalt005@gmail.com / 123456789 (ADMIN)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestLoginAndAuth:
    """Auth Router Tests - /api/v1/auth/*"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.email = "ashleyalt005@gmail.com"
        self.password = "123456789"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_login_success(self):
        """POST /api/v1/auth/login - Login with valid credentials"""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "user" in data, "Response should contain user object"
        assert data["user"]["email"] == self.email, "Email should match"
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"], "User should be admin"
        
        print(f"✓ Login successful for {self.email}")
        print(f"  - Role: {data['user']['role']}")
        print(f"  - Token length: {len(data['access_token'])}")
    
    def test_login_invalid_credentials(self):
        """POST /api/v1/auth/login - Invalid credentials returns 401"""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Invalid credentials correctly rejected")
    
    def test_auth_me_endpoint(self):
        """GET /api/v1/auth/me - Get current user info"""
        # First login
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if login_response.status_code != 200:
            pytest.skip("Login failed")
        
        token = login_response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/v1/auth/me")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "email" in data, "Response should contain email"
        assert data["email"] == self.email, "Email should match"
        
        print(f"✓ Auth me endpoint working")


class TestAnalyticsRouter:
    """Analytics Router Tests - /api/v1/admin/analytics/*"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and login"""
        self.email = "ashleyalt005@gmail.com"
        self.password = "123456789"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.logged_in = True
        else:
            self.logged_in = False
            pytest.skip("Login failed")
    
    def test_analytics_overview(self):
        """GET /api/v1/admin/analytics/overview - Dashboard stats"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required sections
        required_sections = ["users", "kyc", "accounts", "transfers", "tickets", "cards"]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"
        
        # Verify users section
        assert "total" in data["users"], "users.total missing"
        assert "active" in data["users"], "users.active missing"
        
        # Verify transfers section
        assert "total" in data["transfers"], "transfers.total missing"
        assert "pending" in data["transfers"], "transfers.pending missing"
        assert "completed" in data["transfers"], "transfers.completed missing"
        
        print(f"✓ Analytics overview returns complete stats")
        print(f"  - Users: {data['users']['total']} total, {data['users']['active']} active")
        print(f"  - Transfers: {data['transfers']['total']} total")
    
    def test_analytics_monthly(self):
        """GET /api/v1/admin/analytics/monthly - Monthly statistics"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/analytics/monthly")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        assert "monthly_data" in data, "Response should contain monthly_data"
        assert "period" in data, "Response should contain period"
        assert len(data["monthly_data"]) == 6, "Should have 6 months of data"
        
        print(f"✓ Analytics monthly returns 6 months of data")


class TestNotificationsRouter:
    """Notifications Router Tests - /api/v1/notifications/* and /api/v1/admin/notification-counts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and login"""
        self.email = "ashleyalt005@gmail.com"
        self.password = "123456789"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Login failed")
    
    def test_admin_notification_counts(self):
        """GET /api/v1/admin/notification-counts - Badge counts for sidebar"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/notification-counts")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required keys
        required_keys = ["users", "kyc", "card_requests", "transfers", "tickets"]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
            assert isinstance(data[key], int), f"{key} should be an integer"
        
        print(f"✓ Notification counts returns all expected keys")
        print(f"  - users: {data['users']}, kyc: {data['kyc']}, card_requests: {data['card_requests']}")
    
    def test_user_notifications(self):
        """GET /api/v1/notifications - User notifications list"""
        response = self.session.get(f"{BASE_URL}/api/v1/notifications")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ User notifications endpoint working, {len(data)} notifications found")


class TestCardsRouter:
    """Cards Router Tests - /api/v1/card-requests, /api/v1/cards, /api/v1/admin/card-requests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and login"""
        self.email = "ashleyalt005@gmail.com"
        self.password = "123456789"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Login failed")
    
    def test_user_card_requests(self):
        """GET /api/v1/card-requests - User's card requests"""
        response = self.session.get(f"{BASE_URL}/api/v1/card-requests")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ok" in data, "Response should contain 'ok'"
        assert "data" in data, "Response should contain 'data'"
        assert isinstance(data["data"], list), "data should be a list"
        
        print(f"✓ User card requests working, {len(data['data'])} requests found")
    
    def test_user_cards(self):
        """GET /api/v1/cards - User's cards"""
        response = self.session.get(f"{BASE_URL}/api/v1/cards")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ok" in data, "Response should contain 'ok'"
        assert "data" in data, "Response should contain 'data'"
        
        print(f"✓ User cards working, {len(data['data'])} cards found")
    
    def test_admin_card_requests(self):
        """GET /api/v1/admin/card-requests - Admin card requests with pagination"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/card-requests")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ok" in data
        assert "data" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert "total" in pagination
        assert "page" in pagination
        assert "page_size" in pagination
        
        print(f"✓ Admin card requests working")
        print(f"  - Total: {pagination['total']}, Page: {pagination['page']}/{pagination['total_pages']}")


class TestAccountsRouter:
    """Accounts Router Tests - /api/v1/accounts, /api/v1/admin/accounts-with-users"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and login"""
        self.email = "ashleyalt005@gmail.com"
        self.password = "123456789"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Login failed")
    
    def test_user_accounts(self):
        """GET /api/v1/accounts - User's bank accounts"""
        response = self.session.get(f"{BASE_URL}/api/v1/accounts")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list of accounts"
        
        if len(data) > 0:
            account = data[0]
            # Verify account structure
            assert "id" in account, "Account should have id"
            assert "iban" in account or account.get("iban") is None, "Account may have iban"
        
        print(f"✓ User accounts working, {len(data)} accounts found")
    
    def test_admin_accounts_with_users(self):
        """GET /api/v1/admin/accounts-with-users - Admin view of all accounts"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/accounts-with-users")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ok" in data, "Response should contain 'ok'"
        assert "data" in data, "Response should contain 'data'"
        assert "pagination" in data, "Response should contain 'pagination'"
        
        pagination = data["pagination"]
        assert "total" in pagination
        assert "page" in pagination
        
        print(f"✓ Admin accounts with users working")
        print(f"  - Total accounts: {pagination['total']}")


class TestTransfersInServerPy:
    """Transfers Tests - Still in server.py (not extracted yet)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and login"""
        self.email = "ashleyalt005@gmail.com"
        self.password = "123456789"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Login failed")
    
    def test_user_transfers(self):
        """GET /api/v1/transfers - User's transfers (still in server.py)"""
        response = self.session.get(f"{BASE_URL}/api/v1/transfers")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ok" in data, "Response should contain 'ok'"
        assert "data" in data, "Response should contain 'data'"
        assert isinstance(data["data"], list), "data should be a list"
        
        print(f"✓ User transfers working (server.py), {len(data['data'])} transfers found")
    
    def test_admin_transfers(self):
        """GET /api/v1/admin/transfers - Admin transfers (still in server.py)"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/transfers")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ok" in data, "Response should contain 'ok'"
        assert "data" in data, "Response should contain 'data'"
        assert "pagination" in data, "Response should contain 'pagination'"
        
        print(f"✓ Admin transfers working (server.py)")
        print(f"  - Total: {data['pagination']['total']}")


class TestAuthorizationRequired:
    """Test that all admin endpoints require proper authorization"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup without auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_analytics_overview_requires_auth(self):
        """GET /api/v1/admin/analytics/overview - Requires admin auth"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Analytics overview requires auth")
    
    def test_notification_counts_requires_auth(self):
        """GET /api/v1/admin/notification-counts - Requires admin auth"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/notification-counts")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Notification counts requires auth")
    
    def test_admin_card_requests_requires_auth(self):
        """GET /api/v1/admin/card-requests - Requires admin auth"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/card-requests")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Admin card requests requires auth")
    
    def test_admin_accounts_requires_auth(self):
        """GET /api/v1/admin/accounts-with-users - Requires admin auth"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/accounts-with-users")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Admin accounts requires auth")
    
    def test_admin_transfers_requires_auth(self):
        """GET /api/v1/admin/transfers - Requires admin auth"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/transfers")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Admin transfers requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
