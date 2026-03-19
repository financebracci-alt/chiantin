"""
Test Admin Notification Counts Endpoint
Tests for GET /api/v1/admin/notification-counts

This endpoint returns pending item counts for admin sidebar badges:
- kyc_pending: KYC applications with status PENDING
- transfers_pending: Transfers with status SUBMITTED
- card_requests_pending: Card requests with status PENDING
- tickets_unread: Tickets where last message is from client
- users_pending: Users with status PENDING
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Credentials from test requirements
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"


class TestAdminNotificationCounts:
    """Test suite for admin notification counts endpoint."""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get regular user authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"User login failed: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    def test_endpoint_returns_200_for_admin(self, admin_token):
        """Test that endpoint returns 200 for authenticated admin."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Endpoint returns 200 for admin")
    
    def test_endpoint_returns_all_required_fields(self, admin_token):
        """Test that response contains all required count fields."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "kyc_pending",
            "transfers_pending", 
            "card_requests_pending",
            "tickets_unread",
            "users_pending"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
            print(f"✓ Found field: {field} = {data[field]}")
        
        print("✓ All required fields present")
    
    def test_all_counts_are_integers(self, admin_token):
        """Test that all counts are integers."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        for field, value in data.items():
            assert isinstance(value, int), f"Field {field} should be int, got {type(value)}"
            print(f"✓ {field} is integer: {value}")
        
        print("✓ All counts are integers")
    
    def test_all_counts_are_non_negative(self, admin_token):
        """Test that all counts are >= 0."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        for field, value in data.items():
            assert value >= 0, f"Field {field} should be >= 0, got {value}"
            print(f"✓ {field} is non-negative: {value}")
        
        print("✓ All counts are non-negative")
    
    def test_endpoint_requires_authentication(self):
        """Test that endpoint returns 401/403 without authentication."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts"
        )
        # Should fail without auth token
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ Endpoint correctly rejects unauthenticated requests ({response.status_code})")
    
    def test_endpoint_requires_admin_role(self, user_token):
        """Test that endpoint returns 403 for non-admin users."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        # Should fail for regular user
        assert response.status_code == 403, f"Expected 403 for regular user, got {response.status_code}"
        print("✓ Endpoint correctly rejects non-admin users (403)")
    
    def test_endpoint_response_time_is_acceptable(self, admin_token):
        """Test that endpoint responds in acceptable time (<2 seconds for parallel queries)."""
        import time
        
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Response took {elapsed:.2f}s, expected <2s"
        print(f"✓ Response time acceptable: {elapsed:.3f}s")
    
    def test_endpoint_is_idempotent(self, admin_token):
        """Test that multiple calls return consistent results."""
        response1 = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        response2 = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Counts should be identical for back-to-back requests (barring race conditions)
        # Allow for minor differences due to concurrent activity
        for field in data1:
            diff = abs(data1[field] - data2[field])
            assert diff <= 1, f"Field {field} changed significantly between calls: {data1[field]} -> {data2[field]}"
        
        print("✓ Endpoint returns consistent results")
    
    def test_response_has_correct_content_type(self, admin_token):
        """Test that response has application/json content type."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, f"Expected application/json, got {content_type}"
        print(f"✓ Content-Type is correct: {content_type}")


class TestNotificationCountsDataValidation:
    """Additional data validation tests for notification counts."""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("access_token")
    
    def test_kyc_pending_count_is_realistic(self, admin_token):
        """Verify kyc_pending count is within realistic bounds."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Realistic bounds check (shouldn't be negative or unreasonably high for a single query)
        assert 0 <= data["kyc_pending"] <= 1000000, f"kyc_pending out of bounds: {data['kyc_pending']}"
        print(f"✓ kyc_pending is realistic: {data['kyc_pending']}")
    
    def test_transfers_pending_count_is_realistic(self, admin_token):
        """Verify transfers_pending count is within realistic bounds."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 0 <= data["transfers_pending"] <= 1000000, f"transfers_pending out of bounds: {data['transfers_pending']}"
        print(f"✓ transfers_pending is realistic: {data['transfers_pending']}")
    
    def test_card_requests_pending_count_is_realistic(self, admin_token):
        """Verify card_requests_pending count is within realistic bounds."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 0 <= data["card_requests_pending"] <= 1000000, f"card_requests_pending out of bounds: {data['card_requests_pending']}"
        print(f"✓ card_requests_pending is realistic: {data['card_requests_pending']}")
    
    def test_tickets_unread_count_is_realistic(self, admin_token):
        """Verify tickets_unread count is within realistic bounds."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 0 <= data["tickets_unread"] <= 1000000, f"tickets_unread out of bounds: {data['tickets_unread']}"
        print(f"✓ tickets_unread is realistic: {data['tickets_unread']}")
    
    def test_users_pending_count_is_realistic(self, admin_token):
        """Verify users_pending count is within realistic bounds."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 0 <= data["users_pending"] <= 1000000, f"users_pending out of bounds: {data['users_pending']}"
        print(f"✓ users_pending is realistic: {data['users_pending']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
