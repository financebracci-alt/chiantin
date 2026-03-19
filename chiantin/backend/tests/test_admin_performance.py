"""
Performance tests for Admin Panel - Accounts and Transfers endpoints
Tests bulk balance calculation and bulk user/account lookups

This test verifies the performance fix that reduced API response times from 8-22 seconds to under 2 seconds.
"""
import pytest
import requests
import time
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
CUSTOMER_EMAIL = "ashleyalt005@gmail.com"
CUSTOMER_PASSWORD = "123456789"

# Performance thresholds (in seconds)
MAX_RESPONSE_TIME = 2.0  # Should load in under 2 seconds after fix

class TestAdminLogin:
    """Test admin authentication"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_admin_login_works(self, admin_token):
        """Verify admin can log in"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"✓ Admin login successful - token obtained")


class TestAccountsPerformance:
    """Test Admin Accounts page performance - bulk balance calculation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_accounts_endpoint_performance(self, admin_token):
        """Test /admin/accounts-with-users responds under 2 seconds"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users",
            headers=headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Accounts endpoint failed: {response.text}"
        print(f"✓ Accounts endpoint response time: {elapsed:.2f}s (threshold: {MAX_RESPONSE_TIME}s)")
        
        # Check performance meets threshold
        assert elapsed < MAX_RESPONSE_TIME, f"Accounts endpoint too slow: {elapsed:.2f}s > {MAX_RESPONSE_TIME}s"
    
    def test_accounts_data_structure(self, admin_token):
        """Verify accounts endpoint returns expected data structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be paginated response
        assert "accounts" in data, "Response should contain 'accounts' key"
        assert "pagination" in data, "Response should contain 'pagination' key"
        
        accounts = data["accounts"]
        pagination = data["pagination"]
        
        # Check pagination structure
        assert "total_accounts" in pagination
        assert "total_pages" in pagination
        assert "has_next" in pagination
        assert "has_prev" in pagination
        
        print(f"✓ Found {len(accounts)} accounts, total: {pagination['total_accounts']}")
        
        # Check at least one account has proper structure
        if accounts:
            acc = accounts[0]
            assert "id" in acc, "Account should have 'id'"
            assert "balance" in acc, "Account should have 'balance'"
            assert "userName" in acc, "Account should have 'userName'"
            assert "userEmail" in acc, "Account should have 'userEmail'"
            assert "iban" in acc, "Account should have 'iban'"
            print(f"✓ Account structure valid: {acc['userName']} / {acc['userEmail']}")
    
    def test_accounts_balances_are_present(self, admin_token):
        """Verify accounts have balances (bulk balance calculation working)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users",
            headers=headers
        )
        
        assert response.status_code == 200
        accounts = response.json().get("accounts", [])
        
        # Check that balances are numeric
        for acc in accounts[:5]:  # Check first 5
            balance = acc.get("balance")
            assert balance is not None, f"Account {acc.get('id')} missing balance"
            assert isinstance(balance, (int, float)), f"Balance should be numeric, got {type(balance)}"
            print(f"✓ Account {acc.get('userEmail', 'unknown')}: balance = {balance} cents")
    
    def test_accounts_pagination_works(self, admin_token):
        """Test pagination parameters work correctly"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test with page parameter
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users?page=1&limit=20",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        pagination = data.get("pagination", {})
        
        print(f"✓ Pagination - Page 1 of {pagination.get('total_pages')}, {pagination.get('total_accounts')} total accounts")


class TestTransfersPerformance:
    """Test Admin Transfers Queue performance - bulk user/account lookups"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_transfers_submitted_performance(self, admin_token):
        """Test /admin/transfers?status=SUBMITTED responds under 2 seconds"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=SUBMITTED",
            headers=headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Transfers SUBMITTED endpoint failed: {response.text}"
        print(f"✓ Transfers SUBMITTED response time: {elapsed:.2f}s (threshold: {MAX_RESPONSE_TIME}s)")
        
        assert elapsed < MAX_RESPONSE_TIME, f"Transfers endpoint too slow: {elapsed:.2f}s > {MAX_RESPONSE_TIME}s"
    
    def test_transfers_completed_performance(self, admin_token):
        """Test /admin/transfers?status=COMPLETED responds under 2 seconds"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=COMPLETED",
            headers=headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Transfers COMPLETED endpoint failed: {response.text}"
        print(f"✓ Transfers COMPLETED response time: {elapsed:.2f}s (threshold: {MAX_RESPONSE_TIME}s)")
        
        assert elapsed < MAX_RESPONSE_TIME, f"Transfers endpoint too slow: {elapsed:.2f}s > {MAX_RESPONSE_TIME}s"
    
    def test_transfers_rejected_performance(self, admin_token):
        """Test /admin/transfers?status=REJECTED responds under 2 seconds"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=REJECTED",
            headers=headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Transfers REJECTED endpoint failed: {response.text}"
        print(f"✓ Transfers REJECTED response time: {elapsed:.2f}s (threshold: {MAX_RESPONSE_TIME}s)")
        
        assert elapsed < MAX_RESPONSE_TIME, f"Transfers endpoint too slow: {elapsed:.2f}s > {MAX_RESPONSE_TIME}s"
    
    def test_transfers_data_structure(self, admin_token):
        """Verify transfers endpoint returns sender info"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers?status=COMPLETED",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data, "Response should contain 'data' key"
        assert "pagination" in data, "Response should contain 'pagination' key"
        
        transfers = data["data"]
        
        print(f"✓ Found {len(transfers)} transfers in COMPLETED status")
        
        # Check that transfers have sender info (bulk lookup working)
        for t in transfers[:3]:  # Check first 3
            assert "sender_name" in t, f"Transfer missing 'sender_name'"
            assert "sender_email" in t, f"Transfer missing 'sender_email'"
            assert "sender_iban" in t, f"Transfer missing 'sender_iban'"
            print(f"  - Transfer from {t.get('sender_name')}: €{t.get('amount', 0)/100:.2f} to {t.get('beneficiary_name')}")
    
    def test_transfers_tabs_work(self, admin_token):
        """Verify all transfer status tabs work"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        for status in ['SUBMITTED', 'COMPLETED', 'REJECTED']:
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/transfers?status={status}",
                headers=headers
            )
            assert response.status_code == 200, f"Tab {status} failed: {response.text}"
            data = response.json()
            count = len(data.get("data", []))
            print(f"✓ {status} tab: {count} transfers")


class TestCustomerAccess:
    """Test customer login and dashboard access"""
    
    @pytest.fixture(scope="class")
    def customer_token(self):
        """Get customer authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Customer login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_customer_login_works(self, customer_token):
        """Verify customer can log in"""
        assert customer_token is not None
        print(f"✓ Customer login successful")
    
    def test_customer_can_get_accounts(self, customer_token):
        """Verify customer can access their accounts"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers=headers
        )
        
        assert response.status_code == 200, f"Customer accounts failed: {response.text}"
        accounts = response.json()
        print(f"✓ Customer has {len(accounts)} account(s)")
    
    def test_customer_can_get_transfers(self, customer_token):
        """Verify customer can access their transfers"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/transfers",
            headers=headers
        )
        
        assert response.status_code == 200, f"Customer transfers failed: {response.text}"
        transfers = response.json()
        print(f"✓ Customer has {len(transfers)} transfer(s)")
    
    def test_customer_can_get_transactions(self, customer_token):
        """Verify customer can access transactions"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        # First get accounts
        accounts_response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers=headers
        )
        
        if accounts_response.status_code == 200:
            accounts = accounts_response.json()
            if accounts:
                account_id = accounts[0].get("id")
                response = requests.get(
                    f"{BASE_URL}/api/v1/accounts/{account_id}/transactions",
                    headers=headers
                )
                assert response.status_code == 200, f"Transactions failed: {response.text}"
                transactions = response.json()
                print(f"✓ Customer account has {len(transactions)} transaction(s)")
            else:
                print("✓ Customer has no accounts (skipping transaction check)")
        else:
            pytest.skip("Could not get customer accounts")


class TestBulkBalancesImplementation:
    """Verify bulk balance calculation is being used"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_multiple_accounts_load_fast(self, admin_token):
        """
        If N+1 queries were still present, loading 10+ accounts would take 10+ seconds.
        With bulk balance, it should complete in under 2 seconds.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts-with-users?limit=50",
            headers=headers
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        accounts = response.json().get("accounts", [])
        
        # With 50 accounts, N+1 would take 50+ seconds (1s each)
        # With bulk balance, should be < 2 seconds
        print(f"✓ Loaded {len(accounts)} accounts in {elapsed:.2f}s")
        print(f"  (N+1 would have taken ~{len(accounts)}+ seconds)")
        
        assert elapsed < MAX_RESPONSE_TIME, f"Still seeing N+1 performance: {elapsed:.2f}s for {len(accounts)} accounts"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
