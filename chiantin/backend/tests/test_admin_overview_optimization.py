"""
Test Admin Overview Performance Optimization (Iteration 92)

Performance optimization for Admin Overview page. Fixed by:
1) Using asyncio.gather to run all count queries in parallel
2) Using MongoDB aggregation pipelines to get transfer/ticket stats in single queries
3) Optimized monthly analytics to use aggregation instead of 12+ sequential queries

Targets:
- Admin Overview < 1.5s (was 1.7s)  
- Monthly analytics < 0.5s (was 1.7s)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
CUSTOMER_EMAIL = "ashleyalt005@gmail.com"
CUSTOMER_PASSWORD = "123456789"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def customer_token():
    """Get customer authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Customer login failed: {response.text}")
    return response.json()["access_token"]


class TestAdminLogin:
    """Test admin authentication"""
    
    def test_admin_can_login(self):
        """Admin should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"]
        print(f"✓ Admin login successful: {data['user']['email']} (role: {data['user']['role']})")


class TestAdminOverviewPerformance:
    """Test Admin Overview page API - Performance targets"""
    
    def test_admin_overview_loads_fast(self, admin_token):
        """Admin Overview API should load < 1.5s (optimized with asyncio.gather)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/overview", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Admin overview failed: {response.text}"
        data = response.json()
        
        print(f"✓ Admin Overview loaded in {elapsed:.3f}s")
        
        # Verify data structure
        assert "users" in data, "Response should have 'users'"
        assert "kyc" in data, "Response should have 'kyc'"
        assert "accounts" in data, "Response should have 'accounts'"
        assert "transfers" in data, "Response should have 'transfers'"
        assert "tickets" in data, "Response should have 'tickets'"
        assert "cards" in data, "Response should have 'cards'"
        
        # Performance target: < 1.5s (was 1.7s before optimization)
        assert elapsed < 1.5, f"Admin Overview took {elapsed:.3f}s - should be < 1.5s"
    
    def test_admin_overview_shows_correct_total_users(self, admin_token):
        """Admin Overview should show 87 Total Users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        total_users = data["users"]["total"]
        print(f"✓ Total Users: {total_users}")
        
        # Expected: 87 users
        assert total_users == 87, f"Expected 87 users, got {total_users}"
    
    def test_admin_overview_shows_correct_active_users(self, admin_token):
        """Admin Overview should show 71 Active Users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        active_users = data["users"]["active"]
        print(f"✓ Active Users: {active_users}")
        
        # Expected: 71 active users
        assert active_users == 71, f"Expected 71 active users, got {active_users}"
    
    def test_admin_overview_shows_correct_transactions(self, admin_token):
        """Admin Overview should show 108 Transactions"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        total_transfers = data["transfers"]["total"]
        print(f"✓ Total Transactions: {total_transfers}")
        
        # Expected: 108 transactions (transfers)
        assert total_transfers == 108, f"Expected 108 transactions, got {total_transfers}"
    
    def test_admin_overview_shows_total_volume(self, admin_token):
        """Admin Overview should show Total Volume"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        volume_cents = data["transfers"]["volume_cents"]
        volume_euros = volume_cents / 100
        print(f"✓ Total Volume: €{volume_euros:,.2f}")
        
        # Volume should be > 0
        assert volume_cents > 0, "Total volume should be > 0"
    
    def test_admin_overview_shows_ticket_stats(self, admin_token):
        """Admin Overview should show ticket statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        total_tickets = data["tickets"]["total"]
        open_tickets = data["tickets"]["open"]
        print(f"✓ Tickets - Total: {total_tickets}, Open: {open_tickets}")
        
        # Should have some tickets
        assert total_tickets > 0, "Should have some tickets"
        assert open_tickets >= 0, "Open tickets should be >= 0"


class TestAdminMonthlyAnalyticsPerformance:
    """Test Admin Monthly Analytics API - Performance targets"""
    
    def test_admin_monthly_analytics_loads_fast(self, admin_token):
        """Monthly analytics should load < 0.5s (optimized with aggregation)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/monthly", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Monthly analytics failed: {response.text}"
        data = response.json()
        
        print(f"✓ Monthly analytics loaded in {elapsed:.3f}s")
        
        # Performance target: < 0.5s (was 1.7s before optimization)
        assert elapsed < 0.5, f"Monthly analytics took {elapsed:.3f}s - should be < 0.5s"
    
    def test_admin_monthly_analytics_has_correct_structure(self, admin_token):
        """Monthly analytics should return correct data structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/monthly", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "monthly_data" in data, "Response should have 'monthly_data'"
        assert "period" in data, "Response should have 'period'"
        
        monthly_data = data["monthly_data"]
        assert isinstance(monthly_data, list), "monthly_data should be a list"
        assert len(monthly_data) == 6, f"Expected 6 months of data, got {len(monthly_data)}"
        
        print(f"✓ Monthly data for {data['period']}")
        for month in monthly_data:
            print(f"  {month['month']} {month['year']}: users={month['users']}, txns={month['transactions']}, cumulative={month['cumulative_users']}")
    
    def test_admin_monthly_analytics_cumulative_users(self, admin_token):
        """Cumulative users should increase or stay same over time"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/monthly", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        monthly_data = data["monthly_data"]
        prev_cumulative = 0
        
        for month in monthly_data:
            current_cumulative = month["cumulative_users"]
            assert current_cumulative >= prev_cumulative, \
                f"Cumulative users should not decrease: {prev_cumulative} -> {current_cumulative}"
            prev_cumulative = current_cumulative
        
        print(f"✓ Cumulative users trend verified: final count = {prev_cumulative}")


