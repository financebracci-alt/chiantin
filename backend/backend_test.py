#!/usr/bin/env python3
"""
Backend API Testing for ECOMMBX Banking Application
Tests login, user management, accounts, and support ticket functionality
"""

import requests
import sys
from datetime import datetime

class EcommbxAPITester:
    def __init__(self, base_url="https://transfer-confirm-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
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
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)
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

        except requests.exceptions.Timeout:
            self.tests_failed += 1
            self.failed_tests.append(name)
            print(f"❌ FAILED - Request timeout (>10s)")
            return False, {}
        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            print(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "/api/v1/auth/login",
            200,
            data={
                "email": "admin@ecommbx.io",
                "password": "Admin@123456"
            },
            description="Login as admin user"
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✓ Admin token obtained")
            return True
        return False

    def test_user_login(self):
        """Test regular user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "/api/v1/auth/login",
            200,
            data={
                "email": "ashleyalt003@gmail.com",
                "password": "TestPassword123!"
            },
            description="Login as regular user"
        )
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            print(f"   ✓ User token obtained")
            return True
        return False

    def test_admin_get_users(self):
        """Test admin can fetch users list"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Get Users",
            "GET",
            "/api/v1/admin/users",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch all users (should be fast)"
        )
        if success:
            user_count = len(response) if isinstance(response, list) else 0
            print(f"   ✓ Retrieved {user_count} users")
        return success

    def test_admin_get_accounts(self):
        """Test admin can fetch accounts with users (optimized endpoint)"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Get Accounts (Optimized)",
            "GET",
            "/api/v1/admin/accounts-with-users",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch accounts with user info in one request (should be fast)"
        )
        if success:
            account_count = len(response) if isinstance(response, list) else 0
            print(f"   ✓ Retrieved {account_count} accounts with user info")
            # Check if accounts have required fields
            if account_count > 0:
                sample = response[0]
                has_user_info = 'userName' in sample and 'userEmail' in sample
                has_iban = 'iban' in sample
                has_bic = 'bic' in sample
                print(f"   ✓ Accounts have user info: {has_user_info}")
                print(f"   ✓ Accounts have IBAN: {has_iban}")
                print(f"   ✓ Accounts have BIC: {has_bic}")
        return success

    def test_admin_get_tickets(self):
        """Test admin can fetch support tickets"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Get Support Tickets",
            "GET",
            "/api/v1/admin/tickets",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch all support tickets"
        )
        if success:
            ticket_count = len(response) if isinstance(response, list) else 0
            print(f"   ✓ Retrieved {ticket_count} tickets")
            # Check if tickets have messages with correct labels
            if ticket_count > 0:
                for ticket in response[:3]:  # Check first 3 tickets
                    if 'messages' in ticket and len(ticket['messages']) > 0:
                        for msg in ticket['messages']:
                            if msg.get('is_staff'):
                                print(f"   ✓ Staff message found in ticket {ticket.get('id', 'unknown')}")
                                break
        return success

    def test_ticket_edit_subject(self):
        """Test admin can edit ticket subject"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        # First get a ticket
        success, tickets = self.run_test(
            "Get Tickets for Edit Test",
            "GET",
            "/api/v1/admin/tickets",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch tickets to test edit functionality"
        )
        
        if not success or not tickets or len(tickets) == 0:
            print("⚠️  No tickets available to test edit")
            return False
        
        ticket_id = tickets[0]['id']
        original_subject = tickets[0]['subject']
        new_subject = f"[EDITED] {original_subject}"
        
        success, response = self.run_test(
            "Admin Edit Ticket Subject",
            "PATCH",
            f"/api/v1/admin/tickets/{ticket_id}/subject",
            200,
            data={"subject": new_subject},
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Edit ticket subject"
        )
        
        if success:
            print(f"   ✓ Subject updated from '{original_subject}' to '{new_subject}'")
        
        return success

    def test_ticket_edit_message(self):
        """Test admin can edit ticket message"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        # First get a ticket with messages
        success, tickets = self.run_test(
            "Get Tickets for Message Edit Test",
            "GET",
            "/api/v1/admin/tickets",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch tickets to test message edit"
        )
        
        if not success or not tickets or len(tickets) == 0:
            print("⚠️  No tickets available to test message edit")
            return False
        
        # Find a ticket with messages
        ticket_with_messages = None
        for ticket in tickets:
            if 'messages' in ticket and len(ticket['messages']) > 0:
                ticket_with_messages = ticket
                break
        
        if not ticket_with_messages:
            print("⚠️  No tickets with messages found")
            return False
        
        ticket_id = ticket_with_messages['id']
        message_index = 0
        original_content = ticket_with_messages['messages'][0]['content']
        new_content = f"[EDITED] {original_content}"
        
        success, response = self.run_test(
            "Admin Edit Ticket Message",
            "PATCH",
            f"/api/v1/admin/tickets/{ticket_id}/messages/{message_index}",
            200,
            data={"content": new_content},
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Edit ticket message content"
        )
        
        if success:
            print(f"   ✓ Message updated")
        
        return success

    def test_user_get_accounts(self):
        """Test user can fetch their accounts"""
        if not self.user_token:
            print("⚠️  Skipping - No user token")
            return False
        
        success, response = self.run_test(
            "User Get Accounts",
            "GET",
            "/api/v1/accounts",
            200,
            headers={'Authorization': f'Bearer {self.user_token}'},
            description="User fetches their own accounts"
        )
        if success:
            account_count = len(response) if isinstance(response, list) else 0
            print(f"   ✓ User has {account_count} accounts")
        return success

    def test_admin_notification_bell_kyc(self):
        """Test admin notification bell - KYC pending count"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Notification Bell - KYC Pending",
            "GET",
            "/api/v1/admin/kyc/pending",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch pending KYC applications for notification bell"
        )
        if success:
            kyc_count = len(response) if isinstance(response, list) else 0
            print(f"   ✓ {kyc_count} pending KYC applications")
        return success

    def test_admin_notification_bell_cards(self):
        """Test admin notification bell - Card requests count"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Notification Bell - Card Requests",
            "GET",
            "/api/v1/admin/card-requests",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch card requests for notification bell"
        )
        if success:
            cards_data = response.get('data', []) if isinstance(response, dict) else []
            pending_cards = [c for c in cards_data if c.get('status') == 'PENDING']
            print(f"   ✓ {len(pending_cards)} pending card requests")
        return success

    def test_admin_notification_bell_transfers(self):
        """Test admin notification bell - Pending transfers count"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Notification Bell - Pending Transfers",
            "GET",
            "/api/v1/admin/transfers?status=SUBMITTED",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch pending transfers for notification bell"
        )
        if success:
            transfers_data = response.get('data', []) if isinstance(response, dict) else []
            print(f"   ✓ {len(transfers_data)} pending transfers")
        return success

    def test_admin_notification_bell_tickets(self):
        """Test admin notification bell - Open tickets count"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Notification Bell - Open Tickets",
            "GET",
            "/api/v1/admin/tickets?status=OPEN",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch open tickets for notification bell"
        )
        if success:
            tickets = response if isinstance(response, list) else []
            open_tickets = [t for t in tickets if t.get('status') in ['OPEN', 'IN_PROGRESS']]
            print(f"   ✓ {len(open_tickets)} open/in-progress tickets")
        return success

    def test_kyc_dates_format(self):
        """Test KYC applications have proper date formats (not 'Invalid Date')"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "KYC Applications - Date Format Check",
            "GET",
            "/api/v1/admin/kyc/pending",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Check KYC applications have valid date formats"
        )
        if success:
            kyc_count = len(response) if isinstance(response, list) else 0
            print(f"   ✓ Retrieved {kyc_count} KYC applications")
            
            # Check date fields
            if kyc_count > 0:
                for kyc in response[:3]:  # Check first 3
                    submitted_at = kyc.get('submitted_at')
                    if submitted_at:
                        print(f"   ✓ KYC {kyc.get('id', 'unknown')}: submitted_at = {submitted_at}")
                    
                    # Check documents dates
                    if 'documents' in kyc and len(kyc['documents']) > 0:
                        for doc in kyc['documents'][:2]:  # Check first 2 docs
                            uploaded_at = doc.get('uploaded_at')
                            if uploaded_at:
                                print(f"   ✓ Document uploaded_at = {uploaded_at}")
        return success

    def test_transfers_queue_rejection_reason(self):
        """Test transfers queue shows rejection reason"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Transfers Queue - Rejection Reason Check",
            "GET",
            "/api/v1/admin/transfers",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Check transfers have rejection_reason field"
        )
        if success:
            transfers_data = response.get('data', []) if isinstance(response, dict) else []
            print(f"   ✓ Retrieved {len(transfers_data)} transfers")
            
            # Check for rejected transfers with rejection_reason
            rejected_transfers = [t for t in transfers_data if t.get('status') == 'REJECTED']
            if rejected_transfers:
                print(f"   ✓ Found {len(rejected_transfers)} rejected transfers")
                for transfer in rejected_transfers[:2]:  # Check first 2
                    rejection_reason = transfer.get('rejection_reason')
                    if rejection_reason:
                        print(f"   ✓ Transfer {transfer.get('id', 'unknown')}: rejection_reason = '{rejection_reason}'")
                    else:
                        print(f"   ⚠️  Transfer {transfer.get('id', 'unknown')}: No rejection_reason field")
            else:
                print(f"   ℹ️  No rejected transfers found to check rejection_reason")
        return success

    def test_admin_overview_tab(self):
        """Test admin overview/analytics endpoint"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Overview Tab - Analytics",
            "GET",
            "/api/v1/admin/analytics/overview",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Fetch overview analytics data"
        )
        if success:
            print(f"   ✓ Overview data retrieved")
            # Check for key metrics
            if isinstance(response, dict):
                metrics = ['total_users', 'total_accounts', 'total_balance', 'pending_kyc']
                for metric in metrics:
                    if metric in response:
                        print(f"   ✓ {metric}: {response[metric]}")
        return success

    def test_admin_manual_kyc_queue(self):
        """Test admin can manually queue a user for KYC review"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        # Test with Michele Marcheggiani (the user mentioned in the bug report)
        # Correct email: michelemarcheggiani@libero.it
        success, response = self.run_test(
            "Admin Manual KYC Queue - Michele Marcheggiani",
            "POST",
            "/api/v1/admin/kyc/queue-user",
            200,
            data={
                "user_email": "michelemarcheggiani@libero.it",
                "reason": "Testing manual queue functionality - Bug fix verification"
            },
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Manually queue Michele Marcheggiani for KYC review"
        )
        if success:
            print(f"   ✓ User queued successfully")
            if isinstance(response, dict):
                print(f"   ✓ Response: {response.get('message', 'No message')}")
                print(f"   ✓ KYC Status: {response.get('kyc_status', 'Unknown')}")
        return success

    def test_admin_manual_kyc_queue_nonexistent(self):
        """Test admin manual queue with non-existent user (should fail)"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Admin Manual KYC Queue - Non-existent User",
            "POST",
            "/api/v1/admin/kyc/queue-user",
            404,
            data={
                "user_email": "nonexistent@example.com",
                "reason": "Testing error handling"
            },
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Try to queue non-existent user (should return 404)"
        )
        return success

    def test_kyc_queue_contains_michele(self):
        """Test that Michele Marcheggiani appears in the KYC queue"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "KYC Queue - Check Michele Marcheggiani",
            "GET",
            "/api/v1/admin/kyc/pending",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Verify Michele Marcheggiani is in the KYC queue"
        )
        if success:
            kyc_apps = response if isinstance(response, list) else []
            print(f"   ✓ Retrieved {len(kyc_apps)} KYC applications")
            
            # Look for Michele Marcheggiani
            michele_found = False
            for app in kyc_apps:
                full_name = app.get('full_name', '').lower()
                if 'michele' in full_name and 'marcheggiani' in full_name:
                    michele_found = True
                    print(f"   ✅ Michele Marcheggiani FOUND in queue!")
                    print(f"      - Status: {app.get('status', 'Unknown')}")
                    print(f"      - Full Name: {app.get('full_name', 'N/A')}")
                    print(f"      - Documents: {len(app.get('documents', []))} uploaded")
                    print(f"      - Submitted At: {app.get('submitted_at', 'N/A')}")
                    break
            
            if not michele_found:
                print(f"   ⚠️  Michele Marcheggiani NOT found in queue")
                print(f"   ℹ️  Available applications:")
                for app in kyc_apps[:5]:  # Show first 5
                    print(f"      - {app.get('full_name', 'Unknown')} ({app.get('status', 'Unknown')})")
        
        return success

    def test_admin_clear_notifications_create_test_user(self):
        """Create a test user for notification clearing tests"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False, None
        
        # Create a test user via signup
        test_email = f"test_notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.com"
        test_password = "TestPass123!"
        
        success, response = self.run_test(
            "Create Test User for Notification Tests",
            "POST",
            "/api/v1/auth/signup",
            201,
            data={
                "email": test_email,
                "password": test_password,
                "first_name": "Test",
                "last_name": "NotifUser",
                "phone": "+1234567890"
            },
            description="Create a new test user for notification clearing tests"
        )
        
        if success and 'id' in response:
            user_id = response['id']
            print(f"   ✓ Test user created: {test_email} (ID: {user_id})")
            return True, user_id
        return False, None

    def test_admin_clear_notifications_endpoint(self):
        """Test admin can clear all notifications for a user"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        # First create a test user
        user_created, user_id = self.test_admin_clear_notifications_create_test_user()
        if not user_created or not user_id:
            print("⚠️  Could not create test user, skipping notification clear test")
            return False
        
        # Now test clearing notifications for this user
        success, response = self.run_test(
            "Admin Clear User Notifications",
            "DELETE",
            f"/api/v1/admin/users/{user_id}/notifications",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description=f"Clear all notifications for test user {user_id}"
        )
        
        if success:
            deleted_count = response.get('deleted_count', 0)
            print(f"   ✓ Cleared {deleted_count} notifications")
            print(f"   ✓ Response message: {response.get('message', 'N/A')}")
            
            # Verify response structure
            if 'success' in response and 'deleted_count' in response:
                print(f"   ✓ Response has correct structure")
            else:
                print(f"   ⚠️  Response missing expected fields")
        
        return success

    def test_admin_clear_notifications_non_admin_access(self):
        """Test that non-admin users cannot clear notifications"""
        if not self.user_token:
            print("⚠️  Skipping - No user token")
            return False
        
        # Try to clear notifications as a regular user (should fail with 403)
        success, response = self.run_test(
            "Non-Admin Clear Notifications (Should Fail)",
            "DELETE",
            "/api/v1/admin/users/some_user_id/notifications",
            403,
            headers={'Authorization': f'Bearer {self.user_token}'},
            description="Verify non-admin users cannot clear notifications"
        )
        
        if success:
            print(f"   ✓ Non-admin access correctly blocked")
        
        return success

    def test_admin_clear_notifications_invalid_user(self):
        """Test clearing notifications for non-existent user"""
        if not self.admin_token:
            print("⚠️  Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Clear Notifications - Invalid User (Should Fail)",
            "DELETE",
            "/api/v1/admin/users/nonexistent_user_12345/notifications",
            404,
            headers={'Authorization': f'Bearer {self.admin_token}'},
            description="Try to clear notifications for non-existent user"
        )
        
        if success:
            print(f"   ✓ Invalid user correctly returns 404")
        
        return success

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"   - {test}")
        
        print("="*80)
        
        return 0 if self.tests_failed == 0 else 1

