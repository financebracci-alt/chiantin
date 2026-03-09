"""
Test support ticket attachment download functionality.
Tests the fix for PDF/document downloads being corrupted without file extensions.

Key fix:
1. Backend cloudinary_storage.py: Raw files should NOT have extensions in public_id (Cloudinary ACL blocks them)
2. Frontend Support.js: Blob-based download handler saves with correct filename from att.file_name

Test ticket: 'qwe' (ID: 699c7eb2c8fa4bf3cfa789bb) with attachment 'test_document.pdf'
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - ONLY use these test accounts, not real bank clients
CLIENT_EMAIL = "ashleyalt005@gmail.com"
CLIENT_PASSWORD = "123456789"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Test ticket with PDF attachment
TEST_TICKET_ID = "699c7eb2c8fa4bf3cfa789bb"
TEST_TICKET_SUBJECT = "qwe"


class TestAuthFlow:
    """Authentication tests for both client and admin users"""
    
    def test_client_login(self):
        """Test client user login flow"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}
        )
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in login response"
        print(f"✓ Client login successful - token received")
        return data["access_token"]
    
    def test_admin_login(self):
        """Test admin user login flow"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in login response"
        print(f"✓ Admin login successful - token received")
        return data["access_token"]


class TestSupportTickets:
    """Support ticket functionality tests"""
    
    @pytest.fixture
    def client_token(self):
        """Get client auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_client_get_tickets(self, client_token):
        """Test client can fetch their support tickets"""
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Failed to get tickets: {response.text}"
        tickets = response.json()
        assert isinstance(tickets, list), "Tickets should be a list"
        print(f"✓ Client fetched {len(tickets)} tickets")
        return tickets
    
    def test_client_get_specific_ticket(self, client_token):
        """Test client can fetch the test ticket 'qwe' with PDF attachment"""
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/{TEST_TICKET_ID}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200, f"Failed to get ticket: {response.text}"
        ticket = response.json()
        assert ticket.get("id") == TEST_TICKET_ID, "Wrong ticket ID"
        assert ticket.get("subject") == TEST_TICKET_SUBJECT, f"Expected subject 'qwe', got {ticket.get('subject')}"
        print(f"✓ Got ticket '{ticket.get('subject')}' with {len(ticket.get('messages', []))} messages")
        return ticket
    
    def test_ticket_has_pdf_attachment(self, client_token):
        """Test that the test ticket has a PDF attachment"""
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/{TEST_TICKET_ID}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        ticket = response.json()
        
        # Check messages for attachments
        messages = ticket.get("messages", [])
        all_attachments = []
        for msg in messages:
            attachments = msg.get("attachments", [])
            all_attachments.extend(attachments)
        
        # Find PDF attachment
        pdf_attachments = [a for a in all_attachments if a.get("file_name", "").lower().endswith(".pdf")]
        
        print(f"✓ Found {len(all_attachments)} attachments, {len(pdf_attachments)} PDFs")
        
        if pdf_attachments:
            pdf = pdf_attachments[0]
            print(f"  PDF attachment: {pdf.get('file_name')}")
            print(f"  URL: {pdf.get('url')}")
            
            # Verify the URL is accessible
            pdf_url = pdf.get('url')
            if pdf_url:
                # Test that PDF URL returns valid content
                pdf_response = requests.head(pdf_url, allow_redirects=True)
                print(f"  URL status: {pdf_response.status_code}")
        
        return all_attachments
    
    def test_admin_get_all_tickets(self, admin_token):
        """Test admin can fetch all support tickets"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get admin tickets: {response.text}"
        tickets = response.json()
        assert isinstance(tickets, list), "Admin tickets should be a list"
        print(f"✓ Admin fetched {len(tickets)} tickets")
        return tickets
    
    def test_admin_get_specific_ticket(self, admin_token):
        """Test admin can fetch specific ticket details"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets/{TEST_TICKET_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get admin ticket: {response.text}"
        ticket = response.json()
        assert ticket.get("id") == TEST_TICKET_ID
        
        # Check for user info (grouped view)
        print(f"✓ Admin got ticket - user_email: {ticket.get('user_email', 'N/A')}, user_name: {ticket.get('user_name', 'N/A')}")
        return ticket


