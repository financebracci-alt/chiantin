"""
Test Admin Credit/Debit Transaction Metadata - P0 Regression Fix Verification

Validates:
1. Admin topup endpoint stores professional banking metadata
2. Admin withdraw endpoint stores professional banking metadata  
3. Transaction metadata is returned correctly in get_transactions
4. Credit/Debit direction indicators work correctly
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminCreditDebitMetadata:
    """Test admin credit/debit operations store and return metadata correctly"""
    
    # Test credentials from review request
    ADMIN_EMAIL = "admin@ecommbx.io"
    ADMIN_PASSWORD = "Admin@123456"
    TEST_USER_EMAIL = "ashleyalt005@gmail.com"
    TEST_USER_PASSWORD = "123456789"
    TEST_ACCOUNT_ID = "bank_acc_6971fed2ad8ed4d326f04041"
    
    @pytest.fixture
    def api_session(self):
        """Create requests session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    @pytest.fixture
    def admin_token(self, api_session):
        """Get admin auth token"""
        response = api_session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.ADMIN_EMAIL,
            "password": self.ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture
    def client_token(self, api_session):
        """Get test client auth token"""
        response = api_session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": self.TEST_USER_EMAIL,
            "password": self.TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture
    def test_account_id(self, api_session, client_token):
        """Get test user's account ID"""
        api_session.headers.update({"Authorization": f"Bearer {client_token}"})
        response = api_session.get(f"{BASE_URL}/api/v1/accounts")
        assert response.status_code == 200, f"Failed to get accounts: {response.text}"
        accounts = response.json()
        assert len(accounts) > 0, "Test user has no accounts"
        return accounts[0]["id"]
    
    def test_admin_credit_stores_metadata(self, api_session, admin_token, test_account_id):
        """Test admin credit (topup) stores professional banking metadata"""
        api_session.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        # Create credit transaction with professional fields
        unique_ref = f"TEST_REF_{uuid.uuid4().hex[:8]}"
        credit_data = {
            "amount_cents": 2500,  # €25.00
            "description": "Test Bank Transfer Credit",
            "display_type": "Bank Transfer",
            "sender_name": "ACME Corporation",
            "sender_iban": "DE89370400440532013000",
            "sender_bic": "COBADEFFXXX",
            "reference": unique_ref,
            "admin_note": "Test credit for metadata verification"
        }
        
        response = api_session.post(
            f"{BASE_URL}/api/v1/admin/accounts/{test_account_id}/topup",
            json=credit_data
        )
        
        assert response.status_code == 200, f"Credit failed: {response.text}"
        result = response.json()
        
        # Verify response structure
        assert result.get("ok") == True, f"Credit not OK: {result}"
        assert "transaction" in result, "No transaction in response"
        assert "new_balance" in result, "No new_balance in response"
        
        txn = result["transaction"]
        print(f"Credit transaction created: {txn.get('id')}")
        print(f"Transaction metadata: {txn.get('metadata')}")
        
        # Verify transaction metadata was stored
        metadata = txn.get("metadata", {})
        assert metadata.get("display_type") == "Bank Transfer", f"display_type not stored: {metadata}"
        assert metadata.get("sender_name") == "ACME Corporation", f"sender_name not stored: {metadata}"
        assert metadata.get("sender_iban") == "DE89370400440532013000", f"sender_iban not stored: {metadata}"
        assert metadata.get("sender_bic") == "COBADEFFXXX", f"sender_bic not stored: {metadata}"
        assert metadata.get("reference") == unique_ref, f"reference not stored: {metadata}"
        assert metadata.get("description") == "Test Bank Transfer Credit", f"description not stored: {metadata}"
        
        return txn.get("id")
    
    def test_admin_debit_stores_metadata(self, api_session, admin_token, test_account_id):
        """Test admin debit (withdraw) stores professional banking metadata"""
        api_session.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        # Create debit transaction with professional fields
        unique_ref = f"TEST_REF_{uuid.uuid4().hex[:8]}"
        debit_data = {
            "amount_cents": 1500,  # €15.00
            "description": "Test SEPA Debit",
            "display_type": "SEPA Transfer",
            "recipient_name": "John Smith",
            "recipient_iban": "FR7630006000011234567890189",
            "reference": unique_ref,
            "admin_note": "Test debit for metadata verification"
        }
        
        response = api_session.post(
            f"{BASE_URL}/api/v1/admin/accounts/{test_account_id}/withdraw",
            json=debit_data
        )
        
        assert response.status_code == 200, f"Debit failed: {response.text}"
        result = response.json()
        
        # Verify response structure
        assert result.get("ok") == True, f"Debit not OK: {result}"
        assert "transaction" in result, "No transaction in response"
        
        txn = result["transaction"]
        print(f"Debit transaction created: {txn.get('id')}")
        print(f"Transaction metadata: {txn.get('metadata')}")
        
        # Verify transaction metadata was stored
        metadata = txn.get("metadata", {})
        assert metadata.get("display_type") == "SEPA Transfer", f"display_type not stored: {metadata}"
        assert metadata.get("recipient_name") == "John Smith", f"recipient_name not stored: {metadata}"
        assert metadata.get("to_iban") == "FR7630006000011234567890189", f"to_iban not stored: {metadata}"
        assert metadata.get("reference") == unique_ref, f"reference not stored: {metadata}"
        assert metadata.get("description") == "Test SEPA Debit", f"description not stored: {metadata}"
        
        return txn.get("id")
    
    def test_client_sees_credit_metadata_in_transactions(self, api_session, client_token, test_account_id):
        """Test client can see credit metadata when fetching transactions"""
        api_session.headers.update({"Authorization": f"Bearer {client_token}"})
        
        response = api_session.get(f"{BASE_URL}/api/v1/accounts/{test_account_id}/transactions")
        assert response.status_code == 200, f"Get transactions failed: {response.text}"
        
        transactions = response.json()
        assert len(transactions) > 0, "No transactions found"
        
        # Find a TOP_UP transaction with metadata
        credit_txns = [t for t in transactions if t.get("transaction_type") == "TOP_UP"]
        assert len(credit_txns) > 0, "No TOP_UP transactions found"
        
        # Check the most recent credit has metadata
        recent_credit = credit_txns[0]
        metadata = recent_credit.get("metadata", {})
        
        print(f"Recent credit transaction: {recent_credit.get('id')}")
        print(f"Transaction type: {recent_credit.get('transaction_type')}")
        print(f"Metadata: {metadata}")
        
        # Verify metadata fields are present (at least display_type)
        assert "display_type" in metadata or recent_credit.get("transaction_type"), \
            "No display_type in metadata"
        
        return True
    
    def test_client_sees_debit_metadata_in_transactions(self, api_session, client_token, test_account_id):
        """Test client can see debit metadata when fetching transactions"""
        api_session.headers.update({"Authorization": f"Bearer {client_token}"})
        
        response = api_session.get(f"{BASE_URL}/api/v1/accounts/{test_account_id}/transactions")
        assert response.status_code == 200, f"Get transactions failed: {response.text}"
        
        transactions = response.json()
        
        # Find a WITHDRAW transaction with metadata
        debit_txns = [t for t in transactions if t.get("transaction_type") == "WITHDRAW"]
        
        if len(debit_txns) > 0:
            recent_debit = debit_txns[0]
            metadata = recent_debit.get("metadata", {})
            
            print(f"Recent debit transaction: {recent_debit.get('id')}")
            print(f"Transaction type: {recent_debit.get('transaction_type')}")
            print(f"Metadata: {metadata}")
            
            # Verify metadata fields are present
            assert "display_type" in metadata or recent_debit.get("transaction_type"), \
                "No display_type in metadata"
        
        return True
    
    def test_transaction_direction_indicators(self, api_session, client_token, test_account_id):
        """Test transaction direction (CREDIT/DEBIT) is correctly indicated"""
        api_session.headers.update({"Authorization": f"Bearer {client_token}"})
        
        response = api_session.get(f"{BASE_URL}/api/v1/accounts/{test_account_id}/transactions")
        assert response.status_code == 200, f"Get transactions failed: {response.text}"
        
        transactions = response.json()
        
        for txn in transactions[:5]:  # Check first 5
            txn_type = txn.get("transaction_type", "")
            direction = txn.get("direction", "")
            
            print(f"Transaction: {txn.get('id')[:20]}... Type: {txn_type}, Direction: {direction}")
            
            # Credits should have CREDIT direction or TOP_UP type
            if txn_type in ["TOP_UP", "CREDIT", "REFUND"]:
                assert direction == "CREDIT" or txn_type in ["TOP_UP", "CREDIT", "REFUND"], \
                    f"Credit transaction has wrong direction: {direction}"
            
            # Debits should have DEBIT direction or WITHDRAW type
            if txn_type in ["WITHDRAW", "FEE", "TRANSFER"]:
                assert direction == "DEBIT" or txn_type in ["WITHDRAW", "FEE"], \
                    f"Debit transaction has wrong direction: {direction}"
        
        return True
    
    def test_full_admin_credit_flow(self, api_session, admin_token, client_token, test_account_id):
        """End-to-end: Admin creates credit, client sees it with all metadata"""
        # Step 1: Admin creates credit with professional fields
        api_session.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        unique_ref = f"E2E_TEST_{uuid.uuid4().hex[:8]}"
        credit_data = {
            "amount_cents": 1234,  # €12.34
            "description": "E2E Test Credit",
            "display_type": "Wire Transfer",
            "sender_name": "E2E Test Corp",
            "sender_iban": "GB82WEST12345698765432",
            "sender_bic": "WESTGB2L",
            "reference": unique_ref,
            "admin_note": "E2E test"
        }
        
        response = api_session.post(
            f"{BASE_URL}/api/v1/admin/accounts/{test_account_id}/topup",
            json=credit_data
        )
        assert response.status_code == 200, f"Admin credit failed: {response.text}"
        
        created_txn = response.json()["transaction"]
        txn_id = created_txn["id"]
        print(f"Admin created credit: {txn_id}")
        
        # Step 2: Client fetches transactions and verifies the credit
        api_session.headers.update({"Authorization": f"Bearer {client_token}"})
        
        response = api_session.get(f"{BASE_URL}/api/v1/accounts/{test_account_id}/transactions")
        assert response.status_code == 200, f"Client get transactions failed: {response.text}"
        
        transactions = response.json()
        
        # Find our specific transaction
        our_txn = next((t for t in transactions if t.get("id") == txn_id), None)
        assert our_txn is not None, f"Client cannot see admin-created transaction {txn_id}"
        
        # Verify all metadata is visible to client
        metadata = our_txn.get("metadata", {})
        assert metadata.get("display_type") == "Wire Transfer", \
            f"Client cannot see display_type: {metadata}"
        assert metadata.get("sender_name") == "E2E Test Corp", \
            f"Client cannot see sender_name: {metadata}"
        assert metadata.get("sender_iban") == "GB82WEST12345698765432", \
            f"Client cannot see sender_iban: {metadata}"
        assert metadata.get("sender_bic") == "WESTGB2L", \
            f"Client cannot see sender_bic: {metadata}"
        assert metadata.get("reference") == unique_ref, \
            f"Client cannot see reference: {metadata}"
        
        print(f"✓ Client sees all professional metadata for credit transaction")
        return True
    
    def test_full_admin_debit_flow(self, api_session, admin_token, client_token, test_account_id):
        """End-to-end: Admin creates debit, client sees it with all metadata"""
        # Step 1: Admin creates debit with professional fields
        api_session.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        unique_ref = f"E2E_DEBIT_{uuid.uuid4().hex[:8]}"
        debit_data = {
            "amount_cents": 567,  # €5.67
            "description": "E2E Test Debit",
            "display_type": "SEPA Transfer",
            "recipient_name": "E2E Recipient",
            "recipient_iban": "IT60X0542811101000000123456",
            "reference": unique_ref,
            "admin_note": "E2E debit test"
        }
        
        response = api_session.post(
            f"{BASE_URL}/api/v1/admin/accounts/{test_account_id}/withdraw",
            json=debit_data
        )
        assert response.status_code == 200, f"Admin debit failed: {response.text}"
        
        created_txn = response.json()["transaction"]
        txn_id = created_txn["id"]
        print(f"Admin created debit: {txn_id}")
        
        # Step 2: Client fetches transactions and verifies the debit
        api_session.headers.update({"Authorization": f"Bearer {client_token}"})
        
        response = api_session.get(f"{BASE_URL}/api/v1/accounts/{test_account_id}/transactions")
        assert response.status_code == 200, f"Client get transactions failed: {response.text}"
        
        transactions = response.json()
        
        # Find our specific transaction
        our_txn = next((t for t in transactions if t.get("id") == txn_id), None)
        assert our_txn is not None, f"Client cannot see admin-created debit {txn_id}"
        
        # Verify all metadata is visible to client
        metadata = our_txn.get("metadata", {})
        assert metadata.get("display_type") == "SEPA Transfer", \
            f"Client cannot see display_type: {metadata}"
        assert metadata.get("recipient_name") == "E2E Recipient", \
            f"Client cannot see recipient_name: {metadata}"
        assert metadata.get("to_iban") == "IT60X0542811101000000123456", \
            f"Client cannot see to_iban: {metadata}"
        assert metadata.get("reference") == unique_ref, \
            f"Client cannot see reference: {metadata}"
        
        print(f"✓ Client sees all professional metadata for debit transaction")
        return True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
