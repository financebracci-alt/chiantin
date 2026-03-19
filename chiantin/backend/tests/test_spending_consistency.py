"""
Tests for Spending Consistency Fix
Verifies that Overview 'THIS MONTH' and Spending Insights 'This Month' show EXACT same amount

Key test: Dashboard shows €168,580.99 -> Spending Insights 'This Month' must show €168,580.99
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CUSTOMER_EMAIL = "ashleyalt005@gmail.com"
CUSTOMER_PASSWORD = "123456789"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"


class TestSpendingConsistency:
    """Test spending amounts are consistent across different endpoints"""
    
    @pytest.fixture(scope="class")
    def customer_token(self):
        """Get customer auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        assert response.status_code == 200, f"Customer login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_monthly_spending_endpoint(self, customer_token):
        """Test /api/v1/insights/monthly-spending returns correct data (Overview widget source)"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/insights/monthly-spending", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "total" in data, "Response must have 'total' field"
        assert "categories" in data, "Response must have 'categories' field"
        
        # Store the total for comparison
        monthly_total = data["total"]
        print(f"Monthly spending total (Overview): {monthly_total} cents = €{monthly_total/100:,.2f}")
        
        # Expected: 16858099 cents = €168,580.99
        assert monthly_total == 16858099, f"Expected 16858099 cents (€168,580.99), got {monthly_total} (€{monthly_total/100:,.2f})"
        
        return monthly_total
    
    def test_spending_insights_this_month(self, customer_token):
        """Test /api/v1/insights/spending?period=this_month returns SAME as monthly-spending"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/insights/spending?period=this_month", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "total" in data, "Response must have 'total' field"
        
        this_month_total = data["total"]
        print(f"Spending Insights 'This Month' total: {this_month_total} cents = €{this_month_total/100:,.2f}")
        
        # CRITICAL: Must match Overview exactly
        assert this_month_total == 16858099, f"Expected 16858099 cents (€168,580.99), got {this_month_total} (€{this_month_total/100:,.2f})"
        
        return this_month_total
    
    def test_spending_consistency_overview_vs_insights(self, customer_token):
        """CRITICAL: Verify Overview and Spending Insights show SAME amount for 'This Month'"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        # Get Overview (monthly-spending)
        overview_resp = requests.get(f"{BASE_URL}/api/v1/insights/monthly-spending", headers=headers)
        assert overview_resp.status_code == 200
        overview_total = overview_resp.json()["total"]
        
        # Get Spending Insights (period=this_month)
        insights_resp = requests.get(f"{BASE_URL}/api/v1/insights/spending?period=this_month", headers=headers)
        assert insights_resp.status_code == 200
        insights_total = insights_resp.json()["total"]
        
        print(f"Overview 'THIS MONTH': {overview_total} cents = €{overview_total/100:,.2f}")
        print(f"Insights 'This Month': {insights_total} cents = €{insights_total/100:,.2f}")
        
        # CRITICAL ASSERTION: Both must be EXACTLY the same
        assert overview_total == insights_total, (
            f"SPENDING MISMATCH! Overview: €{overview_total/100:,.2f}, "
            f"Insights: €{insights_total/100:,.2f}"
        )
        
        print(f"✓ CONSISTENCY VERIFIED: Both show €{overview_total/100:,.2f}")
    
    def test_spending_insights_last_30_days(self, customer_token):
        """Test Last 30 days shows DIFFERENT amount (rolling vs calendar month)"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/insights/spending?days=30", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        last_30_total = data.get("total", 0)
        print(f"Spending Insights 'Last 30 days': {last_30_total} cents = €{last_30_total/100:,.2f}")
        
        # Expected: 17408099 cents = €174,080.99 (DIFFERENT from This Month)
        # This is correct - Last 30 days is a rolling window, not calendar month
        assert last_30_total == 17408099, f"Expected 17408099 cents (€174,080.99), got {last_30_total} (€{last_30_total/100:,.2f})"
        
        return last_30_total
    
    def test_spending_insights_last_7_days(self, customer_token):
        """Test Last 7 days endpoint works"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/insights/spending?days=7", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        last_7_total = data.get("total", 0)
        print(f"Spending Insights 'Last 7 days': {last_7_total} cents = €{last_7_total/100:,.2f}")
        
        # Should be lower than monthly
        assert last_7_total >= 0, "Total must be non-negative"
    
    def test_spending_insights_last_90_days(self, customer_token):
        """Test Last 90 days endpoint works"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/insights/spending?days=90", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        last_90_total = data.get("total", 0)
        print(f"Spending Insights 'Last 90 days': {last_90_total} cents = €{last_90_total/100:,.2f}")
        
        # Should be >= monthly total
        assert last_90_total >= 0, "Total must be non-negative"
    
    def test_admin_login(self, admin_token):
        """Verify admin login still works"""
        assert admin_token is not None, "Admin token should be valid"
        print("✓ Admin login successful")
    
    def test_admin_overview_loads(self, admin_token):
        """Verify admin overview endpoint still works"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/overview", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify key stats are present (actual structure)
        assert "users" in data, "Missing users section"
        assert "accounts" in data, "Missing accounts section"
        assert "transfers" in data, "Missing transfers section"
        
        users = data.get("users", {})
        transfers = data.get("transfers", {})
        print(f"✓ Admin Overview: {users.get('total')} users, {users.get('active')} active, {transfers.get('total')} transfers")
    
    def test_customer_dashboard_data(self, customer_token):
        """Verify customer can fetch all dashboard data"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        # Get accounts
        accounts_resp = requests.get(f"{BASE_URL}/api/v1/accounts", headers=headers)
        assert accounts_resp.status_code == 200
        
        # Get KYC status
        kyc_resp = requests.get(f"{BASE_URL}/api/v1/kyc/application", headers=headers)
        assert kyc_resp.status_code == 200
        
        # Get cards
        cards_resp = requests.get(f"{BASE_URL}/api/v1/cards", headers=headers)
        assert cards_resp.status_code == 200
        
        print("✓ Customer dashboard data loaded successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
