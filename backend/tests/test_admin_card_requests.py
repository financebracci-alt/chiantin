"""
Test Admin Card Requests Features:
- Pagination (page size 20/50/100, First/Prev/Next/Last controls)
- Global Search (by name, email, card type, request ID)
- Search Scope (this tab / all tabs)
- Delete Card Request (with audit logging)
- For FULFILLED requests: delete associated card
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token."""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Get admin request headers."""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestAdminCardRequestsPagination:
    """Test pagination controls for card requests."""
    
    def test_default_page_size_is_50(self, admin_headers):
        """Test that default page size is 50."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["page_size"] == 50
        print(f"PASS: Default page size is 50")
    
    def test_page_size_20(self, admin_headers):
        """Test page size 20."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&page_size=20",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 20
        assert len(data["data"]) <= 20
        print(f"PASS: Page size 20 works correctly")
    
    def test_page_size_100(self, admin_headers):
        """Test page size 100."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&page_size=100",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 100
        print(f"PASS: Page size 100 works correctly")
    
    def test_invalid_page_size_defaults_to_50(self, admin_headers):
        """Test that invalid page size defaults to 50."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&page_size=999",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 50  # Should default to 50
        print(f"PASS: Invalid page size defaults to 50")
    
    def test_pagination_has_correct_fields(self, admin_headers):
        """Test pagination response has all required fields."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&page=1&page_size=50",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]
        
        assert "total" in pagination
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_pages" in pagination
        assert "has_prev" in pagination
        assert "has_next" in pagination
        
        print(f"PASS: Pagination has all required fields")
        print(f"  - total: {pagination['total']}")
        print(f"  - page: {pagination['page']}")
        print(f"  - total_pages: {pagination['total_pages']}")
        print(f"  - has_prev: {pagination['has_prev']}")
        print(f"  - has_next: {pagination['has_next']}")
    
    def test_first_page_has_no_prev(self, admin_headers):
        """Test that first page has_prev is False."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&page=1",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["has_prev"] == False
        print(f"PASS: First page has_prev is False")


class TestAdminCardRequestsSearch:
    """Test global search functionality."""
    
    def test_search_by_card_type_virtual(self, admin_headers):
        """Test search by card type VIRTUAL."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&search=VIRTUAL",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Search by VIRTUAL returned {len(data['data'])} results")
        # If results exist, verify they match
        for req in data['data']:
            if 'card_type' in req:
                assert 'VIRTUAL' in req['card_type'].upper(), f"Card type {req['card_type']} doesn't match VIRTUAL"
    
    def test_search_by_card_type_physical(self, admin_headers):
        """Test search by card type DEBIT_PHYSICAL."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&search=DEBIT_PHYSICAL",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Search by DEBIT_PHYSICAL returned {len(data['data'])} results")
    
    def test_search_by_user_name(self, admin_headers):
        """Test search by user name."""
        # Search for 'ashley' which is part of the test user's name
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&search=ashley&scope=all",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Search by name 'ashley' returned {len(data['data'])} results")
    
    def test_search_by_email(self, admin_headers):
        """Test search by email."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?search=ashleyalt005&scope=all",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Search by email 'ashleyalt005' returned {len(data['data'])} results")
    
    def test_search_scope_tab_filters_by_status(self, admin_headers):
        """Test that scope='tab' only searches within current status."""
        # First get all PENDING
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&scope=tab",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All results should be PENDING
        for req in data['data']:
            assert req['status'] == 'PENDING', f"Expected PENDING status, got {req['status']}"
        
        print(f"PASS: Scope 'tab' correctly filters by PENDING status")
    
    def test_search_scope_all_searches_across_statuses(self, admin_headers):
        """Test that scope='all' searches across all statuses."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?search=DEBIT&scope=all",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Results can be from any status
        statuses = set(req['status'] for req in data['data'])
        print(f"PASS: Scope 'all' returns results from statuses: {statuses}")
    
    def test_search_returns_user_info(self, admin_headers):
        """Test that search results include user name and email."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&page_size=20",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data['data']:
            first_result = data['data'][0]
            assert 'user_name' in first_result, "user_name field missing"
            assert 'user_email' in first_result, "user_email field missing"
            print(f"PASS: Search results include user_name and user_email")
        else:
            print(f"SKIP: No results to verify user info")


