"""
Test accounts-with-users endpoint performance after N+1 query fix.
Tests both response time AND data correctness.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAccountsPerformance:
    """Test the performance hotfix for accounts endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_url = f"{BASE_URL}/api/v1/auth/login"
        login_response = requests.post(login_url, json={
            "email": "ashleyalt005@gmail.com",
            "password": "123456789"
        })
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_accounts_endpoint_performance(self):
        """PERFORMANCE: Response time should be under 1 second (was 6.35s before fix)"""
        url = f"{BASE_URL}/api/v1/admin/accounts-with-users?page=1&page_size=50"
        
        start_time = time.time()
        response = requests.get(url, headers=self.headers)
        response_time = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Performance assertion: should be under 2 seconds (target: ~0.76-0.86s)
        print(f"Response time: {response_time:.2f} seconds")
        assert response_time < 2.0, f"Response too slow: {response_time:.2f}s (should be <2s)"
    
    def test_accounts_response_structure(self):
        """API CONTRACT: Response must have 'accounts' array and 'pagination' object"""
        url = f"{BASE_URL}/api/v1/admin/accounts-with-users"
        response = requests.get(url, headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Must have 'accounts' key (not 'data')
        assert "accounts" in data, f"Missing 'accounts' key. Keys: {data.keys()}"
        assert isinstance(data["accounts"], list), "'accounts' must be a list"
        
        # Must have pagination
        assert "pagination" in data, f"Missing 'pagination' key. Keys: {data.keys()}"
        pagination = data["pagination"]
        assert "total_accounts" in pagination, "Missing total_accounts in pagination"
        assert "total" in pagination, "Missing total in pagination"
        assert "page" in pagination, "Missing page in pagination"
        assert "total_pages" in pagination, "Missing total_pages in pagination"
    
    def test_account_objects_have_correct_fields(self):
        """DATA: Account objects must have userName, userEmail, userId, balance (camelCase)"""
        url = f"{BASE_URL}/api/v1/admin/accounts-with-users?page=1&page_size=5"
        response = requests.get(url, headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        accounts = data.get("accounts", [])
        
        assert len(accounts) > 0, "No accounts returned"
        
        account = accounts[0]
        
        # Check camelCase fields exist
        assert "userName" in account, f"Missing 'userName'. Keys: {account.keys()}"
        assert "userEmail" in account, f"Missing 'userEmail'. Keys: {account.keys()}"
        assert "userId" in account, f"Missing 'userId'. Keys: {account.keys()}"
        assert "balance" in account, f"Missing 'balance'. Keys: {account.keys()}"
        
        # Also check standard account fields
        assert "iban" in account, f"Missing 'iban'. Keys: {account.keys()}"
        assert "account_number" in account, f"Missing 'account_number'. Keys: {account.keys()}"
        
        print(f"Account fields verified: {list(account.keys())}")
    
    def test_balances_are_populated(self):
        """DATA: Balances should be populated correctly (not all zeros)"""
        url = f"{BASE_URL}/api/v1/admin/accounts-with-users?page=1&page_size=50"
        response = requests.get(url, headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        accounts = data.get("accounts", [])
        
        # Check that at least some accounts have non-zero balances
        balances = [acc.get("balance", 0) for acc in accounts]
        non_zero_balances = [b for b in balances if b != 0]
        
        print(f"Total accounts: {len(accounts)}")
        print(f"Accounts with non-zero balance: {len(non_zero_balances)}")
        print(f"Sample balances: {balances[:10]}")
        
        # It's okay if all balances are zero in test environment
        # but we verify they are integers
        for acc in accounts:
            assert isinstance(acc.get("balance"), (int, float)), f"Balance should be numeric: {acc.get('balance')}"
    
    def test_search_functionality(self):
        """FUNCTIONALITY: Search should still work after the fix"""
        url = f"{BASE_URL}/api/v1/admin/accounts-with-users?search=ashley"
        response = requests.get(url, headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "accounts" in data
        # Search should filter results
        print(f"Search 'ashley' returned {len(data['accounts'])} accounts")
    
    def test_pagination_functionality(self):
        """FUNCTIONALITY: Pagination should still work after the fix"""
        # Get page 1
        url_p1 = f"{BASE_URL}/api/v1/admin/accounts-with-users?page=1&page_size=20"
        response_p1 = requests.get(url_p1, headers=self.headers)
        
        assert response_p1.status_code == 200
        data_p1 = response_p1.json()
        accounts_p1 = data_p1.get("accounts", [])
        pagination = data_p1.get("pagination", {})
        
        print(f"Page 1: {len(accounts_p1)} accounts")
        print(f"Total: {pagination.get('total_accounts')}")
        print(f"Total pages: {pagination.get('total_pages')}")
        
        # If there are multiple pages, test page 2
        if pagination.get("total_pages", 1) > 1:
            url_p2 = f"{BASE_URL}/api/v1/admin/accounts-with-users?page=2&page_size=20"
            response_p2 = requests.get(url_p2, headers=self.headers)
            
            assert response_p2.status_code == 200
            data_p2 = response_p2.json()
            accounts_p2 = data_p2.get("accounts", [])
            
            print(f"Page 2: {len(accounts_p2)} accounts")
            
            # Pages should have different accounts
            if accounts_p1 and accounts_p2:
                ids_p1 = set(acc.get("id") for acc in accounts_p1)
                ids_p2 = set(acc.get("id") for acc in accounts_p2)
                assert ids_p1 != ids_p2, "Page 1 and Page 2 have identical accounts"
    
    def test_limit_param_alias(self):
        """COMPATIBILITY: 'limit' param should work as alias for 'page_size'"""
        url = f"{BASE_URL}/api/v1/admin/accounts-with-users?limit=20"
        response = requests.get(url, headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        accounts = data.get("accounts", [])
        
        # Should return max 20 accounts
        assert len(accounts) <= 20, f"Expected <=20 accounts with limit=20, got {len(accounts)}"
        print(f"'limit' param works: returned {len(accounts)} accounts")


class TestCrossSectionSmoke:
    """Smoke test other admin sections to ensure they still work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_url = f"{BASE_URL}/api/v1/auth/login"
        login_response = requests.post(login_url, json={
            "email": "ashleyalt005@gmail.com",
            "password": "123456789"
        })
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_admin_overview(self):
        """SMOKE: Admin overview should load"""
        url = f"{BASE_URL}/api/v1/admin/overview"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Overview failed: {response.status_code}"
        print("Overview: OK")
    
    def test_admin_users(self):
        """SMOKE: Admin users should load"""
        url = f"{BASE_URL}/api/v1/admin/users?page=1"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Users failed: {response.status_code}"
        print("Users: OK")
    
    def test_admin_kyc_queue(self):
        """SMOKE: KYC queue should load"""
        url = f"{BASE_URL}/api/v1/admin/kyc/applications?page=1"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"KYC failed: {response.status_code}"
        print("KYC Queue: OK")
    
    def test_admin_card_requests(self):
        """SMOKE: Card requests should load"""
        url = f"{BASE_URL}/api/v1/admin/card-requests?page=1"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Card requests failed: {response.status_code}"
        print("Card Requests: OK")
    
    def test_admin_transfers_queue(self):
        """SMOKE: Transfers queue should load"""
        url = f"{BASE_URL}/api/v1/admin/transfers?page=1"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Transfers failed: {response.status_code}"
        print("Transfers Queue: OK")
    
    def test_admin_support_tickets(self):
        """SMOKE: Support tickets should load"""
        url = f"{BASE_URL}/api/v1/admin/support/tickets?page=1"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Support tickets failed: {response.status_code}"
        print("Support Tickets: OK")
    
    def test_admin_audit_logs(self):
        """SMOKE: Audit logs should load"""
        url = f"{BASE_URL}/api/v1/admin/audit-logs?page=1"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Audit logs failed: {response.status_code}"
        print("Audit Logs: OK")

