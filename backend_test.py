"""
Backend API Testing for Project Atlas
Tests all backend endpoints with demo credentials
"""

import requests
import sys
from datetime import datetime

# Backend URL from environment
BASE_URL = "https://bank-atlas.preview.emergentagent.com/api/v1"
HEALTH_URL = "https://bank-atlas.preview.emergentagent.com/api/health"

# Demo credentials
CUSTOMER_EMAIL = "customer@demo.com"
CUSTOMER_PASSWORD = "Demo@123456"
ADMIN_EMAIL = "admin@atlas.local"
ADMIN_PASSWORD = "Admin@123456"


class APITester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.customer_token = None
        self.admin_token = None
        self.customer_user = None
        self.admin_user = None
        self.customer_accounts = []
        self.admin_users = []
        self.test_ticket_id = None

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
        try:
            response = requests.get(HEALTH_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True)
                return True
            else:
                self.log_test("Health Check", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, str(e))
            return False

    def test_customer_login(self):
        """Test customer login"""
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.customer_token = data["access_token"]
                    self.customer_user = data["user"]
                    self.log_test("Customer Login", True)
                    return True
                else:
                    self.log_test("Customer Login", False, "Missing token or user in response")
                    return False
            else:
                self.log_test("Customer Login", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Customer Login", False, str(e))
            return False

    def test_admin_login(self):
        """Test admin login"""
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

    def test_customer_get_me(self):
        """Test get current user endpoint for customer"""
        if not self.customer_token:
            self.log_test("Customer Get Me", False, "No customer token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/auth/me",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("email") == CUSTOMER_EMAIL:
                    self.log_test("Customer Get Me", True)
                    return True
                else:
                    self.log_test("Customer Get Me", False, "Email mismatch")
                    return False
            else:
                self.log_test("Customer Get Me", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Customer Get Me", False, str(e))
            return False

    def test_customer_get_accounts(self):
        """Test get customer accounts"""
        if not self.customer_token:
            self.log_test("Customer Get Accounts", False, "No customer token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/accounts",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.customer_accounts = data
                    self.log_test("Customer Get Accounts", True)
                    print(f"   Found {len(data)} account(s)")
                    if len(data) > 0:
                        print(f"   First account balance: €{data[0].get('balance', 0) / 100:.2f}")
                    return True
                else:
                    self.log_test("Customer Get Accounts", False, "Response is not a list")
                    return False
            else:
                self.log_test("Customer Get Accounts", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Customer Get Accounts", False, str(e))
            return False

    def test_customer_get_transactions(self):
        """Test get customer transactions"""
        if not self.customer_token:
            self.log_test("Customer Get Transactions", False, "No customer token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Customer Get Transactions", False, "No accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            response = requests.get(
                f"{BASE_URL}/accounts/{account_id}/transactions",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Customer Get Transactions", True)
                    print(f"   Found {len(data)} transaction(s)")
                    return True
                else:
                    self.log_test("Customer Get Transactions", False, "Response is not a list")
                    return False
            else:
                self.log_test("Customer Get Transactions", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Customer Get Transactions", False, str(e))
            return False

    def test_admin_get_users(self):
        """Test admin get all users"""
        if not self.admin_token:
            self.log_test("Admin Get Users", False, "No admin token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/users",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.admin_users = data
                    self.log_test("Admin Get Users", True)
                    print(f"   Found {len(data)} user(s)")
                    return True
                else:
                    self.log_test("Admin Get Users", False, "Response is not a list")
                    return False
            else:
                self.log_test("Admin Get Users", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Get Users", False, str(e))
            return False

    def test_admin_get_user_details(self):
        """Test admin get user details"""
        if not self.admin_token:
            self.log_test("Admin Get User Details", False, "No admin token available")
            return False
        
        if not self.admin_users:
            self.log_test("Admin Get User Details", False, "No users available")
            return False
        
        try:
            # Get customer user details
            customer_user = next((u for u in self.admin_users if u["email"] == CUSTOMER_EMAIL), None)
            if not customer_user:
                self.log_test("Admin Get User Details", False, "Customer user not found in user list")
                return False
            
            user_id = customer_user["id"]
            response = requests.get(
                f"{BASE_URL}/admin/users/{user_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "user" in data and "accounts" in data:
                    self.log_test("Admin Get User Details", True)
                    print(f"   User: {data['user']['email']}")
                    print(f"   Accounts: {len(data['accounts'])}")
                    if len(data['accounts']) > 0:
                        print(f"   First account balance: €{data['accounts'][0].get('balance', 0) / 100:.2f}")
                    return True
                else:
                    self.log_test("Admin Get User Details", False, "Missing user or accounts in response")
                    return False
            else:
                self.log_test("Admin Get User Details", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Get User Details", False, str(e))
            return False

    def test_admin_update_user_status(self):
        """Test admin enable/disable user status (BUG FIX TEST)"""
        if not self.admin_token:
            self.log_test("Admin Update User Status", False, "No admin token available")
            return False
        
        if not self.admin_users:
            self.log_test("Admin Update User Status", False, "No users available")
            return False
        
        try:
            # Find a customer user to test with
            customer_user = next((u for u in self.admin_users if u["email"] == CUSTOMER_EMAIL), None)
            if not customer_user:
                self.log_test("Admin Update User Status", False, "Customer user not found")
                return False
            
            user_id = customer_user["id"]
            original_status = customer_user["status"]
            
            # Test 1: Disable user (if currently active)
            if original_status == "ACTIVE":
                response = requests.patch(
                    f"{BASE_URL}/admin/users/{user_id}/status",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json={"status": "DISABLED"},
                    timeout=10
                )
                if response.status_code != 200:
                    self.log_test("Admin Update User Status (Disable)", False, f"Status {response.status_code}: {response.text}")
                    return False
                
                data = response.json()
                if not data.get("success"):
                    self.log_test("Admin Update User Status (Disable)", False, "Success flag not true")
                    return False
                
                print(f"   ✓ Disabled user successfully")
                
                # Test 2: Re-enable user
                response2 = requests.patch(
                    f"{BASE_URL}/admin/users/{user_id}/status",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json={"status": "ACTIVE"},
                    timeout=10
                )
                if response2.status_code != 200:
                    self.log_test("Admin Update User Status (Enable)", False, f"Status {response2.status_code}: {response2.text}")
                    return False
                
                data2 = response2.json()
                if not data2.get("success"):
                    self.log_test("Admin Update User Status (Enable)", False, "Success flag not true")
                    return False
                
                print(f"   ✓ Enabled user successfully")
                self.log_test("Admin Update User Status", True)
                return True
            else:
                # If user is not active, just try to enable them
                response = requests.patch(
                    f"{BASE_URL}/admin/users/{user_id}/status",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json={"status": "ACTIVE"},
                    timeout=10
                )
                if response.status_code == 200:
                    self.log_test("Admin Update User Status", True)
                    print(f"   ✓ Enabled user successfully")
                    return True
                else:
                    self.log_test("Admin Update User Status", False, f"Status {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            self.log_test("Admin Update User Status", False, str(e))
            return False

    def test_admin_top_up(self):
        """Test admin top-up functionality"""
        if not self.admin_token:
            self.log_test("Admin Top-Up", False, "No admin token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Admin Top-Up", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            initial_balance = self.customer_accounts[0]["balance"]
            
            # Top up 5000 cents (€50)
            response = requests.post(
                f"{BASE_URL}/admin/ledger/top-up",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "account_id": account_id,
                    "amount": 5000,
                    "reason": "Test top-up from automated testing"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "transaction_type" in data:
                    self.log_test("Admin Top-Up", True)
                    print(f"   Transaction ID: {data['id']}")
                    print(f"   Type: {data['transaction_type']}")
                    
                    # Verify balance increased
                    response2 = requests.get(
                        f"{BASE_URL}/accounts",
                        headers={"Authorization": f"Bearer {self.customer_token}"},
                        timeout=10
                    )
                    if response2.status_code == 200:
                        accounts = response2.json()
                        new_balance = accounts[0]["balance"]
                        if new_balance > initial_balance:
                            print(f"   Balance increased: €{initial_balance / 100:.2f} → €{new_balance / 100:.2f}")
                        else:
                            print(f"   Warning: Balance did not increase as expected")
                    
                    return True
                else:
                    self.log_test("Admin Top-Up", False, "Missing transaction data in response")
                    return False
            else:
                self.log_test("Admin Top-Up", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Top-Up", False, str(e))
            return False

    def test_mfa_setup(self):
        """Test MFA setup endpoint"""
        if not self.customer_token:
            self.log_test("MFA Setup", False, "No customer token available")
            return False
        
        try:
            response = requests.post(
                f"{BASE_URL}/auth/mfa/setup",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "secret" in data and "qr_code_uri" in data:
                    self.log_test("MFA Setup", True)
                    print(f"   Secret length: {len(data['secret'])}")
                    print(f"   QR URI starts with: {data['qr_code_uri'][:50]}...")
                    return True
                else:
                    self.log_test("MFA Setup", False, "Missing secret or qr_code_uri")
                    return False
            else:
                self.log_test("MFA Setup", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("MFA Setup", False, str(e))
            return False

    def test_kyc_get_application(self):
        """Test get KYC application"""
        if not self.customer_token:
            self.log_test("KYC Get Application", False, "No customer token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/kyc/application",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "status" in data:
                    self.log_test("KYC Get Application", True)
                    print(f"   Status: {data['status']}")
                    return True
                else:
                    self.log_test("KYC Get Application", False, "Missing id or status")
                    return False
            else:
                self.log_test("KYC Get Application", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("KYC Get Application", False, str(e))
            return False

    def test_admin_kyc_pending(self):
        """Test get pending KYC applications"""
        if not self.admin_token:
            self.log_test("Admin KYC Pending", False, "No admin token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/kyc/pending",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Admin KYC Pending", True)
                    print(f"   Found {len(data)} pending application(s)")
                    return True
                else:
                    self.log_test("Admin KYC Pending", False, "Response is not a list")
                    return False
            else:
                self.log_test("Admin KYC Pending", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin KYC Pending", False, str(e))
            return False

    def test_admin_withdraw(self):
        """Test admin withdraw functionality"""
        if not self.admin_token:
            self.log_test("Admin Withdraw", False, "No admin token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Admin Withdraw", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            
            # Withdraw 1000 cents (€10)
            response = requests.post(
                f"{BASE_URL}/admin/ledger/withdraw",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "account_id": account_id,
                    "amount": 1000,
                    "reason": "Test withdrawal from automated testing"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "transaction_type" in data:
                    self.log_test("Admin Withdraw", True)
                    print(f"   Transaction ID: {data['id']}")
                    return True
                else:
                    self.log_test("Admin Withdraw", False, "Missing transaction data")
                    return False
            else:
                self.log_test("Admin Withdraw", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Withdraw", False, str(e))
            return False

    def test_admin_charge_fee(self):
        """Test admin charge fee functionality"""
        if not self.admin_token:
            self.log_test("Admin Charge Fee", False, "No admin token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Admin Charge Fee", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            
            # Charge fee 500 cents (€5)
            response = requests.post(
                f"{BASE_URL}/admin/ledger/charge-fee",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "account_id": account_id,
                    "amount": 500,
                    "reason": "Test fee charge from automated testing"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "transaction_type" in data:
                    self.log_test("Admin Charge Fee", True)
                    print(f"   Transaction ID: {data['id']}")
                    return True
                else:
                    self.log_test("Admin Charge Fee", False, "Missing transaction data")
                    return False
            else:
                self.log_test("Admin Charge Fee", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Charge Fee", False, str(e))
            return False

    def test_admin_professional_credit(self):
        """Test admin professional credit with metadata (NEW FEATURE)"""
        if not self.admin_token:
            self.log_test("Admin Professional Credit", False, "No admin token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Admin Professional Credit", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            initial_balance = self.customer_accounts[0]["balance"]
            
            # Professional credit with full metadata
            response = requests.post(
                f"{BASE_URL}/admin/accounts/{account_id}/topup",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "amount": 25000,  # €250
                    "display_type": "SEPA Transfer",
                    "sender_name": "Deutsche Bank AG",
                    "sender_iban": "DE89370400440532013000",
                    "sender_bic": "DEUTDEDB",
                    "reference": "TRF2024011500123",
                    "description": "Salary Payment January 2024",
                    "admin_note": "Test professional credit from automated testing"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and "new_balance" in data:
                    self.log_test("Admin Professional Credit", True)
                    print(f"   New balance: €{data['new_balance'] / 100:.2f}")
                    print(f"   Balance increased: €{initial_balance / 100:.2f} → €{data['new_balance'] / 100:.2f}")
                    return True
                else:
                    self.log_test("Admin Professional Credit", False, "Missing ok or new_balance in response")
                    return False
            else:
                self.log_test("Admin Professional Credit", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Professional Credit", False, str(e))
            return False

    def test_admin_professional_debit(self):
        """Test admin professional debit with metadata (NEW FEATURE)"""
        if not self.admin_token:
            self.log_test("Admin Professional Debit", False, "No admin token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Admin Professional Debit", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            
            # Get current balance
            response_balance = requests.get(
                f"{BASE_URL}/accounts",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response_balance.status_code != 200:
                self.log_test("Admin Professional Debit", False, "Could not get current balance")
                return False
            
            initial_balance = response_balance.json()[0]["balance"]
            
            # Professional debit with metadata
            response = requests.post(
                f"{BASE_URL}/admin/accounts/{account_id}/withdraw",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "amount": 5000,  # €50
                    "display_type": "Withdrawal",
                    "recipient_name": "Amazon EU",
                    "recipient_iban": "LU280019400644750000",
                    "reference": "INV-2024-001",
                    "description": "Monthly subscription payment",
                    "admin_note": "Test professional debit from automated testing"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and "new_balance" in data:
                    self.log_test("Admin Professional Debit", True)
                    print(f"   New balance: €{data['new_balance'] / 100:.2f}")
                    print(f"   Balance decreased: €{initial_balance / 100:.2f} → €{data['new_balance'] / 100:.2f}")
                    return True
                else:
                    self.log_test("Admin Professional Debit", False, "Missing ok or new_balance in response")
                    return False
            else:
                self.log_test("Admin Professional Debit", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Professional Debit", False, str(e))
            return False

    def test_customer_view_professional_transactions(self):
        """Test customer can view professional transaction metadata (NEW FEATURE)"""
        if not self.customer_token:
            self.log_test("Customer View Professional Transactions", False, "No customer token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Customer View Professional Transactions", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            response = requests.get(
                f"{BASE_URL}/accounts/{account_id}/transactions",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                transactions = response.json()
                if isinstance(transactions, list) and len(transactions) > 0:
                    # Check if recent transactions have professional metadata
                    professional_txns = []
                    for txn in transactions[:5]:  # Check last 5 transactions
                        metadata = txn.get("metadata", {})
                        if metadata.get("display_type") or metadata.get("sender_name"):
                            professional_txns.append({
                                "display_type": metadata.get("display_type"),
                                "sender_name": metadata.get("sender_name"),
                                "reference": metadata.get("reference"),
                                "description": metadata.get("description")
                            })
                    
                    if professional_txns:
                        self.log_test("Customer View Professional Transactions", True)
                        print(f"   Found {len(professional_txns)} professional transaction(s)")
                        for i, txn in enumerate(professional_txns[:2], 1):
                            print(f"   Transaction {i}:")
                            print(f"     Display Type: {txn.get('display_type', 'N/A')}")
                            print(f"     Sender: {txn.get('sender_name', 'N/A')}")
                            print(f"     Reference: {txn.get('reference', 'N/A')}")
                        return True
                    else:
                        self.log_test("Customer View Professional Transactions", False, "No professional transactions found with metadata")
                        return False
                else:
                    self.log_test("Customer View Professional Transactions", False, "No transactions available")
                    return False
            else:
                self.log_test("Customer View Professional Transactions", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Customer View Professional Transactions", False, str(e))
            return False

    def test_admin_audit_logs(self):
        """Test get audit logs"""
        if not self.admin_token:
            self.log_test("Admin Audit Logs", False, "No admin token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/audit-logs",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Admin Audit Logs", True)
                    print(f"   Found {len(data)} audit log(s)")
                    return True
                else:
                    self.log_test("Admin Audit Logs", False, "Response is not a list")
                    return False
            else:
                self.log_test("Admin Audit Logs", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Audit Logs", False, str(e))
            return False

    def test_statement_download(self):
        """Test statement download endpoint"""
        if not self.customer_token:
            self.log_test("Statement Download", False, "No customer token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Statement Download", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            # Try to download current month statement
            now = datetime.now()
            
            response = requests.get(
                f"{BASE_URL}/accounts/{account_id}/statement/{now.year}/{now.month}",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                # Check if response is PDF
                if response.headers.get('content-type') == 'application/pdf':
                    self.log_test("Statement Download", True)
                    print(f"   PDF size: {len(response.content)} bytes")
                    return True
                else:
                    self.log_test("Statement Download", False, "Response is not a PDF")
                    return False
            else:
                self.log_test("Statement Download", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Statement Download", False, str(e))
            return False

    def test_create_support_ticket(self):
        """Test create support ticket"""
        if not self.customer_token:
            self.log_test("Create Support Ticket", False, "No customer token available")
            return False
        
        try:
            response = requests.post(
                f"{BASE_URL}/tickets/create",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                json={
                    "subject": "Test ticket from automated testing",
                    "description": "This is a test ticket created during automated testing."
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "subject" in data and "status" in data:
                    self.log_test("Create Support Ticket", True)
                    print(f"   Ticket ID: {data['id']}")
                    print(f"   Status: {data['status']}")
                    self.test_ticket_id = data['id']
                    return True
                else:
                    self.log_test("Create Support Ticket", False, "Missing ticket data")
                    return False
            else:
                self.log_test("Create Support Ticket", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Create Support Ticket", False, str(e))
            return False

    def test_get_customer_tickets(self):
        """Test get customer tickets"""
        if not self.customer_token:
            self.log_test("Get Customer Tickets", False, "No customer token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/tickets",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Get Customer Tickets", True)
                    print(f"   Found {len(data)} ticket(s)")
                    return True
                else:
                    self.log_test("Get Customer Tickets", False, "Response is not a list")
                    return False
            else:
                self.log_test("Get Customer Tickets", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Customer Tickets", False, str(e))
            return False

    def test_get_notifications(self):
        """Test get notifications"""
        if not self.customer_token:
            self.log_test("Get Notifications", False, "No customer token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/notifications",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Get Notifications", True)
                    print(f"   Found {len(data)} notification(s)")
                    unread = sum(1 for n in data if not n.get('read', False))
                    print(f"   Unread: {unread}")
                    return True
                else:
                    self.log_test("Get Notifications", False, "Response is not a list")
                    return False
            else:
                self.log_test("Get Notifications", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Notifications", False, str(e))
            return False

    def test_create_card_request(self):
        """Test create card request"""
        if not self.customer_token:
            self.log_test("Create Card Request", False, "No customer token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Create Card Request", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            response = requests.post(
                f"{BASE_URL}/card-requests",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                json={
                    "account_id": account_id,
                    "card_type": "DEBIT_PHYSICAL"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and "data" in data:
                    self.log_test("Create Card Request", True)
                    print(f"   Request ID: {data['data'].get('id')}")
                    print(f"   Card Type: {data['data'].get('card_type')}")
                    print(f"   Status: {data['data'].get('status')}")
                    return True
                else:
                    self.log_test("Create Card Request", False, "Missing ok or data in response")
                    return False
            else:
                self.log_test("Create Card Request", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Create Card Request", False, str(e))
            return False

    def test_get_card_requests(self):
        """Test get card requests"""
        if not self.customer_token:
            self.log_test("Get Card Requests", False, "No customer token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/card-requests",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and isinstance(data.get("data"), list):
                    self.log_test("Get Card Requests", True)
                    print(f"   Found {len(data['data'])} card request(s)")
                    return True
                else:
                    self.log_test("Get Card Requests", False, "Missing ok or data is not a list")
                    return False
            else:
                self.log_test("Get Card Requests", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Card Requests", False, str(e))
            return False

    def test_get_cards(self):
        """Test get cards"""
        if not self.customer_token:
            self.log_test("Get Cards", False, "No customer token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/cards",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and isinstance(data.get("data"), list):
                    self.log_test("Get Cards", True)
                    print(f"   Found {len(data['data'])} card(s)")
                    return True
                else:
                    self.log_test("Get Cards", False, "Missing ok or data is not a list")
                    return False
            else:
                self.log_test("Get Cards", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Cards", False, str(e))
            return False

    def test_create_transfer(self):
        """Test create transfer"""
        if not self.customer_token:
            self.log_test("Create Transfer", False, "No customer token available")
            return False
        
        if not self.customer_accounts:
            self.log_test("Create Transfer", False, "No customer accounts available")
            return False
        
        try:
            account_id = self.customer_accounts[0]["id"]
            response = requests.post(
                f"{BASE_URL}/transfers",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                json={
                    "from_account_id": account_id,
                    "beneficiary_name": "Test Recipient",
                    "beneficiary_iban": "DE89370400440532013000",
                    "amount": 1000,
                    "currency": "EUR",
                    "details": "Test transfer from automated testing"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and "data" in data:
                    self.log_test("Create Transfer", True)
                    print(f"   Transfer ID: {data['data'].get('id')}")
                    print(f"   Amount: €{data['data'].get('amount', 0) / 100:.2f}")
                    print(f"   Status: {data['data'].get('status')}")
                    return True
                else:
                    self.log_test("Create Transfer", False, "Missing ok or data in response")
                    return False
            else:
                self.log_test("Create Transfer", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Create Transfer", False, str(e))
            return False

    def test_get_transfers(self):
        """Test get transfers"""
        if not self.customer_token:
            self.log_test("Get Transfers", False, "No customer token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/transfers",
                headers={"Authorization": f"Bearer {self.customer_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and isinstance(data.get("data"), list):
                    self.log_test("Get Transfers", True)
                    print(f"   Found {len(data['data'])} transfer(s)")
                    return True
                else:
                    self.log_test("Get Transfers", False, "Missing ok or data is not a list")
                    return False
            else:
                self.log_test("Get Transfers", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Transfers", False, str(e))
            return False

    def test_admin_get_card_requests(self):
        """Test admin get card requests"""
        if not self.admin_token:
            self.log_test("Admin Get Card Requests", False, "No admin token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/card-requests",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and isinstance(data.get("data"), list):
                    self.log_test("Admin Get Card Requests", True)
                    print(f"   Found {len(data['data'])} pending card request(s)")
                    return True
                else:
                    self.log_test("Admin Get Card Requests", False, "Missing ok or data is not a list")
                    return False
            else:
                self.log_test("Admin Get Card Requests", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Get Card Requests", False, str(e))
            return False

    def test_admin_get_transfers(self):
        """Test admin get transfers"""
        if not self.admin_token:
            self.log_test("Admin Get Transfers", False, "No admin token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/transfers",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and isinstance(data.get("data"), list):
                    self.log_test("Admin Get Transfers", True)
                    print(f"   Found {len(data['data'])} transfer(s)")
                    return True
                else:
                    self.log_test("Admin Get Transfers", False, "Missing ok or data is not a list")
                    return False
            else:
                self.log_test("Admin Get Transfers", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Get Transfers", False, str(e))
            return False

    def test_admin_get_all_tickets(self):
        """Test admin get all tickets"""
        if not self.admin_token:
            self.log_test("Admin Get All Tickets", False, "No admin token available")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/admin/tickets",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Admin Get All Tickets", True)
                    print(f"   Found {len(data)} ticket(s)")
                    return True
                else:
                    self.log_test("Admin Get All Tickets", False, "Response is not a list")
                    return False
            else:
                self.log_test("Admin Get All Tickets", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Get All Tickets", False, str(e))
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("\n" + "="*60)
        print("PROJECT ATLAS - BACKEND API TESTING (ITERATION 12)")
        print("="*60 + "\n")
        
        print("🔍 Testing Backend APIs...\n")
        
        # Health check
        print("--- Health Check ---")
        self.test_health_check()
        print()
        
        # Customer tests
        print("--- Customer Authentication & Data ---")
        if self.test_customer_login():
            self.test_customer_get_me()
            self.test_customer_get_accounts()
            if self.customer_accounts:
                self.test_customer_get_transactions()
        print()
        
        # MFA tests
        print("--- MFA Features ---")
        if self.customer_token:
            self.test_mfa_setup()
        print()
        
        # KYC tests
        print("--- KYC Features ---")
        if self.customer_token:
            self.test_kyc_get_application()
        print()
        
        # Admin tests
        print("--- Admin Authentication & Management ---")
        if self.test_admin_login():
            self.test_admin_get_users()
            if self.admin_users:
                self.test_admin_get_user_details()
                self.test_admin_update_user_status()  # BUG FIX TEST
        print()
        
        # Admin KYC
        print("--- Admin KYC Review ---")
        if self.admin_token:
            self.test_admin_kyc_pending()
        print()
        
        # Admin ledger operations
        print("--- Admin Ledger Operations ---")
        if self.admin_token and self.customer_accounts:
            self.test_admin_top_up()
            self.test_admin_withdraw()
            self.test_admin_charge_fee()
        print()
        
        # Professional Credit/Debit (NEW FEATURE)
        print("--- Professional Admin Credit/Debit (NEW) ---")
        if self.admin_token and self.customer_accounts:
            self.test_admin_professional_credit()
            self.test_admin_professional_debit()
            self.test_customer_view_professional_transactions()
        print()
        
        # Admin audit logs
        print("--- Admin Audit Logs ---")
        if self.admin_token:
            self.test_admin_audit_logs()
        print()
        
        # Statement download
        print("--- Statement Download ---")
        if self.customer_token and self.customer_accounts:
            self.test_statement_download()
        print()
        
        # Support Tickets
        print("--- Support Tickets ---")
        if self.customer_token:
            self.test_create_support_ticket()
            self.test_get_customer_tickets()
        if self.admin_token:
            self.test_admin_get_all_tickets()
        print()
        
        # Notifications
        print("--- Notifications ---")
        if self.customer_token:
            self.test_get_notifications()
        print()
        
        # Card Requests & Transfers (NEW)
        print("--- Card Requests & Transfers ---")
        if self.customer_token and self.customer_accounts:
            self.test_create_card_request()
            self.test_get_card_requests()
            self.test_get_cards()
            self.test_create_transfer()
            self.test_get_transfers()
        print()
        
        # Admin Card Requests & Transfers (NEW)
        print("--- Admin Card Requests & Transfers ---")
        if self.admin_token:
            self.test_admin_get_card_requests()
            self.test_admin_get_transfers()
        print()
        
        # Summary
        print("="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if self.errors:
            print("\n❌ FAILED TESTS:")
            for error in self.errors:
                print(f"  - {error['test']}: {error['error']}")
        
        print("="*60 + "\n")
        
        return self.tests_failed == 0


if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
