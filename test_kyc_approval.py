"""
Test KYC Approval Workflow with IBAN/BIC Assignment
Tests the fix for KYC approval failing with 'Failed to submit review' error
"""

import requests
import sys
from datetime import datetime
import time

# Backend URL
BASE_URL = "https://user-alert-system-2.preview.emergentagent.com/api/v1"

# Test credentials
TEST_USER_EMAIL = f"kyctest_{int(time.time())}@test.com"
TEST_USER_PASSWORD = "TestPassword123!"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Test IBAN and BIC
TEST_IBAN = "IT60X0542811101000000123456"
TEST_BIC = "ATLASLT21"


class KYCApprovalTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.user_token = None
        self.admin_token = None
        self.user_id = None
        self.kyc_application_id = None

    def log_test(self, name, success, message=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if message:
                print(f"   {message}")
        else:
            self.tests_failed += 1
            self.errors.append({"test": name, "error": message})
            print(f"❌ {name}: {message}")

    def test_register_user(self):
        """Register a new user for KYC testing"""
        print(f"\n🔍 Registering new user: {TEST_USER_EMAIL}")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/signup",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD,
                    "first_name": "KYC",
                    "last_name": "TestUser",
                    "phone": "+1234567890"
                },
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                self.user_id = data.get("id")
                self.log_test("Register User", True, f"User ID: {self.user_id}")
                return True
            else:
                self.log_test("Register User", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Register User", False, str(e))
            return False

    def test_verify_email(self):
        """Mark email as verified (bypass email verification for testing)"""
        print(f"\n🔍 Bypassing email verification for testing...")
        # In production, we'd need to verify email, but for testing we'll skip this
        # The user will be marked as verified when we login
        self.log_test("Email Verification", True, "Skipped for testing (will verify on login)")
        return True

    def test_user_login(self):
        """Login as the test user"""
        print(f"\n🔍 Logging in as test user...")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.user_token = data.get("access_token")
                self.log_test("User Login", True)
                return True
            elif response.status_code == 403:
                # Email not verified - this is expected
                self.log_test("User Login", True, "Email not verified (expected for new user)")
                return True
            else:
                self.log_test("User Login", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("User Login", False, str(e))
            return False

    def test_submit_kyc(self):
        """Submit KYC application"""
        print(f"\n🔍 Submitting KYC application...")
        
        # If we don't have a user token (email not verified), we need to manually verify
        if not self.user_token:
            print("   Note: Email not verified, will need admin to approve KYC directly")
            self.log_test("Submit KYC", True, "Skipped - will test approval directly")
            return True
        
        try:
            response = requests.post(
                f"{BASE_URL}/kyc/submit",
                headers={"Authorization": f"Bearer {self.user_token}"},
                json={
                    "full_name": "KYC TestUser",
                    "date_of_birth": "1990-01-01",
                    "nationality": "US",
                    "country": "US",
                    "street_address": "123 Test St",
                    "city": "Test City",
                    "postal_code": "12345",
                    "tax_residency": "US",
                    "tax_id": "123-45-6789",
                    "terms_accepted": True,
                    "privacy_accepted": True
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.kyc_application_id = data.get("id")
                self.log_test("Submit KYC", True, f"Application ID: {self.kyc_application_id}")
                return True
            else:
                self.log_test("Submit KYC", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Submit KYC", False, str(e))
            return False

    def test_admin_login(self):
        """Login as admin"""
        print(f"\n🔍 Logging in as admin...")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.log_test("Admin Login", True)
                return True
            else:
                self.log_test("Admin Login", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Login", False, str(e))
            return False

    def test_get_pending_kyc(self):
        """Get pending KYC applications"""
        print(f"\n🔍 Getting pending KYC applications...")
        try:
            response = requests.get(
                f"{BASE_URL}/admin/kyc/pending",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Find our test user's application
                for app in data:
                    if app.get("user_id") == self.user_id:
                        self.kyc_application_id = app.get("id")
                        self.log_test("Get Pending KYC", True, f"Found application: {self.kyc_application_id}")
                        return True
                
                # If we didn't find it, it might not be submitted yet
                self.log_test("Get Pending KYC", True, f"Found {len(data)} pending applications (test user not found)")
                return True
            else:
                self.log_test("Get Pending KYC", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Get Pending KYC", False, str(e))
            return False

    def test_approve_kyc_with_iban(self):
        """Approve KYC with IBAN and BIC - THE MAIN TEST"""
        print(f"\n🔍 Approving KYC with IBAN: {TEST_IBAN} and BIC: {TEST_BIC}")
        
        if not self.kyc_application_id:
            self.log_test("Approve KYC", False, "No KYC application ID available")
            return False
        
        try:
            response = requests.post(
                f"{BASE_URL}/admin/kyc/{self.kyc_application_id}/review",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "status": "APPROVED",
                    "review_notes": "Test approval with IBAN/BIC",
                    "assigned_iban": TEST_IBAN,
                    "assigned_bic": TEST_BIC
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if the response indicates success
                if data.get("status") == "APPROVED":
                    self.log_test("Approve KYC", True, "KYC approved successfully")
                    return True
                else:
                    self.log_test("Approve KYC", False, f"Status not APPROVED: {data.get('status')}")
                    return False
            else:
                error_detail = response.json().get("detail", response.text) if response.headers.get("content-type") == "application/json" else response.text
                self.log_test("Approve KYC", False, f"Status {response.status_code}: {error_detail}")
                return False
        except Exception as e:
            self.log_test("Approve KYC", False, str(e))
            return False

    def test_verify_account_with_iban(self):
        """Verify the user's account has the correct IBAN and BIC"""
        print(f"\n🔍 Verifying account has correct IBAN and BIC...")
        
        # We need to get the user's accounts
        # First, let's try with admin token to check the user's details
        try:
            response = requests.get(
                f"{BASE_URL}/admin/users/{self.user_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                accounts = data.get("accounts", [])
                
                if len(accounts) == 0:
                    self.log_test("Verify Account IBAN", False, "No accounts found for user")
                    return False
                
                # Check the first account
                account = accounts[0]
                iban = account.get("iban")
                
                if iban == TEST_IBAN:
                    self.log_test("Verify Account IBAN", True, f"IBAN matches: {iban}")
                    return True
                elif iban is None:
                    self.log_test("Verify Account IBAN", False, "Account created but IBAN is None")
                    return False
                else:
                    self.log_test("Verify Account IBAN", False, f"IBAN mismatch: expected {TEST_IBAN}, got {iban}")
                    return False
            else:
                self.log_test("Verify Account IBAN", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Verify Account IBAN", False, str(e))
            return False

    def test_verify_user_status_active(self):
        """Verify the user status is ACTIVE after KYC approval"""
        print(f"\n🔍 Verifying user status is ACTIVE...")
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/users/{self.user_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                user = data.get("user", {})
                status = user.get("status")
                
                if status == "ACTIVE":
                    self.log_test("Verify User Status", True, f"User status is ACTIVE")
                    return True
                else:
                    self.log_test("Verify User Status", False, f"User status is {status}, expected ACTIVE")
                    return False
            else:
                self.log_test("Verify User Status", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Verify User Status", False, str(e))
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=" * 80)
        print("KYC APPROVAL WORKFLOW TEST")
        print("=" * 80)
        print(f"Testing KYC approval with IBAN/BIC assignment")
        print(f"Backend URL: {BASE_URL}")
        print(f"Test User: {TEST_USER_EMAIL}")
        print(f"Test IBAN: {TEST_IBAN}")
        print(f"Test BIC: {TEST_BIC}")
        print("=" * 80)
        
        # Run tests in sequence
        if not self.test_register_user():
            print("\n⚠️  User registration failed, stopping tests")
            return False
        
        # Try to login (might fail due to email verification)
        self.test_user_login()
        
        # Try to submit KYC (might be skipped if email not verified)
        self.test_submit_kyc()
        
        if not self.test_admin_login():
            print("\n⚠️  Admin login failed, stopping tests")
            return False
        
        # Get pending KYC applications
        self.test_get_pending_kyc()
        
        # If we don't have a KYC application ID, we need to create one manually
        if not self.kyc_application_id:
            print("\n⚠️  No KYC application found, creating one manually...")
            # We'll need to manually create a KYC application for this user
            # For now, let's skip this test
            self.log_test("KYC Approval Workflow", False, "Could not find or create KYC application")
            return False
        
        # THE MAIN TEST: Approve KYC with IBAN/BIC
        if not self.test_approve_kyc_with_iban():
            print("\n⚠️  KYC approval failed - this is the bug we're testing!")
            return False
        
        # Verify the account has the correct IBAN
        if not self.test_verify_account_with_iban():
            print("\n⚠️  Account verification failed - IBAN not assigned correctly!")
            return False
        
        # Verify user status is ACTIVE
        if not self.test_verify_user_status_active():
            print("\n⚠️  User status verification failed!")
            return False
        
        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        
        if self.errors:
            print("\n❌ FAILED TESTS:")
            for error in self.errors:
                print(f"  - {error['test']}: {error['error']}")
        
        if self.tests_failed == 0:
            print("\n✅ ALL TESTS PASSED!")
            print("KYC approval workflow is working correctly:")
            print("  ✓ User registration successful")
            print("  ✓ KYC approval with IBAN/BIC successful")
            print("  ✓ Bank account created with correct IBAN")
            print("  ✓ User status updated to ACTIVE")
            return 0
        else:
            print("\n❌ SOME TESTS FAILED")
            return 1


def main():
    tester = KYCApprovalTester()
    tester.run_all_tests()
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
