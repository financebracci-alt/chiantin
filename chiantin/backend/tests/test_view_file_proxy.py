"""
Test View File Proxy Endpoint - Iteration 159

Tests for the new GET /api/v1/tickets/view-file endpoint that proxies Cloudinary files
with Content-Disposition: inline to enable inline viewing of PDFs/documents in new tabs.

Key changes from iteration 158:
- New proxy endpoint added at /api/v1/tickets/view-file
- Frontend changed from <a href> to <button> with handleViewFile handler
- File name click now views inline, download button triggers download
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials (from problem statement)
CLIENT_EMAIL = "ashleyalt005@gmail.com"
CLIENT_PASSWORD = "123456789"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Test ticket with attachments
TEST_TICKET_ID = "699c7eb2c8fa4bf3cfa789bb"
TEST_TICKET_SUBJECT = "qwe"

# Cloudinary URLs from the ticket
CLOUDINARY_PDF_URL_1 = "https://res.cloudinary.com/ditryuycq/raw/upload/v1773059691/tickets/699c7eb2c8fa4bf3cfa789bb/18fa9219-81ab-4366-b248-ccb100d80029_Dichiarazione_Florian_Simoni"
CLOUDINARY_PDF_URL_2 = "https://res.cloudinary.com/ditryuycq/raw/upload/v1773060176/tickets/699c7eb2c8fa4bf3cfa789bb/0d5f9d6d-927c-458c-a37b-9e853a11bb38_test_document"


class TestViewFileProxyEndpoint:
    """Tests for GET /api/v1/tickets/view-file proxy endpoint"""
    
    @pytest.fixture(scope="class")
    def client_token(self):
        """Get auth token for test client user"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Client login failed: {response.status_code}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get auth token for admin user"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("access_token")
    
    def test_view_file_requires_auth(self):
        """Endpoint should require authentication - returns 401 or 403 without token"""
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/view-file",
            params={"url": CLOUDINARY_PDF_URL_2, "filename": "test_document.pdf"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: view-file endpoint requires authentication ({response.status_code} without token)")
    
    def test_view_file_returns_pdf_content(self, client_token):
        """View-file should return PDF with correct content type"""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/view-file",
            params={"url": CLOUDINARY_PDF_URL_2, "filename": "test_document.pdf"},
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF content type, got: {content_type}"
        
        # Check Content-Disposition: inline
        content_disposition = response.headers.get("content-disposition", "")
        assert "inline" in content_disposition.lower(), f"Expected inline disposition, got: {content_disposition}"
        assert "test_document.pdf" in content_disposition, f"Filename not in disposition: {content_disposition}"
        
        # Check we got actual content
        assert len(response.content) > 100, f"Response too small: {len(response.content)} bytes"
        print(f"PASS: view-file returns PDF with inline disposition ({len(response.content)} bytes)")
    
    def test_view_file_rejects_non_cloudinary_url(self, client_token):
        """Security: should reject non-Cloudinary URLs"""
        headers = {"Authorization": f"Bearer {client_token}"}
        
        # Try malicious URL
        malicious_urls = [
            "https://evil.com/malware.pdf",
            "https://res.cloudinary.com/other-account/raw/upload/file.pdf",
            "http://localhost:8001/internal",
            "file:///etc/passwd",
        ]
        
        for malicious_url in malicious_urls:
            response = requests.get(
                f"{BASE_URL}/api/v1/tickets/view-file",
                params={"url": malicious_url, "filename": "test.pdf"},
                headers=headers
            )
            assert response.status_code == 400, f"Should reject {malicious_url}, got {response.status_code}"
        
        print("PASS: view-file correctly rejects non-Cloudinary URLs (security check)")
    
    def test_view_file_with_admin_token(self, admin_token):
        """Admin should also be able to use view-file endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/view-file",
            params={"url": CLOUDINARY_PDF_URL_2, "filename": "test_document.pdf"},
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Admin can use view-file endpoint")


class TestClientLoginAndTickets:
    """Tests for client login and support ticket access"""
    
    def test_client_login(self):
        """Client ashleyalt005@gmail.com should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}
        )
        assert response.status_code == 200, f"Client login failed: {response.status_code}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"PASS: Client login successful for {CLIENT_EMAIL}")
        return data["access_token"]
    
    def test_client_can_fetch_tickets(self):
        """Client should be able to fetch their tickets"""
        # Login first
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}
        )
        token = login_resp.json().get("access_token")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v1/tickets", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        tickets = response.json()
        assert isinstance(tickets, list), "Expected list of tickets"
        print(f"PASS: Client fetched {len(tickets)} tickets")
        
        # Check test ticket 'qwe' exists
        qwe_ticket = next((t for t in tickets if t.get("subject") == TEST_TICKET_SUBJECT), None)
        assert qwe_ticket is not None, f"Test ticket '{TEST_TICKET_SUBJECT}' not found"
        print(f"PASS: Found test ticket '{TEST_TICKET_SUBJECT}' (ID: {qwe_ticket.get('id')})")
    
    def test_client_can_fetch_ticket_details(self):
        """Client should be able to fetch ticket details with attachments"""
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}
        )
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/tickets/{TEST_TICKET_ID}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        ticket = response.json()
        
        # Verify ticket details
        assert ticket.get("subject") == TEST_TICKET_SUBJECT, f"Wrong subject: {ticket.get('subject')}"
        assert "messages" in ticket, "No messages in ticket"
        
        # Check for attachments
        has_attachments = False
        for msg in ticket.get("messages", []):
            if msg.get("attachments"):
                has_attachments = True
                for att in msg["attachments"]:
                    assert "file_name" in att, "Attachment missing file_name"
                    assert "url" in att, "Attachment missing url"
                    print(f"  - Found attachment: {att['file_name']}")
        
        assert has_attachments, "Expected ticket to have attachments"
        print(f"PASS: Ticket {TEST_TICKET_ID} has messages with attachments")


class TestAdminLoginAndTickets:
    """Tests for admin login and ticket management"""
    
    def test_admin_login(self):
        """Admin should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.status_code}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"PASS: Admin login successful for {ADMIN_EMAIL}")
        return data["access_token"]
    
    def test_admin_can_fetch_all_tickets(self):
        """Admin should be able to fetch all tickets (grouped view data)"""
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/admin/tickets", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        tickets = response.json()
        assert isinstance(tickets, list), "Expected list of tickets"
        print(f"PASS: Admin fetched {len(tickets)} tickets")
    
    def test_admin_can_fetch_ticket_details(self):
        """Admin should be able to fetch ticket details"""
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/tickets/{TEST_TICKET_ID}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        ticket = response.json()
        
        # Admin view should include user info
        assert ticket.get("subject") == TEST_TICKET_SUBJECT, f"Wrong subject"
        print(f"PASS: Admin fetched ticket details for {TEST_TICKET_ID}")
        if "user_email" in ticket:
            print(f"  - User email: {ticket.get('user_email')}")


class TestAttachmentURLs:
    """Tests for Cloudinary attachment URLs accessibility"""
    
    def test_cloudinary_url_accessible(self):
        """Cloudinary URL should be accessible (no 401 ACL block)"""
        response = requests.head(CLOUDINARY_PDF_URL_2)
        assert response.status_code in [200, 301, 302], f"Cloudinary URL not accessible: {response.status_code}"
        print(f"PASS: Cloudinary URL accessible ({response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
