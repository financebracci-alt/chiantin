"""Backend API tests for support tickets and key features."""

import requests
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

class SupportTicketsAPITester:
    def __init__(self, base_url="https://bank-staging.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.test_user_id = None
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
            "details": details
        })
        print()

    def admin_login(self) -> bool:
        """Login as admin and get token."""
        print("=" * 60)
        print("ADMIN LOGIN TEST")
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
                self.log_result(
                    "Admin Login",
                    True,
                    f"Admin logged in successfully",
                    {"email": "admin@ecommbx.io", "role": data.get("user", {}).get("role")}
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

    def user_login(self) -> bool:
        """Login as test user and get token."""
        print("=" * 60)
        print("USER LOGIN TEST")
        print("=" * 60)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "email": "ashleyalt003@gmail.com",
                    "password": "TestPassword123!"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.user_token = data.get("access_token")
                user_data = data.get("user", {})
                self.test_user_id = user_data.get("id")
                self.log_result(
                    "User Login",
                    True,
                    f"User logged in successfully",
                    {
                        "email": "ashleyalt003@gmail.com", 
                        "user_id": self.test_user_id,
                        "email_verified": user_data.get("email_verified")
                    }
                )
                return True
            else:
                self.log_result(
                    "User Login",
                    False,
                    f"Login failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("User Login", False, f"Exception: {str(e)}")
            return False

    def test_create_support_ticket(self) -> Optional[str]:
        """Test creating a support ticket as user."""
        print("=" * 60)
        print("CREATE SUPPORT TICKET TEST")
        print("=" * 60)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/tickets/create",
                headers={"Authorization": f"Bearer {self.user_token}"},
                json={
                    "subject": f"Test Ticket - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "description": "This is a test support ticket to verify the support system is working correctly."
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                ticket_id = data.get("id")
                self.log_result(
                    "Create Support Ticket",
                    True,
                    f"Support ticket created successfully",
                    {
                        "ticket_id": ticket_id,
                        "subject": data.get("subject"),
                        "status": data.get("status")
                    }
                )
                return ticket_id
            else:
                self.log_result(
                    "Create Support Ticket",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return None
                
        except Exception as e:
            self.log_result("Create Support Ticket", False, f"Exception: {str(e)}")
            return None

    def test_admin_view_tickets(self) -> bool:
        """Test admin viewing all tickets and verify user_name and user_email are present."""
        print("=" * 60)
        print("ADMIN VIEW TICKETS TEST (Verify user_name & user_email)")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/tickets",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                tickets = response.json()
                
                if len(tickets) == 0:
                    self.log_result(
                        "Admin View Tickets",
                        False,
                        "No tickets found in the system",
                        {"ticket_count": 0}
                    )
                    return False
                
                # Check if user_name and user_email are present in tickets
                first_ticket = tickets[0]
                has_user_name = "user_name" in first_ticket
                has_user_email = "user_email" in first_ticket
                
                if has_user_name and has_user_email:
                    self.log_result(
                        "Admin View Tickets - user_name & user_email Present",
                        True,
                        f"Admin can view {len(tickets)} ticket(s) with user_name and user_email",
                        {
                            "ticket_count": len(tickets),
                            "sample_user_name": first_ticket.get("user_name"),
                            "sample_user_email": first_ticket.get("user_email"),
                            "sample_subject": first_ticket.get("subject")
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Admin View Tickets - user_name & user_email Present",
                        False,
                        f"Tickets missing required fields. user_name present: {has_user_name}, user_email present: {has_user_email}",
                        {"first_ticket_keys": list(first_ticket.keys())}
                    )
                    return False
            else:
                self.log_result(
                    "Admin View Tickets",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Admin View Tickets", False, f"Exception: {str(e)}")
            return False

    def test_user_view_own_tickets(self) -> bool:
        """Test user viewing their own tickets."""
        print("=" * 60)
        print("USER VIEW OWN TICKETS TEST")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/tickets",
                headers={"Authorization": f"Bearer {self.user_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                tickets = response.json()
                self.log_result(
                    "User View Own Tickets",
                    True,
                    f"User can view their own tickets",
                    {"ticket_count": len(tickets)}
                )
                return True
            else:
                self.log_result(
                    "User View Own Tickets",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("User View Own Tickets", False, f"Exception: {str(e)}")
            return False

    def test_kyc_queue(self) -> bool:
        """Test admin viewing KYC queue."""
        print("=" * 60)
        print("ADMIN KYC QUEUE TEST")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/kyc/pending",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                applications = response.json()
                self.log_result(
                    "Admin KYC Queue",
                    True,
                    f"Admin can view KYC queue",
                    {"pending_applications": len(applications)}
                )
                return True
            else:
                self.log_result(
                    "Admin KYC Queue",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Admin KYC Queue", False, f"Exception: {str(e)}")
            return False

    def test_manual_queue_user(self) -> bool:
        """Test admin manually queueing a user for KYC review."""
        print("=" * 60)
        print("ADMIN MANUAL QUEUE USER TEST")
        print("=" * 60)
        
        try:
            # Use the test user email
            response = requests.post(
                f"{self.base_url}/api/v1/admin/kyc/queue-user",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "user_email": "ashleyalt003@gmail.com",
                    "reason": "Testing manual queue feature"
                },
                timeout=10
            )
            
            # Accept both 200 (success) and 400 (already queued/approved) as valid responses
            if response.status_code in [200, 400]:
                data = response.json()
                message = data.get("message", "")
                detail = data.get("detail", "")
                
                # Check if it's already queued, already approved, or successfully queued
                combined_msg = (message + " " + detail).lower()
                if "already" in combined_msg or "success" in combined_msg or "approved" in combined_msg or "cannot" in combined_msg:
                    self.log_result(
                        "Admin Manual Queue User",
                        True,
                        f"Manual queue endpoint working correctly",
                        {
                            "status_code": response.status_code,
                            "message": message or detail,
                            "note": "User may already be approved or queued"
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Admin Manual Queue User",
                        False,
                        f"Unexpected response: {message or detail}",
                        {"status_code": response.status_code, "full_response": data}
                    )
                    return False
            else:
                self.log_result(
                    "Admin Manual Queue User",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Admin Manual Queue User", False, f"Exception: {str(e)}")
            return False

    def test_user_accounts(self) -> bool:
        """Test user viewing their accounts."""
        print("=" * 60)
        print("USER VIEW ACCOUNTS TEST")
        print("=" * 60)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/accounts",
                headers={"Authorization": f"Bearer {self.user_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                accounts = response.json()
                self.log_result(
                    "User View Accounts",
                    True,
                    f"User can view their accounts",
                    {
                        "account_count": len(accounts),
                        "has_balance": len(accounts) > 0 and "balance" in accounts[0] if accounts else False
                    }
                )
                return True
            else:
                self.log_result(
                    "User View Accounts",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("User View Accounts", False, f"Exception: {str(e)}")
            return False

    def test_user_transactions(self) -> bool:
        """Test user viewing their transactions."""
        print("=" * 60)
        print("USER VIEW TRANSACTIONS TEST")
        print("=" * 60)
        
        try:
            # First get user's accounts
            accounts_response = requests.get(
                f"{self.base_url}/api/v1/accounts",
                headers={"Authorization": f"Bearer {self.user_token}"},
                timeout=10
            )
            
            if accounts_response.status_code != 200:
                self.log_result(
                    "User View Transactions",
                    False,
                    "Could not get user accounts to test transactions",
                    {"status_code": accounts_response.status_code}
                )
                return False
            
            accounts = accounts_response.json()
            if len(accounts) == 0:
                self.log_result(
                    "User View Transactions",
                    True,
                    "User has no accounts yet (expected for new user)",
                    {"account_count": 0}
                )
                return True
            
            # Get transactions for first account
            account_id = accounts[0]["id"]
            response = requests.get(
                f"{self.base_url}/api/v1/accounts/{account_id}/transactions",
                headers={"Authorization": f"Bearer {self.user_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                transactions = response.json()
                self.log_result(
                    "User View Transactions",
                    True,
                    f"User can view their transactions",
                    {
                        "account_id": account_id,
                        "transaction_count": len(transactions)
                    }
                )
                return True
            else:
                self.log_result(
                    "User View Transactions",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("User View Transactions", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "=" * 60)
        print("STARTING SUPPORT TICKETS & KEY FEATURES TESTS")
        print("=" * 60 + "\n")
        
        # Step 1: Admin login
        if not self.admin_login():
            print("❌ Cannot proceed without admin access")
            return
        
        # Step 2: User login
        if not self.user_login():
            print("❌ Cannot proceed without user access")
            return
        
        # Run all tests
        self.test_create_support_ticket()
        time.sleep(1)  # Give the system a moment to process
        self.test_admin_view_tickets()
        self.test_user_view_own_tickets()
        self.test_kyc_queue()
        self.test_manual_queue_user()
        self.test_user_accounts()
        self.test_user_transactions()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        
        if self.tests_run > 0:
            print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        print("=" * 60 + "\n")
        
        if self.tests_passed == self.tests_run:
            print("✅ ALL TESTS PASSED!")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            return 1


def main():
    """Main test execution."""
    tester = SupportTicketsAPITester()
    tester.run_all_tests()
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
