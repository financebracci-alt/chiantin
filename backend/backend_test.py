"""Backend API Testing for Project Atlas"""

import requests
import sys
from datetime import datetime

class AtlasBankingAPITester:
    def __init__(self, base_url="https://atlas-fintech.preview.emergentagent.com"):
        self.base_url = base_url
        self.customer_token = None
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.customer_account_id = None
        self.admin_user_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, description=""):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        if description:
            print(f"   Description: {description}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.json()}")
                except:
                    print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_customer_login(self):
        """Test customer login"""
        success, response = self.run_test(
            "Customer Login",
            "POST",
            "/api/v1/auth/login",
            200,
            data={"email": "customer@demo.com", "password": "Demo@123456"},
            description="Login with demo customer credentials"
        )
        if success and 'access_token' in response:
            self.customer_token = response['access_token']
            print(f"   ✓ Customer token obtained")
            return True
        return False

    def test_admin_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "/api/v1/auth/login",
            200,
            data={"email": "admin@atlas.local", "password": "Admin@123456"},
            description="Login with demo admin credentials"
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✓ Admin token obtained")
            return True
        return False

    def test_get_customer_accounts(self):
        """Test getting customer accounts"""
        success, response = self.run_test(
            "Get Customer Accounts",
            "GET",
            "/api/v1/accounts",
            200,
            token=self.customer_token,
            description="Fetch customer's bank accounts"
        )
        if success and isinstance(response, list) and len(response) > 0:
            self.customer_account_id = response[0]['id']
            print(f"   ✓ Found {len(response)} account(s)")
            print(f"   ✓ Account ID: {self.customer_account_id}")
            print(f"   ✓ Balance: €{response[0]['balance']/100:.2f}")
            return True
        return False

    def test_get_kyc_application(self):
        """Test getting KYC application"""
        success, response = self.run_test(
            "Get KYC Application",
            "GET",
            "/api/v1/kyc/application",
            200,
            token=self.customer_token,
            description="Fetch customer's KYC application status"
        )
        if success:
            print(f"   ✓ KYC Status: {response.get('status', 'N/A')}")
            return True
        return False

    def test_get_notifications(self):
        """Test getting notifications"""
        success, response = self.run_test(
            "Get Notifications",
            "GET",
            "/api/v1/notifications",
            200,
            token=self.customer_token,
            description="Fetch customer notifications"
        )
        if success:
            print(f"   ✓ Found {len(response) if isinstance(response, list) else 0} notification(s)")
            return True
        return False

    def test_p2p_transfer(self):
        """Test P2P transfer API"""
        # First, create a test recipient account (signup)
        test_email = f"test_recipient_{datetime.now().strftime('%H%M%S')}@test.com"
        
        # Try to transfer to admin (should work as they have an account)
        success, response = self.run_test(
            "P2P Transfer",
            "POST",
            "/api/v1/transfers/p2p",
            200,
            data={
                "to_email": "admin@atlas.local",
                "amount": 100,  # €1.00 in cents
                "reason": "Test transfer"
            },
            token=self.customer_token,
            description="Transfer €1.00 to another user"
        )
        if success:
            print(f"   ✓ Transfer successful")
            print(f"   ✓ Transaction ID: {response.get('transaction_id', 'N/A')}")
            return True
        return False

    def test_admin_get_users(self):
        """Test admin get all users"""
        success, response = self.run_test(
            "Admin - Get All Users",
            "GET",
            "/api/v1/admin/users",
            200,
            token=self.admin_token,
            description="Fetch all users (admin only)"
        )
        if success and isinstance(response, list):
            print(f"   ✓ Found {len(response)} user(s)")
            if len(response) > 0:
                self.admin_user_id = response[0]['id']
                print(f"   ✓ First user: {response[0].get('email', 'N/A')}")
            return True
        return False

    def test_admin_get_user_details(self):
        """Test admin get user details"""
        if not self.admin_user_id:
            print("⚠️  Skipping - No user ID available")
            return True
        
        success, response = self.run_test(
            "Admin - Get User Details",
            "GET",
            f"/api/v1/admin/users/{self.admin_user_id}",
            200,
            token=self.admin_token,
            description="Fetch detailed user information"
        )
        if success:
            print(f"   ✓ User: {response.get('user', {}).get('email', 'N/A')}")
            print(f"   ✓ Accounts: {len(response.get('accounts', []))}")
            print(f"   ✓ KYC Status: {response.get('kyc_status', 'N/A')}")
            return True
        return False

    def test_admin_get_kyc_pending(self):
        """Test admin get pending KYC"""
        success, response = self.run_test(
            "Admin - Get Pending KYC",
            "GET",
            "/api/v1/admin/kyc/pending",
            200,
            token=self.admin_token,
            description="Fetch pending KYC applications"
        )
        if success:
            print(f"   ✓ Found {len(response) if isinstance(response, list) else 0} pending KYC(s)")
            return True
        return False

    def test_admin_get_audit_logs(self):
        """Test admin get audit logs"""
        success, response = self.run_test(
            "Admin - Get Audit Logs",
            "GET",
            "/api/v1/admin/audit-logs?limit=10",
            200,
            token=self.admin_token,
            description="Fetch audit logs"
        )
        if success:
            print(f"   ✓ Found {len(response) if isinstance(response, list) else 0} audit log(s)")
            return True
        return False

    def test_get_transactions(self):
        """Test getting account transactions"""
        if not self.customer_account_id:
            print("⚠️  Skipping - No account ID available")
            return True
        
        success, response = self.run_test(
            "Get Account Transactions",
            "GET",
            f"/api/v1/accounts/{self.customer_account_id}/transactions",
            200,
            token=self.customer_token,
            description="Fetch account transaction history"
        )
        if success:
            print(f"   ✓ Found {len(response) if isinstance(response, list) else 0} transaction(s)")
            return True
        return False

    def test_health_check(self):
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "/api/health",
            200,
            description="Check API health status"
        )
        if success:
            print(f"   ✓ Status: {response.get('status', 'N/A')}")
            return True
        return False

    def test_add_beneficiary(self):
        """Test adding a beneficiary"""
        success, response = self.run_test(
            "Add Beneficiary",
            "POST",
            "/api/v1/beneficiaries",
            200,
            data={
                "recipient_email": "admin@atlas.local",
                "recipient_name": "Admin User",
                "nickname": "Admin"
            },
            token=self.customer_token,
            description="Add a saved recipient"
        )
        if success:
            print(f"   ✓ Beneficiary added: {response.get('id', 'N/A')}")
            return True
        return False

    def test_get_beneficiaries(self):
        """Test getting beneficiaries"""
        success, response = self.run_test(
            "Get Beneficiaries",
            "GET",
            "/api/v1/beneficiaries",
            200,
            token=self.customer_token,
            description="Fetch saved recipients"
        )
        if success:
            print(f"   ✓ Found {len(response) if isinstance(response, list) else 0} beneficiary(ies)")
            return True
        return False

    def test_create_scheduled_payment(self):
        """Test creating a scheduled payment"""
        from datetime import date
        success, response = self.run_test(
            "Create Scheduled Payment",
            "POST",
            "/api/v1/scheduled-payments",
            200,
            data={
                "recipient_email": "admin@atlas.local",
                "amount": 500,
                "reason": "Monthly subscription",
                "frequency": "MONTHLY",
                "start_date": date.today().isoformat()
            },
            token=self.customer_token,
            description="Create recurring payment"
        )
        if success:
            print(f"   ✓ Scheduled payment created: {response.get('id', 'N/A')}")
            return True
        return False

    def test_get_scheduled_payments(self):
        """Test getting scheduled payments"""
        success, response = self.run_test(
            "Get Scheduled Payments",
            "GET",
            "/api/v1/scheduled-payments",
            200,
            token=self.customer_token,
            description="Fetch scheduled payments"
        )
        if success:
            print(f"   ✓ Found {len(response) if isinstance(response, list) else 0} scheduled payment(s)")
            return True
        return False

    def test_get_spending_insights(self):
        """Test getting spending insights"""
        success, response = self.run_test(
            "Get Spending Insights (30 days)",
            "GET",
            "/api/v1/insights/spending?days=30",
            200,
            token=self.customer_token,
            description="Fetch spending breakdown by category for last 30 days"
        )
        if success:
            # Check response structure
            if 'total' in response and 'categories' in response:
                print(f"   ✓ Response structure correct: total={response['total']}, categories={list(response['categories'].keys())}")
                print(f"   ✓ Total spending: €{response['total']/100:.2f}")
                if response['categories']:
                    for category, amount in response['categories'].items():
                        print(f"   ✓ {category}: €{amount/100:.2f}")
                return True
            else:
                print(f"   ⚠️  Response structure incorrect: {list(response.keys())}")
                return False
        return False

    def test_get_monthly_spending(self):
        """Test getting monthly spending (current calendar month)"""
        success, response = self.run_test(
            "Get Monthly Spending",
            "GET",
            "/api/v1/insights/monthly-spending",
            200,
            token=self.customer_token,
            description="Fetch spending for current calendar month from real ledger data"
        )
        if success:
            # Check response structure
            required_fields = ['total', 'transaction_count', 'categories', 'period']
            missing_fields = [f for f in required_fields if f not in response]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
                return False
            
            print(f"   ✓ Response structure correct")
            print(f"   ✓ Total spending: €{response['total']/100:.2f}")
            print(f"   ✓ Transaction count: {response['transaction_count']}")
            print(f"   ✓ Period: {response['period']['start'][:10]} to {response['period']['end'][:10]}")
            
            if response['categories']:
                print(f"   ✓ Categories breakdown:")
                for category, amount in response['categories'].items():
                    print(f"      - {category}: €{amount/100:.2f}")
            else:
                print(f"   ✓ No spending this month (categories empty)")
            
            # Verify it's NOT the old hardcoded value
            if response['total'] == 85000:  # €850.00 in cents
                print(f"   ⚠️  WARNING: Still returning hardcoded €850.00!")
                return False
            
            return True
        return False

    def test_admin_disable_user(self, user_id):
        """Test admin disabling a user"""
        success, response = self.run_test(
            "Admin - Disable User",
            "PATCH",
            f"/api/v1/admin/users/{user_id}/status",
            200,
            data={"status": "DISABLED"},
            token=self.admin_token,
            description="Admin disables a user account"
        )
        if success:
            print(f"   ✓ User disabled successfully")
            return True
        return False

    def test_admin_enable_user(self, user_id):
        """Test admin enabling a user"""
        success, response = self.run_test(
            "Admin - Enable User",
            "PATCH",
            f"/api/v1/admin/users/{user_id}/status",
            200,
            data={"status": "ACTIVE"},
            token=self.admin_token,
            description="Admin enables a user account"
        )
        if success:
            print(f"   ✓ User enabled successfully")
            return True
        return False

    def test_disabled_user_login(self, email, password):
        """Test that disabled user cannot login"""
        success, response = self.run_test(
            "Disabled User Login (Should Fail)",
            "POST",
            "/api/v1/auth/login",
            403,
            data={"email": email, "password": password},
            description="Attempt to login with disabled account - should return 403"
        )
        if success:
            # Check the error message
            if response.get('detail') == "Account is disabled. Please contact support.":
                print(f"   ✓ Correct error message: '{response.get('detail')}'")
                return True
            else:
                print(f"   ⚠️  Wrong error message: '{response.get('detail')}'")
                print(f"   Expected: 'Account is disabled. Please contact support.'")
                return False
        return False

    def test_active_user_login(self, email, password):
        """Test that active user can login"""
        success, response = self.run_test(
            "Active User Login (Should Succeed)",
            "POST",
            "/api/v1/auth/login",
            200,
            data={"email": email, "password": password},
            description="Login with active account - should succeed"
        )
        if success and 'access_token' in response:
            print(f"   ✓ Login successful, token obtained")
            return True
        return False


