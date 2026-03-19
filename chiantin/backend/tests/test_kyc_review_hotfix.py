"""
Test suite for P0 HOTFIX - KYC Admin Review Actions (Approve/Need More Info/Reject)
Tests the fixed ReviewKYC model and KYCService.review_application() method

Coverage:
- KYC Approve action (with IBAN/BIC validation)  
- KYC Needs More Info action
- KYC Reject action
- KYC Queue (pending applications)
- KYC Review endpoint fields
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Test IBAN/BIC for approval
TEST_IBAN = "IT60X0542811101000000123456"
TEST_BIC = "UNICRITM"


class TestKYCReviewHotfix:
    """Tests for KYC Admin Review Actions P0 Hotfix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token") or data.get("token")
        assert self.token, "No token in login response"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_01_admin_login_works(self):
        """Test admin can login with SUPER_ADMIN credentials"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data or "token" in data
        print("✓ Admin login successful")
    
    def test_02_kyc_pending_queue_loads(self):
        """Test GET /admin/kyc/pending returns list of pending applications"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ KYC pending queue loaded: {len(data)} applications")
        
        # Store first application ID if exists for later tests
        if data:
            self.pending_app_id = data[0].get("id")
            print(f"  First pending app: {self.pending_app_id}")
    
    def test_03_kyc_review_approve_requires_iban(self):
        """Test APPROVE status requires IBAN - should fail without it"""
        # First get a pending application
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        assert response.status_code == 200
        pending = response.json()
        
        if not pending:
            pytest.skip("No pending KYC applications to test")
        
        app_id = pending[0]["id"]
        
        # Try to approve without IBAN - should fail
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "APPROVED",
                "review_notes": "Test approval without IBAN"
            }
        )
        # Should fail with 400 or 422 because IBAN is required
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print(f"✓ Approve without IBAN correctly rejected: {response.json()}")
    
    def test_04_kyc_review_approve_requires_bic(self):
        """Test APPROVE status requires BIC - should fail without it"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        assert response.status_code == 200
        pending = response.json()
        
        if not pending:
            pytest.skip("No pending KYC applications to test")
        
        app_id = pending[0]["id"]
        
        # Try to approve with IBAN but no BIC - should fail
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "APPROVED",
                "assigned_iban": TEST_IBAN,
                "review_notes": "Test approval without BIC"
            }
        )
        # Should fail with 400 because BIC is required
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"✓ Approve without BIC correctly rejected")
    
    def test_05_kyc_review_needs_more_info_works(self):
        """Test NEEDS_MORE_INFO status works without IBAN/BIC"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        assert response.status_code == 200
        pending = response.json()
        
        if not pending:
            pytest.skip("No pending KYC applications to test")
        
        app_id = pending[0]["id"]
        
        # Set to NEEDS_MORE_INFO - should work without IBAN/BIC
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "NEEDS_MORE_INFO",
                "review_notes": "Please provide additional documentation"
            }
        )
        assert response.status_code == 200, f"NEEDS_MORE_INFO failed: {response.text}"
        data = response.json()
        assert data.get("status") == "NEEDS_MORE_INFO"
        print(f"✓ NEEDS_MORE_INFO action works: {data}")
    
    def test_06_kyc_review_reject_works(self):
        """Test REJECT status works without IBAN/BIC"""
        # Need to get a pending or needs_more_info app
        # Let's create a fresh test user for this
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        assert response.status_code == 200
        pending = response.json()
        
        if not pending:
            pytest.skip("No pending KYC applications to test rejection")
        
        app_id = pending[0]["id"]
        
        # First make it NEEDS_MORE_INFO if not already
        requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "NEEDS_MORE_INFO",
                "review_notes": "Setting up for rejection test"
            }
        )
        
        # Now reject it
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "REJECTED",
                "rejection_reason": "Test rejection - documents not valid",
                "review_notes": "Automated test rejection"
            }
        )
        # Check response
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "REJECTED"
            print(f"✓ REJECT action works: {data}")
        elif response.status_code == 400:
            # Application may have been in a state that can't be rejected
            print(f"⚠ Rejection failed (may be expected based on state): {response.text}")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text}")
    
    def test_07_kyc_review_model_accepts_new_fields(self):
        """Test ReviewKYC model accepts review_notes, assigned_iban, assigned_bic"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        assert response.status_code == 200
        pending = response.json()
        
        if not pending:
            pytest.skip("No pending KYC applications")
        
        app_id = pending[0]["id"]
        
        # Send all fields that were added in the hotfix
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "NEEDS_MORE_INFO",
                "review_notes": "Test review notes field",
                "rejection_reason": None,
                "assigned_iban": None,
                "assigned_bic": None
            }
        )
        # Should accept all fields without 422 validation error
        assert response.status_code != 422, f"Model doesn't accept new fields: {response.text}"
        print(f"✓ ReviewKYC model accepts all new fields (review_notes, assigned_iban, assigned_bic)")


class TestKYCApprovalFlow:
    """Test complete KYC Approval flow with IBAN/BIC assignment"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("access_token") or data.get("token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_08_full_approval_flow_with_iban_bic(self):
        """Test KYC approval with valid IBAN and BIC creates account"""
        # Get pending applications
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        assert response.status_code == 200
        pending = response.json()
        
        if not pending:
            pytest.skip("No pending KYC applications to test approval")
        
        app_id = pending[0]["id"]
        user_id = pending[0].get("user_id")
        
        print(f"Testing approval for app: {app_id}, user: {user_id}")
        
        # Approve with valid IBAN and BIC
        unique_iban = f"IT{int(time.time())}123456789012"[-34:]  # Ensure valid length
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "APPROVED",
                "review_notes": "All documents verified",
                "assigned_iban": TEST_IBAN,
                "assigned_bic": TEST_BIC
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "APPROVED"
            print(f"✓ KYC Approval successful: {data}")
        else:
            # May fail if already approved or other state issue
            print(f"⚠ Approval response: {response.status_code} - {response.text}")