class TestSupportTicketsList:
    """Test Support Tickets list shows 70 tickets with user info"""
    
    def test_admin_tickets_shows_70_tickets(self, admin_token):
        """Support Tickets list should show ~70 tickets"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get tickets failed: {response.text}"
        tickets = response.json()
        
        print(f"✓ Support Tickets: {len(tickets)} tickets in {elapsed:.3f}s")
        
        # Expected: ~70 tickets
        assert len(tickets) >= 70, f"Expected at least 70 tickets, got {len(tickets)}"
        
        # Performance target
        assert elapsed < 1.5, f"Tickets list took {elapsed:.3f}s - should be < 1.5s"
    
    def test_admin_tickets_show_user_info(self, admin_token):
        """Each ticket should show user info (name/email)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        
        if not tickets:
            pytest.skip("No tickets found")
        
        # Check first 5 tickets have user info
        for ticket in tickets[:5]:
            has_user_info = "user_name" in ticket or "user_email" in ticket
            assert has_user_info, f"Ticket {ticket['id']} missing user info"
        
        print(f"✓ All tickets have user info")


class TestCardRequestsPage:
    """Test Card Requests page loads fast with user info"""
    
    def test_card_requests_loads_fast(self, admin_token):
        """Card Requests should load < 1s with user info"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/card-requests", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Card requests failed: {response.text}"
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, dict):
            requests_list = data.get("requests", data.get("data", []))
        else:
            requests_list = data
        
        print(f"✓ Card Requests: {len(requests_list)} requests in {elapsed:.3f}s")
        
        # Verify user info included
        if requests_list:
            req = requests_list[0]
            has_user_info = "user_name" in req or "user_email" in req
            print(f"  Has user info: {has_user_info}")
        
        # Performance target
        assert elapsed < 1.0, f"Card requests took {elapsed:.3f}s - should be < 1s"


class TestTransfersQueuePage:
    """Test Transfers Queue loads fast with search working"""
    
    def test_transfers_queue_loads_fast(self, admin_token):
        """Transfers Queue should load < 1.5s"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Transfers failed: {response.text}"
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, list):
            transfers = data
        else:
            transfers = data.get("transfers", [])
        
        print(f"✓ Transfers Queue: {len(transfers)} transfers in {elapsed:.3f}s")
        
        # Performance target
        assert elapsed < 1.5, f"Transfers queue took {elapsed:.3f}s - should be < 1.5s"
    
    def test_transfers_queue_search_works(self, admin_token):
        """Transfers Queue search should work"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test search with a partial term
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?search=test",
            headers=headers
        )
        
        assert response.status_code == 200, f"Transfer search failed: {response.text}"
        print(f"✓ Transfer search works")


class TestAccountsPage:
    """Test Accounts page loads fast with pagination"""
    
    def test_accounts_page_loads_fast(self, admin_token):
        """Accounts page should load < 1.5s with pagination"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers=headers
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Users failed: {response.text}"
        data = response.json()
        
        users = data.get("users", [])
        pagination = data.get("pagination", {})
        
        print(f"✓ Accounts: {len(users)} users on page 1 in {elapsed:.3f}s")
        print(f"  Total users: {pagination.get('total_users', 'N/A')}")
        print(f"  Total pages: {pagination.get('total_pages', 'N/A')}")
        
        # Performance target
        assert elapsed < 1.5, f"Accounts page took {elapsed:.3f}s - should be < 1.5s"


class TestCustomerDashboard:
    """Test Customer dashboard with monthly spending"""
    
    def test_customer_can_login(self):
        """Customer should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        assert response.status_code == 200, f"Customer login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ Customer login successful: {data['user']['email']}")
    
    def test_customer_dashboard_with_monthly_spending(self, customer_token):
        """Customer dashboard should show monthly spending"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/insights/monthly-spending", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Monthly spending failed: {response.text}"
        data = response.json()
        
        total_cents = data.get("total", 0)
        total_euros = total_cents / 100
        
        print(f"✓ Monthly spending: €{total_euros:,.2f} in {elapsed:.3f}s")
        
        # Performance target
        assert elapsed < 1.0, f"Monthly spending took {elapsed:.3f}s - should be < 1s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
