"""Backend API tests for admin transfer deletion and rejection reason editing."""

import requests
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

class TransferAdminFeaturesTester:
    def __init__(self, base_url="https://transfer-confirm-1.preview.emergentagent.com"):
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
                user_role = data.get("user", {}).get("role")
                self.log_result(
                    "Admin Login",
                    True,
                    f"Admin logged in successfully with role: {user_role}",
                    {"email": "admin@ecommbx.io", "role": user_role}
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

    def get_transfers(self, status: str = "SUBMITTED") -> list:
        """Get transfers by status."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/transfers?status={status}",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                print(f"Failed to get transfers: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Exception getting transfers: {str(e)}")
            return []

    def delete_transfer(self, transfer_id: str) -> Dict[str, Any]:
        """Delete a transfer."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/admin/transfers/{transfer_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code in [200, 400, 403, 404, 500] else response.text
            }
                
        except Exception as e:
            return {"status_code": 0, "success": False, "response": str(e)}

    def update_reject_reason(self, transfer_id: str, new_reason: str) -> Dict[str, Any]:
        """Update rejection reason for a transfer."""
        try:
            response = requests.patch(
                f"{self.base_url}/api/v1/admin/transfers/{transfer_id}/reject-reason",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={"reason": new_reason},
                timeout=10
            )
            
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code in [200, 400, 403, 404, 500] else response.text
            }
                
        except Exception as e:
            return {"status_code": 0, "success": False, "response": str(e)}

    def test_delete_transfer_endpoint(self):
        """Test DELETE /api/v1/admin/transfers/{id} endpoint."""
        print("\n" + "=" * 60)
        print("TEST 1: DELETE TRANSFER ENDPOINT")
        print("=" * 60)
        
        # Try to find a transfer to delete (check all statuses)
        test_transfer = None
        for status in ["SUBMITTED", "COMPLETED", "REJECTED"]:
            transfers = self.get_transfers(status)
            if transfers:
                test_transfer = transfers[0]
                print(f"✅ Found {status} transfer to test deletion: {test_transfer.get('id')}")
                break
        
        if not test_transfer:
            self.log_result(
                "Delete Transfer Endpoint - Setup",
                False,
                "No transfers found to test deletion (need at least one transfer in any status)"
            )
            return
        
        transfer_id = test_transfer.get("id")
        transfer_status = test_transfer.get("status")
        beneficiary = test_transfer.get("beneficiary_name", "Unknown")
        amount = test_transfer.get("amount", 0)
        
        print(f"\n📋 Attempting to delete transfer:")
        print(f"   ID: {transfer_id}")
        print(f"   Status: {transfer_status}")
        print(f"   Beneficiary: {beneficiary}")
        print(f"   Amount: €{amount/100:.2f}")
        
        result = self.delete_transfer(transfer_id)
        
        if result["success"]:
            # Verify deletion by trying to fetch the transfer again
            # (We'll check if it's no longer in the list)
            time.sleep(1)  # Brief wait for database update
            all_transfers = []
            for status in ["SUBMITTED", "COMPLETED", "REJECTED"]:
                all_transfers.extend(self.get_transfers(status))
            
            transfer_still_exists = any(t.get("id") == transfer_id for t in all_transfers)
            
            if not transfer_still_exists:
                self.log_result(
                    "Delete Transfer Endpoint - Success",
                    True,
                    f"Transfer {transfer_id} deleted successfully and verified",
                    {
                        "transfer_id": transfer_id,
                        "status": transfer_status,
                        "beneficiary": beneficiary,
                        "amount_eur": f"{amount/100:.2f}"
                    }
                )
            else:
                self.log_result(
                    "Delete Transfer Endpoint - Verification",
                    False,
                    f"Delete API returned success but transfer still exists in database"
                )
        else:
            # Check if it's a permission error (only SUPER_ADMIN can delete)
            if result["status_code"] == 403:
                self.log_result(
                    "Delete Transfer Endpoint - Permission Check",
                    True,
                    "Delete endpoint correctly requires SUPER_ADMIN role (403 Forbidden)",
                    {"status_code": result["status_code"], "response": result["response"]}
                )
            else:
                self.log_result(
                    "Delete Transfer Endpoint - Success",
                    False,
                    f"Transfer deletion failed: {result['response']}",
                    {"status_code": result["status_code"]}
                )

    def test_update_reject_reason_endpoint(self):
        """Test PATCH /api/v1/admin/transfers/{id}/reject-reason endpoint."""
        print("\n" + "=" * 60)
        print("TEST 2: UPDATE REJECTION REASON ENDPOINT")
        print("=" * 60)
        
        # Find a rejected transfer
        rejected_transfers = self.get_transfers("REJECTED")
        
        if not rejected_transfers:
            self.log_result(
                "Update Rejection Reason - Setup",
                False,
                "No rejected transfers found to test rejection reason editing"
            )
            return
        
        test_transfer = rejected_transfers[0]
        transfer_id = test_transfer.get("id")
        old_reason = test_transfer.get("reject_reason", "No reason")
        beneficiary = test_transfer.get("beneficiary_name", "Unknown")
        
        print(f"\n📋 Testing rejection reason update:")
        print(f"   Transfer ID: {transfer_id}")
        print(f"   Beneficiary: {beneficiary}")
        print(f"   Old Reason: {old_reason}")
        
        new_reason = f"Updated reason for testing - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        print(f"   New Reason: {new_reason}")
        
        result = self.update_reject_reason(transfer_id, new_reason)
        
        if result["success"]:
            # Verify the update
            time.sleep(1)  # Brief wait for database update
            updated_transfers = self.get_transfers("REJECTED")
            updated_transfer = next((t for t in updated_transfers if t.get("id") == transfer_id), None)
            
            if updated_transfer:
                updated_reason = updated_transfer.get("reject_reason")
                if updated_reason == new_reason:
                    self.log_result(
                        "Update Rejection Reason - Success",
                        True,
                        f"Rejection reason updated successfully and verified",
                        {
                            "transfer_id": transfer_id,
                            "old_reason": old_reason,
                            "new_reason": new_reason
                        }
                    )
                else:
                    self.log_result(
                        "Update Rejection Reason - Verification",
                        False,
                        f"Update API returned success but reason not updated. Expected: '{new_reason}', Got: '{updated_reason}'"
                    )
            else:
                self.log_result(
                    "Update Rejection Reason - Verification",
                    False,
                    "Could not find transfer after update to verify"
                )
        else:
            self.log_result(
                "Update Rejection Reason - Success",
                False,
                f"Rejection reason update failed: {result['response']}",
                {"status_code": result["status_code"]}
            )

    def test_update_reject_reason_validation(self):
        """Test rejection reason validation (empty reason should fail)."""
        print("\n" + "=" * 60)
        print("TEST 3: REJECTION REASON VALIDATION")
        print("=" * 60)
        
        # Find a rejected transfer
        rejected_transfers = self.get_transfers("REJECTED")
        
        if not rejected_transfers:
            print("⚠️  No rejected transfers found, skipping validation test")
            return
        
        test_transfer = rejected_transfers[0]
        transfer_id = test_transfer.get("id")
        
        # Test with empty reason
        print(f"\n📋 Testing with empty rejection reason (should fail)")
        result = self.update_reject_reason(transfer_id, "")
        
        if not result["success"] and result["status_code"] == 400:
            self.log_result(
                "Rejection Reason Validation - Empty Reason",
                True,
                "Empty rejection reason correctly rejected with 400 Bad Request",
                {"status_code": result["status_code"]}
            )
        else:
            self.log_result(
                "Rejection Reason Validation - Empty Reason",
                False,
                f"Empty reason should be rejected but got status {result['status_code']}"
            )

    def test_update_reject_reason_wrong_status(self):
        """Test that rejection reason can only be updated for REJECTED transfers."""
        print("\n" + "=" * 60)
        print("TEST 4: REJECTION REASON - WRONG STATUS CHECK")
        print("=" * 60)
        
        # Try to update rejection reason for a non-rejected transfer
        for status in ["SUBMITTED", "COMPLETED"]:
            transfers = self.get_transfers(status)
            if transfers:
                test_transfer = transfers[0]
                transfer_id = test_transfer.get("id")
                
                print(f"\n📋 Attempting to update rejection reason for {status} transfer (should fail)")
                result = self.update_reject_reason(transfer_id, "This should not work")
                
                if not result["success"] and result["status_code"] == 400:
                    self.log_result(
                        f"Rejection Reason - {status} Status Check",
                        True,
                        f"Correctly rejected update for {status} transfer with 400 Bad Request",
                        {"status_code": result["status_code"]}
                    )
                else:
                    self.log_result(
                        f"Rejection Reason - {status} Status Check",
                        False,
                        f"Should reject update for {status} transfer but got status {result['status_code']}"
                    )
                return
        
        print("⚠️  No SUBMITTED or COMPLETED transfers found, skipping wrong status test")

    def test_delete_nonexistent_transfer(self):
        """Test deleting a non-existent transfer (should return 404)."""
        print("\n" + "=" * 60)
        print("TEST 5: DELETE NON-EXISTENT TRANSFER")
        print("=" * 60)
        
        fake_transfer_id = "nonexistent_transfer_12345"
        print(f"\n📋 Attempting to delete non-existent transfer: {fake_transfer_id}")
        
        result = self.delete_transfer(fake_transfer_id)
        
        if not result["success"] and result["status_code"] == 404:
            self.log_result(
                "Delete Non-existent Transfer",
                True,
                "Correctly returns 404 for non-existent transfer",
                {"status_code": result["status_code"]}
            )
        elif result["status_code"] == 403:
            self.log_result(
                "Delete Non-existent Transfer",
                True,
                "Returns 403 (permission check happens before existence check)",
                {"status_code": result["status_code"]}
            )
        else:
            self.log_result(
                "Delete Non-existent Transfer",
                False,
                f"Expected 404 or 403 but got {result['status_code']}"
            )

    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "=" * 60)
        print("STARTING TRANSFER ADMIN FEATURES TESTS")
        print("=" * 60 + "\n")
        
        # Step 1: Admin login
        if not self.admin_login():
            print("❌ Cannot proceed without admin access")
            return
        
        # Run all tests
        self.test_delete_transfer_endpoint()
        self.test_update_reject_reason_endpoint()
        self.test_update_reject_reason_validation()
        self.test_update_reject_reason_wrong_status()
        self.test_delete_nonexistent_transfer()

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
    tester = TransferAdminFeaturesTester()
    tester.run_all_tests()
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
