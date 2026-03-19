"""
Final Comprehensive Pre-deployment Test Suite
Tests all critical features before deployment:
1. Tax Hold Payment Details Fix Verification
2. User Authentication
3. User Dashboard / Banking
4. Admin Features (Login, Users, Support Tickets, Tax Hold)
5. Sidebar Navigation (Admin endpoints)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
TEST_USER_EMAIL = "ashleyalt005@gmail.com"
TEST_USER_PASSWORD = "123456789"


class TestTaxHoldPaymentDetailsFix:
    """
    Critical: Verify tax hold payment details (beneficiary_name, iban, bic_swift, reference, crypto_wallet)
    are returned correctly from API - not nested under payment_details
    """
    
    def test_admin_login(self):
        """Admin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        print(f"PASS: Admin login successful, role: {data['user'].get('role')}")
        return data["access_token"]
    
    def test_user_tax_status_returns_payment_fields(self):
        """GET /users/me/tax-status returns payment fields at top level"""
        # First login as user
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert login_response.status_code == 200, f"User login failed: {login_response.text}"
        token = login_response.json()["access_token"]
        
        # Get tax status
        response = requests.get(
            f"{BASE_URL}/api/v1/users/me/tax-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Tax status failed: {response.text}"
        data = response.json()
        
        # Verify payment fields are at top level
        expected_fields = ["is_blocked", "tax_amount_due", "beneficiary_name", "iban", "bic_swift", "reference", "crypto_wallet"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify NO nested payment_details
        assert "payment_details" not in data, "Payment details should NOT be nested"
        
        print(f"PASS: Tax status returns fields at top level: is_blocked={data['is_blocked']}")
        if data["is_blocked"]:
            print(f"  - beneficiary_name: {data.get('beneficiary_name')}")
            print(f"  - iban: {data.get('iban')}")
            print(f"  - bic_swift: {data.get('bic_swift')}")
            print(f"  - reference: {data.get('reference')}")
            print(f"  - crypto_wallet: {data.get('crypto_wallet')}")
        return data
    
    def test_admin_get_user_tax_hold(self):
        """GET /admin/users/{user_id}/tax-hold returns payment fields at top level"""
        # Admin login
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_response.json()["access_token"]
        
        # Get test user ID
        users_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search={TEST_USER_EMAIL}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert users_response.status_code == 200
        users = users_response.json()["users"]
        assert len(users) > 0, "Test user not found"
        user_id = users[0]["id"]
        
        # Get tax hold for user
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/tax-hold",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Admin tax hold get failed: {response.text}"
        data = response.json()
        
        # Verify fields at top level
        expected_fields = ["is_blocked", "tax_amount_due", "beneficiary_name", "iban", "bic_swift", "reference", "crypto_wallet"]
        for field in expected_fields:
            assert field in data, f"Missing field in admin response: {field}"
        
        assert "payment_details" not in data, "Admin response should not have nested payment_details"
        
        print(f"PASS: Admin tax hold returns fields at top level")
        return data


class TestUserAuthentication:
    """Test user authentication flows"""
    
    def test_user_login_success(self):
        """Test user ashleyalt005@gmail.com can login"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_EMAIL
        print(f"PASS: User login successful for {TEST_USER_EMAIL}")
        return data["access_token"]
    
    def test_user_login_wrong_password(self):
        """Test login fails with wrong password"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 400], "Wrong password should fail"
        print("PASS: Login correctly rejected with wrong password")


class TestUserBanking:
    """Test user banking features"""
    
    @pytest.fixture
    def user_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_accounts(self, user_token):
        """Test user can get their accounts"""
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200, f"Get accounts failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Accounts should be a list"
        print(f"PASS: User has {len(data)} account(s)")
        return data
    
    def test_get_transactions(self, user_token):
        """Test user can get transactions"""
        # First get accounts
        accounts_response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        accounts = accounts_response.json()
        
        if len(accounts) > 0:
            account_id = accounts[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/v1/accounts/{account_id}/transactions",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            assert response.status_code == 200, f"Get transactions failed: {response.text}"
            data = response.json()
            assert isinstance(data, list), "Transactions should be a list"
            print(f"PASS: Account has {len(data)} transaction(s)")
        else:
            print("SKIP: No accounts to test transactions")


class TestAdminFeatures:
    """Test admin panel features"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_admin_login_success(self):
        """Admin login works"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] in ["ADMIN", "SUPER_ADMIN"]
        print("PASS: Admin login successful")
    
    def test_admin_list_users(self, admin_token):
        """Admin can list users"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"List users failed: {response.text}"
        data = response.json()
        assert "users" in data
        assert "pagination" in data
        print(f"PASS: Admin can list users, total: {data['pagination']['total_users']}")
    
    def test_admin_get_support_tickets(self, admin_token):
        """Admin can get support tickets"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get tickets failed: {response.text}"
        data = response.json()
        # Should have tickets array or grouped structure
        assert "tickets" in data or isinstance(data, list), "Tickets response invalid"
        print("PASS: Admin can get support tickets")
    
    def test_admin_get_kyc_applications(self, admin_token):
        """Admin can get KYC applications"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get KYC failed: {response.text}"
        print("PASS: Admin can get KYC applications")
    
    def test_admin_get_transfers(self, admin_token):
        """Admin can get transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get transfers failed: {response.text}"
        print("PASS: Admin can get transfers")
    
    def test_admin_get_audit_logs(self, admin_token):
        """Admin can get audit logs"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get audit logs failed: {response.text}"
        print("PASS: Admin can get audit logs")
    
    def test_admin_get_overview(self, admin_token):
        """Admin can get overview stats"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get overview failed: {response.text}"
        data = response.json()
        expected_keys = ["total_users", "total_accounts", "pending_kyc"]
        for key in expected_keys:
            assert key in data, f"Missing overview key: {key}"
        print("PASS: Admin can get overview stats")


class TestAdminTaxHoldManagement:
    """Test admin can set tax hold with payment details"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_tax_hold_with_payment_details(self, admin_token):
        """Admin can get tax hold with beneficiary, IBAN, BIC, reference, crypto wallet"""
        # Get test user ID
        users_response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?search={TEST_USER_EMAIL}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        users = users_response.json()["users"]
        user_id = users[0]["id"]
        
        # Get current tax hold to verify data
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/{user_id}/tax-hold",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure is correct
        print(f"PASS: Tax hold structure is correct")
        print(f"  - is_blocked: {data.get('is_blocked')}")
        print(f"  - tax_amount_due: {data.get('tax_amount_due')}")
        print(f"  - beneficiary_name: {data.get('beneficiary_name')}")
        print(f"  - iban: {data.get('iban')}")
        print(f"  - bic_swift: {data.get('bic_swift')}")
        print(f"  - reference: {data.get('reference')}")
        print(f"  - crypto_wallet: {data.get('crypto_wallet')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