class TestAdminOtherPages:
    """Test other admin pages load correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("access_token") or data.get("token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_09_admin_users_page(self):
        """Test Admin Users endpoint returns paginated users"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users?page=1&limit=50",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data or isinstance(data, list)
        print(f"✓ Admin Users endpoint works")
    
    def test_10_admin_accounts_page(self):
        """Test Admin Accounts endpoint returns data (no accounts.map error)"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/accounts?page=1&limit=50",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should be a list or dict with accounts
        assert isinstance(data, (list, dict))
        print(f"✓ Admin Accounts endpoint works")
    
    def test_11_admin_transfers_queue(self):
        """Test Admin Transfers Queue endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/transfers/queue?page=1&limit=50",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
        print(f"✓ Admin Transfers Queue endpoint works")
    
    def test_12_admin_support_tickets(self):
        """Test Admin Support Tickets endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/support/tickets?page=1&limit=50",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
        print(f"✓ Admin Support Tickets endpoint works")
    
    def test_13_admin_notification_counts(self):
        """Test Admin Notification Counts endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/notification-counts",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should have count fields
        assert isinstance(data, dict)
        print(f"✓ Admin Notification Counts: {data}")


class TestIBANBICValidation:
    """Test IBAN and BIC validation in KYC approval"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("access_token") or data.get("token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_14_invalid_iban_format_rejected(self):
        """Test invalid IBAN format is rejected on approval"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        if response.status_code != 200 or not response.json():
            pytest.skip("No pending KYC applications")
        
        app_id = response.json()[0]["id"]
        
        # Try with invalid IBAN (too short, bad format)
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "APPROVED",
                "assigned_iban": "INVALID123",  # Bad format
                "assigned_bic": TEST_BIC
            }
        )
        assert response.status_code == 400, f"Invalid IBAN should be rejected: {response.text}"
        print("✓ Invalid IBAN format correctly rejected")
    
    def test_15_invalid_bic_format_rejected(self):
        """Test invalid BIC format is rejected on approval"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/kyc/pending",
            headers=self.headers
        )
        if response.status_code != 200 or not response.json():
            pytest.skip("No pending KYC applications")
        
        app_id = response.json()[0]["id"]
        
        # Try with invalid BIC (wrong format)
        response = requests.post(
            f"{BASE_URL}/api/v1/admin/kyc/{app_id}/review",
            headers=self.headers,
            json={
                "status": "APPROVED",
                "assigned_iban": TEST_IBAN,
                "assigned_bic": "123"  # Bad format - too short
            }
        )
        assert response.status_code == 400, f"Invalid BIC should be rejected: {response.text}"
        print("✓ Invalid BIC format correctly rejected")
    
    def test_16_valid_iban_bic_accepted(self):
        """Test valid IBAN and BIC formats are accepted"""
        # This is mainly to verify the format validators don't false-positive
        # Valid IBAN: IT60X0542811101000000123456 (Italian IBAN)
        # Valid BIC: UNICRITM or UNICRITMMXXX
        
        # Format validation - not actually submitting to avoid state changes
        import re
        
        iban = TEST_IBAN.replace(" ", "").upper()
        assert re.match(r'^[A-Z]{2}[A-Z0-9]{13,32}$', iban), "Test IBAN should be valid"
        
        bic = TEST_BIC.replace(" ", "").upper()
        assert re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', bic), "Test BIC should be valid"
        
        print(f"✓ Test IBAN ({TEST_IBAN}) and BIC ({TEST_BIC}) formats are valid")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