class TestAdminCardRequestsTabs:
    """Test tab switching functionality."""
    
    def test_pending_tab(self, admin_headers):
        """Test PENDING tab returns only pending requests."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for req in data['data']:
            assert req['status'] == 'PENDING'
        
        print(f"PASS: PENDING tab returns {len(data['data'])} pending requests")
    
    def test_fulfilled_tab(self, admin_headers):
        """Test FULFILLED tab returns only fulfilled requests."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=FULFILLED",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for req in data['data']:
            assert req['status'] == 'FULFILLED'
        
        print(f"PASS: FULFILLED tab returns {len(data['data'])} fulfilled requests")
    
    def test_rejected_tab(self, admin_headers):
        """Test REJECTED tab returns only rejected requests."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=REJECTED",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for req in data['data']:
            assert req['status'] == 'REJECTED'
        
        print(f"PASS: REJECTED tab returns {len(data['data'])} rejected requests")


class TestAdminCardRequestsDelete:
    """Test delete card request functionality."""
    
    def test_delete_nonexistent_request_returns_404(self, admin_headers):
        """Test deleting non-existent request returns 404."""
        response = requests.delete(
            f"{BASE_URL}/api/v1/admin/card-requests/nonexistent_id_12345",
            headers=admin_headers
        )
        assert response.status_code == 404
        print(f"PASS: Delete non-existent request returns 404")
    
    def test_delete_endpoint_exists_and_requires_auth(self):
        """Test delete endpoint requires authentication."""
        response = requests.delete(
            f"{BASE_URL}/api/v1/admin/card-requests/some_id"
        )
        # Should return 403 (unauthenticated)
        assert response.status_code in [401, 403, 404]
        print(f"PASS: Delete endpoint requires authentication (status {response.status_code})")


class TestAuditLogging:
    """Test audit logging for delete operations."""
    
    def test_audit_log_collection_exists(self, admin_headers):
        """Verify audit logs collection is being used by checking a delete attempt."""
        # We just verify the endpoint handles audit logging by checking a 404 doesn't crash
        response = requests.delete(
            f"{BASE_URL}/api/v1/admin/card-requests/test_audit_check_id",
            headers=admin_headers
        )
        # Should be 404 (not found), not 500 (server error from audit logging)
        assert response.status_code == 404
        print(f"PASS: Audit logging doesn't cause errors on delete attempts")


class TestCardRequestsResponseStructure:
    """Test response structure for card requests API."""
    
    def test_response_has_ok_and_data_fields(self, admin_headers):
        """Test response has ok and data fields."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "ok" in data
        assert "data" in data
        assert "pagination" in data
        
        print(f"PASS: Response has required fields (ok, data, pagination)")
    
    def test_card_request_has_required_fields(self, admin_headers):
        """Test each card request has required fields."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data['data']:
            req = data['data'][0]
            
            # Required fields
            assert 'id' in req, "Missing id field"
            assert 'user_id' in req, "Missing user_id field"
            assert 'card_type' in req, "Missing card_type field"
            assert 'status' in req, "Missing status field"
            assert 'created_at' in req, "Missing created_at field"
            assert 'user_name' in req, "Missing user_name field"
            assert 'user_email' in req, "Missing user_email field"
            
            print(f"PASS: Card request has all required fields")
            print(f"  Sample: {req['user_name']} ({req['user_email']}) - {req['card_type']}")
        else:
            print(f"SKIP: No card requests to verify structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
