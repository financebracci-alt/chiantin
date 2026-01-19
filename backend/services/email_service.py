"""Email service for notifications and OTP using Resend."""

import os
import secrets
import string
import resend
from datetime import datetime, timedelta
from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Load from .env file - use absolute path
def get_env_value(key, default=''):
    # First try environment
    value = os.environ.get(key, '')
    if value:
        return value
    # Then try loading .env manually from multiple possible locations
    possible_paths = [
        Path(__file__).parent.parent / '.env',
        Path('/app/backend/.env'),
        Path('.env'),
    ]
    for env_path in possible_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f'{key}='):
                        return line.split('=', 1)[1]
    return default

# Initialize
RESEND_API_KEY = get_env_value('RESEND_API_KEY')
SENDER_EMAIL = get_env_value('SENDER_EMAIL', 'noreply@ecommbx.io')
resend.api_key = RESEND_API_KEY
APP_NAME = "Project Atlas"
FRONTEND_URL = get_env_value('FRONTEND_URL', 'https://translatlas.preview.emergentagent.com')

# Log initialization status
if RESEND_API_KEY:
    logger.info(f"Email service initialized with Resend API key: {RESEND_API_KEY[:10]}...")
    logger.info(f"Sender email: {SENDER_EMAIL}")
else:
    logger.warning("Email service: No Resend API key found!")


class EmailService:
    """Email service using Resend for real email delivery."""
    
    def __init__(self):
        self.sent_emails = []  # Store for testing/debugging
    
    def send_password_reset(self, to_email: str, reset_token: str, temp_password: Optional[str] = None):
        """Send password reset email via Resend."""
        subject = f"Password Reset - {APP_NAME}"
        reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
        
        if temp_password:
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .password-box {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; }}
                    .password {{ font-family: monospace; font-size: 24px; color: #856404; font-weight: bold; }}
                    .warning {{ color: #dc3545; font-size: 14px; margin-top: 20px; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔐 {APP_NAME}</h1>
                    <p>Password Reset</p>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>Your password has been reset by an administrator.</p>
                    <div class="password-box">
                        <p>Your temporary password:</p>
                        <p class="password">{temp_password}</p>
                    </div>
                    <p class="warning">⚠️ Please login and change your password immediately for security.</p>
                </div>
                <div class="footer">
                    <p>© 2024 {APP_NAME}. All rights reserved.</p>
                </div>
            </body>
            </html>
            """
        else:
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .btn {{ display: inline-block; background: #dc3545; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
                    .btn:hover {{ background: #c82333; }}
                    .token-box {{ background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0; word-break: break-all; font-family: monospace; font-size: 12px; }}
                    .warning {{ color: #666; font-size: 14px; margin-top: 20px; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔐 {APP_NAME}</h1>
                    <p>Password Reset Request</p>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="btn">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <div class="token-box">{reset_link}</div>
                    <p class="warning">⏰ This link expires in 1 hour.</p>
                    <p class="warning">If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                </div>
                <div class="footer">
                    <p>© 2024 {APP_NAME}. All rights reserved.</p>
                </div>
            </body>
            </html>
            """
        
        try:
            # Ensure API key is set before sending
            if not resend.api_key:
                resend.api_key = RESEND_API_KEY
            
            # Send via Resend
            params = {
                "from": f"{APP_NAME} <{SENDER_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Password reset email sent to {to_email}, Resend ID: {response.get('id', 'unknown')}")
            
            # Store for debugging
            self.sent_emails.append({
                'to': to_email,
                'subject': subject,
                'sent_at': datetime.utcnow(),
                'resend_id': response.get('id')
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            # Fallback to mock for development
            print(f"[EMAIL ERROR] Failed to send to {to_email}: {str(e)}")
            return False
    
    def send_otp(self, to_email: str, otp_code: str):
        """Send OTP code via email using Resend."""
        subject = f"Your Login Code - {APP_NAME}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-box {{ background: #fff; border: 2px solid #dc3545; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }}
                .otp {{ font-family: monospace; font-size: 36px; color: #dc3545; font-weight: bold; letter-spacing: 8px; }}
                .warning {{ color: #666; font-size: 14px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔒 {APP_NAME}</h1>
                <p>Verification Code</p>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>Your verification code is:</p>
                <div class="otp-box">
                    <p class="otp">{otp_code}</p>
                </div>
                <p class="warning">⏰ This code expires in 10 minutes.</p>
                <p class="warning">If you didn't request this code, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>© 2024 {APP_NAME}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        try:
            # Ensure API key is set before sending
            if not resend.api_key:
                resend.api_key = RESEND_API_KEY
                
            params = {
                "from": f"{APP_NAME} <{SENDER_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"OTP email sent to {to_email}, Resend ID: {response.get('id', 'unknown')}")
            
            self.sent_emails.append({
                'to': to_email,
                'subject': subject,
                'sent_at': datetime.utcnow(),
                'resend_id': response.get('id')
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to send OTP email to {to_email}: {str(e)}")
            print(f"[EMAIL ERROR] Failed to send OTP to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def generate_temp_password(length: int = 12) -> str:
        """Generate a secure temporary password."""
        characters = string.ascii_letters + string.digits + "!@#$%"
        password = ''.join(secrets.choice(characters) for _ in range(length))
        # Ensure at least one of each type
        if not any(c.isupper() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_uppercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + secrets.choice(string.digits)
        return password
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP."""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @staticmethod
    def generate_reset_token() -> str:
        """Generate a secure reset token."""
        return secrets.token_urlsafe(32)
