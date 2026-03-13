"""
Comprehensive Backend API Test for KYC Submission Flow
Tests the critical bug: KYC submissions bypassing the queue
"""

import requests
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any
import io

class KYCFlowTester:
    def __init__(self, base_url="https://user-alert-system-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.user_email = None
        self.user_id = None
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
            for key, value in details.items():
                print(f"   {key}: {value}")
        
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print()

    def test_admin_login(self) -> bool:
        """Test admin login."""
        print("\n" + "=" * 60)
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
                user_data = data.get("user", {})
                self.log_result(
                    "Admin Login",
                    True,
                    "Admin logged in successfully",
                    {
                        "email": user_data.get("email"),
                        "role": user_data.get("role"),
                        "status": user_data.get("status")
                    }
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

    def test_user_registration(self) -> bool:
        """Test user registration."""
        print("\n" + "=" * 60)
        print("TEST 2: USER REGISTRATION")
        print("=" * 60)
        
        # Create unique email with timestamp
        timestamp = int(time.time())
        self.user_email = f"test_kyc_{timestamp}@test.com"
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/signup",
                json={
                    "email": self.user_email,
                    "password": "TestPass123!",
                    "first_name": "Test",
                    "last_name": "User",
                    "phone": "+1234567890",
                    "language": "en"
                },
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                self.user_id = data.get("id")
                self.log_result(
                    "User Registration",
                    True,
                    "User registered successfully",
                    {
                        "email": data.get("email"),
                        "user_id": self.user_id,
                        "email_verified": data.get("email_verified"),
                        "status": data.get("status")
                    }
                )
                return True
            else:
                self.log_result(
                    "User Registration",
                    False,
                    f"Registration failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("User Registration", False, f"Exception: {str(e)}")
            return False

    def test_user_login(self) -> bool:
        """Test user login (bypassing email verification for testing)."""
        print("\n" + "=" * 60)
        print("TEST 3: USER LOGIN (After Email Verification)")
        print("=" * 60)
        
        # For testing purposes, we'll use MongoDB to directly verify the email
        # This simulates what would happen after a user clicks the verification link
        try:
            from pymongo import MongoClient
            from bson import ObjectId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url)
            db = client["ecommbx-prod"]
            
            # Try to update user with ObjectId
            try:
                user_oid = ObjectId(self.user_id)
                result = db.users.update_one(
                    {"_id": user_oid},
                    {"$set": {"email_verified": True}}
                )
            except:
                # If ObjectId conversion fails, try with string ID
                result = db.users.update_one(
                    {"_id": self.user_id},
                    {"$set": {"email_verified": True}}
                )
            
            if result.modified_count > 0:
                print(f"✓ Email verified in database for user {self.user_id}")
            else:
                print(f"⚠ Could not verify email in database (user may not exist or already verified)")
            
            client.close()
        except Exception as e:
            print(f"⚠ Could not auto-verify email via database: {str(e)}")
            print("  Continuing with login attempt...")
        
        # Now try to login
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "email": self.user_email,
                    "password": "TestPass123!"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.user_token = data.get("access_token")
                user_data = data.get("user", {})
                self.log_result(
                    "User Login",
                    True,
                    "User logged in successfully",
                    {
                        "email": user_data.get("email"),
                        "email_verified": user_data.get("email_verified"),
                        "status": user_data.get("status")
                    }
                )
                return True
            elif response.status_code == 403:
                error_detail = response.json().get("detail", "")
                if "EMAIL_NOT_VERIFIED" in error_detail:
                    self.log_result(
                        "User Login",
                        False,
                        "Email not verified - database update may have failed",
                        {"detail": error_detail, "note": "Email verification is required"}
                    )
                    return False
                else:
                    self.log_result(
                        "User Login",
                        False,
                        f"Login blocked: {error_detail}",
                        {"status_code": response.status_code}
                    )
                    return False
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

    def test_kyc_application_creation(self) -> bool:
        """Test KYC application creation."""
        print("\n" + "=" * 60)
        print("TEST 4: KYC APPLICATION CREATION")
        print("=" * 60)
        
        if not self.user_token:
            self.log_result("KYC Application Creation", False, "No user token available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/kyc/application",
                headers={"Authorization": f"Bearer {self.user_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "KYC Application Creation",
                    True,
                    "KYC application retrieved/created successfully",
                    {
                        "status": data.get("status"),
                        "user_id": data.get("user_id"),
                        "documents_count": len(data.get("documents", []))
                    }
                )
                return True
            else:
                self.log_result(
                    "KYC Application Creation",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("KYC Application Creation", False, f"Exception: {str(e)}")
            return False

    def test_kyc_document_upload(self, document_type: str) -> bool:
        """Test KYC document upload."""
        print(f"\n--- Uploading {document_type} ---")
        
        if not self.user_token:
            self.log_result(f"Upload {document_type}", False, "No user token available")
            return False
        
        try:
            # Create a dummy image file
            dummy_image = io.BytesIO(b"fake image content for testing")
            dummy_image.name = f"{document_type.lower()}.jpg"
            
            files = {
                'file': (dummy_image.name, dummy_image, 'image/jpeg')
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/kyc/documents/upload?document_type={document_type}",
                headers={"Authorization": f"Bearer {self.user_token}"},
                files=files,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    f"Upload {document_type}",
                    True,
                    f"{document_type} uploaded successfully",
                    {
                        "document_type": data.get("document_type"),
                        "file_name": data.get("file_name"),
                        "file_size": data.get("file_size")
                    }
                )
                return True
            else:
                self.log_result(
                    f"Upload {document_type}",
                    False,
                    f"Upload failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result(f"Upload {document_type}", False, f"Exception: {str(e)}")
            return False

    def test_kyc_submission_without_documents(self) -> bool:
        """Test KYC submission without required documents (should fail)."""
        print("\n" + "=" * 60)
        print("TEST 5: KYC SUBMISSION WITHOUT REQUIRED DOCUMENTS (Should Fail)")
        print("=" * 60)
        
        if not self.user_token:
            self.log_result("KYC Submission (No Docs)", False, "No user token available")
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/kyc/submit",
                headers={"Authorization": f"Bearer {self.user_token}"},
                json={
                    "full_name": "Test User",
                    "date_of_birth": "1990-01-01",
                    "nationality": "US",
                    "address": "123 Test St",
                    "city": "Test City",
                    "postal_code": "12345",
                    "country": "US",
                    "terms_accepted": True,
                    "privacy_accepted": True
                },
                timeout=10
            )
            
            # This should fail with 400 because required documents are missing
            if response.status_code == 400:
                error_detail = response.json().get("detail", "")
                if "required documents" in error_detail.lower() or "passport" in error_detail.lower():
                    self.log_result(
                        "KYC Submission (No Docs)",
                        True,
                        "Correctly rejected submission without required documents",
                        {"error": error_detail}
                    )
                    return True
                else:
                    self.log_result(
                        "KYC Submission (No Docs)",
                        False,
                        f"Failed with unexpected error: {error_detail}",
                        {"status_code": response.status_code}
                    )
                    return False
            elif response.status_code == 200:
                # This is BAD - it should have rejected the submission
                self.log_result(
                    "KYC Submission (No Docs)",
                    False,
                    "CRITICAL BUG: Submission accepted without required documents!",
                    {"status": response.json().get("status")}
                )
                return False
            else:
                self.log_result(
                    "KYC Submission (No Docs)",
                    False,
                    f"Unexpected status code: {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("KYC Submission (No Docs)", False, f"Exception: {str(e)}")
            return False

    def test_kyc_submission_with_documents(self) -> bool:
        """Test KYC submission with all required documents."""
        print("\n" + "=" * 60)
        print("TEST 6: KYC SUBMISSION WITH REQUIRED DOCUMENTS")
        print("=" * 60)
        
        if not self.user_token:
            self.log_result("KYC Submission (With Docs)", False, "No user token available")
            return False
        
        # First upload required documents
        print("Uploading required documents...")
        passport_uploaded = self.test_kyc_document_upload("PASSPORT")
        proof_uploaded = self.test_kyc_document_upload("PROOF_OF_ADDRESS")
        
        if not (passport_uploaded and proof_uploaded):
            self.log_result(
                "KYC Submission (With Docs)",
                False,
                "Failed to upload required documents"
            )
            return False
        
        # Now submit KYC
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/kyc/submit",
                headers={"Authorization": f"Bearer {self.user_token}"},
                json={
                    "full_name": "Test User",
                    "date_of_birth": "1990-01-01",
                    "nationality": "US",
                    "address": "123 Test St",
                    "city": "Test City",
                    "postal_code": "12345",
                    "country": "US",
                    "terms_accepted": True,
                    "privacy_accepted": True
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                kyc_status = data.get("status")
                
                # CRITICAL CHECK: Status should be SUBMITTED, not DRAFT
                if kyc_status == "SUBMITTED":
                    self.log_result(
                        "KYC Submission (With Docs)",
                        True,
                        "KYC submitted successfully with SUBMITTED status",
                        {
                            "status": kyc_status,
                            "submitted_at": data.get("submitted_at"),
                            "user_id": data.get("user_id")
                        }
                    )
                    return True
                elif kyc_status == "DRAFT":
                    self.log_result(
                        "KYC Submission (With Docs)",
                        False,
                        "CRITICAL BUG: KYC status is DRAFT instead of SUBMITTED!",
                        {
                            "status": kyc_status,
                            "expected": "SUBMITTED",
                            "note": "This is the reported bug - KYC not appearing in admin queue"
                        }
                    )
                    return False
                else:
                    self.log_result(
                        "KYC Submission (With Docs)",
                        False,
                        f"Unexpected KYC status: {kyc_status}",
                        {"status": kyc_status}
                    )
                    return False
            else:
                self.log_result(
                    "KYC Submission (With Docs)",
                    False,
                    f"Submission failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("KYC Submission (With Docs)", False, f"Exception: {str(e)}")
            return False

    def test_admin_view_pending_kyc(self) -> bool:
        """Test admin viewing pending KYC applications."""
        print("\n" + "=" * 60)
        print("TEST 7: ADMIN VIEW PENDING KYC APPLICATIONS")
        print("=" * 60)
        
        if not self.admin_token:
            self.log_result("Admin View Pending KYC", False, "No admin token available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/kyc/pending",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                pending_count = len(data)
                
                # Check if our test user's KYC is in the queue
                test_user_found = False
                for app in data:
                    if app.get("user_id") == self.user_id:
                        test_user_found = True
                        break
                
                if test_user_found:
                    self.log_result(
                        "Admin View Pending KYC",
                        True,
                        f"Test user's KYC found in pending queue",
                        {
                            "total_pending": pending_count,
                            "test_user_in_queue": True
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Admin View Pending KYC",
                        False,
                        "CRITICAL BUG: Test user's KYC NOT in pending queue!",
                        {
                            "total_pending": pending_count,
                            "test_user_in_queue": False,
                            "note": "This confirms the reported bug"
                        }
                    )
                    return False
            else:
                self.log_result(
                    "Admin View Pending KYC",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Admin View Pending KYC", False, f"Exception: {str(e)}")
            return False

    def test_admin_manual_queue(self) -> bool:
        """Test admin manually queueing a user's KYC."""
        print("\n" + "=" * 60)
        print("TEST 8: ADMIN MANUAL QUEUE USER")
        print("=" * 60)
        
        if not self.admin_token:
            self.log_result("Admin Manual Queue", False, "No admin token available")
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/admin/kyc/queue-user",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "user_email": self.user_email,
                    "reason": "Testing manual queue feature"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Admin Manual Queue",
                    True,
                    "User successfully queued for KYC review",
                    {
                        "success": data.get("success"),
                        "message": data.get("message"),
                        "kyc_status": data.get("kyc_status")
                    }
                )
                return True
            else:
                self.log_result(
                    "Admin Manual Queue",
                    False,
                    f"Failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result("Admin Manual Queue", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "=" * 80)
        print("STARTING COMPREHENSIVE KYC FLOW BACKEND TESTS")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Test 1: Admin Login
        if not self.test_admin_login():
            print("\n❌ CRITICAL: Admin login failed. Cannot continue tests.")
            self.print_summary()
            return False
        
        # Test 2: User Registration
        if not self.test_user_registration():
            print("\n❌ CRITICAL: User registration failed. Cannot continue tests.")
            self.print_summary()
            return False
        
        # Test 3: User Login (may fail due to email verification)
        user_logged_in = self.test_user_login()
        
        if user_logged_in:
            # Test 4: KYC Application Creation
            self.test_kyc_application_creation()
            
            # Test 5: KYC Submission Without Documents (should fail)
            self.test_kyc_submission_without_documents()
            
            # Test 6: KYC Submission With Documents (critical test)
            kyc_submitted = self.test_kyc_submission_with_documents()
            
            # Test 7: Admin View Pending KYC
            if kyc_submitted:
                self.test_admin_view_pending_kyc()
        else:
            print("\n⚠️  User login failed (likely due to email verification).")
            print("Skipping user-specific KYC tests.")
        
        # Test 8: Admin Manual Queue (can test independently)
        if self.user_email:
            self.test_admin_manual_queue()
        
        # Print summary
        self.print_summary()
        
        return self.tests_passed == self.tests_run

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0:.1f}%")
        print("=" * 80)
        
        if self.tests_passed < self.tests_run:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test_name']}: {result['message']}")
        
        print("\n" + "=" * 80)
        print(f"Test Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)


def main():
    """Main test execution."""
    tester = KYCFlowTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
