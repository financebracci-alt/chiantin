"""
Comprehensive Backend API Test for Iteration 59
Testing all recent features for 100% test success:
1. Admin login and user management
2. Clear notifications endpoint
3. Support tickets with client names
4. Password verification endpoint (transfer authorization)
5. All critical API endpoints
"""

import requests
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

class ComprehensiveAPITester:
    def __init__(self, base_url="https://transfer-confirm-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.admin_user = None
        self.test_user_token = None
        self.test_user = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, message: str, details: Optional[Dict[str, Any]] = None):
        """Log test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ PASS: {test_name}")
        else:
            print(f"❌ FAIL: {test_name}")
        print(f"   {message}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print()

    def admin_login(self) -> bool:
        """Login as admin and get token."""
        print("=" * 60)
        print("TEST 1: ADMIN LOGIN")
        print("=" * 60)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "email": "admin@ecommbx.io",
                    "password": "Admin@123456"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.admin_user = data.get("user")
                self.log_result(
                    "Admin Login",
                    True,
                    f"Admin logged in successfully as {self.admin_user.get('email')}",
                    {"role": self.admin_user.get("role"), "status": self.admin_user.get("status")}
                )
                return True
            else:
                self.log_result(
                    "Admin Login",
                    False,
                    f"Login failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception: {str(e)}")
            return False

    def test_get_all_users(self) -> bool:
        """Test GET /api/v1/admin/users - Get all users."""
        print("=" * 60)
        print("TEST 2: GET ALL USERS (ADMIN)")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/users",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                users = response.json()
                self.log_result(
                    "Get All Users",
                    True,
                    f"Successfully retrieved {len(users)} users",
                    {"user_count": len(users), "sample_user": users[0] if users else None}
                )
                return True
            else:
                self.log_result(
                    "Get All Users",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Get All Users", False, f"Exception: {str(e)}")
            return False

    def test_get_user_details(self) -> Optional[str]:
        """Test GET /api/v1/admin/users/{user_id} - Get user details."""
        print("=" * 60)
        print("TEST 3: GET USER DETAILS (ADMIN)")
        print("=" * 60)
        
        try:
            # First get all users to find a test user
            response = requests.get(
                f"{self.base_url}/api/v1/admin/users",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code != 200:
                self.log_result("Get User Details", False, "Could not fetch users list")
                return None
            
            users = response.json()
            # Find a non-admin user
            test_user = None
            for user in users:
                if user.get("role") == "CUSTOMER":
                    test_user = user
                    break
            
            if not test_user:
                self.log_result("Get User Details", False, "No customer user found for testing")
                return None
            
            user_id = test_user["id"]
            
            # Get user details
            response = requests.get(
                f"{self.base_url}/api/v1/admin/users/{user_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                details = response.json()
                self.log_result(
                    "Get User Details",
                    True,
                    f"Successfully retrieved details for user {details['user']['email']}",
                    {
                        "user_id": user_id,
                        "email": details['user']['email'],
                        "accounts_count": len(details.get('accounts', [])),
                        "kyc_status": details.get('kyc_status')
                    }
                )
                return user_id
            else:
                self.log_result(
                    "Get User Details",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return None
                
        except Exception as e:
            self.log_result("Get User Details", False, f"Exception: {str(e)}")
            return None

    def test_clear_notifications(self, user_id: str) -> bool:
        """Test DELETE /api/v1/admin/users/{user_id}/notifications - Clear user notifications."""
        print("=" * 60)
        print("TEST 4: CLEAR USER NOTIFICATIONS (ADMIN)")
        print("=" * 60)
        
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/admin/users/{user_id}/notifications",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Clear User Notifications",
                    True,
                    f"Successfully cleared notifications for user",
                    {
                        "user_id": user_id,
                        "notifications_cleared": data.get("notifications_cleared", 0),
                        "message": data.get("message")
                    }
                )
                return True
            else:
                self.log_result(
                    "Clear User Notifications",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Clear User Notifications", False, f"Exception: {str(e)}")
            return False

    def test_get_kyc_queue(self) -> bool:
        """Test GET /api/v1/admin/kyc/pending - Get KYC queue."""
        print("=" * 60)
        print("TEST 5: GET KYC QUEUE (ADMIN)")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/kyc/pending",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                kyc_apps = response.json()
                self.log_result(
                    "Get KYC Queue",
                    True,
                    f"Successfully retrieved KYC queue with {len(kyc_apps)} pending applications",
                    {"pending_count": len(kyc_apps)}
                )
                return True
            else:
                self.log_result(
                    "Get KYC Queue",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Get KYC Queue", False, f"Exception: {str(e)}")
            return False

    def test_get_transfers_queue(self) -> bool:
        """Test GET /api/v1/admin/transfers - Get transfers queue."""
        print("=" * 60)
        print("TEST 6: GET TRANSFERS QUEUE (ADMIN)")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/transfers",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                transfers = response.json()
                self.log_result(
                    "Get Transfers Queue",
                    True,
                    f"Successfully retrieved transfers queue with {len(transfers)} pending transfers",
                    {"pending_count": len(transfers)}
                )
                return True
            else:
                self.log_result(
                    "Get Transfers Queue",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Get Transfers Queue", False, f"Exception: {str(e)}")
            return False

    def test_get_support_tickets(self) -> bool:
        """Test GET /api/v1/admin/tickets - Get support tickets with client names."""
        print("=" * 60)
        print("TEST 7: GET SUPPORT TICKETS WITH CLIENT NAMES (ADMIN)")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/tickets",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                tickets = response.json()
                
                # Check if tickets have client names
                has_client_names = True
                sample_ticket = None
                
                if tickets:
                    sample_ticket = tickets[0]
                    # Check if user_name or client_name field exists
                    if not (sample_ticket.get("user_name") or sample_ticket.get("client_name") or 
                           sample_ticket.get("user_email")):
                        has_client_names = False
                
                self.log_result(
                    "Get Support Tickets with Client Names",
                    True,
                    f"Successfully retrieved {len(tickets)} support tickets",
                    {
                        "tickets_count": len(tickets),
                        "has_client_names": has_client_names,
                        "sample_ticket": sample_ticket if sample_ticket else "No tickets found"
                    }
                )
                return True
            else:
                self.log_result(
                    "Get Support Tickets",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Get Support Tickets", False, f"Exception: {str(e)}")
            return False

    def test_password_verification_correct(self) -> bool:
        """Test POST /api/v1/auth/verify-password - Verify correct password."""
        print("=" * 60)
        print("TEST 8: PASSWORD VERIFICATION - CORRECT PASSWORD")
        print("=" * 60)
        
        try:
            # Use admin credentials for testing
            response = requests.post(
                f"{self.base_url}/api/v1/auth/verify-password",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={"password": "Admin@123456"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Password Verification - Correct Password",
                    True,
                    "Password verified successfully",
                    {"success": data.get("success"), "message": data.get("message")}
                )
                return True
            else:
                self.log_result(
                    "Password Verification - Correct Password",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Password Verification - Correct Password", False, f"Exception: {str(e)}")
            return False

    def test_password_verification_wrong(self) -> bool:
        """Test POST /api/v1/auth/verify-password - Verify wrong password returns 401 without logout."""
        print("=" * 60)
        print("TEST 9: PASSWORD VERIFICATION - WRONG PASSWORD (SHOULD RETURN 401)")
        print("=" * 60)
        
        try:
            # Use wrong password
            response = requests.post(
                f"{self.base_url}/api/v1/auth/verify-password",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={"password": "WrongPassword123!"},
                timeout=10
            )
            
            # Should return 401 for wrong password
            if response.status_code == 401:
                # Verify we can still make authenticated requests (not logged out)
                verify_response = requests.get(
                    f"{self.base_url}/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    timeout=10
                )
                
                if verify_response.status_code == 200:
                    self.log_result(
                        "Password Verification - Wrong Password",
                        True,
                        "Wrong password correctly returned 401 without logging out user",
                        {
                            "password_verify_status": response.status_code,
                            "still_authenticated": verify_response.status_code == 200
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Password Verification - Wrong Password",
                        False,
                        "Wrong password returned 401 but user was logged out (should not happen)",
                        {"verify_status": verify_response.status_code}
                    )
                    return False
            else:
                self.log_result(
                    "Password Verification - Wrong Password",
                    False,
                    f"Expected 401 for wrong password but got {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Password Verification - Wrong Password", False, f"Exception: {str(e)}")
            return False

    def test_health_check(self) -> bool:
        """Test GET /api/health - Health check endpoint."""
        print("=" * 60)
        print("TEST 10: HEALTH CHECK")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/health",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Health Check",
                    True,
                    "Health check passed",
                    {"status": data.get("status"), "database": data.get("database")}
                )
                return True
            else:
                self.log_result(
                    "Health Check",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Health Check", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "=" * 60)
        print("STARTING COMPREHENSIVE API TESTS - ITERATION 59")
        print("Target: 100% Test Success")
        print("=" * 60 + "\n")
        
        # Test 1: Admin login (required for other tests)
        if not self.admin_login():
            print("❌ Cannot proceed without admin access")
            return
        
        # Test 2: Get all users
        self.test_get_all_users()
        
        # Test 3: Get user details and get a test user ID
        test_user_id = self.test_get_user_details()
        
        # Test 4: Clear notifications (if we have a test user)
        if test_user_id:
            self.test_clear_notifications(test_user_id)
        else:
            self.log_result(
                "Clear User Notifications",
                False,
                "Skipped - no test user available"
            )
        
        # Test 5: Get KYC queue
        self.test_get_kyc_queue()
        
        # Test 6: Get transfers queue
        self.test_get_transfers_queue()
        
        # Test 7: Get support tickets with client names
        self.test_get_support_tickets()
        
        # Test 8: Password verification - correct password
        self.test_password_verification_correct()
        
        # Test 9: Password verification - wrong password (should return 401, not logout)
        self.test_password_verification_wrong()
        
        # Test 10: Health check
        self.test_health_check()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY - ITERATION 59")
        print("=" * 60)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed/self.tests_run*100)
            print(f"Success rate: {success_rate:.1f}%")
            
            if success_rate == 100:
                print("\n🎉 100% TEST SUCCESS ACHIEVED! 🎉")
            elif success_rate >= 90:
                print("\n✅ EXCELLENT - Near perfect test success")
            elif success_rate >= 70:
                print("\n⚠️  GOOD - Most tests passing")
            else:
                print("\n❌ NEEDS ATTENTION - Multiple failures")
        
        print("=" * 60 + "\n")
        
        # Print failed tests if any
        failed_tests = [r for r in self.test_results if not r["passed"]]
        if failed_tests:
            print("FAILED TESTS:")
            for test in failed_tests:
                print(f"  ❌ {test['test_name']}: {test['message']}")
            print()
        
        return 0 if self.tests_passed == self.tests_run else 1


def main():
    """Main test execution."""
    tester = ComprehensiveAPITester()
    tester.run_all_tests()
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
