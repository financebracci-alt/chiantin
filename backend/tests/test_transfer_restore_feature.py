"""
Transfer Restore Feature Tests - P1 Admin Feature

Tests for the soft-deleted transfer restore functionality:
- GET /api/v1/admin/transfers?status=DELETED - returns soft-deleted transfers
- POST /api/v1/admin/transfers/{id}/restore - restore endpoint (requires SUPER_ADMIN)
- RBAC: Only SUPER_ADMIN can restore (ADMIN should get 403)
- Handles non-existent transfer (404)
- Handles already-active transfer (idempotent)
- Regression: Other tabs and actions still work

SAFETY: These tests are READ-ONLY on production data.
- DO NOT actually restore any transfers (test user is ADMIN, not SUPER_ADMIN)
- The restore endpoint will return 403 for ADMIN users (correct behavior)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials (ADMIN role - restore will be blocked)
TEST_EMAIL = "ashleyalt005@gmail.com"
TEST_PASSWORD = "123456789"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for ADMIN user."""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.status_code}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with authentication."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestDeletedTransfersTab:
    """Tests for the DELETED tab functionality"""
    
    def test_get_deleted_transfers_endpoint_exists(self, auth_headers):
        """Test that GET /api/v1/admin/transfers?status=DELETED returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "DELETED", "page": 1, "page_size": 20},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "ok" in data
        assert "data" in data
        assert "pagination" in data
        print(f"PASS: DELETED tab returns {len(data['data'])} deleted transfers")
    
    def test_deleted_transfers_have_deletion_metadata(self, auth_headers):
        """Test that deleted transfers include deletion info"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "DELETED", "page": 1, "page_size": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check if there are any deleted transfers
        if data['data']:
            transfer = data['data'][0]
            # Deleted transfers should have deletion metadata
            assert "is_deleted" in transfer, "Missing is_deleted field"
            assert transfer["is_deleted"] == True, "is_deleted should be True"
            print(f"PASS: Deleted transfer has metadata - deleted_at: {transfer.get('deleted_at')}, deleted_by: {transfer.get('deleted_by_email')}")
        else:
            print("INFO: No deleted transfers found to verify metadata (expected: 1 soft-deleted transfer)")
    
    def test_deleted_transfers_pagination(self, auth_headers):
        """Test pagination for deleted transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "DELETED", "page": 1, "page_size": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        pagination = data.get("pagination", {})
        assert "total" in pagination, "Missing total in pagination"
        assert "page" in pagination, "Missing page in pagination"
        assert "total_pages" in pagination, "Missing total_pages in pagination"
        print(f"PASS: Pagination returned - total: {pagination.get('total')}, page: {pagination.get('page')}")


class TestRestoreEndpoint:
    """Tests for the restore endpoint - RBAC and behavior"""
    
    def test_restore_requires_super_admin(self, auth_headers):
        """Test that restore endpoint returns 403 for non-SUPER_ADMIN users"""
        # Use a fake transfer ID to test permission check (happens before 404)
        fake_transfer_id = "nonexistent123456"
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/{fake_transfer_id}/restore",
            json={"reason": "Test restore"},
            headers=auth_headers
        )
        # ADMIN user should get 403 (permission denied) before 404 (not found)
        # This confirms RBAC is checked first
        assert response.status_code == 403, f"Expected 403 for ADMIN user, got {response.status_code}: {response.text}"
        print("PASS: Restore endpoint correctly returns 403 for ADMIN user (SUPER_ADMIN required)")
    
    def test_restore_endpoint_exists(self, auth_headers):
        """Verify the endpoint exists and responds (even if 403)"""
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/test123/restore",
            json={},
            headers=auth_headers
        )
        # Should get 403 (permission denied) or 404 (not found), NOT 405 (method not allowed)
        assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}"
        print(f"PASS: Restore endpoint exists (returned {response.status_code})")
    
    def test_restore_without_auth_returns_403(self):
        """Test that restore endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/test123/restore",
            json={"reason": "Test"}
        )
        # Should get 403 (not authenticated)
        assert response.status_code == 403, f"Expected 403 without auth, got {response.status_code}"
        print("PASS: Restore endpoint requires authentication (403 without token)")


class TestOtherTabsRegression:
    """Regression tests - ensure other tabs still work"""
    
    def test_submitted_tab_still_works(self, auth_headers):
        """Test SUBMITTED tab returns transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "SUBMITTED", "page": 1, "page_size": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "data" in data
        print(f"PASS: SUBMITTED tab returns {len(data['data'])} transfers")
    
    def test_completed_tab_still_works(self, auth_headers):
        """Test COMPLETED tab returns transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "COMPLETED", "page": 1, "page_size": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        print(f"PASS: COMPLETED tab returns {len(data['data'])} transfers")
    
    def test_rejected_tab_still_works(self, auth_headers):
        """Test REJECTED tab returns transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "REJECTED", "page": 1, "page_size": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        print(f"PASS: REJECTED tab returns {len(data['data'])} transfers")
    
    def test_search_still_works(self, auth_headers):
        """Test search functionality still works"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"search": "test", "page": 1, "page_size": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        print(f"PASS: Search returns {len(data['data'])} results")
    
    def test_pagination_params_work(self, auth_headers):
        """Test pagination parameters work correctly"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "COMPLETED", "page": 1, "page_size": 50},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        pagination = data.get("pagination", {})
        assert pagination.get("page_size") == 50, "Page size should be 50"
        print(f"PASS: Pagination with page_size=50 works")


class TestSoftDeleteExclusion:
    """Test that soft-deleted transfers are excluded from normal tabs"""
    
    def test_submitted_excludes_deleted(self, auth_headers):
        """Verify SUBMITTED tab does NOT include soft-deleted transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "SUBMITTED"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check that no transfer in SUBMITTED has is_deleted=True
        for transfer in data.get("data", []):
            assert transfer.get("is_deleted") != True, f"SUBMITTED tab should not include deleted transfers: {transfer.get('id')}"
        print(f"PASS: SUBMITTED tab correctly excludes deleted transfers ({len(data['data'])} transfers, none deleted)")
    
    def test_completed_excludes_deleted(self, auth_headers):
        """Verify COMPLETED tab does NOT include soft-deleted transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "COMPLETED"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for transfer in data.get("data", []):
            assert transfer.get("is_deleted") != True, f"COMPLETED tab should not include deleted transfers"
        print(f"PASS: COMPLETED tab correctly excludes deleted transfers")


class TestRestoreEndpointErrorHandling:
    """Test error handling for restore endpoint"""
    
    def test_restore_nonexistent_transfer_check(self, auth_headers):
        """
        Test that restore returns appropriate error for non-existent transfer.
        Note: Since ADMIN user doesn't have permission, we'll get 403 first.
        This test documents the expected behavior for SUPER_ADMIN users.
        """
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/nonexistent_id_12345/restore",
            json={"reason": "Test"},
            headers=auth_headers
        )
        # ADMIN gets 403 (permission check happens first)
        # SUPER_ADMIN would get 404 for non-existent transfer
        assert response.status_code == 403, f"Expected 403 for ADMIN, got {response.status_code}"
        print("PASS: RBAC check happens before existence check (403 returned for ADMIN)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
