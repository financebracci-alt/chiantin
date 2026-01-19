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

# Constants
APP_NAME = "ecommbx"
FRONTEND_URL = "https://translatlas.preview.emergentagent.com"

# Hardcode the API key since environment loading is problematic
# This should be moved to proper env vars in production
_RESEND_API_KEY = "re_XAVmgwpr_73e1PpPi56DCGP5msWPupaLZ"
_SENDER_EMAIL = "noreply@ecommbx.io"


class EmailService:
    """Email service using Resend for real email delivery."""
    
    def __init__(self):
        self.sent_emails = []  # Store for testing/debugging
        # Set API key on initialization
        resend.api_key = _RESEND_API_KEY
    
    def send_password_reset(self, to_email: str, reset_token: str, temp_password: Optional[str] = None):
        """Send password reset email via Resend."""
        # Ensure API key is set
        resend.api_key = _RESEND_API_KEY
        
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
            </head>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0;">🔐 {APP_NAME}</h1>
                    <p style="margin: 10px 0 0 0;">Password Reset Request</p>
                </div>
                <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" style="display: inline-block; background: #dc3545; color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0;">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0; word-break: break-all; font-family: monospace; font-size: 12px;">
                        <a href="{reset_link}" style="color: #333;">{reset_link}</a>
                    </div>
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">⏰ This link expires in 1 hour.</p>
                    <p style="color: #666; font-size: 14px;">If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                </div>
                <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
                    <p>© 2024 {APP_NAME}. All rights reserved.</p>
                </div>
            </body>
            </html>
            """
        
        try:
            params = {
                "from": f"{APP_NAME} <{_SENDER_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Password reset email sent to {to_email}, Resend ID: {response.get('id', 'unknown')}")
            
            self.sent_emails.append({
                'to': to_email,
                'subject': subject,
                'sent_at': datetime.utcnow(),
                'resend_id': response.get('id')
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            print(f"[EMAIL ERROR] Failed to send to {to_email}: {str(e)}")
            return False
    
    def send_otp(self, to_email: str, otp_code: str):
        """Send OTP code via email using Resend."""
        # Ensure API key is set
        resend.api_key = _RESEND_API_KEY
        
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
            params = {
                "from": f"{APP_NAME} <{_SENDER_EMAIL}>",
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
