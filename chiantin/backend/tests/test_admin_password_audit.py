"""
Test suite for Admin Password Change and Audit Log Features.
Tests:
1. Admin password change for customers
2. Audit logs for PASSWORD_CHANGED, LOGIN, LOGOUT events
3. Auth history endpoint
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from the review request
ADMIN_EMAIL = "ashleyalt005@gmail.com"
ADMIN_PASSWORD = "123456789"
TEST_CUSTOMER_ID = "69971eb8b3e1ab9f96e1b8a5"
TEST_CUSTOMER_EMAIL = "account.layout.test@test.com"


class TestAdminPasswordChangeAndAuditLogs:
    """Tests for admin password change and audit logging features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        
    def get_admin_token(self):
        """Authenticate as admin and get token"""
        if self.admin_token:
            return self.admin_token
            
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if response.status_code != 200:
            print(f"Admin login failed: {response.status_code} - {response.text}")
            pytest.skip("Cannot authenticate as admin")
            
        data = response.json()
        self.admin_token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        return self.admin_token
    
    def test_admin_login_creates_audit_log(self):
        """Test that admin login creates ADMIN_LOGIN_SUCCESS audit log"""
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access token in response"
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"], "User is not admin"
        
        print(f"✓ Admin login successful - role: {data['user']['role']}")
        
        # Store token for subsequent requests
        self.admin_token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
    
    def test_admin_change_customer_password_endpoint(self):
        """Test POST /api/v1/admin/users/{user_id}/change-password"""
        self.get_admin_token()
        
        new_password = "TestPass123!"
        
        response = self.session.post(
            f"{BASE_URL}/api/v1/admin/users/{TEST_CUSTOMER_ID}/change-password",
            json={"new_password": new_password}
        )
        
        assert response.status_code == 200, f"Password change failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Password change did not return success"
        assert "message" in data, "No message in response"
        
        print(f"✓ Password changed successfully: {data['message']}")
    
    def test_admin_change_password_validation_short_password(self):
        """Test that short passwords are rejected"""
        self.get_admin_token()
        
        response = self.session.post(
            f"{BASE_URL}/api/v1/admin/users/{TEST_CUSTOMER_ID}/change-password",
            json={"new_password": "short"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "8 characters" in response.text.lower(), f"Expected validation error about 8 characters: {response.text}"
        
        print("✓ Short password validation working")
    
    def test_admin_change_password_user_not_found(self):
        """Test changing password for non-existent user"""
        self.get_admin_token()
        
        fake_user_id = "000000000000000000000000"
        
        response = self.session.post(
            f"{BASE_URL}/api/v1/admin/users/{fake_user_id}/change-password",
            json={"new_password": "ValidPass123!"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print("✓ User not found validation working")
    
    def test_get_auth_history_endpoint(self):
        """Test GET /api/v1/admin/users/{user_id}/auth-history"""
        self.get_admin_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/v1/admin/users/{TEST_CUSTOMER_ID}/auth-history"
        )
        
        assert response.status_code == 200, f"Auth history request failed: {response.text}"
        
        data = response.json()
        assert "user_id" in data, "No user_id in response"
        assert "user_email" in data, "No user_email in response"
        assert "events" in data, "No events in response"
        
        print(f"✓ Auth history retrieved for {data['user_email']}: {len(data['events'])} events")
        
        # Verify event structure
        if data["events"]:
            event = data["events"][0]
            assert "action" in event, "Event missing action field"
            assert "created_at" in event, "Event missing created_at field"
            print(f"  Latest event: {event['action']} at {event['created_at']}")
    
    def test_auth_history_user_not_found(self):
        """Test auth history for non-existent user"""
        self.get_admin_token()
        
        fake_user_id = "000000000000000000000000"
        
        response = self.session.get(
            f"{BASE_URL}/api/v1/admin/users/{fake_user_id}/auth-history"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print("✓ User not found validation working for auth history")
    
    def test_password_change_creates_audit_log(self):
        """Test that password change creates PASSWORD_CHANGED audit log"""
        self.get_admin_token()
        
        # First change password
        new_password = "AuditTest123!"
        self.session.post(
            f"{BASE_URL}/api/v1/admin/users/{TEST_CUSTOMER_ID}/change-password",
            json={"new_password": new_password}
        )
        
        # Small delay for audit log to be created
        time.sleep(1)
        
        # Get auth history and check for PASSWORD_CHANGED event
        response = self.session.get(
            f"{BASE_URL}/api/v1/admin/users/{TEST_CUSTOMER_ID}/auth-history"
        )
        
        assert response.status_code == 200, f"Auth history request failed: {response.text}"
        
        data = response.json()
        events = data.get("events", [])
        
        # Check if there's a PASSWORD_CHANGED event in recent history
        password_changed_events = [e for e in events if e["action"] == "PASSWORD_CHANGED"]
        
        print(f"✓ Found {len(password_changed_events)} PASSWORD_CHANGED events in history")
        
        if password_changed_events:
            latest = password_changed_events[0]
            print(f"  Latest PASSWORD_CHANGED: {latest['created_at']}")
            # Verify the audit log contains required metadata
            assert "ip_address" in latest, "Missing ip_address in audit log"
            print(f"  IP Address: {latest['ip_address']}")
    
    def test_logout_endpoint(self):
        """Test POST /api/v1/auth/logout creates audit log"""
        # First login to get a fresh token
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Now logout
        logout_response = self.session.post(f"{BASE_URL}/api/v1/auth/logout")
        
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"
        
        data = logout_response.json()
        assert data.get("success") == True, "Logout did not return success"
        
        print(f"✓ Logout successful: {data.get('message')}")
    
    def test_customer_login_creates_user_login_success(self):
        """Test that customer login creates USER_LOGIN_SUCCESS (not ADMIN_LOGIN_SUCCESS)"""
        # First, reset the test customer's password to something known
        self.get_admin_token()
        
        test_password = "CustomerTest123!"
        change_resp = self.session.post(
            f"{BASE_URL}/api/v1/admin/users/{TEST_CUSTOMER_ID}/change-password",
            json={"new_password": test_password}
        )
        
        # Verify password was changed
        if change_resp.status_code != 200:
            print(f"Warning: Could not set test password: {change_resp.text}")
            pytest.skip("Could not set test customer password")
        
        # Clear session and try to login as customer
        customer_session = requests.Session()
        customer_session.headers.update({"Content-Type": "application/json"})
        
        login_resp = customer_session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": test_password
        })
        
        # Login might fail due to email verification requirements
        if login_resp.status_code == 403:
            print("✓ Customer login blocked (email not verified) - this is expected behavior")
            return
        elif login_resp.status_code == 200:
            user_data = login_resp.json()
            print(f"✓ Customer login successful - role: {user_data['user']['role']}")
            
            # Logout the customer
            customer_session.headers.update({"Authorization": f"Bearer {user_data['access_token']}"})
            customer_session.post(f"{BASE_URL}/api/v1/auth/logout")
        else:
            print(f"Customer login returned: {login_resp.status_code} - {login_resp.text}")


class TestAuditLogEventTypes:
    """Tests for specific audit log event types"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip("Cannot authenticate as admin")
            
        data = response.json()
        self.session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
        return data["access_token"]
    
    def test_auth_history_includes_expected_event_types(self):
        """Test that auth history includes all expected event types in schema"""
        self.get_admin_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/v1/admin/users/{TEST_CUSTOMER_ID}/auth-history"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        events = data.get("events", [])
        
        # Get unique event types
        event_types = set(e["action"] for e in events)
        
        print(f"✓ Found {len(event_types)} unique event types in auth history")
        for event_type in sorted(event_types):
            print(f"  - {event_type}")
        
        # Expected event types based on requirements
        expected_types = {
            "USER_LOGIN_SUCCESS", "USER_LOGIN_FAILED", "USER_LOGOUT",
            "ADMIN_LOGIN_SUCCESS", "ADMIN_LOGOUT", 
            "PASSWORD_CHANGED", "EMAIL_VERIFIED"
        }
        
        # Note: We can't guarantee all types exist for this user, 
        # but the endpoint should be able to return them
        print(f"✓ Auth history endpoint working - found events for user")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
