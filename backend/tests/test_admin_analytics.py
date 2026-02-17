"""
Backend tests for Admin Analytics Dashboard fix verification.
Tests the /api/v1/admin/analytics/overview endpoint which was fixed
to provide comprehensive stats for the admin dashboard.

Fix summary: Analytics.js was calling /admin/users expecting an array,
but that endpoint returns {users: [...], pagination: {...}}.
The fix updated Analytics.js to use /admin/analytics/overview endpoint.
"""

import pytest
import requests
import os

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token."""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    return data["access_token"]


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Create authenticated session for admin."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


class TestAdminAnalyticsOverview:
    """Test the /admin/analytics/overview endpoint - the core fix."""
    
    def test_analytics_overview_returns_200(self, admin_client):
        """Test that analytics overview endpoint returns 200 OK."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ Analytics overview endpoint returns 200")
    
    def test_analytics_overview_structure(self, admin_client):
        """Test that analytics overview returns correct data structure."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        data = response.json()
        
        # Verify main keys exist
        assert "users" in data, "Missing 'users' key"
        assert "kyc" in data, "Missing 'kyc' key"
        assert "accounts" in data, "Missing 'accounts' key"
        assert "transfers" in data, "Missing 'transfers' key"
        assert "tickets" in data, "Missing 'tickets' key"
        assert "cards" in data, "Missing 'cards' key"
        
        print(f"✅ Analytics overview has correct top-level structure")
    
    def test_analytics_users_stats(self, admin_client):
        """Test users stats in analytics response."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        data = response.json()
        
        users = data["users"]
        assert "total" in users, "Missing users.total"
        assert "active" in users, "Missing users.active"
        assert isinstance(users["total"], int), "users.total should be int"
        assert isinstance(users["active"], int), "users.active should be int"
        assert users["total"] >= users["active"], "Total users should be >= active users"
        
        print(f"✅ Users stats: total={users['total']}, active={users['active']}")
    
    def test_analytics_kyc_stats(self, admin_client):
        """Test KYC stats in analytics response."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        data = response.json()
        
        kyc = data["kyc"]
        assert "pending" in kyc, "Missing kyc.pending"
        assert "approved" in kyc, "Missing kyc.approved"
        assert isinstance(kyc["pending"], int), "kyc.pending should be int"
        assert isinstance(kyc["approved"], int), "kyc.approved should be int"
        
        print(f"✅ KYC stats: pending={kyc['pending']}, approved={kyc['approved']}")
    
    def test_analytics_transfers_stats(self, admin_client):
        """Test transfers stats in analytics response (includes volume_cents)."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        data = response.json()
        
        transfers = data["transfers"]
        assert "total" in transfers, "Missing transfers.total"
        assert "pending" in transfers, "Missing transfers.pending"
        assert "completed" in transfers, "Missing transfers.completed"
        assert "rejected" in transfers, "Missing transfers.rejected"
        assert "volume_cents" in transfers, "Missing transfers.volume_cents (fix enhancement)"
        
        assert isinstance(transfers["volume_cents"], int), "volume_cents should be int"
        
        print(f"✅ Transfer stats: total={transfers['total']}, volume_cents={transfers['volume_cents']}")
    
    def test_analytics_values_not_all_zeros(self, admin_client):
        """Verify the BUG FIX - stats should NOT all be zeros."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/analytics/overview")
        data = response.json()
        
        # The original bug was all stats showing zero
        # At least users.total should be > 0 for a live system with 111 users
        assert data["users"]["total"] > 0, "BUG: Total users is 0 - stats not loading"
        
        # Expected values based on the fix verification
        assert data["users"]["total"] == 111, f"Expected 111 total users, got {data['users']['total']}"
        assert data["users"]["active"] == 85, f"Expected 85 active users, got {data['users']['active']}"
        assert data["kyc"]["pending"] == 2, f"Expected 2 pending KYC, got {data['kyc']['pending']}"
        assert data["transfers"]["total"] == 79, f"Expected 79 transfers, got {data['transfers']['total']}"
        
        print("✅ BUG FIX VERIFIED: Stats are NOT all zeros!")


class TestAdminUsersEndpoint:
    """Test /admin/users endpoint - this was the problematic endpoint."""
    
    def test_admin_users_returns_paginated_response(self, admin_client):
        """Verify /admin/users returns paginated structure (not plain array)."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/users")
        assert response.status_code == 200
        
        data = response.json()
        
        # The old code expected an array, but this endpoint returns paginated response
        assert "users" in data, "Missing 'users' key in response"
        assert "pagination" in data, "Missing 'pagination' key in response"
        assert isinstance(data["users"], list), "users should be a list"
        
        print(f"✅ /admin/users correctly returns paginated response")
    
    def test_admin_users_pagination_info(self, admin_client):
        """Test pagination info in users response."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/users?page=1&limit=50")
        data = response.json()
        
        pagination = data["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total_users" in pagination
        assert "total_pages" in pagination
        
        assert pagination["total_users"] == 111, f"Expected 111 users, got {pagination['total_users']}"
        
        print(f"✅ Users pagination: {pagination['total_users']} total, {pagination['total_pages']} pages")


class TestAdminKYCEndpoint:
    """Test /admin/kyc/pending endpoint for regression."""
    
    def test_pending_kyc_returns_list(self, admin_client):
        """Test pending KYC endpoint returns list of applications."""
        response = admin_client.get(f"{BASE_URL}/api/v1/admin/kyc/pending")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Pending KYC should return a list"
        
        # There should be 2 pending KYC (based on analytics)
        print(f"✅ Pending KYC returns {len(data)} applications")


class TestAuthEndpoints:
    """Test auth endpoints still work (no regression)."""
    
    def test_admin_login_success(self):
        """Test admin login works."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "SUPER_ADMIN"
        
        print("✅ Admin login works correctly")
    
    def test_invalid_login_rejected(self):
        """Test invalid credentials are rejected."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        
        print("✅ Invalid login correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
