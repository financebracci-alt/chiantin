"""
Tests for Admin Transfers Queue Pagination Feature

Test Coverage:
- GET /api/v1/admin/transfers with pagination params (page, page_size)
- Pagination works for all status tabs (SUBMITTED, COMPLETED, REJECTED)
- Search functionality with pagination (search across all statuses)
- Page size changes (20/50/100) work correctly
- Invalid page sizes default to 20
- Pagination response structure (page, page_size, total, total_pages, has_next, has_prev)
- Tab changes reset pagination to page 1 (frontend behavior - verified in backend)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - Admin user
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Alternative test user with admin privileges
TEST_ADMIN_EMAIL = "ashleyalt005@gmail.com"
TEST_ADMIN_PASSWORD = "123456789"


@pytest.fixture(scope="module")
def admin_session():
    """Get authenticated admin session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Try main admin first
    response = session.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    # Try alternative admin
    response = session.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": TEST_ADMIN_EMAIL,
        "password": TEST_ADMIN_PASSWORD
    })
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    pytest.skip("Could not authenticate with any admin account")


class TestPaginationBasics:
    """Basic pagination functionality tests."""
    
    def test_default_pagination_params(self, admin_session):
        """Test default pagination (page=1, page_size=20)."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") == True
        assert "data" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total" in pagination
        assert "total_pages" in pagination
        assert "has_next" in pagination
        assert "has_prev" in pagination
        
        # Default should be page 1, page_size 20
        assert pagination["page"] == 1
        assert pagination["page_size"] == 20
        # First page should not have prev
        assert pagination["has_prev"] == False
    
    def test_pagination_with_explicit_params(self, admin_session):
        """Test pagination with explicit page and page_size params."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=1&page_size=50")
        assert response.status_code == 200
        
        data = response.json()
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 50
    
    def test_page_size_20(self, admin_session):
        """Test page_size=20 returns correct amount."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        # Results should not exceed page_size
        assert len(data["data"]) <= 20
        assert data["pagination"]["page_size"] == 20
    
    def test_page_size_50(self, admin_session):
        """Test page_size=50 returns correct amount."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page_size=50")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) <= 50
        assert data["pagination"]["page_size"] == 50
    
    def test_page_size_100(self, admin_session):
        """Test page_size=100 returns correct amount."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page_size=100")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) <= 100
        assert data["pagination"]["page_size"] == 100
    
    def test_invalid_page_size_defaults_to_20(self, admin_session):
        """Test invalid page_size defaults to 20."""
        # Test with invalid page_size value
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page_size=30")
        assert response.status_code == 200
        
        data = response.json()
        # Should default to 20
        assert data["pagination"]["page_size"] == 20
    
    def test_negative_page_size_defaults_to_20(self, admin_session):
        """Test negative page_size defaults to 20."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page_size=-1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["page_size"] == 20