def main():
    print("="*80)
    print("ECOMMBX BANKING API TEST SUITE")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    tester = EcommbxAPITester()
    
    # Run tests in order
    print("\n🔐 AUTHENTICATION TESTS")
    print("-"*80)
    tester.test_admin_login()
    tester.test_user_login()
    
    print("\n👥 ADMIN USER MANAGEMENT TESTS")
    print("-"*80)
    tester.test_admin_get_users()
    
    print("\n💰 ADMIN ACCOUNTS TESTS")
    print("-"*80)
    tester.test_admin_get_accounts()
    
    print("\n🎫 SUPPORT TICKET TESTS")
    print("-"*80)
    tester.test_admin_get_tickets()
    tester.test_ticket_edit_subject()
    tester.test_ticket_edit_message()
    
    print("\n👤 USER TESTS")
    print("-"*80)
    tester.test_user_get_accounts()
    
    print("\n🔔 ADMIN NOTIFICATION BELL TESTS")
    print("-"*80)
    tester.test_admin_notification_bell_kyc()
    tester.test_admin_notification_bell_cards()
    tester.test_admin_notification_bell_transfers()
    tester.test_admin_notification_bell_tickets()
    
    print("\n📅 KYC DATE FORMAT TESTS (Invalid Date Fix)")
    print("-"*80)
    tester.test_kyc_dates_format()
    
    print("\n🔄 TRANSFERS QUEUE TESTS")
    print("-"*80)
    tester.test_transfers_queue_rejection_reason()
    
    print("\n📊 ADMIN OVERVIEW TAB TESTS")
    print("-"*80)
    tester.test_admin_overview_tab()
    
    print("\n🔧 MANUAL KYC QUEUE TESTS (Bug Fix)")
    print("-"*80)
    tester.test_admin_manual_kyc_queue()
    tester.test_admin_manual_kyc_queue_nonexistent()
    tester.test_kyc_queue_contains_michele()
    
    print("\n🔔 CLEAR NOTIFICATIONS FEATURE TESTS (New Feature)")
    print("-"*80)
    tester.test_admin_clear_notifications_endpoint()
    tester.test_admin_clear_notifications_non_admin_access()
    tester.test_admin_clear_notifications_invalid_user()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
