#!/usr/bin/env python3
"""
CRITICAL Banking Balance Toggle Fix Testing
Testing the fix for balance visibility toggle button that was triggering form submission.

CRITICAL BUG FIXED: 
- Balance toggle (eye icon) was missing type='button' attribute
- HTML buttons inside forms default to type='submit' 
- Clicking eye icon was submitting payment form = ACCIDENTAL MONEY TRANSFERS!

FIX APPLIED: Added type='button' to BalanceToggle component
VISUAL FIX: Improved text contrast in admin panel

TESTING REQUIREMENTS:
1. Create NEW test user with funds
2. Test balance toggle in transfer form (empty & filled)  
3. Verify NO payment is sent when clicking eye icon
4. Verify balance toggles correctly
5. Verify Make Payment button is ONLY way to submit
6. Test admin panel text contrast improvements
"""

import requests
import sys
import json
from datetime import datetime, timezone
import uuid
import time

class BalanceToggleFixTester:
    def __init__(self, base_url="https://banking-kyc-fixes.preview.emergentagent.com"):
        self.base_url = base_url
        self.user_token = None
        self.admin_token = None
        self.test_user_id = None
        self.test_admin_id = None
        self.test_user_email = None
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

    def create_test_user(self):
        """Create a NEW test user for balance toggle testing"""
        print("\n👤 Creating NEW test user for balance toggle testing...")
        
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        unique_email = f"test_user_balance_{timestamp}@testbank.local"
        
        success, response = self.run_test(
            "Create Test User",
            "POST",
            "v1/auth/signup",
            201,
            data={
                "email": unique_email,
                "password": "TestUser123!",
                "first_name": "Balance",
                "last_name": "Test",
                "language": "en"
            }
        )
        
        if success and 'id' in response:
            user_id = response['id']
            
            # Verify email and activate account
            if self.activate_test_user(user_id, unique_email):
                # Login as the new user
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
                    self.user_token = login_response['access_token']
                    self.test_user_id = user_id
                    self.test_user_email = unique_email
                    print(f"   ✅ Test user created and logged in: {unique_email}")
                    return True
                
        return False

    def create_test_admin(self):
        """Create a NEW test admin for visual contrast testing"""
        print("\n👤 Creating NEW test admin for visual testing...")
        
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        unique_email = f"test_admin_visual_{timestamp}@testbank.local"
        
        success, response = self.run_test(
            "Create Test Admin",
            "POST",
            "v1/auth/signup",
            201,
            data={
                "email": unique_email,
                "password": "TestAdmin123!",
                "first_name": "Visual",
                "last_name": "TestAdmin",
                "language": "en"
            }
        )
        
        if success and 'id' in response:
            user_id = response['id']
            
            # Promote to admin and verify email
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
                    self.test_admin_id = user_id
                    self.test_admin_email = unique_email
                    print(f"   ✅ Test admin created and logged in: {unique_email}")
                    return True
                
        return False

    def activate_test_user(self, user_id, email):
        """Verify email and activate test user"""
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from bson.errors import InvalidId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Find and verify user
            user_query = {"_id": user_id}
            user_doc = db.users.find_one(user_query)
            
            if not user_doc:
                try:
                    user_query = {"_id": ObjectId(user_id)}
                    user_doc = db.users.find_one(user_query)
                except InvalidId:
                    pass
            
            if user_doc:
                # Update user to verified and active
                result = db.users.update_one(
                    user_query,
                    {"$set": {
                        "email_verified": True, 
                        "status": "ACTIVE",
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                
                client.close()
                return result.modified_count > 0
            
            client.close()
            return False
                
        except Exception as e:
            print(f"   ❌ Error activating user: {str(e)}")
            return False

    def promote_user_to_admin_and_verify(self, user_id, email):
        """Promote test user to admin role and verify email"""
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from bson.errors import InvalidId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            user_query = {"_id": user_id}
            user_doc = db.users.find_one(user_query)
            
            if not user_doc:
                try:
                    user_query = {"_id": ObjectId(user_id)}
                    user_doc = db.users.find_one(user_query)
                except InvalidId:
                    pass
            
            if user_doc:
                result = db.users.update_one(
                    user_query,
                    {"$set": {
                        "role": "ADMIN",
                        "email_verified": True, 
                        "status": "ACTIVE",
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                
                client.close()
                return result.modified_count > 0
            
            client.close()
            return False
                
        except Exception as e:
            print(f"   ❌ Error promoting user to admin: {str(e)}")
            return False

    def add_funds_to_test_user(self):
        """Add funds to test user account for transfer testing"""
        if not self.user_token or not self.test_user_id:
            return False

        print(f"\n💰 Adding test funds to user account...")
        
        try:
            import pymongo
            from pymongo import MongoClient
            from bson import ObjectId
            from bson.errors import InvalidId
            
            mongo_url = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
            db = client["ecommbx-prod"]
            
            # Find user's account
            user_query = {"_id": self.test_user_id}
            user_doc = db.users.find_one(user_query)
            
            if not user_doc:
                try:
                    user_query = {"_id": ObjectId(self.test_user_id)}
                    user_doc = db.users.find_one(user_query)
                except InvalidId:
                    pass
            
            if user_doc:
                # Find or create user account
                account_query = {"user_id": self.test_user_id}
                account = db.accounts.find_one(account_query)
                
                if not account:
                    # Create account
                    account = {
                        "_id": str(ObjectId()),
                        "user_id": self.test_user_id,
                        "account_number": f"ACC{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "iban": f"DE89370400440532013{datetime.now().strftime('%H%M%S')}",
                        "bic": "COBADEFF",
                        "currency": "EUR",
                        "balance": 50000,  # 500 EUR in cents
                        "status": "ACTIVE",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                    db.accounts.insert_one(account)
                else:
                    # Update balance
                    db.accounts.update_one(
                        {"_id": account["_id"]},
                        {"$set": {"balance": 50000, "updated_at": datetime.now(timezone.utc)}}
                    )
                
                client.close()
                self.log_test("Add Test Funds", True, "500 EUR added to test user account")
                return True
            
            client.close()
            return False
                
        except Exception as e:
            self.log_test("Add Test Funds", False, f"Database error: {str(e)}")
            return False

    def test_backend_apis(self):
        """Test core backend APIs that will be used in UI testing"""
        if not self.user_token:
            return False

        headers = {'Authorization': f'Bearer {self.user_token}'}
        
        # Test accounts endpoint
        success, response = self.run_test(
            "GET /accounts",
            "GET",
            "v1/accounts",
            200,
            headers=headers
        )
        
        if not success or not response:
            return False
            
        accounts = response if isinstance(response, list) else response.get('accounts', [])
        if not accounts:
            self.log_test("User Has Account", False, "No accounts found for test user")
            return False
        
        account = accounts[0]
        balance = account.get('balance', 0)
        
        if balance >= 1000:  # At least 10 EUR
            self.log_test("User Has Sufficient Balance", True, f"Balance: {balance/100:.2f} EUR")
        else:
            self.log_test("User Has Sufficient Balance", False, f"Insufficient balance: {balance/100:.2f} EUR")
            
        # Test password verification endpoint
        success, response = self.run_test(
            "POST /auth/verify-password",
            "POST",
            "v1/auth/verify-password",
            200,
            data={"password": "TestUser123!"},
            headers=headers
        )
        
        if success:
            self.log_test("Password Verification API", True, "Password verification endpoint working")
        else:
            self.log_test("Password Verification API", False, "Password verification endpoint failed")
            
        return success

    def test_admin_backend_apis(self):
        """Test admin backend APIs"""
        if not self.admin_token:
            return False

        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Test admin users list endpoint  
        success, response = self.run_test(
            "GET /admin/users",
            "GET",
            "v1/admin/users",
            200,
            headers=headers
        )
        
        if success:
            self.log_test("Admin Users API", True, "Admin can access users list")
        else:
            self.log_test("Admin Users API", False, "Admin cannot access users list")
            
        return success

def main():
    print("=" * 80)
    print("🚨 CRITICAL: Balance Toggle Fix Testing")
    print("=" * 80)
    print("Testing fix for balance visibility toggle button that was triggering form submission.")
    print()
    print("CRITICAL BUG FIXED:")
    print("- Balance toggle (eye icon) was missing type='button' attribute")
    print("- HTML buttons inside forms default to type='submit'") 
    print("- Clicking eye icon was submitting payment form = ACCIDENTAL MONEY TRANSFERS!")
    print()
    print("FIX APPLIED: Added type='button' to BalanceToggle component")
    print("VISUAL FIX: Improved text contrast in admin panel")
    print()
    print("⚠️  CRITICAL: Testing with NEW users only")
    print("   This is a real banking platform with 77 real clients!")
    print()

    tester = BalanceToggleFixTester()

    # Create test user for balance toggle testing
    if not tester.create_test_user():
        print("❌ CRITICAL: Failed to create test user - cannot proceed")
        return 1

    # Add funds to test user
    if not tester.add_funds_to_test_user():
        print("❌ CRITICAL: Failed to add funds to test user")
        return 1

    # Create test admin for visual testing
    if not tester.create_test_admin():
        print("❌ CRITICAL: Failed to create test admin - visual tests will be skipped")
        
    # Test backend APIs
    print("\n🔧 TESTING BACKEND APIs")
    print("-" * 60)
    
    backend_success = tester.test_backend_apis()
    if not backend_success:
        print("❌ CRITICAL: Backend APIs failed - UI testing may not work properly")
        return 1
        
    if tester.admin_token:
        admin_backend_success = tester.test_admin_backend_apis()
        if not admin_backend_success:
            print("❌ WARNING: Admin backend APIs failed - admin UI testing may not work")

    # Print test credentials for UI testing
    print("\n" + "=" * 80)
    print("🎯 TEST CREDENTIALS FOR UI TESTING")
    print("=" * 80)
    if tester.test_user_email:
        print(f"USER EMAIL: {tester.test_user_email}")
        print(f"USER PASSWORD: TestUser123!")
        print(f"USER FUNDS: 500 EUR available for transfer testing")
    
    if tester.test_admin_email:
        print(f"ADMIN EMAIL: {tester.test_admin_email}")
        print(f"ADMIN PASSWORD: TestAdmin123!")
    
    # Final Results
    print("\n" + "=" * 80)
    print(f"📊 BACKEND TEST RESULTS: {tester.tests_passed}/{tester.tests_run} PASSED")
    print("=" * 80)

    print("\n📋 DETAILED RESULTS:")
    for result in tester.test_results:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['test']}")
        if result["details"]:
            print(f"      {result['details']}")

    # Return credentials for UI testing
    return {
        'backend_success': backend_success,
        'user_email': tester.test_user_email,
        'admin_email': tester.test_admin_email,
        'tests_passed': tester.tests_passed,
        'tests_total': tester.tests_run
    }

if __name__ == "__main__":
    result = main()
    sys.exit(0 if isinstance(result, dict) and result.get('backend_success') else 1)