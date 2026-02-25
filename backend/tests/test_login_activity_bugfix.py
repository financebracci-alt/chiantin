"""
Test Login Activity Bugfix - P0 HOTFIX
Tests for User Details > Login Activity panel showing entries

Root Cause: After refactor, login events stored in 'audit_logs' collection
but auth-history endpoint was querying 'auth_events' collection.

Fix: Updated endpoint to query audit_logs with auth-related action filters.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLoginActivityBugfix:
    """Tests for the Login Activity (auth-history) bugfix"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@ecommbx.io", "password": "Admin@123456"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, admin_token):
        """Get auth headers with admin token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_auth_history_endpoint_returns_events(self, auth_headers):
        """Test that auth-history endpoint returns login events for test user"""
        # Test user ID: 6971fed2ad8ed4d326f04041 (ashleyalt005@gmail.com)
        user_id = "6971fed2ad8ed4d326f04041"
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/auth-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Auth history request failed: {response.text}"
        
        data = response.json()
        assert "events" in data, "Response should contain 'events' key"
        
        events = data["events"]
        assert len(events) > 0, "Auth history should return events (not empty)"
        print(f"SUCCESS: Found {len(events)} authentication events")
    
    def test_auth_history_events_have_correct_fields(self, auth_headers):
        """Test that events contain all required fields (IP, timestamp, action, source)"""
        user_id = "6971fed2ad8ed4d326f04041"
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/auth-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        events = response.json()["events"]
        assert len(events) > 0, "Should have events to validate"
        
        # Check first event has all required fields
        first_event = events[0]
        required_fields = ["id", "action", "description", "ip_address", "created_at"]
        for field in required_fields:
            assert field in first_event, f"Event should have '{field}' field"
        
        # Check optional but expected fields
        assert "source" in first_event, "Event should have 'source' field"
        assert "actor_email" in first_event, "Event should have 'actor_email' field"
        
        print(f"SUCCESS: Event has all required fields: {list(first_event.keys())}")
    
    def test_auth_history_contains_login_events(self, auth_headers):
        """Test that auth history contains USER_LOGIN_SUCCESS events"""
        user_id = "6971fed2ad8ed4d326f04041"
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/auth-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        events = response.json()["events"]
        
        # Check for login success events
        login_events = [e for e in events if "LOGIN_SUCCESS" in e["action"]]
        assert len(login_events) > 0, "Should have LOGIN_SUCCESS events"
        print(f"SUCCESS: Found {len(login_events)} login success events")
    
    def test_auth_history_user_specific(self, auth_headers):
        """Test that auth history only shows events for the specific user"""
        user_id = "6971fed2ad8ed4d326f04041"
        user_email = "ashleyalt005@gmail.com"
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/auth-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        events = response.json()["events"]
        
        # All events should be related to the user
        for event in events:
            actor_email = event.get("actor_email")
            if actor_email:
                # Events should be from this user or about this user
                # (actor_email matches or it's an action on their account)
                assert user_email in event.get("description", "") or actor_email == user_email, \
                    f"Event should be related to user: {event}"
        
        print("SUCCESS: All events are user-specific")
    
    def test_auth_history_not_showing_other_users_events(self, auth_headers):
        """Test that auth history doesn't show unrelated users' events"""
        user_id = "6971fed2ad8ed4d326f04041"
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/auth-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        events = response.json()["events"]
        
        # Should not see random other user emails in actor_email
        # (except admin acting on this user's account which is allowed)
        for event in events:
            actor = event.get("actor_email", "")
            if actor and "admin@ecommbx.io" not in actor:
                # Non-admin actors should only be the user themselves
                assert "ashleyalt005@gmail.com" in actor or "ashleyalt005" in event.get("description", ""), \
                    f"Event actor should be the user or admin, got: {actor}"
        
        print("SUCCESS: No unrelated user events")
    
    def test_audit_logs_still_working(self, auth_headers):
        """Regression test: Audit Logs page should still work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Audit logs request failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Audit logs should return a list"
        assert len(data) > 0, "Should have audit log entries"
        
        # Check first entry has expected fields
        first_log = data[0]
        assert "action" in first_log
        assert "created_at" in first_log
        
        print(f"SUCCESS: Audit logs working, got {len(data)} entries")
    
    def test_admin_login_creates_audit_log(self, auth_headers):
        """Test that admin login events appear in audit logs"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs?action=ADMIN_LOGIN_SUCCESS&limit=5",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Should have admin login events in audit logs"
        
        # Verify the events are for admin
        for log in data:
            assert "admin@ecommbx.io" in log.get("performed_by_email", "") or \
                   "admin@ecommbx.io" in log.get("description", ""), \
                   "Admin login event should reference admin email"
        
        print(f"SUCCESS: Admin login events in audit logs: {len(data)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
