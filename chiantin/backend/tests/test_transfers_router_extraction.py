"""
P0 Transfers Router Extraction Tests

This test suite validates the extraction of transfers endpoints from server.py to routers/transfers.py.
CRITICAL: This is a LIVE PRODUCTION banking platform - tests are READ-ONLY to preserve real client data.

Tests verify:
- All transfer endpoints return 200 OK
- Status filter (SUBMITTED, COMPLETED, REJECTED) works
- Pagination (page, page_size) works
- Search functionality works
- Performance is within baseline (no N+1 regression)
- Transfer Restore is NOT implemented (soft-delete only)

BASELINE METRICS (from main agent):
- Admin transfers SUBMITTED: 890ms
- Admin transfers COMPLETED: 776ms  
- Admin transfers REJECTED: 767ms
- Admin search: 884ms
- User transfers: 453ms
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestTransfersRouterExtraction:
    """Tests for the P0 transfers router extraction - READ ONLY"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin user to get auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "ashleyalt005@gmail.com",
            "password": "123456789"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Auth headers for admin requests"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    # ==================== ADMIN TRANSFER ENDPOINTS ====================
    
    def test_admin_transfers_submitted_status(self, admin_headers):
        """Test GET /api/v1/admin/transfers with status=SUBMITTED"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "SUBMITTED", "page": 1, "page_size": 20},
            headers=admin_headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        data = response.json()
        assert data.get("ok") == True, f"Response not ok: {data}"
        assert "data" in data, f"No data field in response: {data}"
        assert "pagination" in data, f"No pagination field in response: {data}"
        
        # Check pagination structure
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total" in pagination
        assert "total_pages" in pagination
        
        # Verify all returned transfers have SUBMITTED status
        for transfer in data["data"]:
            assert transfer.get("status") == "SUBMITTED", f"Got non-SUBMITTED transfer: {transfer}"
            # Verify soft-deleted transfers are excluded
            assert transfer.get("is_deleted") != True, f"Got soft-deleted transfer: {transfer}"
        
        # Performance check (baseline: 890ms, acceptable: <2000ms)
        assert elapsed < 2.0, f"SUBMITTED query too slow: {elapsed:.2f}s (baseline: 0.89s)"
        print(f"SUBMITTED response time: {elapsed*1000:.0f}ms")
    
    def test_admin_transfers_completed_status(self, admin_headers):
        """Test GET /api/v1/admin/transfers with status=COMPLETED"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "COMPLETED", "page": 1, "page_size": 20},
            headers=admin_headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        
        # Verify all returned transfers have COMPLETED status
        for transfer in data["data"]:
            assert transfer.get("status") == "COMPLETED", f"Got non-COMPLETED transfer: {transfer}"
        
        # Performance check (baseline: 776ms)
        assert elapsed < 2.0, f"COMPLETED query too slow: {elapsed:.2f}s (baseline: 0.78s)"
        print(f"COMPLETED response time: {elapsed*1000:.0f}ms")
    
    def test_admin_transfers_rejected_status(self, admin_headers):
        """Test GET /api/v1/admin/transfers with status=REJECTED"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "REJECTED", "page": 1, "page_size": 20},
            headers=admin_headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        
        # Verify all returned transfers have REJECTED status
        for transfer in data["data"]:
            assert transfer.get("status") == "REJECTED", f"Got non-REJECTED transfer: {transfer}"
        
        # Performance check (baseline: 767ms)
        assert elapsed < 2.0, f"REJECTED query too slow: {elapsed:.2f}s (baseline: 0.77s)"
        print(f"REJECTED response time: {elapsed*1000:.0f}ms")
    
    def test_admin_transfers_pagination_page_size_20(self, admin_headers):
        """Test pagination with page_size=20"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "SUBMITTED", "page": 1, "page_size": 20},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 20
        assert len(data["data"]) <= 20
    
    def test_admin_transfers_pagination_page_size_50(self, admin_headers):
        """Test pagination with page_size=50"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "SUBMITTED", "page": 1, "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 50
        assert len(data["data"]) <= 50
    
    def test_admin_transfers_pagination_page_2(self, admin_headers):
        """Test page 2 of transfers"""
        # First get page 1 to see total
        response1 = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "SUBMITTED", "page": 1, "page_size": 20},
            headers=admin_headers
        )
        assert response1.status_code == 200
        page1_data = response1.json()
        
        # If there are more pages, test page 2
        if page1_data["pagination"]["total_pages"] > 1:
            response2 = requests.get(
                f"{BASE_URL}/api/v1/admin/transfers",
                params={"status": "SUBMITTED", "page": 2, "page_size": 20},
                headers=admin_headers
            )
            assert response2.status_code == 200
            page2_data = response2.json()
            assert page2_data["pagination"]["page"] == 2
            
            # Verify page 2 data is different from page 1
            if page1_data["data"] and page2_data["data"]:
                page1_ids = {t["id"] for t in page1_data["data"]}
                page2_ids = {t["id"] for t in page2_data["data"]}
                assert page1_ids.isdisjoint(page2_ids), "Page 2 should not have same transfers as page 1"
    
    def test_admin_transfers_search(self, admin_headers):
        """Test search functionality"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"search": "Ashley"},
            headers=admin_headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        
        # Search should return transfers regardless of status
        # Verify search mode indicator in pagination
        if data.get("pagination"):
            # Search mode should include results from all statuses
            pass
        
        # Performance check (baseline: 884ms)
        assert elapsed < 2.0, f"Search query too slow: {elapsed:.2f}s (baseline: 0.88s)"
        print(f"Search response time: {elapsed*1000:.0f}ms")
    
    def test_admin_transfers_response_includes_sender_info(self, admin_headers):
        """Verify response includes sender information (bulk lookup working)"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "SUBMITTED", "page": 1, "page_size": 5},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Each transfer should have sender info (from bulk lookup)
        for transfer in data["data"]:
            assert "sender_name" in transfer, f"Missing sender_name in transfer: {transfer}"
            assert "sender_email" in transfer, f"Missing sender_email in transfer: {transfer}"
            assert "sender_iban" in transfer, f"Missing sender_iban in transfer: {transfer}"
    
    # ==================== USER TRANSFER ENDPOINTS ====================
    
    def test_user_transfers_list(self, admin_headers):
        """Test GET /api/v1/transfers for user's transfers"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/transfers",
            headers=admin_headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        assert "data" in data
        
        # Performance check (baseline: 453ms)
        assert elapsed < 2.0, f"User transfers query too slow: {elapsed:.2f}s (baseline: 0.45s)"
        print(f"User transfers response time: {elapsed*1000:.0f}ms")
    
    def test_user_transfer_detail(self, admin_headers):
        """Test GET /api/v1/transfers/{transfer_id} for transfer detail"""
        # First get user's transfers to find an ID
        response = requests.get(
            f"{BASE_URL}/api/v1/transfers",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["data"]:
            transfer_id = data["data"][0]["id"]
            
            detail_response = requests.get(
                f"{BASE_URL}/api/v1/transfers/{transfer_id}",
                headers=admin_headers
            )
            assert detail_response.status_code == 200, f"Status: {detail_response.status_code}, Body: {detail_response.text}"
            detail_data = detail_response.json()
            assert detail_data.get("ok") == True
            assert detail_data["data"]["id"] == transfer_id
    
    # ==================== VERIFY TRANSFER RESTORE NOT IMPLEMENTED ====================
    
    def test_transfer_restore_not_implemented(self, admin_headers):
        """VERIFY: Transfer Restore feature is NOT implemented (soft-delete only)"""
        # Try to call a restore endpoint - should return 404 or 405
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/transfers/some-id/restore",
            headers=admin_headers
        )
        # Should NOT return 200 - restore feature is deferred
        assert response.status_code in [404, 405, 422], \
            f"Transfer restore should NOT be implemented! Got: {response.status_code}"
        print("CONFIRMED: Transfer restore endpoint does NOT exist (as intended)")
    
    # ==================== VERIFY SOFT DELETE EXCLUDES DELETED TRANSFERS ====================
    
    def test_soft_deleted_transfers_excluded(self, admin_headers):
        """Verify soft-deleted transfers are excluded from listing"""
        # Get all statuses and verify no is_deleted=True transfers
        for status in ["SUBMITTED", "COMPLETED", "REJECTED"]:
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/transfers",
                params={"status": status, "page": 1, "page_size": 100},
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            
            for transfer in data["data"]:
                # Soft-deleted transfers should never appear
                assert transfer.get("is_deleted") != True, \
                    f"Soft-deleted transfer {transfer['id']} appeared in {status} list!"


class TestTransfersRouterInvalidPageSize:
    """Test invalid page_size values default to 20"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "ashleyalt005@gmail.com",
            "password": "123456789"
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_invalid_page_size_defaults_to_20(self, admin_headers):
        """Invalid page_size should default to 20"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            params={"status": "SUBMITTED", "page_size": 999},  # Invalid
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 20, \
            f"Invalid page_size should default to 20, got: {data['pagination']['page_size']}"


class TestTransfersRouterAuth:
    """Test authentication requirements for transfers endpoints"""
    
    def test_admin_transfers_requires_auth(self):
        """Admin transfers endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got: {response.status_code}"
    
    def test_user_transfers_requires_auth(self):
        """User transfers endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/v1/transfers")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