def main():
    print("=" * 70)
    print("PROJECT ATLAS - BACKEND API TESTING")
    print("=" * 70)
    
    tester = AtlasBankingAPITester()
    
    # Run tests in order
    print("\n" + "=" * 70)
    print("SECTION 1: AUTHENTICATION")
    print("=" * 70)
    
    if not tester.test_health_check():
        print("\n❌ Health check failed - API may be down")
        return 1
    
    if not tester.test_customer_login():
        print("\n❌ Customer login failed - stopping tests")
        return 1
    
    if not tester.test_admin_login():
        print("\n❌ Admin login failed - stopping tests")
        return 1
    
    print("\n" + "=" * 70)
    print("SECTION 2: DISABLED USER LOGIN BUG FIX TESTING")
    print("=" * 70)
    print("Testing the fix: Disabled users should NOT be able to login")
    
    # Get customer user ID for testing
    customer_email = "customer@demo.com"
    customer_password = "Demo@123456"
    
    # First, get all users to find customer ID
    success, users_response = tester.run_test(
        "Get Customer User ID",
        "GET",
        "/api/v1/admin/users",
        200,
        token=tester.admin_token,
        description="Find customer user ID for testing"
    )
    
    customer_user_id = None
    if success and isinstance(users_response, list):
        for user in users_response:
            if user.get('email') == customer_email:
                customer_user_id = user.get('id')
                print(f"   ✓ Found customer user ID: {customer_user_id}")
                break
    
    if not customer_user_id:
        print("\n❌ Could not find customer user ID - stopping disabled user tests")
    else:
        # Test 1: Verify active user can login
        print("\n--- Test 1: Active User Login ---")
        if not tester.test_active_user_login(customer_email, customer_password):
            print("❌ Active user login failed")
        
        # Test 2: Admin disables the user
        print("\n--- Test 2: Admin Disables User ---")
        if not tester.test_admin_disable_user(customer_user_id):
            print("❌ Failed to disable user")
        
        # Test 3: Disabled user tries to login (should fail with 403)
        print("\n--- Test 3: Disabled User Login Attempt ---")
        if not tester.test_disabled_user_login(customer_email, customer_password):
            print("❌ Disabled user login test failed")
        
        # Test 4: Admin re-enables the user
        print("\n--- Test 4: Admin Re-enables User ---")
        if not tester.test_admin_enable_user(customer_user_id):
            print("❌ Failed to re-enable user")
        
        # Test 5: Re-enabled user can login again
        print("\n--- Test 5: Re-enabled User Login ---")
        if not tester.test_active_user_login(customer_email, customer_password):
            print("❌ Re-enabled user login failed")
        else:
            # Update the customer token for subsequent tests
            tester.customer_token = None
            tester.test_customer_login()
    
    print("\n" + "=" * 70)
    print("SECTION 3: CUSTOMER FEATURES")
    print("=" * 70)
    
    tester.test_get_customer_accounts()
    tester.test_get_kyc_application()
    tester.test_get_notifications()
    tester.test_get_transactions()
    tester.test_p2p_transfer()
    
    print("\n" + "=" * 70)
    print("SECTION 4: ADVANCED BANKING FEATURES")
    print("=" * 70)
    
    tester.test_add_beneficiary()
    tester.test_get_beneficiaries()
    tester.test_create_scheduled_payment()
    tester.test_get_scheduled_payments()
    
    print("\n" + "=" * 70)
    print("SECTION 5: SPENDING INSIGHTS (REAL LEDGER DATA)")
    print("=" * 70)
    print("Testing the new feature: Real spending calculation from ledger")
    
    tester.test_get_spending_insights()
    tester.test_get_monthly_spending()
    
    print("\n" + "=" * 70)
    print("SECTION 5: ADMIN FEATURES")
    print("=" * 70)
    
    tester.test_admin_get_users()
    tester.test_admin_get_user_details()
    tester.test_admin_get_kyc_pending()
    tester.test_admin_get_audit_logs()
    
    # Print final results
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    print("=" * 70)
    
    return 0 if tester.tests_passed == tester.tests_run else 1


if __name__ == "__main__":
    sys.exit(main())
