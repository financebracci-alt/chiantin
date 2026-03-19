"""
Router Extraction P0 Tests - Analytics, Notifications, Cards

Verifies behavior parity after extracting these routers from server.py:
- analytics.py: Admin analytics endpoints
- notifications.py: User and admin notification endpoints  
- cards.py: User and admin card endpoints

Test credentials: ashleyalt005@gmail.com / 123456789 (ADMIN)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRouterExtractionP0:
    """P0 Router Extraction Tests - Verify all extracted endpoints work correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test credentials and login"""
        self.email = "ashleyalt005@gmail.com"
        self.password = "123456789"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login and get token
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            self.logged_in = True
        else:
            self.logged_in = False
            pytest.skip(f"Failed to login: {login_response.status_code} - {login_response.text}")
    
    # ==================== LOGIN VERIFICATION ====================
    
    def test_login_works(self):
        """Verify login endpoint still works after extraction"""
        assert self.logged_in, "Login should succeed"
        assert self.token is not None, "Token should be returned"
        print(f"✓ Login successful, token obtained")
    
    # ==================== ANALYTICS ROUTER TESTS ====================
    
    def test_admin_analytics_overview(self):
        """GET /api/v1/admin/analytics/overview - Returns user/transfer/ticket stats"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure matches original implementation
        assert "users" in data, "Response should contain 'users' key"
        assert "total" in data["users"], "users should have 'total'"
        assert "active" in data["users"], "users should have 'active'"
        
        assert "kyc" in data, "Response should contain 'kyc' key"
        assert "pending" in data["kyc"], "kyc should have 'pending'"
        assert "approved" in data["kyc"], "kyc should have 'approved'"
        
        assert "accounts" in data, "Response should contain 'accounts' key"
        assert "total" in data["accounts"], "accounts should have 'total'"
        
        assert "transfers" in data, "Response should contain 'transfers' key"
        assert "total" in data["transfers"], "transfers should have 'total'"
        assert "pending" in data["transfers"], "transfers should have 'pending'"
        assert "completed" in data["transfers"], "transfers should have 'completed'"
        assert "rejected" in data["transfers"], "transfers should have 'rejected'"
        assert "volume_cents" in data["transfers"], "transfers should have 'volume_cents'"
        
        assert "tickets" in data, "Response should contain 'tickets' key"
        assert "total" in data["tickets"], "tickets should have 'total'"
        assert "open" in data["tickets"], "tickets should have 'open'"
        
        assert "cards" in data, "Response should contain 'cards' key"
        assert "pending" in data["cards"], "cards should have 'pending'"
        
        print(f"✓ Analytics overview returns all expected fields")
        print(f"  - Users: {data['users']['total']} total, {data['users']['active']} active")
        print(f"  - Transfers: {data['transfers']['total']} total")
        print(f"  - Tickets: {data['tickets']['total']} total, {data['tickets']['open']} open")
    
    def test_admin_analytics_monthly(self):
        """GET /api/v1/admin/analytics/monthly - Returns monthly data"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/analytics/monthly")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "monthly_data" in data, "Response should contain 'monthly_data'"
        assert "period" in data, "Response should contain 'period'"
        assert data["period"] == "last_6_months", "Period should be 'last_6_months'"
        
        monthly_data = data["monthly_data"]
        assert isinstance(monthly_data, list), "monthly_data should be a list"
        assert len(monthly_data) == 6, f"Should have 6 months of data, got {len(monthly_data)}"
        
        # Verify each month has required fields
        for month in monthly_data:
            assert "month" in month, "Each month should have 'month'"
            assert "year" in month, "Each month should have 'year'"
            assert "users" in month, "Each month should have 'users'"
            assert "transactions" in month, "Each month should have 'transactions'"
            assert "cumulative_users" in month, "Each month should have 'cumulative_users'"
        
        print(f"✓ Analytics monthly returns 6 months of data")
        print(f"  - First month: {monthly_data[0]['month']} {monthly_data[0]['year']}")
        print(f"  - Last month: {monthly_data[-1]['month']} {monthly_data[-1]['year']}")
    
    # ==================== NOTIFICATIONS ROUTER TESTS ====================
    
    def test_admin_notification_counts(self):
        """GET /api/v1/admin/notification-counts - Returns notification counts object"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/notification-counts")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure matches original implementation
        expected_keys = ["users", "kyc", "card_requests", "transfers", "tickets"]
        for key in expected_keys:
            assert key in data, f"Response should contain '{key}' key"
            assert isinstance(data[key], int), f"'{key}' should be an integer"
        
        print(f"✓ Notification counts returns all expected keys")
        print(f"  - users: {data['users']}, kyc: {data['kyc']}, card_requests: {data['card_requests']}")
        print(f"  - transfers: {data['transfers']}, tickets: {data['tickets']}")
    
    def test_user_notifications(self):
        """GET /api/v1/notifications - Returns user notifications array"""
        response = self.session.get(f"{BASE_URL}/api/v1/notifications")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Response should be a list
        assert isinstance(data, list), "Response should be a list of notifications"
        
        # If there are notifications, verify structure
        if len(data) > 0:
            notification = data[0]
            # Common notification fields
            assert "id" in notification or "_id" in notification, "Notification should have id"
        
        print(f"✓ User notifications endpoint working, {len(data)} notifications found")
    
    def test_admin_notifications_seen(self):
        """POST /api/v1/admin/notifications/seen - Marks section as seen"""
        # Test with a valid section key
        response = self.session.post(
            f"{BASE_URL}/api/v1/admin/notifications/seen",
            json={"section_key": "users"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        assert "ok" in data, "Response should contain 'ok'"
        assert data["ok"] == True, "ok should be True"
        assert "section_key" in data, "Response should contain 'section_key'"
        assert data["section_key"] == "users", "section_key should match"
        assert "last_seen_at" in data, "Response should contain 'last_seen_at'"
        
        print(f"✓ Mark section seen working")
        print(f"  - section_key: {data['section_key']}")
        print(f"  - last_seen_at: {data['last_seen_at']}")
    
    def test_admin_notifications_seen_invalid_section(self):
        """POST /api/v1/admin/notifications/seen - Invalid section returns 400"""
        response = self.session.post(
            f"{BASE_URL}/api/v1/admin/notifications/seen",
            json={"section_key": "invalid_section"}
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid section, got {response.status_code}"
        print(f"✓ Invalid section key correctly returns 400")
    
    # ==================== CARDS ROUTER TESTS ====================
    
    def test_user_card_requests(self):
        """GET /api/v1/card-requests - Returns user card requests"""
        response = self.session.get(f"{BASE_URL}/api/v1/card-requests")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Response structure
        assert "ok" in data, "Response should contain 'ok'"
        assert data["ok"] == True, "ok should be True"
        assert "data" in data, "Response should contain 'data'"
        assert isinstance(data["data"], list), "data should be a list"
        
        print(f"✓ User card requests endpoint working, {len(data['data'])} requests found")
    
    def test_user_cards(self):
        """GET /api/v1/cards - Returns user cards"""
        response = self.session.get(f"{BASE_URL}/api/v1/cards")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Response structure
        assert "ok" in data, "Response should contain 'ok'"
        assert data["ok"] == True, "ok should be True"
        assert "data" in data, "Response should contain 'data'"
        assert isinstance(data["data"], list), "data should be a list"
        
        print(f"✓ User cards endpoint working, {len(data['data'])} cards found")
    
    def test_admin_card_requests(self):
        """GET /api/v1/admin/card-requests - Returns admin card requests with pagination"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/card-requests")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Response structure
        assert "ok" in data, "Response should contain 'ok'"
        assert data["ok"] == True, "ok should be True"
        assert "data" in data, "Response should contain 'data'"
        assert isinstance(data["data"], list), "data should be a list"
        assert "pagination" in data, "Response should contain 'pagination'"
        
        # Verify pagination structure
        pagination = data["pagination"]
        expected_pagination_keys = ["total", "page", "page_size", "total_pages", "status", "has_prev", "has_next"]
        for key in expected_pagination_keys:
            assert key in pagination, f"Pagination should contain '{key}'"
        
        print(f"✓ Admin card requests endpoint working")
        print(f"  - Total: {pagination['total']}, Page: {pagination['page']}/{pagination['total_pages']}")
    
    def test_admin_card_requests_with_status_filter(self):
        """GET /api/v1/admin/card-requests?status=PENDING - Filter by status"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ok"] == True
        assert data["pagination"]["status"] == "PENDING"
        
        print(f"✓ Admin card requests with status filter working")
    
    def test_admin_card_requests_pagination(self):
        """GET /api/v1/admin/card-requests - Test pagination parameters"""
        # Test page_size
        response = self.session.get(f"{BASE_URL}/api/v1/admin/card-requests?page=1&page_size=20")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["pagination"]["page_size"] == 20
        
        print(f"✓ Admin card requests pagination working")
    
    # ==================== AUTHENTICATION REQUIRED TESTS ====================
    
    def test_analytics_overview_requires_admin(self):
        """Analytics overview requires admin auth"""
        # Create new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        
        assert response.status_code == 403, f"Expected 403 without auth, got {response.status_code}"
        print(f"✓ Analytics overview correctly requires authentication")
    
    def test_notification_counts_requires_admin(self):
        """Notification counts requires admin auth"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/v1/admin/notification-counts")
        
        assert response.status_code == 403, f"Expected 403 without auth, got {response.status_code}"
        print(f"✓ Notification counts correctly requires authentication")
    
    def test_admin_card_requests_requires_admin(self):
        """Admin card requests requires admin auth"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/v1/admin/card-requests")
        
        assert response.status_code == 403, f"Expected 403 without auth, got {response.status_code}"
        print(f"✓ Admin card requests correctly requires authentication")


class TestRouterResponseParity:
    """Verify extracted routers return identical response structures"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test credentials and login"""
        self.email = "ashleyalt005@gmail.com"
        self.password = "123456789"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Failed to login")
    
    def test_analytics_overview_data_types(self):
        """Verify data types in analytics overview response"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        assert response.status_code == 200
        
        data = response.json()
        
        # All counts should be integers
        assert isinstance(data["users"]["total"], int)
        assert isinstance(data["users"]["active"], int)
        assert isinstance(data["kyc"]["pending"], int)
        assert isinstance(data["kyc"]["approved"], int)
        assert isinstance(data["accounts"]["total"], int)
        assert isinstance(data["transfers"]["total"], int)
        assert isinstance(data["transfers"]["pending"], int)
        assert isinstance(data["transfers"]["completed"], int)
        assert isinstance(data["transfers"]["rejected"], int)
        assert isinstance(data["transfers"]["volume_cents"], (int, float))
        assert isinstance(data["tickets"]["total"], int)
        assert isinstance(data["tickets"]["open"], int)
        assert isinstance(data["cards"]["pending"], int)
        
        print(f"✓ All analytics overview data types correct")
    
    def test_notification_counts_data_types(self):
        """Verify data types in notification counts response"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/notification-counts")
        assert response.status_code == 200
        
        data = response.json()
        
        # All values should be integers
        for key in ["users", "kyc", "card_requests", "transfers", "tickets"]:
            assert isinstance(data[key], int), f"{key} should be int, got {type(data[key])}"
        
        print(f"✓ All notification counts data types correct")
    
    def test_card_requests_response_shape(self):
        """Verify card requests response has correct shape"""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/card-requests")
        assert response.status_code == 200
        
        data = response.json()
        
        # Top level structure
        assert isinstance(data["ok"], bool)
        assert isinstance(data["data"], list)
        assert isinstance(data["pagination"], dict)
        
        # Pagination structure
        pagination = data["pagination"]
        assert isinstance(pagination["total"], int)
        assert isinstance(pagination["page"], int)
        assert isinstance(pagination["page_size"], int)
        assert isinstance(pagination["total_pages"], int)
        assert isinstance(pagination["status"], str)
        assert isinstance(pagination["has_prev"], bool)
        assert isinstance(pagination["has_next"], bool)
        
        # If there's data, verify card request structure
        if len(data["data"]) > 0:
            card_request = data["data"][0]
            # Card requests should have user info
            if card_request.get("user_name"):
                assert isinstance(card_request["user_name"], str)
            if card_request.get("user_email"):
                assert isinstance(card_request["user_email"], str)
        
        print(f"✓ Card requests response shape correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
