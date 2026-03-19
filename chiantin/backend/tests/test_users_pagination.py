"""
Backend API tests for Users Tab Pagination Fix
Testing the fix for the issue where users beyond #100 (like Josep #104) were not visible

Key fix: 
1) Removed 100 user limit
2) Added pagination (20, 50, 100 per page with default 50)
3) Search searches ALL users in database (not just current page)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "admin@ecommbx.io",
        "password": "Admin@123456"
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


class TestAdminUsersPagination:
    """Tests for /api/v1/admin/users endpoint with pagination"""
    
    def test_default_pagination_returns_50_users(self, admin_token):
        """Default pagination should return 50 users per page"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check paginated response structure
        assert "users" in data
        assert "pagination" in data
        
        # Verify pagination info
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["limit"] == 50
        assert pagination["total_users"] >= 100, "Should have more than 100 users to test the fix"
        assert len(data["users"]) <= 50
        
        print(f"✅ Total users: {pagination['total_users']}, Users on page: {len(data['users'])}")
    
    def test_pagination_shows_correct_total_count(self, admin_token):
        """Pagination should show correct total count (110 users)"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        pagination = response.json()["pagination"]
        
        # Verify total users is approximately 110 (may vary slightly)
        assert pagination["total_users"] >= 100, "Should have 100+ users"
        print(f"✅ Total users count: {pagination['total_users']}")
    
    def test_pagination_20_users_per_page(self, admin_token):
        """Test 20 users per page option"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pagination"]["limit"] == 20
        assert len(data["users"]) <= 20
        # With 110 users and 20 per page, should have 6 pages
        assert data["pagination"]["total_pages"] >= 5
        
        print(f"✅ 20 per page: {data['pagination']['total_pages']} pages")
    
    def test_pagination_100_users_per_page(self, admin_token):
        """Test 100 users per page option"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=100",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pagination"]["limit"] == 100
        assert len(data["users"]) <= 100
        # With 110 users and 100 per page, should have 2 pages
        assert data["pagination"]["total_pages"] == 2
        
        print(f"✅ 100 per page: {data['pagination']['total_pages']} pages")
    
    def test_page_navigation_page_2(self, admin_token):
        """Test navigating to page 2"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=2&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        pagination = response.json()["pagination"]
        
        assert pagination["page"] == 2
        assert pagination["has_prev"] == True
        assert pagination["has_next"] == True  # With 110 users, page 2 should have next
        
        print("✅ Page 2 navigation working")
    
    def test_page_navigation_last_page(self, admin_token):
        """Test navigating to last page"""
        # First get total pages
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        total_pages = response.json()["pagination"]["total_pages"]
        
        # Navigate to last page
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page={total_pages}&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        pagination = response.json()["pagination"]
        
        assert pagination["page"] == total_pages
        assert pagination["has_prev"] == True
        assert pagination["has_next"] == False  # Last page should not have next
        
        print(f"✅ Last page ({total_pages}) navigation working")


class TestSearchFunctionality:
    """Tests for search functionality - KEY FIX VERIFICATION"""
    
    def test_search_finds_josep_key_test(self, admin_token):
        """
        KEY TEST: Search for 'josep' should find Josep De Las Heras Descarrega
        This user was previously hidden because he was user #104 but only first 100 were shown
        """
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=josep",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find Josep
        users = data["users"]
        assert len(users) >= 1, "Should find at least one user named Josep"
        
        # Verify Josep De Las Heras Descarrega is in results
        josep_found = any(
            "Josep" in user.get("first_name", "") and 
            "De Las Heras" in user.get("last_name", "")
            for user in users
        )
        
        assert josep_found, "Josep De Las Heras Descarrega should be found in search results"
        
        # Verify search returns correct pagination info
        assert data["pagination"]["total_users"] >= 1
        
        print("✅ KEY TEST PASSED: Josep De Las Heras Descarrega found in search!")
    
    def test_search_returns_all_matching_users(self, admin_token):
        """Search should return ALL matching users regardless of page"""
        # Search for a common pattern
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # When searching, pagination shows found users
        assert data["pagination"]["total_users"] == len(data["users"]), \
            "Search should return all matching users (not paginated)"
        
        print(f"✅ Search returns all matching users: {len(data['users'])} found")
    
    def test_search_by_email(self, admin_token):
        """Search should work with email addresses"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=jdlh1010",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find Josep by email
        assert len(data["users"]) >= 1
        assert any("jdlh1010" in user.get("email", "") for user in data["users"])
        
        print("✅ Search by email working")
    
    def test_empty_search_returns_paginated_view(self, admin_token):
        """Empty search should return paginated view"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search=&page=1&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return paginated results
        assert data["pagination"]["total_pages"] > 1
        
        print("✅ Empty search returns paginated view")


class TestFiltersStillWork:
    """Test that other filters still work with pagination"""
    
    def test_status_filter(self, admin_token):
        """Status filter should work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        users = response.json()["users"]
        
        # Check that status is present in user data
        assert all("status" in user for user in users)
        
        print("✅ Status data available for filtering")
    
    def test_role_filter(self, admin_token):
        """Role filter should work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        users = response.json()["users"]
        
        # Check that role is present in user data
        assert all("role" in user for user in users)
        
        print("✅ Role data available for filtering")
    
    def test_tax_hold_filter(self, admin_token):
        """Tax hold filter should work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        users = response.json()["users"]
        
        # Check that has_tax_hold is present in user data
        assert all("has_tax_hold" in user for user in users)
        
        print("✅ Tax hold data available for filtering")
    
    def test_notes_filter(self, admin_token):
        """Notes filter should work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        users = response.json()["users"]
        
        # Check that admin_notes is present in user data
        assert all("admin_notes" in user for user in users)
        
        print("✅ Admin notes data available for filtering")


class TestUserDetailsAccess:
    """Test that individual user details work"""
    
    def test_get_user_details(self, admin_token):
        """Should be able to get individual user details"""
        # First get a user ID
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        user_id = response.json()["users"][0]["id"]
        
        # Get user details
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user" in data
        assert data["user"]["id"] == user_id
        
        print(f"✅ User details accessible for user ID: {user_id}")


class TestAccountsStillWork:
    """Test that Accounts tab still works"""
    
    def test_accounts_with_users_endpoint(self, admin_token):
        """Accounts with users endpoint should work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        accounts = response.json()
        
        # Should have accounts
        assert len(accounts) > 0
        
        # Check account structure
        if len(accounts) > 0:
            account = accounts[0]
            assert "iban" in account or "account_number" in account
        
        print(f"✅ Accounts endpoint returns {len(accounts)} accounts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
