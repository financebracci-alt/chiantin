"""Backend API tests for duplicate IBAN handling and IBAN update endpoint."""

import requests
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

class DuplicateIBANTester:
    def __init__(self, base_url="https://elated-vaughan-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
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
        print("ADMIN LOGIN")
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
                    {"email": "admin@ecommbx.io"}
                )
                return True
            else:
                self.log_result(
                    "Admin Login",
                    False,
                    f"Login failed with status {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception: {str(e)}")
            return False

    def get_all_users(self) -> list:
        """Get all users."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/users",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get users: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Exception getting users: {str(e)}")
            return []

    def get_user_details(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details including accounts."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/users/{user_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get user details: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Exception getting user details: {str(e)}")
            return None

    def get_pending_kyc_applications(self) -> list:
        """Get all pending KYC applications."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/kyc/pending",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get pending KYC: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Exception getting pending KYC: {str(e)}")
            return []

    def approve_kyc_with_iban(self, application_id: str, iban: str, bic: str) -> Dict[str, Any]:
        """Approve KYC application with specific IBAN."""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/admin/kyc/{application_id}/review",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "status": "APPROVED",
                    "assigned_iban": iban,
                    "assigned_bic": bic,
                    "review_notes": "Test approval for duplicate IBAN testing"
                },
                timeout=10
            )
            
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code in [200, 400, 500] else response.text
            }
                
        except Exception as e:
            return {"status_code": 0, "success": False, "response": str(e)}

    def update_account_iban(self, user_id: str, iban: str, bic: str) -> Dict[str, Any]:
        """Update IBAN and BIC for a user's account using the new endpoint."""
        try:
            response = requests.patch(
                f"{self.base_url}/api/v1/admin/users/{user_id}/account-iban",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "iban": iban,
                    "bic": bic
                },
                timeout=10
            )
            
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code in [200, 400, 404] else response.text
            }
                
        except Exception as e:
            return {"status_code": 0, "success": False, "response": str(e)}

    def test_duplicate_iban_allowed(self):
        """Test that duplicate IBANs are allowed (no unique constraint)."""
        print("\n" + "=" * 60)
        print("TEST 1: DUPLICATE IBAN ALLOWED IN KYC APPROVAL")
        print("=" * 60)
        
        # Get pending KYC applications
        pending_apps = self.get_pending_kyc_applications()
        
        if len(pending_apps) < 2:
            print(f"⚠️  Only {len(pending_apps)} pending KYC application(s) found")
            print("⚠️  Need at least 2 applications to test duplicate IBAN scenario")
            
            # Try to find users with accounts instead
            users = self.get_all_users()
            users_with_accounts = []
            
            for user in users[:10]:  # Check first 10 users
                details = self.get_user_details(user["id"])
                if details and details.get("accounts"):
                    users_with_accounts.append(details)
                    if len(users_with_accounts) >= 2:
                        break
            
            if len(users_with_accounts) >= 2:
                print(f"✅ Found {len(users_with_accounts)} users with accounts for testing")
                self.test_duplicate_iban_via_update(users_with_accounts)
            else:
                self.log_result(
                    "Duplicate IBAN Test Setup",
                    False,
                    "Not enough test data (need 2 pending KYC apps or 2 users with accounts)"
                )
            return
        
        # Use first two pending applications
        app1 = pending_apps[0]
        app2 = pending_apps[1]
        
        app1_id = app1.get("id")
        app2_id = app2.get("id")
        user1_id = app1.get("user_id")
        user2_id = app2.get("user_id")
        
        # Use the same IBAN for both
        test_iban = "IT60X0542811101000000123456"
        test_bic = "BCITITMM"  # Valid 8-character BIC
        
        print(f"\n📋 Approving first KYC with IBAN: {test_iban}")
        result1 = self.approve_kyc_with_iban(app1_id, test_iban, test_bic)
        
        if result1["success"]:
            print(f"✅ First KYC approved successfully")
            
            # Now try to approve second KYC with SAME IBAN
            print(f"\n📋 Approving second KYC with SAME IBAN: {test_iban}")
            result2 = self.approve_kyc_with_iban(app2_id, test_iban, test_bic)
            
            if result2["success"]:
                self.log_result(
                    "Duplicate IBAN Allowed in KYC Approval",
                    True,
                    f"Successfully approved two KYC applications with the same IBAN: {test_iban}",
                    {"user1_id": user1_id, "user2_id": user2_id, "iban": test_iban}
                )
            else:
                self.log_result(
                    "Duplicate IBAN Allowed in KYC Approval",
                    False,
                    f"Second KYC approval failed (should succeed): {result2['response']}",
                    {"status_code": result2["status_code"]}
                )
        else:
            self.log_result(
                "Duplicate IBAN Test Setup",
                False,
                f"First KYC approval failed: {result1['response']}"
            )

    def test_duplicate_iban_via_update(self, users_with_accounts: list):
        """Test duplicate IBAN via the update endpoint."""
        print("\n" + "=" * 60)
        print("TEST 1B: DUPLICATE IBAN ALLOWED VIA UPDATE ENDPOINT")
        print("=" * 60)
        
        user1 = users_with_accounts[0]
        user2 = users_with_accounts[1]
        
        user1_id = user1["user"]["id"]
        user2_id = user2["user"]["id"]
        
        # Use the same IBAN for both
        test_iban = "FR1420041010050500013M02606"
        test_bic = "BNPAFRPP"
        
        print(f"\n📋 Updating first user's IBAN to: {test_iban}")
        result1 = self.update_account_iban(user1_id, test_iban, test_bic)
        
        if result1["success"]:
            print(f"✅ First user's IBAN updated successfully")
            
            # Now try to update second user with SAME IBAN
            print(f"\n📋 Updating second user's IBAN to SAME IBAN: {test_iban}")
            result2 = self.update_account_iban(user2_id, test_iban, test_bic)
            
            if result2["success"]:
                self.log_result(
                    "Duplicate IBAN Allowed via Update Endpoint",
                    True,
                    f"Successfully updated two accounts with the same IBAN: {test_iban}",
                    {"user1_id": user1_id, "user2_id": user2_id, "iban": test_iban}
                )
            else:
                self.log_result(
                    "Duplicate IBAN Allowed via Update Endpoint",
                    False,
                    f"Second IBAN update failed (should succeed): {result2['response']}",
                    {"status_code": result2["status_code"]}
                )
        else:
            self.log_result(
                "Duplicate IBAN Test Setup",
                False,
                f"First IBAN update failed: {result1['response']}"
            )

    def test_update_iban_endpoint(self):
        """Test the new PATCH /api/v1/admin/users/{user_id}/account-iban endpoint."""
        print("\n" + "=" * 60)
        print("TEST 2: UPDATE IBAN ENDPOINT")
        print("=" * 60)
        
        # Find a user with an account
        users = self.get_all_users()
        test_user = None
        
        for user in users[:10]:
            details = self.get_user_details(user["id"])
            if details and details.get("accounts"):
                test_user = details
                break
        
        if not test_user:
            self.log_result(
                "Update IBAN Endpoint Test",
                False,
                "No user with account found for testing"
            )
            return
        
        user_id = test_user["user"]["id"]
        old_iban = test_user["accounts"][0].get("iban", "None")
        
        # Test with valid IBAN and BIC
        new_iban = "ES9121000418450200051332"
        new_bic = "CAIXESBBXXX"
        
        print(f"\n📋 Updating IBAN for user {user_id}")
        print(f"   Old IBAN: {old_iban}")
        print(f"   New IBAN: {new_iban}")
        
        result = self.update_account_iban(user_id, new_iban, new_bic)
        
        if result["success"]:
            # Verify the update
            updated_details = self.get_user_details(user_id)
            if updated_details:
                updated_iban = updated_details["accounts"][0].get("iban")
                if updated_iban == new_iban:
                    self.log_result(
                        "Update IBAN Endpoint - Success",
                        True,
                        f"IBAN updated successfully from {old_iban} to {new_iban}",
                        {"user_id": user_id, "new_iban": new_iban, "new_bic": new_bic}
                    )
                else:
                    self.log_result(
                        "Update IBAN Endpoint - Verification",
                        False,
                        f"IBAN update succeeded but verification failed. Expected: {new_iban}, Got: {updated_iban}"
                    )
            else:
                self.log_result(
                    "Update IBAN Endpoint - Verification",
                    False,
                    "Could not verify IBAN update"
                )
        else:
            self.log_result(
                "Update IBAN Endpoint - Success",
                False,
                f"IBAN update failed: {result['response']}",
                {"status_code": result["status_code"]}
            )

    def test_iban_validation(self):
        """Test IBAN format validation."""
        print("\n" + "=" * 60)
        print("TEST 3: IBAN FORMAT VALIDATION")
        print("=" * 60)
        
        # Find a user with an account
        users = self.get_all_users()
        test_user = None
        
        for user in users[:10]:
            details = self.get_user_details(user["id"])
            if details and details.get("accounts"):
                test_user = details
                break
        
        if not test_user:
            self.log_result(
                "IBAN Validation Test",
                False,
                "No user with account found for testing"
            )
            return
        
        user_id = test_user["user"]["id"]
        
        # Test invalid IBAN formats
        invalid_ibans = [
            ("12345", "ATLASLT21", "Too short"),
            ("INVALID", "ATLASLT21", "Invalid format"),
            ("1234567890123456", "ATLASLT21", "No country code"),
            ("", "ATLASLT21", "Empty IBAN")
        ]
        
        for invalid_iban, bic, description in invalid_ibans:
            print(f"\n📋 Testing invalid IBAN: {description}")
            result = self.update_account_iban(user_id, invalid_iban, bic)
            
            if not result["success"] and result["status_code"] == 400:
                print(f"✅ Invalid IBAN correctly rejected: {description}")
            else:
                self.log_result(
                    f"IBAN Validation - {description}",
                    False,
                    f"Invalid IBAN should be rejected but got status {result['status_code']}"
                )
                return
        
        self.log_result(
            "IBAN Format Validation",
            True,
            "All invalid IBAN formats were correctly rejected",
            {"tested_cases": len(invalid_ibans)}
        )

    def test_bic_validation(self):
        """Test BIC format validation."""
        print("\n" + "=" * 60)
        print("TEST 4: BIC FORMAT VALIDATION")
        print("=" * 60)
        
        # Find a user with an account
        users = self.get_all_users()
        test_user = None
        
        for user in users[:10]:
            details = self.get_user_details(user["id"])
            if details and details.get("accounts"):
                test_user = details
                break
        
        if not test_user:
            self.log_result(
                "BIC Validation Test",
                False,
                "No user with account found for testing"
            )
            return
        
        user_id = test_user["user"]["id"]
        valid_iban = "GB82WEST12345698765432"
        
        # Test invalid BIC formats
        invalid_bics = [
            ("123", "Too short"),
            ("INVALID", "Invalid format"),
            ("12345678", "No letters"),
            ("", "Empty BIC")
        ]
        
        for invalid_bic, description in invalid_bics:
            print(f"\n📋 Testing invalid BIC: {description}")
            result = self.update_account_iban(user_id, valid_iban, invalid_bic)
            
            if not result["success"] and result["status_code"] == 400:
                print(f"✅ Invalid BIC correctly rejected: {description}")
            else:
                self.log_result(
                    f"BIC Validation - {description}",
                    False,
                    f"Invalid BIC should be rejected but got status {result['status_code']}"
                )
                return
        
        self.log_result(
            "BIC Format Validation",
            True,
            "All invalid BIC formats were correctly rejected",
            {"tested_cases": len(invalid_bics)}
        )

    def test_endpoint_not_found(self):
        """Test that endpoint returns 404 for non-existent user."""
        print("\n" + "=" * 60)
        print("TEST 5: ENDPOINT ERROR HANDLING")
        print("=" * 60)
        
        fake_user_id = "nonexistent_user_12345"
        result = self.update_account_iban(fake_user_id, "GB82WEST12345698765432", "NWBKGB2L")
        
        if not result["success"] and result["status_code"] == 404:
            self.log_result(
                "Endpoint 404 Handling",
                True,
                "Endpoint correctly returns 404 for non-existent user",
                {"status_code": result["status_code"]}
            )
        else:
            self.log_result(
                "Endpoint 404 Handling",
                False,
                f"Expected 404 but got {result['status_code']}"
            )

    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "=" * 60)
        print("STARTING DUPLICATE IBAN & UPDATE ENDPOINT TESTS")
        print("=" * 60 + "\n")
        
        # Step 1: Admin login
        if not self.admin_login():
            print("❌ Cannot proceed without admin access")
            return
        
        # Run all tests
        self.test_duplicate_iban_allowed()
        self.test_update_iban_endpoint()
        self.test_iban_validation()
        self.test_bic_validation()
        self.test_endpoint_not_found()

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
    tester = DuplicateIBANTester()
    tester.run_all_tests()
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
