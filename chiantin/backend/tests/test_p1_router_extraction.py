"""
P1 Router Extraction Tests - Recipients, Beneficiaries, Insights, Scheduled Payments

Tests extracted routers for:
- /api/v1/recipients - user saved recipients management
- /api/v1/beneficiaries - user saved beneficiaries management
- /api/v1/insights/spending - spending breakdown
- /api/v1/insights/monthly-spending - monthly spending summary
- /api/v1/scheduled-payments - scheduled payments management

IMPORTANT: READ-ONLY tests only - DO NOT create/delete real data
This is a LIVE PRODUCTION banking platform with REAL CLIENTS.
"""

import pytest
import requests
import os
import time

# Use public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "ashleyalt005@gmail.com"
TEST_PASSWORD = "123456789"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for testing."""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get auth headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestRecipients:
    """Test /api/v1/recipients endpoints (READ-ONLY)"""
    
    def test_get_recipients_success(self, auth_headers):
        """GET /api/v1/recipients - should return user's recipients list"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/recipients",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "ok" in data
        assert data["ok"] == True
        assert "data" in data
        assert isinstance(data["data"], list)
        
        print(f"GET /api/v1/recipients: {response.status_code} - {len(data['data'])} recipients - {elapsed_ms:.0f}ms")
    
    def test_get_recipients_requires_auth(self):
        """GET /api/v1/recipients without auth should return 403"""
        response = requests.get(f"{BASE_URL}/api/v1/recipients")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_recipients_response_time(self, auth_headers):
        """Recipients endpoint should respond within 600ms (baseline: 467ms)"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/recipients",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert elapsed_ms < 600, f"Response time {elapsed_ms:.0f}ms exceeds 600ms threshold"
        print(f"Recipients response time: {elapsed_ms:.0f}ms (baseline: 467ms)")


class TestBeneficiaries:
    """Test /api/v1/beneficiaries endpoints (READ-ONLY)"""
    
    def test_get_beneficiaries_success(self, auth_headers):
        """GET /api/v1/beneficiaries - should return user's beneficiaries list"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/beneficiaries",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure - beneficiaries returns a list directly
        assert isinstance(data, list)
        
        print(f"GET /api/v1/beneficiaries: {response.status_code} - {len(data)} beneficiaries - {elapsed_ms:.0f}ms")
    
    def test_get_beneficiaries_requires_auth(self):
        """GET /api/v1/beneficiaries without auth should return 403"""
        response = requests.get(f"{BASE_URL}/api/v1/beneficiaries")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_beneficiaries_response_time(self, auth_headers):
        """Beneficiaries endpoint should respond within 600ms (baseline: 491ms)"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/beneficiaries",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert elapsed_ms < 600, f"Response time {elapsed_ms:.0f}ms exceeds 600ms threshold"
        print(f"Beneficiaries response time: {elapsed_ms:.0f}ms (baseline: 491ms)")


class TestInsights:
    """Test /api/v1/insights/* endpoints (READ-ONLY)"""
    
    def test_get_spending_insights_success(self, auth_headers):
        """GET /api/v1/insights/spending - should return spending breakdown"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/insights/spending",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "total" in data
        assert "categories" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["categories"], dict)
        
        print(f"GET /api/v1/insights/spending: {response.status_code} - total: {data['total']} - {elapsed_ms:.0f}ms")
    
    def test_get_spending_with_days_param(self, auth_headers):
        """GET /api/v1/insights/spending?days=7 - should accept days parameter"""
        response = requests.get(
            f"{BASE_URL}/api/v1/insights/spending",
            headers=auth_headers,
            params={"days": 7}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "total" in data
        assert "categories" in data
    
    def test_get_spending_with_this_month_period(self, auth_headers):
        """GET /api/v1/insights/spending?period=this_month - should match monthly-spending"""
        response = requests.get(
            f"{BASE_URL}/api/v1/insights/spending",
            headers=auth_headers,
            params={"period": "this_month"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "total" in data
    
    def test_get_monthly_spending_success(self, auth_headers):
        """GET /api/v1/insights/monthly-spending - should return monthly spending"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/insights/monthly-spending",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "total" in data
        assert "transaction_count" in data
        assert "categories" in data
        assert "period" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["transaction_count"], int)
        assert isinstance(data["categories"], dict)
        assert "start" in data["period"]
        assert "end" in data["period"]
        
        print(f"GET /api/v1/insights/monthly-spending: {response.status_code} - total: {data['total']}, txns: {data['transaction_count']} - {elapsed_ms:.0f}ms")
    
    def test_insights_requires_auth(self):
        """Insights endpoints without auth should return 403"""
        response = requests.get(f"{BASE_URL}/api/v1/insights/spending")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        response = requests.get(f"{BASE_URL}/api/v1/insights/monthly-spending")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_spending_response_time(self, auth_headers):
        """Spending insight endpoint should respond within 700ms (baseline: 568ms)"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/insights/spending",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert elapsed_ms < 700, f"Response time {elapsed_ms:.0f}ms exceeds 700ms threshold"
        print(f"Spending insight response time: {elapsed_ms:.0f}ms (baseline: 568ms)")
    
    def test_monthly_spending_response_time(self, auth_headers):
        """Monthly spending endpoint should respond within 800ms (baseline: 696ms)"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/insights/monthly-spending",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert elapsed_ms < 800, f"Response time {elapsed_ms:.0f}ms exceeds 800ms threshold"
        print(f"Monthly spending response time: {elapsed_ms:.0f}ms (baseline: 696ms)")


class TestScheduledPayments:
    """Test /api/v1/scheduled-payments endpoints (READ-ONLY)"""
    
    def test_get_scheduled_payments_success(self, auth_headers):
        """GET /api/v1/scheduled-payments - should return user's scheduled payments"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/scheduled-payments",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure - returns a list
        assert isinstance(data, list)
        
        print(f"GET /api/v1/scheduled-payments: {response.status_code} - {len(data)} payments - {elapsed_ms:.0f}ms")
    
    def test_get_scheduled_payments_requires_auth(self):
        """GET /api/v1/scheduled-payments without auth should return 403"""
        response = requests.get(f"{BASE_URL}/api/v1/scheduled-payments")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_scheduled_payments_response_time(self, auth_headers):
        """Scheduled payments endpoint should respond within 600ms (baseline: 452ms)"""
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/scheduled-payments",
            headers=auth_headers
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert elapsed_ms < 600, f"Response time {elapsed_ms:.0f}ms exceeds 600ms threshold"
        print(f"Scheduled payments response time: {elapsed_ms:.0f}ms (baseline: 452ms)")


class TestCrossSectionEndpoints:
    """Test that other admin sections still work after extraction (regression)"""
    
    def test_admin_users_still_works(self, auth_headers):
        """GET /api/v1/admin/users - should still return user list"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers=auth_headers,
            params={"page": 1, "limit": 5}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "users" in data
        assert "pagination" in data
        print(f"Admin users: {len(data['users'])} users")
    
    def test_admin_transfers_still_works(self, auth_headers):
        """GET /api/v1/admin/transfers - should still return transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers",
            headers=auth_headers,
            params={"status": "SUBMITTED", "page": 1, "limit": 5}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "ok" in data
        assert "data" in data
        assert "pagination" in data
        print(f"Admin transfers: {len(data['data'])} transfers")
    
    def test_admin_card_requests_still_works(self, auth_headers):
        """GET /api/v1/admin/card-requests - should still return card requests"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/card-requests",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "ok" in data
        assert "data" in data
        print(f"Admin card requests: {len(data['data'])} requests")
    
    def test_admin_tickets_still_works(self, auth_headers):
        """GET /api/v1/admin/tickets - should still return tickets"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers=auth_headers,
            params={"page": 1, "limit": 5}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Admin tickets: {len(data)} tickets")
    
    def test_accounts_still_works(self, auth_headers):
        """GET /api/v1/accounts - should still return user accounts"""
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"User accounts: {len(data)} accounts")
    
    def test_user_transfers_still_works(self, auth_headers):
        """GET /api/v1/transfers - should still return user transfers"""
        response = requests.get(
            f"{BASE_URL}/api/v1/transfers",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "ok" in data
        assert "data" in data
        print(f"User transfers: {len(data['data'])} transfers")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
