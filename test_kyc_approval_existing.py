"""
Test KYC Approval Workflow with IBAN/BIC Assignment
Uses existing pending KYC application
"""

import requests
import sys

# Backend URL
BASE_URL = "https://file-download-debug.preview.emergentagent.com/api/v1"

# Admin credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Test IBAN and BIC
TEST_IBAN = "IT60X0542811101000000123456"
TEST_BIC = "ATLSLT21"  # 8 characters (valid BIC format)


class KYCApprovalTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.admin_token = None
        self.kyc_application_id = None
        self.user_id = None

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
                
                if len(data) > 0:
                    # Use the first pending application
                    app = data[0]
                    self.kyc_application_id = app.get("id")
                    self.user_id = app.get("user_id")
                    self.log_test("Get Pending KYC", True, f"Found application: {self.kyc_application_id} for user: {self.user_id}")
                    return True
                else:
                    self.log_test("Get Pending KYC", False, "No pending KYC applications found")
                    return False
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
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if the response indicates success
                if data.get("status") == "APPROVED":
                    self.log_test("Approve KYC", True, "KYC approved successfully (no 'Failed to submit review' error)")
                    return True
                else:
                    self.log_test("Approve KYC", False, f"Status not APPROVED: {data.get('status')}")
                    return False
            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except:
                    error_detail = response.text
                
                # Check if this is the "Failed to submit review" error
                if "Failed to submit review" in error_detail or "Failed to create/update bank account" in error_detail:
                    self.log_test("Approve KYC", False, f"❌ BUG DETECTED: {error_detail}")
                else:
                    self.log_test("Approve KYC", False, f"Status {response.status_code}: {error_detail}")
                return False
        except Exception as e:
            self.log_test("Approve KYC", False, str(e))
            return False

    def test_verify_account_with_iban(self):
        """Verify the user's account has the correct IBAN and BIC"""
        print(f"\n🔍 Verifying account has correct IBAN and BIC...")
        
        if not self.user_id:
            self.log_test("Verify Account IBAN", False, "No user ID available")
            return False
        
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
                    self.log_test("Verify Account IBAN", False, "❌ BUG: No accounts found for user after KYC approval")
                    return False
                
                # Check the first account
                account = accounts[0]
                iban = account.get("iban")
                
                print(f"   Account IBAN: {iban}")
                print(f"   Expected IBAN: {TEST_IBAN}")
                
                if iban == TEST_IBAN:
                    self.log_test("Verify Account IBAN", True, f"✓ IBAN matches: {iban}")
                    return True
                elif iban is None:
                    self.log_test("Verify Account IBAN", False, "❌ BUG: Account created but IBAN is None")
                    return False
                else:
                    self.log_test("Verify Account IBAN", False, f"❌ BUG: IBAN mismatch: expected {TEST_IBAN}, got {iban}")
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
        
        if not self.user_id:
            self.log_test("Verify User Status", False, "No user ID available")
            return False
        
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
                
                print(f"   User status: {status}")
                
                if status == "ACTIVE":
                    self.log_test("Verify User Status", True, f"✓ User status is ACTIVE")
                    return True
                else:
                    self.log_test("Verify User Status", False, f"❌ User status is {status}, expected ACTIVE")
                    return False
            else:
                self.log_test("Verify User Status", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Verify User Status", False, str(e))
            return False

    def test_verify_kyc_status(self):
        """Verify the KYC status is APPROVED"""
        print(f"\n🔍 Verifying KYC status is APPROVED...")
        
        if not self.kyc_application_id:
            self.log_test("Verify KYC Status", False, "No KYC application ID available")
            return False
        
        try:
            # Get all pending KYC applications (should not include our approved one)
            response = requests.get(
                f"{BASE_URL}/admin/kyc/pending",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if our application is still in the pending list
                for app in data:
                    if app.get("id") == self.kyc_application_id:
                        self.log_test("Verify KYC Status", False, f"❌ KYC application still in pending list with status: {app.get('status')}")
                        return False
                
                self.log_test("Verify KYC Status", True, "✓ KYC application no longer in pending list (approved)")
                return True
            else:
                self.log_test("Verify KYC Status", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Verify KYC Status", False, str(e))
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=" * 80)
        print("KYC APPROVAL WORKFLOW TEST")
        print("=" * 80)
        print(f"Testing KYC approval with IBAN/BIC assignment")
        print(f"Backend URL: {BASE_URL}")
        print(f"Test IBAN: {TEST_IBAN}")
        print(f"Test BIC: {TEST_BIC}")
        print("=" * 80)
        
        # Run tests in sequence
        if not self.test_admin_login():
            print("\n⚠️  Admin login failed, stopping tests")
            return False
        
        if not self.test_get_pending_kyc():
            print("\n⚠️  No pending KYC applications found, stopping tests")
            return False
        
        # THE MAIN TEST: Approve KYC with IBAN/BIC
        if not self.test_approve_kyc_with_iban():
            print("\n⚠️  KYC approval failed - this is the bug we're testing!")
            # Continue to check what happened
        
        # Verify the account has the correct IBAN
        self.test_verify_account_with_iban()
        
        # Verify user status is ACTIVE
        self.test_verify_user_status_active()
        
        # Verify KYC status is APPROVED
        self.test_verify_kyc_status()
        
        return self.tests_failed == 0

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
            print("  ✓ KYC approval with IBAN/BIC successful (no 'Failed to submit review' error)")
            print("  ✓ Bank account created with correct IBAN")
            print("  ✓ User status updated to ACTIVE")
            print("  ✓ KYC status updated to APPROVED")
            return 0
        else:
            print("\n❌ SOME TESTS FAILED")
            print("\nPossible issues:")
            print("  - KYC approval may have failed with 'Failed to submit review' error")
            print("  - Bank account may not have been created")
            print("  - IBAN may not have been assigned correctly")
            print("  - User status may not have been updated to ACTIVE")
            return 1


def main():
    tester = KYCApprovalTester()
    tester.run_all_tests()
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
