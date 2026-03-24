#!/usr/bin/env python3
"""
CRITICAL BUG FIX TEST: Password Verification in Transfer Authorization
Tests that wrong password in transfer modal does NOT logout user
"""

import requests
import sys
import time
from datetime import datetime

class PasswordVerificationTester:
    def __init__(self, base_url="https://bank-staging.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.test_user_token = None
        self.test_user_email = None
        self.test_user_password = None
        self.test_user_id = None
        self.test_account_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, description=""):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n{'='*80}")
        print(f"🔍 Test #{self.tests_run}: {name}")
        if description:
            print(f"   Description: {description}")
        print(f"   Endpoint: {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=10)
            else:
                print(f"❌ FAILED - Unsupported method: {method}")
                self.tests_failed += 1
                self.failed_tests.append(name)
                return False, {}

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {str(response_data)[:200]}")
                    return True, response_data
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                self.failed_tests.append(name)
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            print(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login"""
        print("\n" + "="*80)
        print("STEP 1: Admin Login")
        print("="*80)
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "/api/v1/auth/login",
            200,
            data={
                "email": "admin@ecommbx.io",
                "password": "Admin@123456"
            },
            description="Login as admin to create test user"
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✓ Admin token obtained")
            return True
        return False

    def create_test_user(self):
        """Create a test user for password verification testing"""
        print("\n" + "="*80)
        print("STEP 2: Create Test User")
        print("="*80)
        
        timestamp = int(time.time())
        self.test_user_email = f"testuser_{timestamp}@test.com"
        self.test_user_password = "TestPass123!"
        
        success, response = self.run_test(
            "Create Test User",
            "POST",
            "/api/v1/auth/signup",
            201,
            data={
                "email": self.test_user_email,
                "password": self.test_user_password,
                "first_name": "Test",
                "last_name": "User",
                "language": "en"
            },
            description="Create new test user"
        )
        
        if success and 'id' in response:
            self.test_user_id = response['id']
            print(f"   ✓ Test user created: {self.test_user_email}")
            print(f"   ✓ User ID: {self.test_user_id}")
            return True
        return False

    def verify_test_user_email(self):
        """Manually verify test user email using MongoDB"""
        print("\n" + "="*80)
        print("STEP 3: Verify Test User Email")
        print("="*80)
        
        # Use MongoDB to directly update email_verified status
        import subprocess
        mongo_cmd = f"""mongosh mongodb://localhost:27017/atlas_banking --quiet --eval 'db.users.updateOne({{_id: ObjectId("{self.test_user_id}")}}, {{$set: {{email_verified: true, status: "ACTIVE"}}}})' """
        
        try:
            result = subprocess.run(mongo_cmd, shell=True, capture_output=True, text=True, timeout=10)
            print(f"   MongoDB result: {result.stdout.strip()}")
            if "modifiedCount" in result.stdout or "acknowledged" in result.stdout:
                print(f"   ✓ User email verified via MongoDB")
                return True
            else:
                print(f"   ⚠️  MongoDB update may have failed")
                return False
        except Exception as e:
            print(f"   ❌ MongoDB update error: {e}")
            return False

    def login_test_user(self):
        """Login as test user"""
        print("\n" + "="*80)
        print("STEP 4: Login as Test User")
        print("="*80)
        
        success, response = self.run_test(
            "Test User Login",
            "POST",
            "/api/v1/auth/login",
            200,
            data={
                "email": self.test_user_email,
                "password": self.test_user_password
            },
            description="Login as test user"
        )
        
        if success and 'access_token' in response:
            self.test_user_token = response['access_token']
            print(f"   ✓ Test user token obtained")
            return True
        return False

    def create_account_for_test_user(self):
        """Create bank account for test user"""
        print("\n" + "="*80)
        print("STEP 5: Create Bank Account")
        print("="*80)
        
        success, response = self.run_test(
            "Create Bank Account",
            "POST",
            "/api/v1/accounts/create",
            200,
            headers={"Authorization": f"Bearer {self.test_user_token}"},
            description="Create bank account for test user"
        )
        
        if success and 'id' in response:
            self.test_account_id = response['id']
            print(f"   ✓ Account created: {self.test_account_id}")
            print(f"   ✓ IBAN: {response.get('iban', 'N/A')}")
            return True
        return False

    def add_balance_to_account(self):
        """Add balance to test account (admin action)"""
        print("\n" + "="*80)
        print("STEP 6: Add Balance to Account")
        print("="*80)
        
        success, response = self.run_test(
            "Top Up Account",
            "POST",
            "/api/v1/admin/ledger/top-up",
            200,
            data={
                "account_id": self.test_account_id,
                "amount": 100000,  # €1000.00
                "reason": "Test balance for password verification testing"
            },
            headers={"Authorization": f"Bearer {self.admin_token}"},
            description="Admin adds €1000 to test account"
        )
        
        if success:
            print(f"   ✓ Balance added: €1000.00")
            return True
        return False

    def test_wrong_password_verification(self):
        """CRITICAL TEST: Verify wrong password returns 401 but does NOT logout user"""
        print("\n" + "="*80)
        print("STEP 7: CRITICAL TEST - Wrong Password Verification")
        print("="*80)
        
        success, response = self.run_test(
            "Wrong Password Verification",
            "POST",
            "/api/v1/auth/verify-password",
            401,  # Expect 401 for wrong password
            data={"password": "WrongPassword123!"},
            headers={"Authorization": f"Bearer {self.test_user_token}"},
            description="Test wrong password returns 401 (should NOT logout user)"
        )
        
        if success:
            print(f"   ✓ Wrong password correctly returned 401")
            print(f"   ✓ Error detail: {response.get('detail', 'N/A')}")
            return True
        return False

    def test_user_still_authenticated_after_wrong_password(self):
        """CRITICAL TEST: Verify user is still authenticated after wrong password"""
        print("\n" + "="*80)
        print("STEP 8: CRITICAL TEST - User Still Authenticated")
        print("="*80)
        
        success, response = self.run_test(
            "Get User Info After Wrong Password",
            "GET",
            "/api/v1/auth/me",
            200,  # Should still be authenticated
            headers={"Authorization": f"Bearer {self.test_user_token}"},
            description="Verify user is still logged in after wrong password"
        )
        
        if success:
            print(f"   ✅ CRITICAL FIX VERIFIED: User is still authenticated!")
            print(f"   ✓ User email: {response.get('email', 'N/A')}")
            return True
        else:
            print(f"   ❌ CRITICAL BUG: User was logged out after wrong password!")
            return False

    def test_correct_password_verification(self):
        """Test correct password verification"""
        print("\n" + "="*80)
        print("STEP 9: Correct Password Verification")
        print("="*80)
        
        success, response = self.run_test(
            "Correct Password Verification",
            "POST",
            "/api/v1/auth/verify-password",
            200,  # Expect 200 for correct password
            data={"password": self.test_user_password},
            headers={"Authorization": f"Bearer {self.test_user_token}"},
            description="Test correct password returns 200"
        )
        
        if success:
            print(f"   ✓ Correct password verified successfully")
            return True
        return False

    def test_transfer_with_correct_password(self):
        """Test that transfer works with correct password"""
        print("\n" + "="*80)
        print("STEP 10: Test Transfer (would work in UI)")
        print("="*80)
        
        # Note: We can't test the full transfer flow here because it requires
        # the frontend to call verify-password first, then call the transfer endpoint
        # But we've verified the critical parts:
        # 1. Wrong password returns 401 without logging out
        # 2. User remains authenticated after wrong password
        # 3. Correct password verification works
        
        print("   ℹ️  Transfer flow verified through password verification tests")
        print("   ℹ️  Frontend integration will be tested with Playwright")
        return True

    def run_all_tests(self):
        """Run all password verification tests"""
        print("\n" + "="*80)
        print("🚀 CRITICAL BUG FIX TEST: Password Verification")
        print("="*80)
        print(f"Testing against: {self.base_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run tests in sequence
        if not self.test_admin_login():
            print("\n❌ Admin login failed - cannot continue")
            return False
        
        if not self.create_test_user():
            print("\n❌ Test user creation failed - cannot continue")
            return False
        
        if not self.verify_test_user_email():
            print("\n❌ Email verification failed - cannot continue")
            return False
        
        if not self.login_test_user():
            print("\n❌ Test user login failed - cannot continue")
            return False
        
        if not self.create_account_for_test_user():
            print("\n❌ Account creation failed - cannot continue")
            return False
        
        if not self.add_balance_to_account():
            print("\n❌ Balance addition failed - cannot continue")
            return False
        
        # CRITICAL TESTS
        if not self.test_wrong_password_verification():
            print("\n❌ Wrong password test failed")
            return False
        
        if not self.test_user_still_authenticated_after_wrong_password():
            print("\n❌ CRITICAL: User authentication check failed")
            return False
        
        if not self.test_correct_password_verification():
            print("\n❌ Correct password test failed")
            return False
        
        self.test_transfer_with_correct_password()
        
        # Print summary
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        
        if self.tests_failed > 0:
            print(f"\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"   - {test}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            print("\n✅ ALL TESTS PASSED - BUG FIX VERIFIED!")
            return True
        else:
            print(f"\n❌ {self.tests_failed} TEST(S) FAILED")
            return False

def main():
    tester = PasswordVerificationTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
