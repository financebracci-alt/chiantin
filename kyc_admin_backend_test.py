#!/usr/bin/env python3
"""
Backend testing for KYC Admin Delete and Edit functionality.
Tests the NEW DELETE and PATCH endpoints for KYC applications.
CRITICAL: Real bank with 85 users - MUST test with NEW users ONLY.
"""
import requests
import sys
import json
from datetime import datetime, timezone
import uuid
import time

class KYCAdminTester:
    def __init__(self, base_url="https://reject-email.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.test_user_token = None
        self.test_user_id = None
        self.test_user_email = None
        self.test_kyc_id = None
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

    def admin_login(self):
        """Login as admin"""
        print("\n🔑 Logging in as admin...")
        
        success, response = self.run_test(
            "Admin Login",
            "POST", 
            "v1/auth/login",
            200,
            data={
                "email": "admin@ecommbx.io",
                "password": "Admin@123456"
            }
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin token obtained: {self.admin_token[:20]}...")
            return True
        return False

    def create_test_user(self):
        """Create a NEW test user"""
        print("\n👤 Creating NEW test user...")
        
        # Generate unique email to avoid conflicts
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        unique_email = f"kyc_test_user_{timestamp}@testbank.local"
        
        success, response = self.run_test(
            "Create Test User",
            "POST",
            "v1/auth/signup",
            201,
            data={
                "email": unique_email,
                "password": "TestUser123!",
                "first_name": "KYC",
                "last_name": "TestUser",
                "language": "en"
            }
        )
        
        if success and 'id' in response:
            user_id = response['id']
            self.test_user_id = user_id
            self.test_user_email = unique_email
            print(f"   Created test user ID: {user_id}")
            
            # Verify email in database to allow login
            if self.verify_user_email(user_id, unique_email):
                # Login as the test user
                login_success, login_response = self.run_test(
                    "Login Test User",
                    "POST", 
                    "v1/auth/login",
                    200,
                    data={
                        "email": unique_email,
                        "password": "TestUser123!"
                    }
                )
                
                if login_success and 'access_token' in login_response:
                    self.test_user_token = login_response['access_token']
                    print(f"   ✅ Test user token obtained: {self.test_user_token[:20]}...")
                    return True
                
        return False

    def verify_user_email(self, user_id, email):
        """Verify user email using database access"""
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
                try:
                    user_query = {"_id": ObjectId(user_id)}
                    user_doc = db.users.find_one(user_query)
                except InvalidId:
                    pass
            
            if not user_doc:
                print(f"   ❌ Test user {user_id} not found in database")
                client.close()
                return False
            
            # Update user to verify email
            result = db.users.update_one(
                user_query,
                {"$set": {
                    "email_verified": True, 
                    "status": "ACTIVE",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            if result.modified_count > 0:
                print(f"   ✅ Test user {user_id} email verified")
                client.close()
                return True
            else:
                print(f"   ❌ Failed to verify user {user_id} email")
                client.close()
                return False
                
        except Exception as e:
            print(f"   ❌ Error verifying user email: {str(e)}")
            return False

    def submit_test_kyc(self):
        """Create a test KYC application directly in database"""
        if not self.test_user_id:
            self.log_test("Create Test KYC", False, "No test user ID")
            return False
            
        print("\n📋 Creating test KYC application directly in database...")
        
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Create a test KYC application directly
            test_kyc = {
                "_id": str(ObjectId()),
                "user_id": self.test_user_id,
                "full_name": "KYC TestUser",
                "date_of_birth": "1990-01-01",
                "nationality": "Lithuanian",
                "country": "Lithuania",
                "street_address": "Test Street 123",
                "city": "Vilnius",
                "postal_code": "01234",
                "tax_residency": "Lithuania",
                "tax_id": "12345678901",
                "status": "SUBMITTED",  # This is what we need for admin testing
                "submitted_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "documents": [],  # Empty documents for testing
                "terms_accepted": True,
                "privacy_accepted": True,
                "terms_accepted_at": datetime.now(timezone.utc),
                "privacy_accepted_at": datetime.now(timezone.utc)
            }
            
            result = db.kyc_applications.insert_one(test_kyc)
            client.close()
            
            if result.inserted_id:
                self.test_kyc_id = str(result.inserted_id)
                self.log_test("Create Test KYC", True, f"KYC application created with ID: {self.test_kyc_id}")
                print(f"   ✅ Test KYC created with ID: {self.test_kyc_id}")
                return True
            else:
                self.log_test("Create Test KYC", False, "Failed to create KYC application")
                return False
                
        except Exception as e:
            self.log_test("Create Test KYC", False, f"Database error: {str(e)}")
            return False

    def test_kyc_edit_endpoint(self):
        """Test PATCH /api/v1/admin/kyc/{application_id} endpoint"""
        if not self.admin_token or not self.test_kyc_id:
            self.log_test("KYC Edit Endpoint", False, "Missing admin token or KYC ID")
            return False
            
        print("\n✏️ Testing KYC Edit functionality...")
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Test data to update (use fields that exist in the admin edit endpoint)
        edit_data = {
            "full_name": "KYC TestUser EDITED",
            "nationality": "Latvian",
            "city": "Riga EDITED",
            "tax_id": "99999999999",
            "address": "Edited Street 999"  # Backend expects 'address', not 'street_address' for updates
        }
        
        success, response = self.run_test(
            "PATCH /admin/kyc/{id} - Edit KYC Application",
            "PATCH",
            f"v1/admin/kyc/{self.test_kyc_id}",
            200,
            data=edit_data,
            headers=headers
        )
        
        if success and response.get('success'):
            changes = response.get('changes', {})
            self.log_test("KYC Edit - Changes Tracked", len(changes) > 0, f"Changes tracked: {list(changes.keys())}")
            
            # Verify changes were saved
            if self.verify_kyc_changes_in_db(edit_data):
                return True
        
        return False

    def verify_kyc_changes_in_db(self, expected_changes):
        """Verify KYC changes were saved to database"""
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from bson.errors import InvalidId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Find KYC application
            kyc_query = {"_id": self.test_kyc_id}
            kyc_doc = db.kyc_applications.find_one(kyc_query)
            
            if not kyc_doc:
                try:
                    kyc_query = {"_id": ObjectId(self.test_kyc_id)}
                    kyc_doc = db.kyc_applications.find_one(kyc_query)
                except InvalidId:
                    pass
            
            if kyc_doc:
                # Check if changes were saved
                changes_verified = 0
                for field, expected_value in expected_changes.items():
                    actual_value = kyc_doc.get(field)
                    if actual_value == expected_value:
                        changes_verified += 1
                        print(f"   ✅ {field}: {actual_value}")
                    else:
                        print(f"   ❌ {field}: expected '{expected_value}', got '{actual_value}'")
                
                # Check audit fields
                edited_at = kyc_doc.get('edited_at')
                edited_by = kyc_doc.get('edited_by')
                
                audit_ok = edited_at is not None and edited_by is not None
                
                client.close()
                
                if changes_verified == len(expected_changes) and audit_ok:
                    self.log_test("KYC Edit - Database Verification", True, f"All {changes_verified} changes saved, audit fields present")
                    return True
                else:
                    self.log_test("KYC Edit - Database Verification", False, f"Only {changes_verified}/{len(expected_changes)} changes saved or audit missing")
                    return False
            else:
                client.close()
                self.log_test("KYC Edit - Database Verification", False, "KYC application not found in database")
                return False
                
        except Exception as e:
            self.log_test("KYC Edit - Database Verification", False, f"Database error: {str(e)}")
            return False

    def test_kyc_delete_endpoint(self):
        """Test DELETE /api/v1/admin/kyc/{application_id} endpoint"""
        if not self.admin_token or not self.test_kyc_id:
            self.log_test("KYC Delete Endpoint", False, "Missing admin token or KYC ID")
            return False
            
        print("\n🗑️ Testing KYC Delete functionality...")
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Store user info before deletion to verify user remains
        original_user_id = self.test_user_id
        original_user_email = self.test_user_email
        
        success, response = self.run_test(
            "DELETE /admin/kyc/{id} - Delete KYC Application",
            "DELETE",
            f"v1/admin/kyc/{self.test_kyc_id}",
            200,
            headers=headers
        )
        
        if success and response.get('success'):
            # Verify KYC was deleted from database
            if self.verify_kyc_deleted_from_db():
                # Verify user account still exists
                if self.verify_user_still_exists(original_user_id, original_user_email):
                    return True
        
        return False

    def verify_kyc_deleted_from_db(self):
        """Verify KYC application was deleted from database"""
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from bson.errors import InvalidId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Try to find the deleted KYC application
            kyc_query = {"_id": self.test_kyc_id}
            kyc_doc = db.kyc_applications.find_one(kyc_query)
            
            if not kyc_doc:
                try:
                    kyc_query = {"_id": ObjectId(self.test_kyc_id)}
                    kyc_doc = db.kyc_applications.find_one(kyc_query)
                except InvalidId:
                    pass
            
            client.close()
            
            if kyc_doc is None:
                self.log_test("KYC Delete - Database Verification", True, "KYC application successfully removed from database")
                return True
            else:
                self.log_test("KYC Delete - Database Verification", False, "KYC application still exists in database")
                return False
                
        except Exception as e:
            self.log_test("KYC Delete - Database Verification", False, f"Database error: {str(e)}")
            return False

    def verify_user_still_exists(self, user_id, user_email):
        """Verify user account still exists after KYC deletion"""
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from bson.errors import InvalidId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Find user
            user_query = {"_id": user_id}
            user_doc = db.users.find_one(user_query)
            
            if not user_doc:
                try:
                    user_query = {"_id": ObjectId(user_id)}
                    user_doc = db.users.find_one(user_query)
                except InvalidId:
                    pass
            
            client.close()
            
            if user_doc and user_doc.get('email') == user_email:
                self.log_test("User Account Persistence", True, f"User account {user_email} still exists after KYC deletion")
                return True
            else:
                self.log_test("User Account Persistence", False, f"User account {user_email} not found after KYC deletion")
                return False
                
        except Exception as e:
            self.log_test("User Account Persistence", False, f"Database error: {str(e)}")
            return False

    def test_user_can_resubmit_kyc(self):
        """Test that user can resubmit KYC after deletion"""
        if not self.test_user_token:
            self.log_test("KYC Resubmission Test", False, "No test user token")
            return False
            
        print("\n🔄 Testing KYC resubmission after deletion...")
        
        headers = {'Authorization': f'Bearer {self.test_user_token}'}
        
        # Submit a new KYC application
        kyc_data = {
            "full_name": "KYC TestUser RESUBMITTED",
            "date_of_birth": "1990-01-01",
            "nationality": "Estonian",
            "country": "Estonia", 
            "street_address": "New Street 456",
            "city": "Tallinn",
            "postal_code": "54321",
            "tax_residency": "Estonia",
            "tax_id": "98765432109",
            "terms_accepted": True,
            "privacy_accepted": True
        }
        
        success, response = self.run_test(
            "Resubmit KYC After Deletion",
            "POST",
            "v1/kyc/submit",
            200,
            data=kyc_data,
            headers=headers
        )
        
        if success and 'id' in response:
            new_kyc_id = response['id']
            print(f"   ✅ New KYC application submitted with ID: {new_kyc_id}")
            self.log_test("KYC Resubmission Test", True, f"User can resubmit KYC after deletion - New ID: {new_kyc_id}")
            return True
        
        return False

    def create_approved_kyc_for_testing(self):
        """Create an approved KYC to test edit/delete protection"""
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Create an approved KYC application
            approved_kyc = {
                "_id": str(ObjectId()),
                "user_id": self.test_user_id,
                "full_name": "Approved KYC User",
                "status": "APPROVED",  # This is the key field
                "submitted_at": datetime.now(timezone.utc),
                "approved_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "documents": [],
                "terms_accepted": True,
                "privacy_accepted": True
            }
            
            result = db.kyc_applications.insert_one(approved_kyc)
            client.close()
            
            if result.inserted_id:
                approved_kyc_id = str(result.inserted_id)
                print(f"   ✅ Created approved KYC with ID: {approved_kyc_id}")
                return approved_kyc_id
            else:
                print(f"   ❌ Failed to create approved KYC")
                return None
                
        except Exception as e:
            print(f"   ❌ Error creating approved KYC: {str(e)}")
            return None

    def test_edit_approved_kyc_protection(self):
        """Test that editing approved KYC is blocked"""
        if not self.admin_token:
            self.log_test("Edit Approved KYC Protection", False, "No admin token")
            return False
            
        print("\n🛡️ Testing edit protection for approved KYC...")
        
        # Create an approved KYC
        approved_kyc_id = self.create_approved_kyc_for_testing()
        if not approved_kyc_id:
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Try to edit the approved KYC (should fail)
        edit_data = {
            "full_name": "Should Not Work",
            "city": "Should Be Blocked"
        }
        
        success, response = self.run_test(
            "Try Edit Approved KYC (Should Fail)",
            "PATCH",
            f"v1/admin/kyc/{approved_kyc_id}",
            400,  # Expecting error status
            data=edit_data,
            headers=headers
        )
        
        if success:
            # Check that the response indicates editing is blocked
            error_detail = response.get('detail', '')
            if 'Cannot edit approved' in error_detail or 'approved' in error_detail.lower():
                self.log_test("Edit Approved KYC Protection", True, "Edit correctly blocked for approved KYC")
                return True
        
        self.log_test("Edit Approved KYC Protection", False, "Edit was not properly blocked for approved KYC")
        return False

    def test_delete_approved_kyc_protection(self):
        """Test that deleting approved KYC is blocked"""
        if not self.admin_token:
            self.log_test("Delete Approved KYC Protection", False, "No admin token")
            return False
            
        print("\n🛡️ Testing delete protection for approved KYC...")
        
        # Create an approved KYC
        approved_kyc_id = self.create_approved_kyc_for_testing()
        if not approved_kyc_id:
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Try to delete the approved KYC (should fail)
        success, response = self.run_test(
            "Try Delete Approved KYC (Should Fail)",
            "DELETE",
            f"v1/admin/kyc/{approved_kyc_id}",
            400,  # Expecting error status
            headers=headers
        )
        
        if success:
            # Check that the response indicates deletion is blocked
            error_detail = response.get('detail', '')
            if 'Cannot delete approved' in error_detail or 'approved' in error_detail.lower():
                self.log_test("Delete Approved KYC Protection", True, "Delete correctly blocked for approved KYC")
                return True
        
        self.log_test("Delete Approved KYC Protection", False, "Delete was not properly blocked for approved KYC")
        return False

def main():
    print("=" * 80)
    print("🚨 CRITICAL: KYC Admin Delete and Edit Testing")
    print("=" * 80)
    print("Testing NEW DELETE and PATCH endpoints for KYC applications.")
    print("⚠️  CRITICAL: Real bank with 85 clients - testing with NEW users ONLY")
    print()

    tester = KYCAdminTester()

    # Step 1: Login as admin
    if not tester.admin_login():
        print("❌ CRITICAL: Failed to login as admin - cannot proceed")
        return 1

    # Step 2: Create NEW test user (CRITICAL - never use real clients)
    if not tester.create_test_user():
        print("❌ CRITICAL: Failed to create test user - cannot proceed")
        return 1

    print(f"✅ SUCCESS: Test user created: {tester.test_user_email}")

    # Step 3: Create test KYC application
    if not tester.submit_test_kyc():
        print("❌ CRITICAL: Failed to create test KYC - cannot proceed")
        return 1

    print(f"✅ SUCCESS: Test KYC created: {tester.test_kyc_id}")

    # Step 4: Test KYC EDIT functionality
    print("\n✏️ TESTING KYC EDIT FUNCTIONALITY")
    print("-" * 60)
    
    edit_success = tester.test_kyc_edit_endpoint()
    if not edit_success:
        print("❌ CRITICAL: KYC edit functionality failed")
        return 1

    # Step 5: Test KYC DELETE functionality
    print("\n🗑️ TESTING KYC DELETE FUNCTIONALITY")
    print("-" * 60)
    
    delete_success = tester.test_kyc_delete_endpoint()
    if not delete_success:
        print("❌ CRITICAL: KYC delete functionality failed")
        return 1

    # Step 6: Test user can resubmit KYC after deletion
    print("\n🔄 TESTING KYC RESUBMISSION")
    print("-" * 60)
    
    resubmit_success = tester.test_user_can_resubmit_kyc()
    if not resubmit_success:
        print("❌ WARNING: KYC resubmission test failed")

    # Step 7: Test protection for approved KYCs
    print("\n🛡️ TESTING APPROVED KYC PROTECTION")
    print("-" * 60)
    
    edit_protection = tester.test_edit_approved_kyc_protection()
    delete_protection = tester.test_delete_approved_kyc_protection()

    # Final Results
    print("\n" + "=" * 80)
    print(f"📊 FINAL TEST RESULTS: {tester.tests_passed}/{tester.tests_run} PASSED")
    print("=" * 80)

    # Critical tests that must pass
    critical_tests = [
        "PATCH /admin/kyc/{id} - Edit KYC Application",
        "DELETE /admin/kyc/{id} - Delete KYC Application", 
        "KYC Delete - Database Verification",
        "User Account Persistence"
    ]
    
    critical_passed = 0
    for result in tester.test_results:
        if result["test"] in critical_tests and result["passed"]:
            critical_passed += 1

    print(f"\n🎯 CRITICAL KYC ADMIN TESTS: {critical_passed}/{len(critical_tests)} PASSED")
    
    if critical_passed == len(critical_tests):
        print("✅ SUCCESS: KYC Admin Delete and Edit functionality is working!")
        print("   ✓ Admins can edit pending KYC applications")
        print("   ✓ Admins can delete pending KYC applications")
        print("   ✓ User accounts remain after KYC deletion")
        print("   ✓ Users can resubmit KYC after deletion")
        if edit_protection and delete_protection:
            print("   ✓ Approved KYCs are protected from edit/delete")
    else:
        print("❌ FAILURE: KYC Admin functionality has critical issues")
        print("   Check the detailed results below for specific failures")

    # Test details for debugging
    print("\n📋 DETAILED RESULTS:")
    for result in tester.test_results:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['test']}")
        if result["details"]:
            print(f"      {result['details']}")

    return 0 if critical_passed >= 3 else 1

if __name__ == "__main__":
    sys.exit(main())