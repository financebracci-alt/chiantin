"""
P0 HOTFIX Regression Tests for Banking Platform.

Tests the two critical fixes:
1. KYC Queue - Pending endpoint now returns personal info fields
2. Tax Hold Amount - Now reads tax_amount_cents correctly (not tax_amount_due field)

Plus full admin panel regression testing.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://user-alert-system-2.preview.emergentagent.com').rstrip('/')


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_admin_login(self, auth_token):
        """Admin can login successfully"""
        assert auth_token is not None
        assert len(auth_token) > 20
        print("✓ Admin login successful")
    
    def test_auth_me(self, auth_token):
        """Auth me endpoint returns admin info"""
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "ashleyalt005@gmail.com"
        assert data["role"] == "ADMIN"
        print(f"✓ Auth me returns: {data['email']} ({data['role']})")


class TestKYCHotfix:
    """Tests for KYC Queue fix - personal info fields in pending endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_kyc_pending_endpoint_returns_200(self, auth_token):
        """KYC pending endpoint accessible"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ KYC pending endpoint: {len(response.json())} pending applications")
    
    def test_kyc_pending_has_personal_info_fields(self, auth_token):
        """KYC pending endpoint returns personal info fields (P0 HOTFIX)"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        apps = response.json()
        
        if len(apps) > 0:
            app = apps[0]
            # Check ALL personal info fields required by admin frontend
            required_fields = [
                "id", "user_id", "user_email", "user_name", "status",
                "full_name", "nationality", "country", "street_address",
                "city", "postal_code", "tax_residency", "date_of_birth"
            ]
            
            for field in required_fields:
                assert field in app, f"Missing field: {field}"
                print(f"  ✓ {field}: {app.get(field)}")
            
            print(f"✓ KYC application has all personal info fields")
        else:
            print("⚠ No pending KYC applications to verify")
    
    def test_kyc_pending_has_documents(self, auth_token):
        """KYC pending endpoint returns documents array"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        apps = response.json()
        
        if len(apps) > 0:
            app = apps[0]
            assert "documents" in app, "Missing documents field"
            docs = app["documents"]
            assert isinstance(docs, list), "Documents should be a list"
            
            if len(docs) > 0:
                doc = docs[0]
                assert "document_type" in doc
                assert "file_name" in doc
                print(f"✓ Documents present: {len(docs)} documents")
            else:
                print("⚠ No documents in KYC application")
        else:
            print("⚠ No pending KYC applications to verify")


class TestTaxHoldHotfix:
    """Tests for Tax Hold fix - tax_amount_cents field"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_tax_hold_endpoint_returns_200(self, auth_token):
        """Tax hold endpoint accessible"""
        # User with known tax hold: 699c203fda173e07eee262b3 (hannan1979ma@yahoo.com)
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/699c203fda173e07eee262b3/tax-hold",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Tax hold endpoint accessible")
    
    def test_tax_hold_returns_correct_amount(self, auth_token):
        """Tax hold returns non-zero amount (P0 HOTFIX - was showing €0)"""
        # User with known tax hold: €4,157.00
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users/699c203fda173e07eee262b3/tax-hold",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "is_blocked" in data
        assert "tax_amount_due" in data
        
        # This was the bug - showing €0 instead of actual amount
        assert data["is_blocked"] == True, "User should be blocked"
        assert data["tax_amount_due"] > 0, f"Tax amount should be > 0, got: {data['tax_amount_due']}"
        assert data["tax_amount_due"] == 4157.0, f"Expected €4,157.00, got: €{data['tax_amount_due']}"
        
        print(f"✓ Tax hold amount: €{data['tax_amount_due']:,.2f}")
        print(f"✓ Blocked status: {data['is_blocked']}")
        print(f"✓ Reason: {data.get('reason')}")


class TestAdminOverview:
    """Admin Overview dashboard tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_admin_overview_loads(self, auth_token):
        """Admin overview dashboard loads with stats"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/overview",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check key stats are present
        assert "users" in data or "total_users" in data
        print(f"✓ Admin overview loads successfully")


class TestAdminUsers:
    """Admin Users list tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_users_list_loads(self, auth_token):
        """Admin users list loads with pagination"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        assert "pagination" in data
        assert isinstance(data["users"], list)
        print(f"✓ Users list loads: {len(data['users'])} users")


class TestAdminAccounts:
    """Admin Accounts list tests (no accounts.map error)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_accounts_list_loads(self, auth_token):
        """Admin accounts list loads without accounts.map error"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users?page=1&page_size=20",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return accounts array (not cause .map() error)
        assert "accounts" in data or isinstance(data, list)
        print(f"✓ Accounts list loads successfully")


class TestAdminCardRequests:
    """Admin Card Requests tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_card_requests_loads(self, auth_token):
        """Card requests list loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests?status=PENDING",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Card requests loads successfully")


class TestAdminTransfersQueue:
    """Admin Transfers Queue tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_transfers_submitted_tab(self, auth_token):
        """Transfers SUBMITTED tab loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=SUBMITTED&page=1&page_size=20",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Transfers SUBMITTED tab loads")
    
    def test_transfers_completed_tab(self, auth_token):
        """Transfers COMPLETED tab loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=COMPLETED&page=1&page_size=20",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Transfers COMPLETED tab loads")
    
    def test_transfers_rejected_tab(self, auth_token):
        """Transfers REJECTED tab loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=REJECTED&page=1&page_size=20",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Transfers REJECTED tab loads")


class TestAdminSupportTickets:
    """Admin Support Tickets tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_tickets_list_loads(self, auth_token):
        """Support tickets list loads"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Support tickets list loads")


class TestAdminAuditLogs:
    """Admin Audit Logs tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_audit_logs_load(self, auth_token):
        """Audit logs load"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/audit-logs?page=1&page_size=20",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Audit logs load")


class TestNotifications:
    """Notification badge tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ashleyalt005@gmail.com", "password": "123456789"}
        )
        return response.json()["access_token"]
    
    def test_notification_counts(self, auth_token):
        """Notification counts endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Notification counts endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
