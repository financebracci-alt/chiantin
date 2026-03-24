"""
Pre-Deployment Comprehensive Test Suite
Tests all critical banking features before production deployment
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://bank-staging.preview.emergentagent.com"

# Test credentials
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"


class TestUserAuthentication:
    """Test user authentication flows"""
    
    def test_user_login(self):
        """Test that test user can login"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        print(f"User Login Status: {response.status_code}")
        assert response.status_code == 200, f"User login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"User Login: SUCCESS - token received")
        return data["access_token"]
    
    def test_user_me_endpoint(self):
        """Test /users/me endpoint with user auth"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Get user info
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
        print(f"User /me Status: {response.status_code}")
        assert response.status_code == 200, f"Get user info failed: {response.text}"
        data = response.json()
        assert data.get("email") == TEST_USER_EMAIL
        print(f"User Info: {data.get('first_name')} {data.get('last_name')}")


class TestUserDashboard:
    """Test user dashboard features"""
    
    @pytest.fixture
    def user_token(self):
        """Get user auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_user_accounts(self, user_token):
        """Test user can get their accounts"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/accounts", headers=headers)
        print(f"User Accounts Status: {response.status_code}")
        assert response.status_code == 200, f"Get accounts failed: {response.text}"
        accounts = response.json()
        assert isinstance(accounts, list), "Accounts should be a list"
        print(f"User has {len(accounts)} account(s)")
        if accounts:
            print(f"First account IBAN: {accounts[0].get('iban', 'N/A')}")
            return accounts[0].get("id")
    
    def test_user_transactions(self, user_token):
        """Test user can get their transactions"""
        headers = {"Authorization": f"Bearer {user_token}"}
        # First get accounts
        acc_response = requests.get(f"{BASE_URL}/api/v1/accounts", headers=headers)
        assert acc_response.status_code == 200
        accounts = acc_response.json()
        if not accounts:
            pytest.skip("User has no accounts")
        
        account_id = accounts[0].get("id")
        response = requests.get(f"{BASE_URL}/api/v1/accounts/{account_id}/transactions", headers=headers)
        print(f"User Transactions Status: {response.status_code}")
        assert response.status_code == 200, f"Get transactions failed: {response.text}"
        transactions = response.json()
        print(f"User has {len(transactions)} transaction(s)")
    
    def test_user_kyc_status(self, user_token):
        """Test user can get their KYC status"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/kyc/application", headers=headers)
        print(f"User KYC Status: {response.status_code}")
        assert response.status_code in [200, 404], f"Get KYC failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            print(f"KYC Status: {data.get('status', 'N/A')}")


class TestUserSupport:
    """Test user support ticket features"""
    
    @pytest.fixture
    def user_token(self):
        """Get user auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_user_tickets(self, user_token):
        """Test user can view their support tickets"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/tickets", headers=headers)
        print(f"User Tickets Status: {response.status_code}")
        assert response.status_code == 200, f"Get tickets failed: {response.text}"
        tickets = response.json()
        print(f"User has {len(tickets)} ticket(s)")


class TestAdminAuthentication:
    """Test admin authentication flows"""
    
    def test_admin_login(self):
        """Test that admin can login"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        print(f"Admin Login Status: {response.status_code}")
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Admin Login: SUCCESS")
        return data["access_token"]


class TestAdminDashboard:
    """Test admin dashboard features"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_stats(self, admin_token):
        """Test admin can get dashboard stats"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/stats", headers=headers)
        print(f"Admin Stats Status: {response.status_code}")
        assert response.status_code == 200, f"Get admin stats failed: {response.text}"
        data = response.json()
        print(f"Total Users: {data.get('total_users', 'N/A')}")
    
    def test_admin_users_list(self, admin_token):
        """Test admin can list users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/users?page=1&limit=20", headers=headers)
        print(f"Admin Users List Status: {response.status_code}")
        assert response.status_code == 200, f"Get admin users failed: {response.text}"
        data = response.json()
        # Check for pagination structure
        if "users" in data:
            print(f"Users on page: {len(data['users'])}")
            print(f"Total users: {data.get('pagination', {}).get('total_users', 'N/A')}")


class TestAdminSupportTickets:
    """Test admin support ticket features"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_tickets_list(self, admin_token):
        """Test admin can list all tickets"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=headers)
        print(f"Admin Tickets List Status: {response.status_code}")
        assert response.status_code == 200, f"Get admin tickets failed: {response.text}"
        tickets = response.json()
        print(f"Total tickets: {len(tickets)}")


class TestAdminKYCQueue:
    """Test admin KYC queue features"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_kyc_queue(self, admin_token):
        """Test admin can view KYC queue"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/kyc", headers=headers)
        print(f"Admin KYC Queue Status: {response.status_code}")
        assert response.status_code == 200, f"Get KYC queue failed: {response.text}"


class TestAdminTransfersQueue:
    """Test admin transfers queue features"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_transfers_queue(self, admin_token):
        """Test admin can view transfers queue"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/transfers", headers=headers)
        print(f"Admin Transfers Queue Status: {response.status_code}")
        assert response.status_code == 200, f"Get transfers queue failed: {response.text}"


class TestAdminLedger:
    """Test admin ledger/accounts features"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_ledger_stats(self, admin_token):
        """Test admin can view ledger stats"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/ledger/stats", headers=headers)
        print(f"Admin Ledger Stats Status: {response.status_code}")
        # Ledger stats may not exist, so we accept 200 or 404
        assert response.status_code in [200, 404], f"Get ledger stats failed: {response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