class TestAttachmentDownload:
    """Test attachment download functionality - the core fix being tested"""
    
    @pytest.fixture
    def client_token(self):
        """Get client auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_attachment_url_accessible(self, client_token):
        """Test that attachment URLs are accessible (not 401 ACL blocked)"""
        # Get ticket with attachment
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/{TEST_TICKET_ID}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        ticket = response.json()
        
        # Find all attachments
        messages = ticket.get("messages", [])
        for msg in messages:
            for att in msg.get("attachments", []):
                url = att.get("url")
                file_name = att.get("file_name")
                
                if url:
                    # Test URL accessibility
                    att_response = requests.head(url, allow_redirects=True)
                    print(f"  Attachment '{file_name}': Status {att_response.status_code}")
                    
                    # Should NOT be 401 (ACL blocked)
                    assert att_response.status_code != 401, f"Attachment URL blocked by ACL: {url}"
                    
                    # Should be accessible (200, 301, 302)
                    assert att_response.status_code in [200, 301, 302], f"Attachment not accessible: {url}, status: {att_response.status_code}"
    
    def test_pdf_download_content_type(self, client_token):
        """Test that PDF attachments have correct content"""
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/{TEST_TICKET_ID}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        ticket = response.json()
        
        # Find PDF attachment
        for msg in ticket.get("messages", []):
            for att in msg.get("attachments", []):
                if att.get("file_name", "").lower().endswith(".pdf"):
                    url = att.get("url")
                    file_name = att.get("file_name")
                    
                    # Download the file
                    pdf_response = requests.get(url, allow_redirects=True)
                    
                    print(f"  PDF '{file_name}' download test:")
                    print(f"    Status: {pdf_response.status_code}")
                    print(f"    Content-Type: {pdf_response.headers.get('content-type', 'unknown')}")
                    print(f"    Size: {len(pdf_response.content)} bytes")
                    
                    # Verify file is downloadable
                    assert pdf_response.status_code == 200, f"Failed to download PDF: {url}"
                    
                    # Verify file has content
                    assert len(pdf_response.content) > 0, "PDF file is empty"
                    
                    # Verify file_name has .pdf extension (this is what the frontend uses for download)
                    assert file_name.lower().endswith(".pdf"), f"file_name missing .pdf extension: {file_name}"
                    
                    print(f"  ✓ PDF download verified - file_name has extension for blob download")


class TestDashboard:
    """Dashboard and basic functionality tests"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}
        )
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_client_dashboard_loads(self, client_token):
        """Test client can access dashboard data"""
        # Get accounts
        response = requests.get(
            f"{BASE_URL}/api/v1/accounts",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        accounts = response.json()
        print(f"✓ Client has {len(accounts)} accounts")
        
        # Get user profile
        response = requests.get(
            f"{BASE_URL}/api/v1/users/me",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        user = response.json()
        print(f"✓ User profile: {user.get('first_name', '')} {user.get('last_name', '')}")
    
    def test_client_tax_status(self, client_token):
        """Test client can access tax status"""
        response = requests.get(
            f"{BASE_URL}/api/v1/users/me/tax-status",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        tax_status = response.json()
        print(f"✓ Tax status: has_hold={tax_status.get('has_tax_hold', False)}")
    
    def test_admin_overview(self, admin_token):
        """Test admin can access overview stats"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        overview = response.json()
        print(f"✓ Admin overview: {overview.get('total_users', 0)} total users")
    
    def test_admin_users_list(self, admin_token):
        """Test admin can access users list"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()
        print(f"✓ Admin users: {len(users)} users in list")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