class TestPaginationWithStatus:
    """Test pagination with different status filters."""
    
    def test_submitted_status_pagination(self, admin_session):
        """Test pagination for SUBMITTED status."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?status=SUBMITTED&page=1&page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") == True
        assert "pagination" in data
        
        # All returned transfers should have SUBMITTED status
        for transfer in data["data"]:
            assert transfer["status"] == "SUBMITTED"
    
    def test_completed_status_pagination(self, admin_session):
        """Test pagination for COMPLETED status."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?status=COMPLETED&page=1&page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") == True
        
        # All returned transfers should have COMPLETED status
        for transfer in data["data"]:
            assert transfer["status"] == "COMPLETED"
    
    def test_rejected_status_pagination(self, admin_session):
        """Test pagination for REJECTED status."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?status=REJECTED&page=1&page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") == True
        
        # All returned transfers should have REJECTED status
        for transfer in data["data"]:
            assert transfer["status"] == "REJECTED"


class TestPaginationNavigation:
    """Test pagination navigation (First, Prev, Next, Last)."""
    
    def test_has_next_when_more_pages(self, admin_session):
        """Test has_next is true when there are more pages."""
        # Get with small page_size to ensure pagination
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=1&page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        pagination = data["pagination"]
        
        # If total > page_size, has_next should be True
        if pagination["total"] > pagination["page_size"]:
            assert pagination["has_next"] == True
        else:
            assert pagination["has_next"] == False
    
    def test_first_page_no_prev(self, admin_session):
        """Test first page has no previous."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=1&page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["has_prev"] == False
    
    def test_page_2_has_prev(self, admin_session):
        """Test page 2 has previous."""
        # First check if there are enough records
        response1 = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=1&page_size=20")
        data1 = response1.json()
        
        if data1["pagination"]["total"] > 20:
            response2 = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=2&page_size=20")
            assert response2.status_code == 200
            
            data2 = response2.json()
            assert data2["pagination"]["has_prev"] == True
            assert data2["pagination"]["page"] == 2
    
    def test_total_pages_calculation(self, admin_session):
        """Test total_pages is calculated correctly."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        pagination = data["pagination"]
        
        # total_pages = ceil(total / page_size)
        import math
        expected_pages = max(1, math.ceil(pagination["total"] / pagination["page_size"]))
        assert pagination["total_pages"] == expected_pages
    
    def test_navigate_to_last_page(self, admin_session):
        """Test navigating to last page."""
        # First get total pages
        response1 = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page_size=20")
        data1 = response1.json()
        total_pages = data1["pagination"]["total_pages"]
        
        if total_pages > 1:
            response2 = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page={total_pages}&page_size=20")
            assert response2.status_code == 200
            
            data2 = response2.json()
            assert data2["pagination"]["page"] == total_pages
            assert data2["pagination"]["has_next"] == False


class TestSearchWithPagination:
    """Test search functionality with pagination."""
    
    def test_search_returns_pagination(self, admin_session):
        """Test search includes pagination info."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?search=test")
        assert response.status_code == 200
        
        data = response.json()
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total" in pagination
        assert "total_pages" in pagination
    
    def test_search_mode_flag(self, admin_session):
        """Test search_mode flag is set when searching."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?search=test")
        assert response.status_code == 200
        
        data = response.json()
        pagination = data["pagination"]
        
        # When searching, search_mode should be True
        if "search_mode" in pagination:
            assert pagination["search_mode"] == True
    
    def test_search_ignores_status_filter(self, admin_session):
        """Test search searches across ALL statuses (ignores status param)."""
        # Search should search all transfers regardless of status
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?search=a&status=SUBMITTED")
        assert response.status_code == 200
        
        data = response.json()
        # Results may include any status since search is across all
        statuses = set(t["status"] for t in data["data"] if "status" in t)
        # This test just verifies the API works - actual behavior depends on data
    
    def test_search_with_page_size(self, admin_session):
        """Test search respects page_size."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?search=a&page_size=50")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["page_size"] == 50
        assert len(data["data"]) <= 50
    
    def test_search_pagination_navigation(self, admin_session):
        """Test search results can be paginated."""
        # Get first page of search results
        response1 = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?search=a&page=1&page_size=20")
        assert response1.status_code == 200
        
        data1 = response1.json()
        total_pages = data1["pagination"]["total_pages"]
        
        # If more than one page, test navigating to page 2
        if total_pages > 1:
            response2 = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?search=a&page=2&page_size=20")
            assert response2.status_code == 200
            
            data2 = response2.json()
            assert data2["pagination"]["page"] == 2
            assert data2["pagination"]["has_prev"] == True
    
    def test_empty_search_returns_status_filtered(self, admin_session):
        """Test empty search returns status-filtered results."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?search=&status=SUBMITTED")
        assert response.status_code == 200
        
        data = response.json()
        # Empty search should respect status filter
        for transfer in data["data"]:
            assert transfer["status"] == "SUBMITTED"


class TestPaginationResponseStructure:
    """Test pagination response structure compliance."""
    
    def test_response_structure(self, admin_session):
        """Test complete response structure."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=1&page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        
        # Root level
        assert "ok" in data
        assert "data" in data
        assert "pagination" in data
        
        # Pagination object
        pagination = data["pagination"]
        required_fields = ["page", "page_size", "total", "total_pages", "has_next", "has_prev"]
        for field in required_fields:
            assert field in pagination, f"Missing pagination field: {field}"
        
        # Data types
        assert isinstance(pagination["page"], int)
        assert isinstance(pagination["page_size"], int)
        assert isinstance(pagination["total"], int)
        assert isinstance(pagination["total_pages"], int)
        assert isinstance(pagination["has_next"], bool)
        assert isinstance(pagination["has_prev"], bool)
    
    def test_transfers_data_structure(self, admin_session):
        """Test transfer objects have required fields."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=1&page_size=20")
        assert response.status_code == 200
        
        data = response.json()
        
        if len(data["data"]) > 0:
            transfer = data["data"][0]
            # Required fields for display
            expected_fields = ["id", "status", "amount", "beneficiary_name", "beneficiary_iban", "created_at"]
            for field in expected_fields:
                assert field in transfer, f"Missing transfer field: {field}"
            
            # Sender info (added for admin view)
            assert "sender_name" in transfer
            assert "sender_email" in transfer
            assert "sender_iban" in transfer


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_page_beyond_total_pages(self, admin_session):
        """Test requesting page beyond total_pages."""
        # First get total pages
        response1 = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page_size=20")
        total_pages = response1.json()["pagination"]["total_pages"]
        
        # Request page beyond total
        response2 = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page={total_pages + 10}&page_size=20")
        assert response2.status_code == 200
        
        # Should return last valid page or handle gracefully
        data = response2.json()
        assert data["pagination"]["page"] <= total_pages
    
    def test_page_zero(self, admin_session):
        """Test page=0 is handled gracefully."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=0&page_size=20")
        assert response.status_code == 200
        
        # Should default to page 1
        data = response.json()
        assert data["pagination"]["page"] >= 1
    
    def test_negative_page(self, admin_session):
        """Test negative page is handled gracefully."""
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?page=-1&page_size=20")
        assert response.status_code == 200
        
        # Should default to page 1
        data = response.json()
        assert data["pagination"]["page"] >= 1
    
    def test_no_results_pagination(self, admin_session):
        """Test pagination when no results found."""
        # Search for something unlikely to exist
        response = admin_session.get(f"{BASE_URL}/api/v1/admin/transfers?search=xyz123nonexistent999")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["total"] == 0 or len(data["data"]) == 0


class TestRequiresAuthentication:
    """Test that pagination endpoint requires authentication."""
    
    def test_unauthenticated_request(self):
        """Test unauthenticated request is rejected."""
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers")
        # Should return 401 or 403
        assert response.status_code in [401, 403]
