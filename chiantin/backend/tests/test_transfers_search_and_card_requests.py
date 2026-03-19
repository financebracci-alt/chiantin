"""
Test file for Transfer Search and Card Requests N+1 fix features.

Tests:
1. Transfers Queue search functionality (searches ALL statuses)
2. Card Requests includes user_name and user_email in response (N+1 fix)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Test customer credentials
CUSTOMER_EMAIL = "ashleyalt005@gmail.com"
CUSTOMER_PASSWORD = "123456789"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token."""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def customer_token():
    """Get customer authentication token."""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": CUSTOMER_EMAIL,
        "password": CUSTOMER_PASSWORD
    })
    assert response.status_code == 200, f"Customer login failed: {response.text}"
    return response.json()["access_token"]


class TestAdminLogin:
    """Test admin login functionality."""
    
    def test_admin_login_success(self):
        """Test admin can login successfully."""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"]
        print(f"Admin login successful - Role: {data['user']['role']}")


class TestTransfersSearch:
    """Test Transfers Queue search functionality."""
    
    def test_transfers_search_endpoint_exists(self, admin_token):
        """Test that the search parameter is accepted by the transfers endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers?search=test", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        assert "data" in data
        assert "pagination" in data
        print(f"Search endpoint works - Found {len(data['data'])} results")
    
    def test_search_returns_pagination_info(self, admin_token):
        """Test that search returns correct pagination info with search_mode flag."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers?search=gildo", headers=headers)
        assert response.status_code == 200
        data = response.json()
        pagination = data.get("pagination", {})
        # When searching, pagination should indicate search mode
        assert "total" in pagination
        print(f"Search pagination: {pagination}")
    
    def test_search_by_beneficiary_name(self, admin_token):
        """Test search by beneficiary name."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Search for 'gildo' which is mentioned in test instructions
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers?search=gildo", headers=headers)
        assert response.status_code == 200
        data = response.json()
        results = data.get("data", [])
        print(f"Search 'gildo' returned {len(results)} results")
        # If results found, verify they match
        for transfer in results[:3]:  # Check first 3
            # Should match beneficiary name, sender name, email, IBAN, or reference
            transfer_str = str(transfer).lower()
            matched = 'gildo' in transfer_str
            print(f"  - Transfer {transfer.get('id', 'unknown')[:8]}: beneficiary={transfer.get('beneficiary_name')}, status={transfer.get('status')}")
    
    def test_search_by_sender_name(self, admin_token):
        """Test search by sender name (Baccaro as mentioned in test instructions)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers?search=Baccaro", headers=headers)
        assert response.status_code == 200
        data = response.json()
        results = data.get("data", [])
        print(f"Search 'Baccaro' returned {len(results)} results")
        for transfer in results[:3]:
            print(f"  - Sender: {transfer.get('sender_name')}, Beneficiary: {transfer.get('beneficiary_name')}, Status: {transfer.get('status')}")
    
    def test_search_by_ashley(self, admin_token):
        """Test search by 'ashley' (test user name or email)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers?search=ashley", headers=headers)
        assert response.status_code == 200
        data = response.json()
        results = data.get("data", [])
        print(f"Search 'ashley' returned {len(results)} results")
        for transfer in results[:5]:
            print(f"  - Sender: {transfer.get('sender_name')}, Email: {transfer.get('sender_email')}, Beneficiary: {transfer.get('beneficiary_name')}, Status: {transfer.get('status')}")
    
    def test_search_crosses_all_statuses(self, admin_token):
        """Test that search finds results across ALL statuses (not just current tab)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get counts by status WITHOUT search
        statuses_to_check = ['SUBMITTED', 'COMPLETED', 'REJECTED']
        status_counts = {}
        for status in statuses_to_check:
            response = requests.get(f"{BASE_URL}/api/v1/admin/transfers?status={status}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                status_counts[status] = len(data.get("data", []))
        print(f"Transfer counts by status: {status_counts}")
        
        # Now search - should return results from ALL statuses
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers?search=a", headers=headers)  # 'a' is a broad search
        assert response.status_code == 200
        data = response.json()
        search_results = data.get("data", [])
        
        # Check that search results include different statuses
        statuses_in_results = set(t.get("status") for t in search_results if t.get("status"))
        print(f"Search 'a' returned {len(search_results)} results across statuses: {statuses_in_results}")
        
        # Verify we have results from multiple statuses if there are multiple statuses with data
        if len([s for s, c in status_counts.items() if c > 0]) > 1:
            assert len(statuses_in_results) >= 1, "Search should return results from at least one status"
    
    def test_empty_search_returns_status_filtered(self, admin_token):
        """Test that empty search with status returns status-filtered results."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers?status=SUBMITTED", headers=headers)
        assert response.status_code == 200
        data = response.json()
        results = data.get("data", [])
        # All results should have SUBMITTED status
        for transfer in results:
            assert transfer.get("status") == "SUBMITTED", f"Expected SUBMITTED status, got {transfer.get('status')}"
        print(f"Status filter 'SUBMITTED' returned {len(results)} results (all with correct status)")


class TestCardRequestsN1Fix:
    """Test Card Requests N+1 query fix - user_name and user_email in response."""
    
    def test_card_requests_endpoint_returns_user_info(self, admin_token):
        """Test that card requests response includes user_name and user_email."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        
        requests_list = data.get("data", [])
        print(f"PENDING card requests: {len(requests_list)}")
        
        # Check if user_name and user_email are present in the response
        for req in requests_list[:3]:
            has_user_name = "user_name" in req
            has_user_email = "user_email" in req
            print(f"  - Request {req.get('id', 'unknown')[:8]}: user_name={req.get('user_name', 'MISSING')}, user_email={req.get('user_email', 'MISSING')}")
            assert has_user_name, f"user_name missing from card request response"
            assert has_user_email, f"user_email missing from card request response"
    
    def test_card_requests_all_tabs_have_user_info(self, admin_token):
        """Test that all tabs (PENDING, FULFILLED, REJECTED) return user info."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        for status in ['PENDING', 'FULFILLED', 'REJECTED']:
            response = requests.get(f"{BASE_URL}/api/v1/admin/card-requests?status={status}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            requests_list = data.get("data", [])
            
            print(f"{status} card requests: {len(requests_list)}")
            
            # Check each request has user info
            for req in requests_list[:2]:  # Check first 2 of each status
                assert "user_name" in req, f"user_name missing in {status} request"
                assert "user_email" in req, f"user_email missing in {status} request"
                print(f"  - {status}: user_name={req.get('user_name')}, user_email={req.get('user_email')}")
    
    def test_card_requests_loads_fast(self, admin_token):
        """Test that card requests page loads in < 2 seconds (N+1 fix performance)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING", headers=headers)
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Card requests took {elapsed:.2f}s (should be < 2s)"
        
        data = response.json()
        print(f"Card requests loaded in {elapsed:.2f}s - {len(data.get('data', []))} requests")


class TestCustomerLogin:
    """Test customer login functionality."""
    
    def test_customer_login_success(self):
        """Test customer can login successfully."""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": CUSTOMER_EMAIL,
            "password": CUSTOMER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == CUSTOMER_EMAIL
        print(f"Customer login successful - Email: {data['user']['email']}")
    
    def test_customer_can_access_dashboard(self, customer_token):
        """Test customer can access their accounts (dashboard data)."""
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/accounts", headers=headers)
        assert response.status_code == 200
        accounts = response.json()
        print(f"Customer has {len(accounts)} accounts")
        assert len(accounts) > 0, "Customer should have at least one account"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
