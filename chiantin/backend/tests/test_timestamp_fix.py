"""
Test timestamp timezone fix for Audit Logs, Users, and Auth History.
This verifies that all timestamps include the 'Z' UTC suffix so JavaScript interprets them correctly.

ROOT CAUSE: MongoDB returns naive datetimes (no tzinfo). When Python calls .isoformat() on naive datetime,
it produces strings like '2026-02-23T13:45:00' without timezone suffix. JavaScript's new Date() interprets
this as LOCAL time, not UTC.

FIX: Created format_timestamp_utc() helper that adds 'Z' suffix to all timestamps.
Now timestamps are '2026-02-23T13:45:00.000Z' which JavaScript correctly interprets as UTC.
"""

import pytest
import requests
import os
from datetime import datetime

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "ashleyalt005@gmail.com"
TEST_PASSWORD = "123456789"


class TestTimestampFix:
    """Test that all API endpoints return timestamps with UTC 'Z' suffix."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get token."""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    def _is_valid_utc_timestamp(self, timestamp_str):
        """Check if timestamp string ends with 'Z' (UTC suffix)."""
        if timestamp_str is None:
            return True  # Null timestamps are valid
        return timestamp_str.endswith('Z')
    
    def _parse_utc_timestamp(self, timestamp_str):
        """Parse a UTC timestamp string and return datetime object."""
        if timestamp_str is None:
            return None
        # Remove the Z suffix and parse
        return datetime.fromisoformat(timestamp_str.rstrip('Z'))
    
    # ============== AUDIT LOGS TIMESTAMP TESTS ==============
    
    def test_audit_logs_endpoint_returns_200(self):
        """Test that audit logs endpoint is accessible."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/audit-logs?limit=10")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_audit_logs_timestamps_have_utc_suffix(self):
        """Test that all audit log timestamps have 'Z' UTC suffix."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/audit-logs?limit=50")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        logs = response.json()
        assert isinstance(logs, list), "Expected list of logs"
        
        if len(logs) == 0:
            pytest.skip("No audit logs found to test timestamps")
        
        # Check each log's created_at timestamp
        for i, log in enumerate(logs):
            created_at = log.get("created_at")
            assert self._is_valid_utc_timestamp(created_at), \
                f"Audit log {i} timestamp '{created_at}' does not have 'Z' suffix"
            
        print(f"✓ Verified {len(logs)} audit log timestamps all have 'Z' suffix")
    
    def test_audit_logs_filter_by_entity_type(self):
        """Test audit logs filtering by entity type."""
        # Test filtering by 'auth' entity type
        response = self.session.get(f"{BASE_URL}/api/v1/admin/audit-logs?limit=20&entity_type=auth")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        logs = response.json()
        for log in logs:
            assert log.get("entity_type") == "auth", f"Expected entity_type 'auth', got '{log.get('entity_type')}'"
            # Verify timestamp format
            created_at = log.get("created_at")
            assert self._is_valid_utc_timestamp(created_at), \
                f"Filtered audit log timestamp '{created_at}' does not have 'Z' suffix"
        
        print(f"✓ Filter by entity_type works, verified {len(logs)} logs")
    
    def test_audit_logs_sorted_by_time(self):
        """Test that audit logs are sorted by time (most recent first)."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/audit-logs?limit=20")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        logs = response.json()
        if len(logs) < 2:
            pytest.skip("Need at least 2 logs to test sorting")
        
        # Verify descending order (most recent first)
        for i in range(len(logs) - 1):
            current_time = self._parse_utc_timestamp(logs[i].get("created_at"))
            next_time = self._parse_utc_timestamp(logs[i + 1].get("created_at"))
            if current_time and next_time:
                assert current_time >= next_time, \
                    f"Logs not sorted: {logs[i].get('created_at')} should be >= {logs[i+1].get('created_at')}"
        
        print(f"✓ Audit logs correctly sorted by time (descending)")
    
    # ============== USERS LIST TIMESTAMP TESTS ==============
    
    def test_users_list_endpoint_returns_200(self):
        """Test that users list endpoint is accessible."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=10")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_users_list_created_at_has_utc_suffix(self):
        """Test that users list created_at timestamps have 'Z' UTC suffix."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=20")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        users = data.get("users", [])
        
        if len(users) == 0:
            pytest.skip("No users found to test timestamps")
        
        # Check each user's created_at timestamp
        for i, user in enumerate(users):
            created_at = user.get("created_at")
            assert self._is_valid_utc_timestamp(created_at), \
                f"User {i} ({user.get('email')}) timestamp '{created_at}' does not have 'Z' suffix"
        
        print(f"✓ Verified {len(users)} user created_at timestamps all have 'Z' suffix")
    
    # ============== USER DETAILS TIMESTAMP TESTS ==============
    
    def test_user_details_endpoint_returns_200(self):
        """Test that user details endpoint is accessible."""
        # First get a user ID
        response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=1")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        users = data.get("users", [])
        if len(users) == 0:
            pytest.skip("No users found")
        
        user_id = users[0]["id"]
        
        # Get user details
        response = self.session.get(f"{BASE_URL}/api/v1/admin/users/{user_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_user_details_timestamps_have_utc_suffix(self):
        """Test that user details created_at and last_login_at have 'Z' UTC suffix."""
        # First get a user ID
        response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        users = data.get("users", [])
        if len(users) == 0:
            pytest.skip("No users found")
        
        tested_count = 0
        for user in users:
            user_id = user["id"]
            
            # Get user details
            response = self.session.get(f"{BASE_URL}/api/v1/admin/users/{user_id}")
            if response.status_code != 200:
                continue
            
            user_details = response.json()
            
            # Check created_at
            created_at = user_details.get("created_at")
            assert self._is_valid_utc_timestamp(created_at), \
                f"User {user_id} created_at '{created_at}' does not have 'Z' suffix"
            
            # Check last_login_at (may be null)
            last_login_at = user_details.get("last_login_at")
            assert self._is_valid_utc_timestamp(last_login_at), \
                f"User {user_id} last_login_at '{last_login_at}' does not have 'Z' suffix"
            
            tested_count += 1
        
        assert tested_count > 0, "No users could be tested"
        print(f"✓ Verified {tested_count} user detail timestamps (created_at, last_login_at) have 'Z' suffix")
    
    # ============== AUTH HISTORY TIMESTAMP TESTS ==============
    
    def test_auth_history_endpoint_returns_200(self):
        """Test that auth history endpoint is accessible."""
        # First get a user ID
        response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=1")
        assert response.status_code == 200
        
        data = response.json()
        users = data.get("users", [])
        if len(users) == 0:
            pytest.skip("No users found")
        
        user_id = users[0]["id"]
        
        # Get auth history
        response = self.session.get(f"{BASE_URL}/api/v1/admin/users/{user_id}/auth-history?limit=10")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_auth_history_timestamps_have_utc_suffix(self):
        """Test that auth history events have 'Z' UTC suffix."""
        # First get users
        response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        users = data.get("users", [])
        if len(users) == 0:
            pytest.skip("No users found")
        
        events_tested = 0
        for user in users:
            user_id = user["id"]
            
            # Get auth history
            response = self.session.get(f"{BASE_URL}/api/v1/admin/users/{user_id}/auth-history?limit=20")
            if response.status_code != 200:
                continue
            
            history = response.json()
            events = history.get("events", [])
            
            for event in events:
                created_at = event.get("created_at")
                assert self._is_valid_utc_timestamp(created_at), \
                    f"Auth event '{event.get('action')}' timestamp '{created_at}' does not have 'Z' suffix"
                events_tested += 1
            
            if events_tested > 0:
                break  # Found events to test
        
        if events_tested == 0:
            pytest.skip("No auth history events found to test")
        
        print(f"✓ Verified {events_tested} auth history event timestamps have 'Z' suffix")
    
    # ============== REGRESSION TESTS ==============
    
    def test_admin_overview_endpoint(self):
        """Test that admin overview section still works."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/overview")
        # Overview may or may not exist, but should not crash
        assert response.status_code in [200, 404, 405], \
            f"Overview endpoint error: {response.status_code}"
    
    def test_transfers_endpoint(self):
        """Test that transfers queue still works."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/transfers?status=SUBMITTED&limit=5")
        assert response.status_code == 200, f"Transfers endpoint failed: {response.status_code}"
        print("✓ Transfers queue endpoint working")
    
    def test_cards_endpoint(self):
        """Test that card requests still work."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING&limit=5")
        assert response.status_code == 200, f"Card requests endpoint failed: {response.status_code}"
        print("✓ Card requests endpoint working")
    
    def test_support_tickets_endpoint(self):
        """Test that support tickets still work."""
        response = self.session.get(f"{BASE_URL}/api/v1/admin/tickets?limit=5")
        assert response.status_code == 200, f"Support tickets endpoint failed: {response.status_code}"
        print("✓ Support tickets endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
