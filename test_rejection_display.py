"""
Test money transfer rejection display issues
Tests that rejected transfers show correct status and rejection reason
"""

import requests
import sys
from datetime import datetime

# Backend URL
BASE_URL = "https://file-download-debug.preview.emergentagent.com/api/v1"

# Test credentials
TEST_USER_EMAIL = "ashleyalt004@gmail.com"
TEST_USER_PASSWORD = "TestPassword123!"

class RejectionDisplayTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.token = None
        self.user = None
        self.accounts = []
        self.transactions = []

    def log_test(self, name, success, message=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if message:
                print(f"   ℹ️  {message}")
        else:
            self.tests_failed += 1
            self.errors.append({"test": name, "error": message})
            print(f"❌ {name}: {message}")

    def test_login(self):
        """Test login with test user"""
        print("\n🔐 Testing Login...")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.token = data["access_token"]
                    self.user = data["user"]
                    self.log_test("Login", True, f"Logged in as {self.user.get('email')}")
                    return True
                else:
                    self.log_test("Login", False, "Missing token or user in response")
                    return False
            else:
                self.log_test("Login", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Login", False, str(e))
            return False

    def test_get_accounts(self):
        """Test getting user accounts"""
        print("\n💳 Testing Get Accounts...")
        try:
            response = requests.get(
                f"{BASE_URL}/accounts",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            if response.status_code == 200:
                self.accounts = response.json()
                if len(self.accounts) > 0:
                    self.log_test("Get Accounts", True, f"Found {len(self.accounts)} account(s)")
                    return True
                else:
                    self.log_test("Get Accounts", False, "No accounts found")
                    return False
            else:
                self.log_test("Get Accounts", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Get Accounts", False, str(e))
            return False

    def test_get_transactions(self):
        """Test getting transactions and check for rejected transfers"""
        print("\n📊 Testing Get Transactions...")
        if not self.accounts:
            self.log_test("Get Transactions", False, "No accounts available")
            return False

        try:
            account_id = self.accounts[0]["id"]
            response = requests.get(
                f"{BASE_URL}/accounts/{account_id}/transactions",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            if response.status_code == 200:
                self.transactions = response.json()
                self.log_test("Get Transactions", True, f"Retrieved {len(self.transactions)} transaction(s)")
                return True
            else:
                self.log_test("Get Transactions", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Get Transactions", False, str(e))
            return False

    def test_rejected_transfer_status(self):
        """Test that rejected transfers have correct status"""
        print("\n🚫 Testing Rejected Transfer Status...")
        
        if not self.transactions:
            self.log_test("Rejected Transfer Status", False, "No transactions to check")
            return False

        # Find rejected transfers
        rejected_transfers = [t for t in self.transactions if t.get("status") == "REJECTED"]
        
        if len(rejected_transfers) == 0:
            self.log_test("Rejected Transfer Status", False, "No rejected transfers found in transaction history")
            print("   ℹ️  Available transaction statuses:", [t.get("status") for t in self.transactions])
            return False

        # Check each rejected transfer
        all_correct = True
        for txn in rejected_transfers:
            txn_id = txn.get("id", "unknown")
            status = txn.get("status")
            
            if status != "REJECTED":
                self.log_test(f"Rejected Transfer Status (ID: {txn_id})", False, 
                             f"Expected status 'REJECTED', got '{status}'")
                all_correct = False
            else:
                self.log_test(f"Rejected Transfer Status (ID: {txn_id})", True, 
                             f"Status is correctly 'REJECTED'")

        return all_correct

    def test_rejection_reason_present(self):
        """Test that rejected transfers have rejection_reason field"""
        print("\n📝 Testing Rejection Reason Field...")
        
        if not self.transactions:
            self.log_test("Rejection Reason Field", False, "No transactions to check")
            return False

        # Find rejected transfers
        rejected_transfers = [t for t in self.transactions if t.get("status") == "REJECTED"]
        
        if len(rejected_transfers) == 0:
            self.log_test("Rejection Reason Field", False, "No rejected transfers found")
            return False

        # Check each rejected transfer for rejection_reason
        all_have_reason = True
        for txn in rejected_transfers:
            txn_id = txn.get("id", "unknown")
            rejection_reason = txn.get("rejection_reason")
            metadata_rejection = txn.get("metadata", {}).get("rejection_reason")
            
            if rejection_reason or metadata_rejection:
                reason_text = rejection_reason or metadata_rejection
                self.log_test(f"Rejection Reason (ID: {txn_id})", True, 
                             f"Reason: '{reason_text}'")
            else:
                self.log_test(f"Rejection Reason (ID: {txn_id})", False, 
                             "No rejection_reason field found")
                print(f"   ℹ️  Transaction data: {txn}")
                all_have_reason = False

        return all_have_reason

    def test_non_rejected_transfers(self):
        """Test that non-rejected transfers show correct status"""
        print("\n✅ Testing Non-Rejected Transfer Status...")
        
        if not self.transactions:
            self.log_test("Non-Rejected Transfer Status", False, "No transactions to check")
            return False

        # Find non-rejected transfers
        non_rejected = [t for t in self.transactions if t.get("status") != "REJECTED"]
        
        if len(non_rejected) == 0:
            self.log_test("Non-Rejected Transfer Status", True, "All transfers are rejected (expected for this test user)")
            return True

        # Check each non-rejected transfer
        all_correct = True
        for txn in non_rejected:
            txn_id = txn.get("id", "unknown")
            status = txn.get("status")
            
            if status in ["POSTED", "SUBMITTED", "PENDING", "COMPLETED"]:
                self.log_test(f"Non-Rejected Transfer Status (ID: {txn_id})", True, 
                             f"Status is '{status}'")
            else:
                self.log_test(f"Non-Rejected Transfer Status (ID: {txn_id})", False, 
                             f"Unexpected status '{status}'")
                all_correct = False

        return all_correct

    def test_timezone_display(self):
        """Test that timestamps are in correct timezone"""
        print("\n🕐 Testing Timezone Display...")
        
        if not self.transactions:
            self.log_test("Timezone Display", False, "No transactions to check")
            return False

        # Check timestamps
        all_correct = True
        for txn in self.transactions[:3]:  # Check first 3 transactions
            txn_id = txn.get("id", "unknown")
            created_at = txn.get("created_at")
            
            if created_at:
                # Check if timestamp ends with 'Z' or has timezone info
                if created_at.endswith('Z') or '+' in created_at or created_at.count('-') > 2:
                    self.log_test(f"Timezone Format (ID: {txn_id})", True, 
                                 f"Timestamp: {created_at}")
                else:
                    self.log_test(f"Timezone Format (ID: {txn_id})", False, 
                                 f"Timestamp missing timezone info: {created_at}")
                    all_correct = False
            else:
                self.log_test(f"Timezone Format (ID: {txn_id})", False, 
                             "No created_at timestamp")
                all_correct = False

        return all_correct

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("🧪 Money Transfer Rejection Display Tests")
        print("=" * 60)
        
        # Run tests in sequence
        if not self.test_login():
            print("\n❌ Login failed, cannot continue tests")
            return False
        
        if not self.test_get_accounts():
            print("\n❌ Get accounts failed, cannot continue tests")
            return False
        
        if not self.test_get_transactions():
            print("\n❌ Get transactions failed, cannot continue tests")
            return False
        
        # Run validation tests
        self.test_rejected_transfer_status()
        self.test_rejection_reason_present()
        self.test_non_rejected_transfers()
        self.test_timezone_display()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        
        if self.errors:
            print("\n❌ Failed Tests:")
            for error in self.errors:
                print(f"  - {error['test']}: {error['error']}")
        
        print("=" * 60)
        
        return self.tests_failed == 0


if __name__ == "__main__":
    tester = RejectionDisplayTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
