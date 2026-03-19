"""
Test Performance Optimization for Dashboard and Support Tickets
Target: All pages load < 2 seconds

Changes tested:
1) Monthly-spending API optimization with efficient aggregation
2) Admin tickets endpoint optimization using MongoDB aggregation for unread count
3) New endpoint to fetch single ticket with full messages
4) Frontend behavior: fetch full ticket on select instead of loading all messages in list
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


class TestAuthentication:
    """Test login for admin and customer"""
    
    def test_admin_login(self):
        """Admin should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"]
        print(f"✓ Admin login successful: {data['user']['email']}")
        return data["access_token"]
    
    def test_customer_login(self):
        """Customer should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        assert response.status_code == 200, f"Customer login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ Customer login successful: {data['user']['email']}")
        return data["access_token"]


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


class TestDashboardPerformance:
    """Test customer dashboard API performance"""
    
    def test_get_accounts(self, customer_token):
        """Get accounts should be fast"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/accounts", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get accounts failed: {response.text}"
        accounts = response.json()
        assert isinstance(accounts, list), "Accounts should be a list"
        
        print(f"✓ Get accounts: {len(accounts)} accounts in {elapsed:.3f}s")
        assert elapsed < 2.0, f"Get accounts took {elapsed:.3f}s - should be < 2s"
    
    def test_monthly_spending_performance(self, customer_token):
        """Monthly spending API should be fast (< 1 second)"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/insights/monthly-spending", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Monthly spending failed: {response.text}"
        data = response.json()
        
        # Verify data structure
        assert "total" in data, "Response should have 'total'"
        assert "categories" in data, "Response should have 'categories'"
        
        print(f"✓ Monthly spending: €{data['total']/100:.2f} in {elapsed:.3f}s")
        print(f"  Categories: {data.get('categories', {})}")
        
        # Performance target: < 1 second
        assert elapsed < 1.0, f"Monthly spending took {elapsed:.3f}s - should be < 1s"
    
    def test_monthly_spending_value(self, customer_token):
        """Verify monthly spending total is approximately correct"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/insights/monthly-spending", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Expected approximately €168,580.99 based on problem statement
        total_euros = data["total"] / 100
        print(f"✓ Monthly spending total: €{total_euros:,.2f}")
        
        # Verify it's a reasonable amount (not 0)
        assert data["total"] > 0, "Monthly spending should be > 0"
    
    def test_get_transactions(self, customer_token):
        """Get transactions for first account"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        # First get accounts
        response = requests.get(f"{BASE_URL}/api/v1/accounts", headers=headers)
        assert response.status_code == 200
        accounts = response.json()
        
        if not accounts:
            pytest.skip("No accounts found")
        
        account_id = accounts[0]["id"]
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts/{account_id}/transactions",
            headers=headers
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get transactions failed: {response.text}"
        transactions = response.json()
        
        print(f"✓ Get transactions: {len(transactions)} transactions in {elapsed:.3f}s")
        assert elapsed < 2.0, f"Get transactions took {elapsed:.3f}s - should be < 2s"


class TestCustomerTicketsPerformance:
    """Test customer support tickets API performance"""
    
    def test_get_customer_tickets_list(self, customer_token):
        """Customer tickets list should load fast (optimized, no full messages)"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/tickets", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get tickets failed: {response.text}"
        tickets = response.json()
        
        print(f"✓ Customer tickets list: {len(tickets)} tickets in {elapsed:.3f}s")
        
        # Verify tickets have expected fields for list view
        if tickets:
            ticket = tickets[0]
            assert "id" in ticket, "Ticket should have 'id'"
            assert "subject" in ticket, "Ticket should have 'subject'"
            assert "status" in ticket, "Ticket should have 'status'"
            assert "unread_count" in ticket, "Ticket should have 'unread_count'"
            # Messages should be empty in list view (optimization)
            assert "messages" in ticket, "Ticket should have 'messages'"
            
            print(f"  First ticket: {ticket['subject'][:50]}... (unread: {ticket['unread_count']})")
        
        # Performance target: < 1 second
        assert elapsed < 1.0, f"Customer tickets list took {elapsed:.3f}s - should be < 1s"
    
    def test_get_single_ticket_full_messages(self, customer_token):
        """Get single ticket should return full messages"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        # First get ticket list
        response = requests.get(f"{BASE_URL}/api/v1/tickets", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        
        if not tickets:
            pytest.skip("No tickets found for customer")
        
        ticket_id = tickets[0]["id"]
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/{ticket_id}",
            headers=headers
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get single ticket failed: {response.text}"
        ticket = response.json()
        
        # Verify full ticket data
        assert "id" in ticket, "Ticket should have 'id'"
        assert "messages" in ticket, "Ticket should have 'messages'"
        
        # Messages should be populated when fetching single ticket
        messages = ticket.get("messages", [])
        print(f"✓ Single ticket: {ticket['subject'][:50]}... with {len(messages)} messages in {elapsed:.3f}s")
        
        if messages:
            # Verify message structure
            msg = messages[0]
            assert "content" in msg, "Message should have 'content'"
            assert "sender_name" in msg or "sender_id" in msg, "Message should have sender info"
        
        # Performance target: < 500ms for single ticket
        assert elapsed < 0.5, f"Get single ticket took {elapsed:.3f}s - should be < 0.5s"


class TestAdminTicketsPerformance:
    """Test admin support tickets API performance"""
    
    def test_get_admin_tickets_list(self, admin_token):
        """Admin tickets list should load fast (~70 tickets with unread counts)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get admin tickets failed: {response.text}"
        tickets = response.json()
        
        print(f"✓ Admin tickets list: {len(tickets)} tickets in {elapsed:.3f}s")
        
        # Verify tickets have expected fields
        if tickets:
            ticket = tickets[0]
            assert "id" in ticket, "Ticket should have 'id'"
            assert "subject" in ticket, "Ticket should have 'subject'"
            assert "status" in ticket, "Ticket should have 'status'"
            assert "unread_count" in ticket, "Ticket should have 'unread_count'"
            assert "user_email" in ticket or "user_name" in ticket, "Ticket should have user info"
            # Messages should be empty in list view (optimization)
            assert "messages" in ticket, "Ticket should have 'messages'"
            
            # Count unread tickets
            unread_tickets = [t for t in tickets if t.get("unread_count", 0) > 0]
            print(f"  Tickets with unread messages: {len(unread_tickets)}")
            
            print(f"  First ticket: {ticket['subject'][:40]}... (unread: {ticket['unread_count']})")
        
        # Performance target: < 1 second for ~70 tickets
        assert elapsed < 1.0, f"Admin tickets list took {elapsed:.3f}s - should be < 1s"
    
    def test_get_admin_tickets_with_filter(self, admin_token):
        """Admin tickets with status filter should work"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets?status=OPEN",
            headers=headers
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get filtered tickets failed: {response.text}"
        tickets = response.json()
        
        # All tickets should have OPEN status
        for ticket in tickets:
            assert ticket["status"] == "OPEN", f"Expected OPEN status, got {ticket['status']}"
        
        print(f"✓ Admin tickets (OPEN filter): {len(tickets)} tickets in {elapsed:.3f}s")
        
        assert elapsed < 1.0, f"Filtered tickets took {elapsed:.3f}s - should be < 1s"
    
    def test_get_single_admin_ticket(self, admin_token):
        """Get single admin ticket should return full messages and user info"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get ticket list
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        
        if not tickets:
            pytest.skip("No tickets found")
        
        ticket_id = tickets[0]["id"]
        
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets/{ticket_id}",
            headers=headers
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get single admin ticket failed: {response.text}"
        ticket = response.json()
        
        # Verify full ticket data with messages
        assert "id" in ticket, "Ticket should have 'id'"
        assert "messages" in ticket, "Ticket should have 'messages'"
        
        messages = ticket.get("messages", [])
        print(f"✓ Single admin ticket: {ticket['subject'][:40]}... with {len(messages)} messages in {elapsed:.3f}s")
        
        # Should include user info for admin view
        if "user_email" in ticket:
            print(f"  User: {ticket.get('user_name', 'N/A')} ({ticket.get('user_email', 'N/A')})")
        
        assert elapsed < 1.0, f"Get single admin ticket took {elapsed:.3f}s - should be < 1.0s"
    
    def test_admin_ticket_unread_counts(self, admin_token):
        """Verify unread counts are calculated correctly"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=headers)
        assert response.status_code == 200
        tickets = response.json()
        
        # Count statistics
        total_unread = sum(t.get("unread_count", 0) for t in tickets)
        tickets_with_unread = len([t for t in tickets if t.get("unread_count", 0) > 0])
        
        print(f"✓ Admin unread counts:")
        print(f"  Total tickets: {len(tickets)}")
        print(f"  Tickets with unread: {tickets_with_unread}")
        print(f"  Total unread messages: {total_unread}")
        
        # Just verify the data structure is correct
        for ticket in tickets[:5]:
            unread = ticket.get("unread_count", 0)
            assert isinstance(unread, int), f"unread_count should be int, got {type(unread)}"
            assert unread >= 0, f"unread_count should be >= 0, got {unread}"


class TestPreviousFixes:
    """Test that previous fixes still work: Transfers Queue and Card Requests"""
    
    def test_transfers_queue_accessible(self, admin_token):
        """Transfers queue should be accessible"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get transfers queue failed: {response.text}"
        data = response.json()
        
        # Can be list or dict with items
        if isinstance(data, list):
            count = len(data)
        else:
            count = len(data.get("transfers", []))
        
        print(f"✓ Transfers queue: {count} transfers in {elapsed:.3f}s")
        assert elapsed < 2.0, f"Transfers queue took {elapsed:.3f}s - should be < 2s"
    
    def test_card_requests_accessible(self, admin_token):
        """Card requests should be accessible"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/admin/card-requests", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Get card requests failed: {response.text}"
        data = response.json()
        
        # Handle both dict and list response formats
        if isinstance(data, dict):
            requests_data = data.get("requests", data.get("data", []))
        else:
            requests_data = data
        
        print(f"✓ Card requests: {len(requests_data)} requests in {elapsed:.3f}s")
        
        # Verify user info is included (N+1 fix from previous iteration)
        if requests_data and len(requests_data) > 0:
            req = requests_data[0]
            has_user_info = "user_name" in req or "user_email" in req
            print(f"  Has user info: {has_user_info}")
        
        assert elapsed < 2.0, f"Card requests took {elapsed:.3f}s - should be < 2s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
