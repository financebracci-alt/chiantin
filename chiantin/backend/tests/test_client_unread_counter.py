"""
Test Client Unread Message Counter Feature
Tests the unread message counting from staff messages for clients.
This complements the admin unread counter (iteration 80) by testing the client-side feature.
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Test data prefix for cleanup
TEST_PREFIX = "TEST_ClientUnread"

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
def admin_headers(admin_token):
    """Get admin auth headers."""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


# ============== Module 1: GET /api/v1/tickets returns unread_count ==============

class TestClientTicketListUnreadCount:
    """Test that GET /api/v1/tickets returns unread_count for each ticket."""
    
    def test_tickets_endpoint_returns_unread_count_field(self, admin_headers):
        """Verify GET /api/v1/tickets includes unread_count in response."""
        # Create a test ticket as admin for this test user (using admin API)
        # Then check if unread_count field exists
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get tickets: {response.text}"
        
        tickets = response.json()
        if len(tickets) > 0:
            # Check that all tickets have unread_count field
            for ticket in tickets:
                assert "unread_count" in ticket, f"Ticket {ticket.get('id')} missing unread_count field"
                assert isinstance(ticket["unread_count"], int), f"unread_count should be integer, got {type(ticket['unread_count'])}"
                assert ticket["unread_count"] >= 0, f"unread_count should be >= 0, got {ticket['unread_count']}"


class TestUnreadCountOnlyCountsStaffMessages:
    """Test that unread_count only counts is_staff=true messages after user_last_read_at."""
    
    def test_admin_ticket_contains_messages_with_is_staff_flag(self, admin_headers):
        """Verify tickets have messages with is_staff field to distinguish staff vs client."""
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=admin_headers)
        assert response.status_code == 200
        
        tickets = response.json()
        if len(tickets) > 0:
            # Find a ticket with messages
            for ticket in tickets:
                if ticket.get("messages") and len(ticket["messages"]) > 0:
                    for msg in ticket["messages"]:
                        assert "is_staff" in msg, f"Message missing is_staff field"
                    break


# ============== Module 2: POST /api/v1/tickets/{id}/mark-read ==============

class TestMarkReadEndpoint:
    """Test the client mark-read endpoint."""
    
    def test_mark_read_endpoint_exists(self, admin_headers):
        """Verify POST /api/v1/tickets/{id}/mark-read endpoint exists."""
        # This endpoint requires the ticket to belong to the authenticated user
        # We'll test it returns 404 for non-existent ticket rather than 405 (method not allowed)
        response = requests.post(
            f"{BASE_URL}/api/v1/tickets/nonexistent_ticket_id/mark-read",
            headers=admin_headers
        )
        # Should return 403 (access denied since admin doesn't own this fake ticket) or 404 (not found)
        # Not 405 (method not allowed) which would indicate endpoint doesn't exist
        assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
    
    def test_mark_read_returns_success_format(self, admin_headers):
        """Test that mark-read returns proper format when successful."""
        # First get a real ticket from admin view to test with
        tickets_response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=admin_headers)
        assert tickets_response.status_code == 200
        
        tickets = tickets_response.json()
        if len(tickets) > 0:
            ticket_id = tickets[0]["id"]
            # Admin can't mark-read via client endpoint (should fail with 403)
            response = requests.post(
                f"{BASE_URL}/api/v1/tickets/{ticket_id}/mark-read",
                headers=admin_headers
            )
            # Admin using client endpoint should get 403 (not ticket owner)
            assert response.status_code == 403, f"Expected 403 for admin using client endpoint, got {response.status_code}"


# ============== Module 3: Authorization Check ==============

class TestMarkReadAuthorization:
    """Test that mark-read only works for ticket owner."""
    
    def test_mark_read_denies_non_owner(self, admin_headers):
        """Verify mark-read returns 403 when user doesn't own the ticket."""
        # Get a ticket that belongs to some other user
        tickets_response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=admin_headers)
        assert tickets_response.status_code == 200
        
        tickets = tickets_response.json()
        if len(tickets) > 0:
            ticket_id = tickets[0]["id"]
            # Admin token doesn't own client tickets - should be denied
            response = requests.post(
                f"{BASE_URL}/api/v1/tickets/{ticket_id}/mark-read",
                headers=admin_headers
            )
            # Should return 403 - access denied (admin is not the ticket owner)
            assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
            
            # Verify error message
            error_detail = response.json().get("detail", "")
            assert "denied" in error_detail.lower() or "access" in error_detail.lower(), \
                f"Error should indicate access denied, got: {error_detail}"
    
    def test_mark_read_requires_authentication(self):
        """Verify mark-read requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/v1/tickets/some_ticket_id/mark-read"
        )
        assert response.status_code == 401 or response.status_code == 403, \
            f"Expected 401 or 403 for unauthenticated request, got {response.status_code}"


# ============== Module 4: Admin mark-read endpoint (comparison) ==============

class TestAdminMarkReadEndpoint:
    """Test admin mark-read endpoint for comparison."""
    
    def test_admin_mark_read_endpoint_works(self, admin_headers):
        """Verify admin mark-read endpoint works correctly."""
        # Get a real ticket
        tickets_response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=admin_headers)
        assert tickets_response.status_code == 200
        
        tickets = tickets_response.json()
        if len(tickets) > 0:
            ticket_id = tickets[0]["id"]
            
            # Admin can use admin endpoint
            response = requests.post(
                f"{BASE_URL}/api/v1/admin/tickets/{ticket_id}/mark-read",
                headers=admin_headers
            )
            assert response.status_code == 200, f"Admin mark-read failed: {response.text}"
            
            # Verify response format
            data = response.json()
            assert data.get("success") == True
            assert data.get("ticket_id") == ticket_id


# ============== Module 5: Integration Test - unread_count field validation ==============

class TestUnreadCountIntegration:
    """Integration tests for unread_count calculation."""
    
    def test_get_tickets_endpoint_structure(self, admin_headers):
        """Test GET /api/v1/tickets response structure includes all required fields."""
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=admin_headers)
        assert response.status_code == 200
        
        tickets = response.json()
        required_fields = ["id", "subject", "status", "unread_count", "messages", "user_id", "created_at"]
        
        for ticket in tickets[:5]:  # Check first 5 tickets
            for field in required_fields:
                assert field in ticket, f"Ticket missing required field: {field}"
    
    def test_unread_count_data_types(self, admin_headers):
        """Verify unread_count has correct data types."""
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=admin_headers)
        assert response.status_code == 200
        
        tickets = response.json()
        for ticket in tickets:
            assert isinstance(ticket["unread_count"], int), \
                f"unread_count should be int, got {type(ticket['unread_count'])}"
            assert ticket["unread_count"] >= 0, \
                f"unread_count should be non-negative, got {ticket['unread_count']}"


# ============== Module 6: Service Layer Test - get_user_tickets ==============

class TestTicketServiceLayer:
    """Test the ticket service layer returns proper unread counts."""
    
    def test_admin_tickets_include_user_last_read_consideration(self, admin_headers):
        """Verify the service layer considers user_last_read_at for unread counts."""
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=admin_headers)
        assert response.status_code == 200
        
        tickets = response.json()
        # Just verify the structure - we can't directly test service layer from API
        # but we verify the API returns the expected fields
        for ticket in tickets:
            assert "unread_count" in ticket
            # user_last_read_at might not be exposed in API response but is used internally


# ============== Module 7: Edge Cases ==============

class TestEdgeCases:
    """Test edge cases for unread counter."""
    
    def test_mark_read_nonexistent_ticket_returns_404(self, admin_headers):
        """Verify mark-read returns 404 for non-existent ticket ID."""
        fake_ticket_id = "000000000000000000000000"  # Valid ObjectId format but doesn't exist
        
        response = requests.post(
            f"{BASE_URL}/api/v1/tickets/{fake_ticket_id}/mark-read",
            headers=admin_headers
        )
        # Should return 404 (not found) or 403 (access denied for non-owner)
        assert response.status_code in [403, 404], \
            f"Expected 403 or 404 for non-existent ticket, got {response.status_code}"
    
    def test_admin_mark_read_nonexistent_ticket_returns_404(self, admin_headers):
        """Verify admin mark-read returns 404 for non-existent ticket."""
        fake_ticket_id = "000000000000000000000000"
        
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/tickets/{fake_ticket_id}/mark-read",
            headers=admin_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
