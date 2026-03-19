"""
Backend API Regression Tests for P0/P2 Refactor
Tests health endpoints (extracted to routers) and admin audit logs.

This test verifies that the behavior-preserving refactors did not break any functionality:
- P0: Frontend AdminDashboard simplified to routing component (uses AdminUsersPage)
- P2: Backend server.py partially split into routers (health.py, audit.py)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "ashleyalt005@gmail.com"
ADMIN_PASSWORD = "123456789"


class TestHealthEndpoints:
    """Test health endpoints extracted to routers/health.py"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "Chiantin"
        print(f"✅ Health check: {data}")
    
    def test_db_health_endpoint(self):
        """Test /api/db-health returns database status"""
        response = requests.get(f"{BASE_URL}/api/db-health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database_name" in data
        assert "user_count" in data
        assert data["user_count"] > 0
        print(f"✅ DB Health: {data['database_name']}, {data['user_count']} users")


class TestAdminLogin:
    """Test admin authentication"""
    
    def test_admin_login(self):
        """Test admin can login successfully"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "ADMIN"
        print(f"✅ Admin login successful: {data['user']['email']}")
        return data["access_token"]


class TestAuditLogs:
    """Test audit logs endpoint extracted to routers/audit.py"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_audit_logs_endpoint(self, admin_token):
        """Test /api/v1/admin/audit-logs returns audit logs"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            log = data[0]
            assert "id" in log
            assert "action" in log
            assert "entity_type" in log
            assert "created_at" in log
            print(f"✅ Audit logs: {len(data)} entries, latest action: {log['action']}")
        else:
            print("✅ Audit logs endpoint working (no entries yet)")
    
    def test_audit_logs_filter_by_entity_type(self, admin_token):
        """Test audit logs can be filtered by entity type"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs?limit=5&entity_type=auth",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned logs should have entity_type = auth
        for log in data:
            assert log["entity_type"] == "auth"
        print(f"✅ Audit logs filter: {len(data)} auth events")


class TestAdminUsersEndpoint:
    """Test admin users endpoint (used by AdminUsersPage component)"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_get_users_paginated(self, admin_token):
        """Test /api/v1/admin/users returns paginated user list"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "pagination" in data
        assert len(data["users"]) <= 20
        assert data["pagination"]["page"] == 1
        print(f"✅ Users endpoint: {len(data['users'])} users, total: {data['pagination']['total_users']}")
    
    def test_get_users_search(self, admin_token):
        """Test users search functionality"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=hannan",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        # Search should return filtered results
        print(f"✅ Users search 'hannan': {len(data['users'])} results")
    
    def test_get_single_user_details(self, admin_token):
        """Test getting single user details"""
        # First get a user ID
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()["users"]
        if len(users) == 0:
            pytest.skip("No users found")
        
        user_id = users[0]["id"]
        
        # Get user details
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["id"] == user_id
        print(f"✅ User details: {data['user']['email']}")


class TestKYCQueue:
    """Test KYC queue endpoint (used by KYC Queue section)"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_get_pending_kyc(self, admin_token):
        """Test /api/v1/admin/kyc/pending returns pending KYC applications"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ KYC pending queue: {len(data)} applications")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
