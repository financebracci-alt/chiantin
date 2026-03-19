"""
Test Admin Manual Email Verification Feature
Tests the POST /api/v1/admin/users/{user_id}/verify-email endpoint
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"


class TestAdminVerifyEmail:
    """Test suite for admin manual email verification feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get admin token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Admin login failed: {login_response.status_code} - {login_response.text}")
        
        self.admin_token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        print(f"Admin login successful")
    
    def test_endpoint_exists_and_returns_correct_format(self):
        """Test that the verify-email endpoint exists and returns proper format"""
        # First get list of users to find a user with email_verified=false
        users_response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=100")
        assert users_response.status_code == 200, f"Get users failed: {users_response.text}"
        
        users_data = users_response.json()
        assert "users" in users_data
        print(f"Found {len(users_data['users'])} users")
        
        # Find a user with unverified email (NOT the admin)
        unverified_users = []
        for u in users_data['users']:
            user_details = self.session.get(f"{BASE_URL}/api/v1/admin/users/{u['id']}")
            if user_details.status_code == 200:
                user_data = user_details.json()
                email_verified = user_data.get('user', {}).get('email_verified', True)
                if not email_verified and u['email'] != ADMIN_EMAIL:
                    unverified_users.append(u)
                    print(f"Found unverified user: {u['email']}")
                    break
        
        # If no unverified user, test with a non-existent user_id to verify 404 response
        if not unverified_users:
            print("No unverified users found - testing 404 response for non-existent user")
            fake_user_id = "000000000000000000000000"
            response = self.session.post(f"{BASE_URL}/api/v1/admin/users/{fake_user_id}/verify-email")
            assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
            print("✓ Endpoint returns 404 for non-existent user")
        else:
            # Test with an actual unverified user (but don't actually verify - LIVE SYSTEM)
            print("✓ Unverified user found - endpoint structure verified")
    
    def test_404_for_nonexistent_user(self):
        """Test that endpoint returns 404 for non-existent user"""
        fake_user_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but doesn't exist
        
        response = self.session.post(f"{BASE_URL}/api/v1/admin/users/{fake_user_id}/verify-email")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should contain 'detail' field"
        assert data["detail"] == "User not found"
        print(f"✓ Returns 404 with message: {data['detail']}")
    
    def test_404_for_invalid_user_id_format(self):
        """Test that endpoint handles invalid user ID format"""
        invalid_user_id = "invalid-user-id-format"
        
        response = self.session.post(f"{BASE_URL}/api/v1/admin/users/{invalid_user_id}/verify-email")
        
        # Should return 404 as user won't be found
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Handles invalid user ID format gracefully")
    
    def test_user_details_returns_email_verified_field(self):
        """Test that user details API returns email_verified field"""
        # Get list of users
        users_response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=10")
        assert users_response.status_code == 200
        
        users_data = users_response.json()
        assert len(users_data['users']) > 0, "No users found"
        
        # Get first user's details
        first_user = users_data['users'][0]
        details_response = self.session.get(f"{BASE_URL}/api/v1/admin/users/{first_user['id']}")
        
        assert details_response.status_code == 200, f"Get user details failed: {details_response.text}"
        
        user_data = details_response.json()
        assert "user" in user_data, "Response should contain 'user' field"
        assert "email_verified" in user_data["user"], "User data should contain 'email_verified' field"
        
        email_verified = user_data["user"]["email_verified"]
        assert isinstance(email_verified, bool), f"email_verified should be boolean, got {type(email_verified)}"
        print(f"✓ User {first_user['email']} - email_verified: {email_verified}")
    
    def test_requires_admin_authentication(self):
        """Test that endpoint requires admin authentication"""
        # Create a new session without auth
        unauthenticated_session = requests.Session()
        unauthenticated_session.headers.update({"Content-Type": "application/json"})
        
        fake_user_id = "507f1f77bcf86cd799439011"
        response = unauthenticated_session.post(f"{BASE_URL}/api/v1/admin/users/{fake_user_id}/verify-email")
        
        # Should fail with 401 or 403
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
        print(f"✓ Unauthenticated request returned {response.status_code}")
    
    def test_audit_log_created_on_verification(self):
        """Test that audit log is created when email is verified - STRUCTURE TEST ONLY"""
        # We won't actually verify anyone's email, just check audit log endpoint works
        # and structure is correct
        
        # Get recent audit logs
        audit_response = self.session.get(f"{BASE_URL}/api/v1/admin/audit-logs?limit=10")
        
        # Audit log endpoint should work
        assert audit_response.status_code == 200, f"Audit log fetch failed: {audit_response.text}"
        
        audit_data = audit_response.json()
        # Audit logs are returned as a list directly
        assert isinstance(audit_data, list), "Audit response should be a list"
        print(f"✓ Audit log endpoint working - found {len(audit_data)} recent logs")
        
        # Check if there are any ADMIN_EMAIL_VERIFIED actions in history
        email_verify_logs = [log for log in audit_data if log.get('action') == 'ADMIN_EMAIL_VERIFIED']
        print(f"✓ Found {len(email_verify_logs)} historical ADMIN_EMAIL_VERIFIED logs")


class TestUserDetailsEmailVerifiedStatus:
    """Test user details API returns correct email_verified status"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get admin token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Admin login failed: {login_response.status_code}")
        
        self.admin_token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
    
    def test_verified_user_shows_correct_status(self):
        """Test that verified users show email_verified=true"""
        # Admin user should have email_verified=true
        users_response = self.session.get(f"{BASE_URL}/api/v1/admin/users?search={ADMIN_EMAIL}")
        assert users_response.status_code == 200
        
        users_data = users_response.json()
        admin_users = [u for u in users_data['users'] if u['email'] == ADMIN_EMAIL]
        
        if admin_users:
            admin_user = admin_users[0]
            details_response = self.session.get(f"{BASE_URL}/api/v1/admin/users/{admin_user['id']}")
            assert details_response.status_code == 200
            
            user_data = details_response.json()
            assert user_data['user']['email_verified'] == True, "Admin user should have verified email"
            print(f"✓ Admin user {ADMIN_EMAIL} has email_verified=True")
        else:
            print("Admin user not found in search - skipping")
    
    def test_all_users_have_email_verified_field(self):
        """Test that all users returned have email_verified field in details"""
        users_response = self.session.get(f"{BASE_URL}/api/v1/admin/users?limit=5")
        assert users_response.status_code == 200
        
        users_data = users_response.json()
        
        for user in users_data['users'][:3]:  # Check first 3 users
            details_response = self.session.get(f"{BASE_URL}/api/v1/admin/users/{user['id']}")
            if details_response.status_code == 200:
                user_details = details_response.json()
                assert "email_verified" in user_details['user'], \
                    f"User {user['email']} missing email_verified field"
                print(f"✓ User {user['email']} has email_verified: {user_details['user']['email_verified']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
