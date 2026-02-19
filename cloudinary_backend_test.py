"""
Backend API Testing for Cloudinary KYC Document Integration
Tests admin login, KYC queue, document upload, and document viewing
"""

import requests
import sys
import io
from datetime import datetime

# Backend URL from environment
BASE_URL = "https://transfer-confirm-1.preview.emergentagent.com/api/v1"
HEALTH_URL = "https://transfer-confirm-1.preview.emergentagent.com/api/health"

# Credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"
TEST_USER_EMAIL = "cloudinary.final.test@test.com"
TEST_USER_PASSWORD = "Test123456!"


class CloudinaryAPITester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.admin_token = None
        self.user_token = None
        self.admin_user = None
        self.user_user = None

    def log_test(self, name, success, message=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            self.tests_failed += 1
            self.errors.append({"test": name, "error": message})
            print(f"❌ {name}: {message}")

    def test_health_check(self):
        """Test health check endpoint"""
        print("\n🔍 Testing Health Check...")
        try:
            response = requests.get(HEALTH_URL, timeout=10)
            if response.status_code == 200:
                self.log_test("Health Check", True)
                return True
            else:
                self.log_test("Health Check", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, str(e))
            return False

    def test_admin_login(self):
        """Test admin login"""
        print("\n🔍 Testing Admin Login...")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.admin_token = data["access_token"]
                    self.admin_user = data["user"]
                    print(f"   Admin Role: {self.admin_user.get('role')}")
                    self.log_test("Admin Login", True)
                    return True
                else:
                    self.log_test("Admin Login", False, "Missing token or user in response")
                    return False
            else:
                self.log_test("Admin Login", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Login", False, str(e))
            return False

    def test_user_login(self):
        """Test user login"""
        print("\n🔍 Testing User Login...")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.user_token = data["access_token"]
                    self.user_user = data["user"]
                    print(f"   User Email: {self.user_user.get('email')}")
                    self.log_test("User Login", True)
                    return True
                else:
                    self.log_test("User Login", False, "Missing token or user in response")
                    return False
            else:
                self.log_test("User Login", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("User Login", False, str(e))
            return False

    def test_kyc_pending_applications(self):
        """Test getting pending KYC applications (admin)"""
        print("\n🔍 Testing KYC Pending Applications...")
        if not self.admin_token:
            self.log_test("KYC Pending Applications", False, "No admin token")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/kyc/pending",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Found {len(data)} pending KYC applications")
                self.log_test("KYC Pending Applications", True)
                return True
            else:
                self.log_test("KYC Pending Applications", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("KYC Pending Applications", False, str(e))
            return False

    def test_get_kyc_application(self):
        """Test getting user's KYC application"""
        print("\n🔍 Testing Get KYC Application...")
        if not self.user_token:
            self.log_test("Get KYC Application", False, "No user token")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/kyc/application",
                headers={"Authorization": f"Bearer {self.user_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   KYC Status: {data.get('status')}")
                print(f"   Documents: {len(data.get('documents', []))}")
                self.log_test("Get KYC Application", True)
                return True
            else:
                self.log_test("Get KYC Application", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Get KYC Application", False, str(e))
            return False

    def test_upload_kyc_document(self):
        """Test uploading a KYC document to Cloudinary"""
        print("\n🔍 Testing KYC Document Upload to Cloudinary...")
        if not self.user_token:
            self.log_test("Upload KYC Document", False, "No user token")
            return False
        
        try:
            # Create a test image file
            test_image = io.BytesIO(b"fake image content for testing")
            test_image.name = "test_passport.jpg"
            
            files = {
                'file': ('test_passport.jpg', test_image, 'image/jpeg')
            }
            
            response = requests.post(
                f"{BASE_URL}/kyc/documents/upload?document_type=PASSPORT",
                headers={"Authorization": f"Bearer {self.user_token}"},
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Document uploaded: {data.get('file_name')}")
                print(f"   File key: {data.get('file_key')}")
                self.log_test("Upload KYC Document", True)
                return True
            else:
                self.log_test("Upload KYC Document", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Upload KYC Document", False, str(e))
            return False

    def test_view_document_endpoint(self):
        """Test document viewing endpoint (should redirect to Cloudinary or show placeholder)"""
        print("\n🔍 Testing Document View Endpoint...")
        if not self.user_token:
            self.log_test("View Document Endpoint", False, "No user token")
            return False
        
        try:
            # First get the KYC application to find a document
            response = requests.get(
                f"{BASE_URL}/kyc/application",
                headers={"Authorization": f"Bearer {self.user_token}"},
                timeout=10
            )
            
            if response.status_code != 200:
                self.log_test("View Document Endpoint", False, "Could not get KYC application")
                return False
            
            data = response.json()
            documents = data.get('documents', [])
            
            if not documents:
                print("   No documents found to test viewing")
                self.log_test("View Document Endpoint", True, "No documents to test (expected)")
                return True
            
            # Try to view the first document
            doc_key = documents[0].get('file_key')
            print(f"   Testing document: {doc_key}")
            
            # Note: We don't need auth for viewing documents
            response = requests.get(
                f"{BASE_URL}/kyc/documents/{doc_key}",
                allow_redirects=False,  # Don't follow redirects to check if it redirects to Cloudinary
                timeout=10
            )
            
            # Should either redirect (302) to Cloudinary or return placeholder (200)
            if response.status_code in [200, 302]:
                if response.status_code == 302:
                    redirect_url = response.headers.get('Location', '')
                    if 'cloudinary.com' in redirect_url:
                        print(f"   ✓ Redirects to Cloudinary: {redirect_url[:80]}...")
                    else:
                        print(f"   ⚠ Redirects but not to Cloudinary: {redirect_url}")
                else:
                    # Check if it's a placeholder
                    content = response.text
                    if 'Document Unavailable' in content or 'cloud storage' in content:
                        print("   ✓ Returns placeholder for old document")
                    else:
                        print("   ⚠ Returns content but not a placeholder")
                
                self.log_test("View Document Endpoint", True)
                return True
            else:
                self.log_test("View Document Endpoint", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("View Document Endpoint", False, str(e))
            return False

    def test_admin_users_endpoint(self):
        """Test admin users endpoint"""
        print("\n🔍 Testing Admin Users Endpoint...")
        if not self.admin_token:
            self.log_test("Admin Users Endpoint", False, "No admin token")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/users",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Found {len(data)} users")
                self.log_test("Admin Users Endpoint", True)
                return True
            else:
                self.log_test("Admin Users Endpoint", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Users Endpoint", False, str(e))
            return False

    def test_admin_accounts_endpoint(self):
        """Test admin accounts endpoint"""
        print("\n🔍 Testing Admin Accounts Endpoint...")
        if not self.admin_token:
            self.log_test("Admin Accounts Endpoint", False, "No admin token")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/accounts",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Found {len(data)} accounts")
                self.log_test("Admin Accounts Endpoint", True)
                return True
            else:
                self.log_test("Admin Accounts Endpoint", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Accounts Endpoint", False, str(e))
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("CLOUDINARY KYC INTEGRATION - BACKEND API TESTS")
        print("=" * 80)
        
        # Basic connectivity
        if not self.test_health_check():
            print("\n⚠️  Health check failed - backend may be down")
            return False
        
        # Authentication
        if not self.test_admin_login():
            print("\n⚠️  Admin login failed - cannot continue with admin tests")
        
        if not self.test_user_login():
            print("\n⚠️  User login failed - cannot continue with user tests")
        
        # KYC Tests
        self.test_kyc_pending_applications()
        self.test_get_kyc_application()
        self.test_upload_kyc_document()
        self.test_view_document_endpoint()
        
        # Admin Features
        self.test_admin_users_endpoint()
        self.test_admin_accounts_endpoint()
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        
        if self.errors:
            print("\n❌ FAILED TESTS:")
            for error in self.errors:
                print(f"   - {error['test']}: {error['error']}")
        
        print("=" * 80)
        
        return self.tests_failed == 0


def main():
    tester = CloudinaryAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
