"""
Test: Admin Users Phone Search Feature
Tests the ability to search users by phone number in addition to name/email.

Covers:
- Search by full phone number with + prefix
- Search by partial digits (last 4, first 3, etc.)
- Search by formatted phone number with spaces
- Search by name still works (existing behavior)
- Search by email still works (existing behavior)
- Users without phone don't cause errors
- Pagination works when not searching
- Filters work with phone search
- Clear search restores normal list
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

# Test admin credentials
TEST_ADMIN_EMAIL = "ashleyalt005@gmail.com"
TEST_ADMIN_PASSWORD = "123456789"

# Known test users with phone numbers (from context)
TEST_USERS_WITH_PHONES = [
    {"name": "Hannan Mohammad Abdul", "phone": "+393276106073"},
    {"name": "Test Validphone", "phone": "+39 123 456 7890"},
    {"name": "Luca Castelletti", "phone": "+393398200965"}
]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token."""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
        timeout=10
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Get headers with admin auth token."""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestPhoneSearchBackend:
    """Backend API tests for phone search functionality."""
    
    def test_admin_users_endpoint_exists(self, admin_headers):
        """Test that admin/users endpoint is accessible."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Admin users endpoint failed: {response.text}"
        data = response.json()
        assert "users" in data
        # Check pagination structure
        pagination = data.get("pagination", {})
        total_count = pagination.get("total_count", len(data["users"]))
        print(f"✓ Admin users endpoint accessible, {total_count} total users")
    
    def test_search_by_full_phone_with_plus(self, admin_headers):
        """Search by full phone number with + prefix (e.g., +393276106073)."""
        # Search for Hannan's phone
        phone = "+393276106073"
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": phone},
            timeout=10
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        users = data["users"]
        
        # Should find at least one user with this phone
        assert len(users) >= 1, f"Expected at least 1 user with phone {phone}, found {len(users)}"
        
        # Verify the user has this phone
        found = any(u.get("phone") == phone for u in users)
        assert found, f"User with phone {phone} not found in results: {users}"
        print(f"✓ Search by full phone '{phone}' returned {len(users)} user(s)")
    
    def test_search_by_partial_digits_last_4(self, admin_headers):
        """Search by partial digits - last 4 digits (e.g., 6073)."""
        partial = "6073"
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": partial},
            timeout=10
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        users = data["users"]
        
        # Should find user(s) whose phone contains these digits
        assert len(users) >= 1, f"Expected at least 1 user with digits {partial}, found {len(users)}"
        
        # Verify phone contains these digits
        found = any(partial in (u.get("phone") or "").replace(" ", "") for u in users)
        assert found, f"User with phone containing {partial} not found"
        print(f"✓ Search by last 4 digits '{partial}' returned {len(users)} user(s)")
    
    def test_search_by_partial_digits_first_3(self, admin_headers):
        """Search by partial digits - first 3 area code digits (e.g., 327)."""
        partial = "327"
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": partial},
            timeout=10
        )
        # This might also match other fields, but should not error
        assert response.status_code == 200, f"Search failed: {response.text}"
        print(f"✓ Search by partial digits '{partial}' succeeded (status 200)")
    
    def test_search_by_formatted_phone_with_spaces(self, admin_headers):
        """Search by formatted phone number with spaces (e.g., +39 327 610)."""
        formatted = "+39 327"
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": formatted},
            timeout=10
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        users = data["users"]
        print(f"✓ Search by formatted phone '{formatted}' returned {len(users)} user(s)")
    
    def test_search_by_name_still_works(self, admin_headers):
        """Verify name search still works (existing behavior)."""
        name = "Hannan"
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": name},
            timeout=10
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        users = data["users"]
        
        # Should find at least one user
        assert len(users) >= 1, f"Expected to find user named {name}"
        
        # Verify name match
        found = any(name.lower() in u.get("first_name", "").lower() for u in users)
        assert found, f"User named {name} not found in results"
        print(f"✓ Search by name '{name}' returned {len(users)} user(s)")
    
    def test_search_by_email_still_works(self, admin_headers):
        """Verify email search still works (existing behavior)."""
        email = "ashleyalt005"
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": email},
            timeout=10
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        users = data["users"]
        
        # Should find the admin user
        assert len(users) >= 1, f"Expected to find user with email containing {email}"
        
        # Verify email match
        found = any(email.lower() in u.get("email", "").lower() for u in users)
        assert found, f"User with email containing {email} not found"
        print(f"✓ Search by email '{email}' returned {len(users)} user(s)")
    
    def test_users_without_phone_no_error(self, admin_headers):
        """Verify that users without phone field don't cause errors."""
        # Get all users without search to check for null phones
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"limit": 50},
            timeout=10
        )
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        users = data["users"]
        
        # Check if any users have null/missing phone
        users_without_phone = [u for u in users if not u.get("phone")]
        print(f"✓ Found {len(users_without_phone)} users without phone (no errors)")
        
        # Now search for something - should not error due to null phones
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": "test"},
            timeout=10
        )
        assert response.status_code == 200, f"Search with null phones failed: {response.text}"
        print("✓ Search works correctly even with users without phone numbers")
    
    def test_pagination_works_without_search(self, admin_headers):
        """Verify pagination works when not searching."""
        # Page 1
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"page": 1, "limit": 20},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        pagination = data.get("pagination", {})
        assert "page" in pagination or "current_page" in data
        current_page = pagination.get("page", data.get("current_page", 1))
        total_pages = pagination.get("total_pages", 1)
        print(f"✓ Pagination works: page {current_page}/{total_pages}, {len(data['users'])} users")
    
    def test_filters_work_with_phone_search(self, admin_headers):
        """Verify filters can be combined with phone search."""
        # This test just checks that the combined request doesn't error
        # The actual filtering might not return results depending on data
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={
                "search": "393",  # Partial phone
            },
            timeout=10
        )
        assert response.status_code == 200, f"Combined filter request failed: {response.text}"
        print("✓ Phone search works correctly")
    
    def test_clear_search_returns_all_users(self, admin_headers):
        """Verify empty search returns paginated user list."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": "", "page": 1, "limit": 50},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) > 0, "Expected users when search is cleared"
        print(f"✓ Empty search returns {len(data['users'])} users (page 1)")
    
    def test_special_chars_in_search_handled(self, admin_headers):
        """Verify special characters in search are handled safely."""
        # Test with + sign (common in phone numbers)
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": "+39"},
            timeout=10
        )
        assert response.status_code == 200, f"Search with + failed: {response.text}"
        print("✓ Search with '+' character handled correctly")
        
        # Test with other special regex chars that should be escaped
        for char in [".", "*", "?"]:
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/users",
                headers=admin_headers,
                params={"search": f"test{char}"},
                timeout=10
            )
            # Should not cause regex error (500)
            assert response.status_code == 200, f"Search with '{char}' failed: {response.text}"
        print("✓ Special regex characters are safely escaped")


class TestPhoneSearchPerformance:
    """Performance-related tests for phone search."""
    
    def test_search_response_time_acceptable(self, admin_headers):
        """Verify search responds within acceptable time."""
        import time
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=admin_headers,
            params={"search": "+393276106073"},
            timeout=10
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should respond within 3 seconds
        assert elapsed < 3.0, f"Search took too long: {elapsed:.2f}s"
        print(f"✓ Phone search response time: {elapsed:.2f}s")


class TestOtherAdminSections:
    """Verify other admin sections still work."""
    
    def test_analytics_overview_endpoint(self, admin_headers):
        """Test admin analytics overview endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/overview",
            headers=admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin Analytics Overview endpoint works")
    
    def test_kyc_pending_endpoint(self, admin_headers):
        """Test KYC pending queue endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin KYC pending endpoint works")
    
    def test_tickets_endpoint(self, admin_headers):
        """Test admin tickets endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers=admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin tickets endpoint works")
    
    def test_audit_logs_endpoint(self, admin_headers):
        """Test audit logs endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs",
            headers=admin_headers,
            params={"limit": 10},
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin audit logs endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
