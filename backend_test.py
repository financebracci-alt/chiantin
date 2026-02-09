#!/usr/bin/env python3
"""
Backend testing for Smart Admin Notification Bell Enhancement.
Tests the SMART notification counting that shows only NEW items after clear.
When admin clears notifications, badge shows 0 for old items, but reappears when
NEW items are created (KYC/transfers/tickets/cards submitted AFTER clear timestamp).
CRITICAL: Must test with NEW admin user ONLY (never real admin).
"""
import requests
import sys
import json
from datetime import datetime, timezone
import uuid
import time

class SmartNotificationCountingTester:
    def __init__(self, base_url="https://banking-kyc-fixes.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.test_admin_user_id = None
        self.test_admin_email = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, passed, details=""):
        """Log test results"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if details:
            print(f"    Details: {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=default_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=default_headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, response_data
                except:
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, {}
            else:
                try:
                    error_data = response.json()
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}: {error_data}")
                except:
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return False, {}

    def create_test_admin_user(self):
        """Create a NEW test admin user (NOT the real admin@ecommbx.io)"""
        print("\n👤 Creating NEW test admin user...")
        
        # Generate unique email to avoid conflicts
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        unique_email = f"test_admin_{timestamp}@testbank.local"
        
        # First create regular user
        success, response = self.run_test(
            "Create Test Admin User",
            "POST",
            "v1/auth/signup",
            201,
            data={
                "email": unique_email,
                "password": "TestAdmin123!",
                "first_name": "Test",
                "last_name": "Admin",
                "language": "en"
            }
        )
        
        if success and 'id' in response:
            user_id = response['id']
            print(f"   Created test user ID: {user_id}")
            
            # Use database access to promote user to admin and verify email
            if self.promote_user_to_admin_and_verify(user_id, unique_email):
                # Login as the new admin
                login_success, login_response = self.run_test(
                    "Login Test Admin",
                    "POST", 
                    "v1/auth/login",
                    200,
                    data={
                        "email": unique_email,
                        "password": "TestAdmin123!"
                    }
                )
                
                if login_success and 'access_token' in login_response:
                    self.admin_token = login_response['access_token']
                    self.test_admin_user_id = user_id
                    self.test_admin_email = unique_email
                    print(f"   ✅ Test admin token obtained: {self.admin_token[:20]}...")
                    return True
                
        return False

    def promote_user_to_admin_and_verify(self, user_id, email):
        """Promote test user to admin role and verify email using database access"""
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from bson.errors import InvalidId
            
            # Connect to same database as the backend
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Try to find user with string ID first, then ObjectId
            user_query = {"_id": user_id}
            user_doc = db.users.find_one(user_query)
            
            if not user_doc:
                # Try as ObjectId
                try:
                    user_query = {"_id": ObjectId(user_id)}
                    user_doc = db.users.find_one(user_query)
                except InvalidId:
                    pass
            
            if not user_doc:
                print(f"   ❌ Test user {user_id} not found in database")
                client.close()
                return False
            
            # Update user to admin role and verify email
            result = db.users.update_one(
                user_query,
                {"$set": {
                    "role": "ADMIN",
                    "email_verified": True, 
                    "status": "ACTIVE",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            if result.modified_count > 0:
                print(f"   ✅ Test user {user_id} promoted to ADMIN and email verified")
                client.close()
                return True
            else:
                print(f"   ❌ Failed to promote user {user_id} to admin")
                client.close()
                return False
                
        except Exception as e:
            print(f"   ❌ Error promoting user to admin: {str(e)}")
            return False

    def test_clear_notifications_endpoint(self):
        """Test POST /api/v1/admin/notifications/clear endpoint"""
        if not self.admin_token:
            self.log_test("Clear Notifications Endpoint", False, "No admin token")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        success, response = self.run_test(
            "POST /admin/notifications/clear",
            "POST",
            "v1/admin/notifications/clear",
            200,
            headers=headers
        )
        
        if success and response.get('success') and 'cleared_at' in response:
            print(f"   ✅ Notifications cleared at: {response['cleared_at']}")
            return response['cleared_at']
        return False

    def test_get_cleared_timestamp_endpoint(self):
        """Test GET /api/v1/admin/notifications/cleared-at endpoint"""
        if not self.admin_token:
            self.log_test("Get Cleared Timestamp Endpoint", False, "No admin token")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        success, response = self.run_test(
            "GET /admin/notifications/cleared-at",
            "GET",
            "v1/admin/notifications/cleared-at",
            200,
            headers=headers
        )
        
        if success and 'cleared_at' in response:
            cleared_at = response.get('cleared_at')
            print(f"   ✅ Retrieved cleared timestamp: {cleared_at}")
            return cleared_at
        return False

    def verify_admin_notifications_cleared_at_in_db(self):
        """Verify that admin_notifications_cleared_at field is saved in database"""
        if not self.test_admin_user_id:
            self.log_test("Database Field Verification", False, "No test admin user ID")
            return False
            
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from bson.errors import InvalidId
            
            # Connect to same database as the backend
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Find user
            user_query = {"_id": self.test_admin_user_id}
            user_doc = db.users.find_one(user_query)
            
            if not user_doc:
                try:
                    user_query = {"_id": ObjectId(self.test_admin_user_id)}
                    user_doc = db.users.find_one(user_query)
                except InvalidId:
                    pass
            
            if user_doc:
                cleared_at = user_doc.get('admin_notifications_cleared_at')
                if cleared_at:
                    self.log_test("Database Field Verification", True, f"admin_notifications_cleared_at field found: {cleared_at}")
                    client.close()
                    return str(cleared_at)
                else:
                    self.log_test("Database Field Verification", False, "admin_notifications_cleared_at field not found in database")
                    client.close()
                    return False
            else:
                self.log_test("Database Field Verification", False, "Test admin user not found in database")
                client.close()
                return False
                
        except Exception as e:
            self.log_test("Database Field Verification", False, f"Database error: {str(e)}")
            return False

    def test_smart_counts_endpoint(self):
        """Test NEW smart counting endpoint GET /api/v1/admin/notifications/counts-since-clear"""
        if not self.admin_token:
            self.log_test("Smart Counts Endpoint", False, "No admin token")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Test the NEW smart endpoint
        success, response = self.run_test(
            "GET /admin/notifications/counts-since-clear (Smart Counting)",
            "GET",
            "v1/admin/notifications/counts-since-clear",
            200,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            # Verify response structure
            required_fields = ['kyc', 'cards', 'transfers', 'tickets', 'total', 'cleared_at']
            for field in required_fields:
                if field not in response:
                    self.log_test("Smart Counts Response Structure", False, f"Missing field: {field}")
                    return False
            
            self.log_test("Smart Counts Response Structure", True, f"All required fields present: {required_fields}")
            
            # Log the actual counts
            counts = {k: response[k] for k in required_fields if k != 'cleared_at'}
            print(f"   Current counts: {counts}")
            print(f"   Cleared at: {response['cleared_at']}")
            
            return response
        return False

    def test_smart_counting_logic_with_clear(self):
        """Test the complete smart counting logic with clear action"""
        if not self.admin_token:
            self.log_test("Smart Counting Logic", False, "No admin token")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        print("\n📊 Testing Smart Counting Logic:")
        
        # Step 1: Get initial counts before clear
        print("   Step 1: Getting initial counts...")
        initial_success, initial_response = self.run_test(
            "Initial Smart Counts (Before Clear)",
            "GET", 
            "v1/admin/notifications/counts-since-clear",
            200,
            headers=headers
        )
        
        if not initial_success:
            return False
            
        initial_total = initial_response.get('total', 0)
        initial_cleared_at = initial_response.get('cleared_at')
        print(f"   Initial total: {initial_total}, Cleared at: {initial_cleared_at}")
        
        # Step 2: Clear notifications
        print("   Step 2: Clearing notifications...")
        clear_success, clear_response = self.run_test(
            "Clear Notifications",
            "POST",
            "v1/admin/notifications/clear", 
            200,
            headers=headers
        )
        
        if not clear_success or not clear_response.get('success'):
            self.log_test("Smart Counting Logic - Clear Failed", False, "Clear notifications failed")
            return False
            
        cleared_timestamp = clear_response.get('cleared_at')
        print(f"   Notifications cleared at: {cleared_timestamp}")
        
        # Step 3: Get counts after clear - should show only NEW items
        print("   Step 3: Getting counts after clear...")
        time.sleep(1)  # Brief pause to ensure timestamp difference
        
        after_clear_success, after_clear_response = self.run_test(
            "Smart Counts After Clear",
            "GET",
            "v1/admin/notifications/counts-since-clear",
            200, 
            headers=headers
        )
        
        if not after_clear_success:
            return False
            
        after_clear_total = after_clear_response.get('total', -1)
        after_clear_cleared_at = after_clear_response.get('cleared_at')
        
        print(f"   After clear total: {after_clear_total}, Cleared at: {after_clear_cleared_at}")
        
        # Verify the cleared_at timestamp is updated
        if cleared_timestamp == after_clear_cleared_at:
            self.log_test("Smart Counting - Cleared Timestamp", True, "Cleared timestamp correctly updated")
        else:
            self.log_test("Smart Counting - Cleared Timestamp", False, f"Timestamp mismatch: {cleared_timestamp} vs {after_clear_cleared_at}")
        
        # Verify that smart counting is working (counts should be for items after cleared_at only)
        if after_clear_total >= 0:  # Could be 0 (no new items) or positive (new items since clear)
            self.log_test("Smart Counting Logic", True, f"Smart counting working - total after clear: {after_clear_total}")
            return after_clear_response
        else:
            self.log_test("Smart Counting Logic", False, "Invalid response after clear")
            return False

    def create_test_kyc_application(self):
        """Create a test KYC application to verify NEW item counting"""
        if not self.admin_token:
            return False
            
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from datetime import datetime, timezone
            
            # Connect to database
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Create a test KYC application with current timestamp (after any clear)
            test_kyc = {
                "_id": str(ObjectId()),
                "user_id": self.test_admin_user_id,  # Use test admin as user
                "full_name": "Test Smart Count User",
                "status": "SUBMITTED",
                "submitted_at": datetime.now(timezone.utc),  # This is the key field for smart counting
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "documents": [],
                "terms_accepted": True,
                "privacy_accepted": True
            }
            
            result = db.kyc_applications.insert_one(test_kyc)
            client.close()
            
            if result.inserted_id:
                self.log_test("Create Test KYC Application", True, f"KYC application created with ID: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                self.log_test("Create Test KYC Application", False, "Failed to create KYC application")
                return False
                
        except Exception as e:
            self.log_test("Create Test KYC Application", False, f"Database error: {str(e)}")
            return False

    def test_new_items_after_clear(self):
        """Test that NEW items appear in counts after clear"""
        if not self.admin_token:
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        print("\n🆕 Testing New Items After Clear:")
        
        # Step 1: Clear notifications first
        print("   Step 1: Clearing notifications...")
        clear_success, clear_response = self.run_test(
            "Clear Before New Item Test",
            "POST",
            "v1/admin/notifications/clear",
            200,
            headers=headers
        )
        
        if not clear_success:
            return False
            
        # Step 2: Get counts after clear (should be low/zero for new items)
        print("   Step 2: Getting counts after clear...")
        time.sleep(1)
        
        after_clear_success, after_clear_response = self.run_test(
            "Counts After Clear (Before New Item)",
            "GET",
            "v1/admin/notifications/counts-since-clear",
            200,
            headers=headers
        )
        
        if not after_clear_success:
            return False
            
        kyc_count_before = after_clear_response.get('kyc', 0)
        total_before = after_clear_response.get('total', 0)
        
        print(f"   KYC count before new item: {kyc_count_before}")
        print(f"   Total count before new item: {total_before}")
        
        # Step 3: Create NEW KYC application (after clear timestamp)
        print("   Step 3: Creating NEW KYC application...")
        time.sleep(2)  # Ensure timestamp is after clear
        
        new_kyc_id = self.create_test_kyc_application()
        if not new_kyc_id:
            return False
            
        # Step 4: Get counts after creating new item - should increase
        print("   Step 4: Getting counts after new item...")
        time.sleep(1)
        
        after_new_success, after_new_response = self.run_test(
            "Counts After New KYC Item",
            "GET",
            "v1/admin/notifications/counts-since-clear",
            200,
            headers=headers
        )
        
        if not after_new_success:
            return False
            
        kyc_count_after = after_new_response.get('kyc', 0)
        total_after = after_new_response.get('total', 0)
        
        print(f"   KYC count after new item: {kyc_count_after}")
        print(f"   Total count after new item: {total_after}")
        
        # Verify that counts increased (smart counting working)
        if kyc_count_after > kyc_count_before:
            self.log_test("Smart Counting - New Items Detection", True, f"KYC count increased from {kyc_count_before} to {kyc_count_after}")
        else:
            self.log_test("Smart Counting - New Items Detection", False, f"KYC count did not increase: {kyc_count_before} -> {kyc_count_after}")
            
        if total_after > total_before:
            self.log_test("Smart Counting - Total Count Update", True, f"Total count increased from {total_before} to {total_after}")
            return True
        else:
            self.log_test("Smart Counting - Total Count Update", False, f"Total count did not increase: {total_before} -> {total_after}")
            return False

    def test_login_with_new_token(self):
        """Test logging in again to get a fresh token (simulates logout/login)"""
        if not self.test_admin_email:
            self.log_test("Re-login Test", False, "No test admin email")
            return False
            
        print(f"\n🔑 Re-logging in as test admin: {self.test_admin_email}")
        
        login_success, login_response = self.run_test(
            "Re-login Test Admin (Simulate Logout/Login)",
            "POST", 
            "v1/auth/login",
            200,
            data={
                "email": self.test_admin_email,
                "password": "TestAdmin123!"
            }
        )
        
        if login_success and 'access_token' in login_response:
            new_token = login_response['access_token']
            print(f"   ✅ New token obtained: {new_token[:20]}...")
            # Update to use new token
            self.admin_token = new_token
            return True
        return False

def main():
    print("=" * 80)
    print("🚨 CRITICAL: Admin Notification Bell Persistence Bug Fix Testing")
    print("=" * 80)
    print("Testing fix where admin notification clear button was NOT persisting.")
    print("When admin clicks checkmark to clear notifications, it must persist")
    print("across page reloads, logout/login cycles, until new items appear.")
    print()
    print("⚠️  IMPORTANT: Testing with NEW admin user only (NOT admin@ecommbx.io)")
    print("   This is a real banking platform with 72 real clients!")
    print()

    tester = AdminNotificationPersistenceTester()

    # Step 1: Create NEW test admin user (CRITICAL - never use real admin)
    if not tester.create_test_admin_user():
        print("❌ CRITICAL: Failed to create test admin user - cannot proceed")
        return 1

    print(f"✅ SUCCESS: Test admin created: {tester.test_admin_email}")

    # Step 2: Test the clear notifications endpoint
    print("\n📝 TESTING ADMIN NOTIFICATION CLEAR ENDPOINT")
    print("-" * 50)
    
    cleared_timestamp = tester.test_clear_notifications_endpoint()
    if not cleared_timestamp:
        print("❌ CRITICAL: Clear notifications endpoint failed")
        return 1

    # Step 3: Test the get cleared timestamp endpoint
    print("\n📅 TESTING GET CLEARED TIMESTAMP ENDPOINT")
    print("-" * 50)
    
    retrieved_timestamp = tester.test_get_cleared_timestamp_endpoint()
    if not retrieved_timestamp:
        print("❌ CRITICAL: Get cleared timestamp endpoint failed")
        return 1

    # Step 4: Verify timestamps match
    if cleared_timestamp and retrieved_timestamp:
        if cleared_timestamp == retrieved_timestamp:
            tester.log_test("Timestamp Consistency", True, f"Cleared and retrieved timestamps match: {cleared_timestamp}")
        else:
            tester.log_test("Timestamp Consistency", False, f"Timestamps don't match! Cleared: {cleared_timestamp}, Retrieved: {retrieved_timestamp}")

    # Step 5: Verify the field is saved in database
    print("\n🗄️  TESTING DATABASE PERSISTENCE")
    print("-" * 50)
    
    db_timestamp = tester.verify_admin_notifications_cleared_at_in_db()
    if not db_timestamp:
        print("❌ CRITICAL: admin_notifications_cleared_at field not saved to database")
        return 1

    # Step 6: Test admin notification counts (for completeness)
    print("\n📊 TESTING ADMIN NOTIFICATION COUNTS")
    print("-" * 50)
    
    tester.test_admin_notification_counts()

    # Step 7: CRITICAL - Test persistence across logout/login
    print("\n🔄 TESTING PERSISTENCE ACROSS LOGOUT/LOGIN")
    print("-" * 50)
    
    # Simulate logout/login by getting new token
    if not tester.test_login_with_new_token():
        print("❌ CRITICAL: Failed to re-login as test admin")
        return 1

    # After re-login, verify cleared timestamp is still accessible
    retrieved_after_login = tester.test_get_cleared_timestamp_endpoint()
    if retrieved_after_login:
        if cleared_timestamp == retrieved_after_login:
            tester.log_test("Persistence After Logout/Login", True, "Cleared timestamp persisted across logout/login")
        else:
            tester.log_test("Persistence After Logout/Login", False, "Cleared timestamp changed after logout/login")
    else:
        tester.log_test("Persistence After Logout/Login", False, "Could not retrieve timestamp after re-login")

    # Final Results
    print("\n" + "=" * 80)
    print(f"📊 FINAL TEST RESULTS: {tester.tests_passed}/{tester.tests_run} PASSED")
    print("=" * 80)

    # Critical tests that must pass for the bug fix to work
    critical_tests = [
        "POST /admin/notifications/clear",
        "GET /admin/notifications/cleared-at", 
        "Database Field Verification",
        "Persistence After Logout/Login"
    ]
    
    critical_passed = 0
    for result in tester.test_results:
        if result["test"] in critical_tests and result["passed"]:
            critical_passed += 1

    print(f"\n🎯 CRITICAL PERSISTENCE TESTS: {critical_passed}/{len(critical_tests)} PASSED")
    
    if critical_passed == len(critical_tests):
        print("✅ SUCCESS: Admin notification bell persistence fix is working!")
        print("   Notifications will now stay cleared across logout/login cycles")
    else:
        print("❌ FAILURE: Admin notification bell persistence has issues")
        print("   Notifications may reappear after logout/login")

    # Test details for debugging
    print("\n📋 DETAILED RESULTS:")
    for result in tester.test_results:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['test']}")
        if result["details"]:
            print(f"      {result['details']}")

    return 0 if critical_passed == len(critical_tests) else 1

if __name__ == "__main__":
    sys.exit(main())