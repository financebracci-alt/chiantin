"""Email service for notifications and OTP using Resend."""

import os
import secrets
import string
import resend
from datetime import datetime, timedelta
from typing import Optional
import logging
from pathlib import Path

# Import settings from config
from config import settings

logger = logging.getLogger(__name__)

# Constants - use settings from config.py (which reads from environment)
APP_NAME = settings.APP_NAME

# Get configuration from environment via settings
def get_frontend_url():
    """Get frontend URL from settings."""
    return settings.FRONTEND_URL

def get_resend_api_key():
    """Get Resend API key from settings."""
    return settings.RESEND_API_KEY

def get_sender_email():
    """Get sender email from settings."""
    return settings.SENDER_EMAIL

# Email translations for i18n support
EMAIL_TRANSLATIONS = {
    'en': {
        # Password Reset Email
        'password_reset_subject': f'Password Reset - {APP_NAME}',
        'password_reset_title': 'Password Reset Request',
        'password_reset_greeting': 'Hello,',
        'password_reset_body': 'We received a request to reset your password. Click the button below to create a new password:',
        'password_reset_button': 'Reset Password',
        'password_reset_link_instruction': 'Or copy and paste this link into your browser:',
        'password_reset_expiry': '⏰ This link expires in 1 hour.',
        'password_reset_ignore': "If you didn't request this password reset, please ignore this email. Your password will remain unchanged.",
        'password_reset_footer': f'© 2024 {APP_NAME}. All rights reserved.',
        
        # Admin Password Reset
        'admin_reset_title': 'Password Reset',
        'admin_reset_body': 'Your password has been reset by an administrator.',
        'temp_password_label': 'Your temporary password:',
        'admin_reset_warning': '⚠️ Please login and change your password immediately for security.',
        
        # OTP Email
        'otp_subject': f'Your Login Code - {APP_NAME}',
        'otp_title': 'Verification Code',
        'otp_greeting': 'Hello,',
        'otp_body': 'Your verification code is:',
        'otp_expiry': '⏰ This code expires in 10 minutes.',
        'otp_ignore': "If you didn't request this code, please ignore this email.",
        
        # Email Verification
        'email_verify_subject': f'Verify Your Email - {APP_NAME}',
        'email_verify_title': 'Welcome to ecommbx',
        'email_verify_greeting': 'Hello',
        'email_verify_body': 'Thank you for registering with ecommbx. To complete your registration and access your account, please verify your email address by clicking the button below:',
        'email_verify_button': 'Verify Email Address',
        'email_verify_link_instruction': 'Or copy and paste this link into your browser:',
        'email_verify_expiry': '⏰ This verification link expires in 24 hours.',
        'email_verify_ignore': "If you didn't create an account with us, please ignore this email.",
        'email_verify_security_note': '🔒 For your security, you must verify your email before accessing your account.',
        
        # Transfer Confirmation Email
        'transfer_subject': 'We received your transfer request – Ref',
        'transfer_title': 'Transfer Submitted',
        'transfer_greeting': 'Dear',
        'transfer_body': 'Your transfer request has been submitted and is being processed.',
        'transfer_summary': 'Transfer Summary',
        'transfer_amount': 'Amount',
        'transfer_recipient': 'Recipient',
        'transfer_recipient_iban': 'Recipient IBAN',
        'transfer_from_account': 'From Account',
        'transfer_date': 'Date & Time',
        'transfer_type': 'Transfer Type',
        'transfer_reference': 'Reference',
        'transfer_status': 'Status',
        'transfer_status_processing': 'Processing',
        'transfer_note_1': 'Processing times may vary depending on cut-off times and verification checks.',
        'transfer_note_2': 'You can track the status in your Transaction History.',
        'transfer_button': 'View Transfer Details',
        'transfer_security_warning': 'If you did not authorize this transfer, please contact our support team immediately.',
        'transfer_disclaimer': 'Please do not reply to this email. For assistance, contact support@ecommbx.group',
    },
    'it': {
        # Password Reset Email
        'password_reset_subject': f'Reimpostazione Password - {APP_NAME}',
        'password_reset_title': 'Richiesta Reimpostazione Password',
        'password_reset_greeting': 'Ciao,',
        'password_reset_body': 'Abbiamo ricevuto una richiesta per reimpostare la tua password. Clicca il pulsante qui sotto per creare una nuova password:',
        'password_reset_button': 'Reimposta Password',
        'password_reset_link_instruction': 'Oppure copia e incolla questo link nel tuo browser:',
        'password_reset_expiry': '⏰ Questo link scade tra 1 ora.',
        'password_reset_ignore': 'Se non hai richiesto la reimpostazione della password, ignora questa email. La tua password rimarrà invariata.',
        'password_reset_footer': f'© 2024 {APP_NAME}. Tutti i diritti riservati.',
        
        # Admin Password Reset
        'admin_reset_title': 'Reimpostazione Password',
        'admin_reset_body': 'La tua password è stata reimpostata da un amministratore.',
        'temp_password_label': 'La tua password temporanea:',
        'admin_reset_warning': '⚠️ Accedi e cambia immediatamente la tua password per sicurezza.',
        
        # OTP Email
        'otp_subject': f'Il Tuo Codice di Accesso - {APP_NAME}',
        'otp_title': 'Codice di Verifica',
        'otp_greeting': 'Ciao,',
        'otp_body': 'Il tuo codice di verifica è:',
        'otp_expiry': '⏰ Questo codice scade tra 10 minuti.',
        'otp_ignore': 'Se non hai richiesto questo codice, ignora questa email.',
        
        # Email Verification
        'email_verify_subject': f'Verifica la Tua Email - {APP_NAME}',
        'email_verify_title': 'Benvenuto in ecommbx',
        'email_verify_greeting': 'Ciao',
        'email_verify_body': 'Grazie per esserti registrato con ecommbx. Per completare la registrazione e accedere al tuo account, verifica il tuo indirizzo email cliccando il pulsante qui sotto:',
        'email_verify_button': 'Verifica Indirizzo Email',
        'email_verify_link_instruction': 'Oppure copia e incolla questo link nel tuo browser:',
        'email_verify_expiry': '⏰ Questo link di verifica scade tra 24 ore.',
        'email_verify_ignore': 'Se non hai creato un account con noi, ignora questa email.',
        'email_verify_security_note': '🔒 Per la tua sicurezza, devi verificare la tua email prima di accedere al tuo account.',
        
        # Transfer Confirmation Email
        'transfer_subject': 'Abbiamo ricevuto la tua richiesta di bonifico – Rif',
        'transfer_title': 'Bonifico Inviato',
        'transfer_greeting': 'Gentile',
        'transfer_body': 'La tua richiesta di bonifico è stata inviata ed è in elaborazione.',
        'transfer_summary': 'Riepilogo Bonifico',
        'transfer_amount': 'Importo',
        'transfer_recipient': 'Beneficiario',
        'transfer_recipient_iban': 'IBAN Beneficiario',
        'transfer_from_account': 'Dal Conto',
        'transfer_date': 'Data e Ora',
        'transfer_type': 'Tipo Bonifico',
        'transfer_reference': 'Riferimento',
        'transfer_status': 'Stato',
        'transfer_status_processing': 'In Elaborazione',
        'transfer_note_1': 'I tempi di elaborazione possono variare a seconda degli orari limite e dei controlli di verifica.',
        'transfer_note_2': 'Puoi monitorare lo stato nella tua Cronologia Transazioni.',
        'transfer_button': 'Visualizza Dettagli Bonifico',
        'transfer_security_warning': 'Se non hai autorizzato questo bonifico, contatta immediatamente il nostro servizio clienti.',
        'transfer_disclaimer': 'Si prega di non rispondere a questa email. Per assistenza, contattare support@ecommbx.group',
    }
}


def get_translation(key: str, language: str = 'en') -> str:
    """Get translation for a given key and language."""
    lang = language.lower() if language else 'en'
    if lang not in EMAIL_TRANSLATIONS:
        lang = 'en'
    return EMAIL_TRANSLATIONS[lang].get(key, EMAIL_TRANSLATIONS['en'].get(key, key))


class EmailService:
    """Email service using Resend for real email delivery."""
    
    def __init__(self):
        self.sent_emails = []  # Store for testing/debugging
        # Set API key on initialization from environment
        api_key = get_resend_api_key()
        if api_key:
            resend.api_key = api_key
    
    def send_password_reset(self, to_email: str, reset_token: str, temp_password: Optional[str] = None, language: str = 'en'):
        """Send password reset email via Resend with localization support."""
        # Ensure API key is set from environment
        api_key = get_resend_api_key()
        if not api_key:
            logger.warning(f"RESEND_API_KEY not configured - skipping password reset email to {to_email}")
            return False
            
        resend.api_key = api_key
        
        sender_email = get_sender_email()
        frontend_url = get_frontend_url()
        
        t = lambda key: get_translation(key, language)
        subject = t('password_reset_subject')
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        if temp_password:
            # Admin-initiated password reset with temporary password
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #FFFFFF; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .header h1 {{ margin: 0; color: #FFFFFF; }}
                    .header .brand {{ color: #FFFFFF; background-color: transparent; }}
                    .header .brand-accent {{ color: #dc3545; }}
                    .header p {{ color: #FFFFFF; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .password-box {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; }}
                    .password {{ font-family: monospace; font-size: 24px; color: #856404; font-weight: bold; }}
                    .warning {{ color: #dc3545; font-size: 14px; margin-top: 20px; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1 style="color: #FFFFFF;">🔐 <span class="brand" style="color: #FFFFFF;">ecomm</span><span class="brand-accent">bx</span></h1>
                    <p style="color: #FFFFFF;">{t('admin_reset_title')}</p>
                </div>
                <div class="content">
                    <p>{t('password_reset_greeting')}</p>
                    <p>{t('admin_reset_body')}</p>
                    <div class="password-box">
                        <p>{t('temp_password_label')}</p>
                        <p class="password">{temp_password}</p>
                    </div>
                    <p class="warning">{t('admin_reset_warning')}</p>
                </div>
                <div class="footer">
                    <p>{t('password_reset_footer')}</p>
                </div>
            </body>
            </html>
            """
        else:
            # User-initiated password reset with link
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0; color: #FFFFFF;">🔐 <span style="color: #FFFFFF; background-color: transparent;">ecomm</span><span style="color: #dc3545;">bx</span></h1>
                    <p style="margin: 10px 0 0 0; color: #FFFFFF;">{t('password_reset_title')}</p>
                </div>
                <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                    <p>{t('password_reset_greeting')}</p>
                    <p>{t('password_reset_body')}</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" style="display: inline-block; background: #dc3545; color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0;">{t('password_reset_button')}</a>
                    </p>
                    <p>{t('password_reset_link_instruction')}</p>
                    <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0; word-break: break-all; font-family: monospace; font-size: 12px;">
                        <a href="{reset_link}" style="color: #333;">{reset_link}</a>
                    </div>
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">{t('password_reset_expiry')}</p>
                    <p style="color: #666; font-size: 14px;">{t('password_reset_ignore')}</p>
                </div>
                <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
                    <p>{t('password_reset_footer')}</p>
                </div>
            </body>
            </html>
            """
        
        try:
            params = {
                "from": f"{APP_NAME} <{sender_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Password reset email sent to {to_email} (lang={language}), Resend ID: {response.get('id', 'unknown')}")
            
            self.sent_emails.append({
                'to': to_email,
                'subject': subject,
                'sent_at': datetime.utcnow(),
                'resend_id': response.get('id'),
                'language': language
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            print(f"[EMAIL ERROR] Failed to send to {to_email}: {str(e)}")
            return False
    
    def send_otp(self, to_email: str, otp_code: str, language: str = 'en'):
        """Send OTP code via email using Resend with localization support."""
        # Ensure API key is set from environment
        api_key = get_resend_api_key()
        if not api_key:
            logger.warning(f"RESEND_API_KEY not configured - skipping OTP email to {to_email}")
            return False
            
        resend.api_key = api_key
        
        sender_email = get_sender_email()
        
        t = lambda key: get_translation(key, language)
        subject = t('otp_subject')
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #FFFFFF; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ margin: 0; color: #FFFFFF; }}
                .header .brand {{ color: #FFFFFF; background-color: transparent; }}
                .header .brand-accent {{ color: #dc3545; }}
                .header p {{ color: #FFFFFF; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-box {{ background: #fff; border: 2px solid #dc3545; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }}
                .otp {{ font-family: monospace; font-size: 36px; color: #dc3545; font-weight: bold; letter-spacing: 8px; }}
                .warning {{ color: #666; font-size: 14px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="color: #FFFFFF;">🔒 <span class="brand" style="color: #FFFFFF;">ecomm</span><span class="brand-accent">bx</span></h1>
                <p style="color: #FFFFFF;">{t('otp_title')}</p>
            </div>
            <div class="content">
                <p>{t('otp_greeting')}</p>
                <p>{t('otp_body')}</p>
                <div class="otp-box">
                    <p class="otp">{otp_code}</p>
                </div>
                <p class="warning">{t('otp_expiry')}</p>
                <p class="warning">{t('otp_ignore')}</p>
            </div>
            <div class="footer">
                <p>{t('password_reset_footer')}</p>
            </div>
        </body>
        </html>
        """
        
        try:
            params = {
                "from": f"{APP_NAME} <{sender_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"OTP email sent to {to_email} (lang={language}), Resend ID: {response.get('id', 'unknown')}")
            
            self.sent_emails.append({
                'to': to_email,
                'subject': subject,
                'sent_at': datetime.utcnow(),
                'resend_id': response.get('id'),
                'language': language
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to send OTP email to {to_email}: {str(e)}")
            print(f"[EMAIL ERROR] Failed to send OTP to {to_email}: {str(e)}")
            return False
    
    def send_verification_email(self, to_email: str, verification_token: str, first_name: str = '', language: str = 'en'):
        """Send email verification email via Resend with localization support."""
        # Ensure API key is set from environment
        api_key = get_resend_api_key()
        if not api_key:
            logger.warning(f"RESEND_API_KEY not configured - skipping verification email to {to_email}")
            return False
            
        resend.api_key = api_key
        
        sender_email = get_sender_email()
        frontend_url = get_frontend_url()
        
        t = lambda key: get_translation(key, language)
        subject = t('email_verify_subject')
        verify_link = f"{frontend_url}/verify-email?token={verification_token}"
        
        # Personalize greeting with first name if provided
        greeting = f"{t('email_verify_greeting')} {first_name}," if first_name else f"{t('email_verify_greeting')},"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; color: #FFFFFF;">✉️ <span style="color: #FFFFFF; background-color: transparent;">ecomm</span><span style="color: #dc3545;">bx</span></h1>
                <p style="margin: 10px 0 0 0; color: #FFFFFF;">{t('email_verify_title')}</p>
            </div>
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">{greeting}</p>
                <p>{t('email_verify_body')}</p>
                <p style="text-align: center;">
                    <a href="{verify_link}" style="display: inline-block; background: #dc3545; color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0;">{t('email_verify_button')}</a>
                </p>
                <p>{t('email_verify_link_instruction')}</p>
                <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0; word-break: break-all; font-family: monospace; font-size: 12px;">
                    <a href="{verify_link}" style="color: #333;">{verify_link}</a>
                </div>
                <p style="color: #666; font-size: 14px; margin-top: 20px;">{t('email_verify_expiry')}</p>
                <p style="color: #28a745; font-size: 14px; background: #d4edda; padding: 12px; border-radius: 6px;">{t('email_verify_security_note')}</p>
                <p style="color: #666; font-size: 14px;">{t('email_verify_ignore')}</p>
            </div>
            <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
                <p>{t('password_reset_footer')}</p>
            </div>
        </body>
        </html>
        """
        
        try:
            params = {
                "from": f"{APP_NAME} <{sender_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Verification email sent to {to_email} (lang={language}), Resend ID: {response.get('id', 'unknown')}")
            
            self.sent_emails.append({
                'to': to_email,
                'subject': subject,
                'sent_at': datetime.utcnow(),
                'resend_id': response.get('id'),
                'language': language,
                'type': 'verification'
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
            print(f"[EMAIL ERROR] Failed to send verification email to {to_email}: {str(e)}")
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
    
    @staticmethod
    def generate_verification_token() -> str:
        """Generate a secure email verification token."""
        return secrets.token_urlsafe(32)
    
    def send_transfer_confirmation_email(
        self,
        to_email: str,
        first_name: str,
        reference_number: str,
        amount_cents: int,
        beneficiary_name: str,
        beneficiary_iban: str,
        sender_iban: str,
        transfer_type: str = "SEPA Transfer",
        transfer_date: datetime = None,
        language: str = 'en'
    ) -> dict:
        """
        Send transfer confirmation email via Resend with localization support.
        
        Returns:
            dict with keys: success (bool), provider_id (str or None), error (str or None)
        """
        # Ensure API key is set from environment
        api_key = get_resend_api_key()
        if not api_key:
            error_msg = "RESEND_API_KEY not configured"
            logger.warning(f"[TRANSFER EMAIL] {error_msg} - skipping email to {to_email}")
            return {'success': False, 'provider_id': None, 'error': error_msg}
            
        resend.api_key = api_key
        
        sender_email = get_sender_email()
        if not sender_email:
            error_msg = "SENDER_EMAIL not configured"
            logger.warning(f"[TRANSFER EMAIL] {error_msg} - skipping email to {to_email}")
            return {'success': False, 'provider_id': None, 'error': error_msg}
        
        frontend_url = get_frontend_url()
        
        t = lambda key: get_translation(key, language)
        
        # Subject line with reference number
        subject = f"{t('transfer_subject')} #{reference_number}"
        
        # Format amount in EU style (€1.234,56)
        amount_euros = amount_cents / 100
        amount_formatted = f"€{amount_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Mask IBAN for security (show first 4 and last 4 characters)
        def mask_iban(iban: str) -> str:
            if not iban or len(iban) < 8:
                return iban or "N/A"
            return f"{iban[:4]}{'*' * (len(iban) - 8)}{iban[-4:]}"
        
        masked_beneficiary_iban = mask_iban(beneficiary_iban)
        masked_sender_iban = mask_iban(sender_iban)
        
        # Format date
        if transfer_date:
            date_formatted = transfer_date.strftime("%d/%m/%Y %H:%M")
        else:
            date_formatted = datetime.utcnow().strftime("%d/%m/%Y %H:%M")
        
        # Transaction history URL
        transactions_url = f"{frontend_url}/transactions"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; color: #FFFFFF;">💸 <span style="color: #FFFFFF; background-color: transparent;">ecomm</span><span style="color: #dc3545;">bx</span></h1>
                <p style="margin: 10px 0 0 0; font-size: 18px; color: #FFFFFF;">{t('transfer_title')}</p>
            </div>
            <div style="background: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <p style="font-size: 16px;">{t('transfer_greeting')} {first_name},</p>
                <p>{t('transfer_body')}</p>
                
                <!-- Transfer Summary Box -->
                <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h3 style="margin: 0 0 15px 0; color: #1a1a2e; font-size: 16px; border-bottom: 2px solid #dc3545; padding-bottom: 10px;">{t('transfer_summary')}</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #666; font-size: 14px;">{t('transfer_reference')}</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #1a1a2e; font-family: monospace;">#{reference_number}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666; font-size: 14px;">{t('transfer_amount')}</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #dc3545; font-size: 18px;">{amount_formatted}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666; font-size: 14px;">{t('transfer_recipient')}</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #1a1a2e;">{beneficiary_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666; font-size: 14px;">{t('transfer_recipient_iban')}</td>
                            <td style="padding: 8px 0; text-align: right; font-family: monospace; color: #1a1a2e;">{masked_beneficiary_iban}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666; font-size: 14px;">{t('transfer_from_account')}</td>
                            <td style="padding: 8px 0; text-align: right; font-family: monospace; color: #1a1a2e;">{masked_sender_iban}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666; font-size: 14px;">{t('transfer_date')}</td>
                            <td style="padding: 8px 0; text-align: right; color: #1a1a2e;">{date_formatted} UTC</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666; font-size: 14px;">{t('transfer_type')}</td>
                            <td style="padding: 8px 0; text-align: right; color: #1a1a2e;">{transfer_type}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666; font-size: 14px;">{t('transfer_status')}</td>
                            <td style="padding: 8px 0; text-align: right;">
                                <span style="background: #ffc107; color: #212529; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">{t('transfer_status_processing')}</span>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <!-- Processing Notes -->
                <div style="background: #e7f3ff; border-left: 4px solid #007bff; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #004085;">📋 {t('transfer_note_1')}</p>
                    <p style="margin: 0; font-size: 14px; color: #004085;">📊 {t('transfer_note_2')}</p>
                </div>
                
                <!-- View Details Button -->
                <p style="text-align: center;">
                    <a href="{transactions_url}" style="display: inline-block; background: #dc3545; color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 15px 0;">{t('transfer_button')}</a>
                </p>
                
                <!-- Security Warning -->
                <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; color: #856404; font-size: 13px;">⚠️ <strong>{t('transfer_security_warning')}</strong></p>
                </div>
                
                <!-- Disclaimer -->
                <p style="color: #999; font-size: 12px; text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee;">{t('transfer_disclaimer')}</p>
            </div>
            <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
                <p>{t('password_reset_footer')}</p>
            </div>
        </body>
        </html>
        """
        
        # Structured logging for debugging
        logger.info(f"[TRANSFER EMAIL] Attempting to send confirmation email: transferRef={reference_number}, recipient={to_email}, lang={language}")
        
        try:
            params = {
                "from": f"{APP_NAME} <{sender_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            
            response = resend.Emails.send(params)
            provider_id = response.get('id', '')
            
            logger.info(f"[TRANSFER EMAIL] SUCCESS: transferRef={reference_number}, recipient={to_email}, lang={language}, resendId={provider_id}")
            
            self.sent_emails.append({
                'to': to_email,
                'subject': subject,
                'sent_at': datetime.utcnow(),
                'resend_id': provider_id,
                'language': language,
                'type': 'transfer_confirmation',
                'reference': reference_number
            })
            
            # Return detailed success result
            return {
                'success': True,
                'provider_id': provider_id,
                'error': None
            }
        except Exception as e:
            error_msg = str(e)[:200]  # Truncate long errors
            logger.error(f"[TRANSFER EMAIL] FAILED: transferRef={reference_number}, recipient={to_email}, error={error_msg}")
            print(f"[EMAIL ERROR] Failed to send transfer confirmation to {to_email}: {error_msg}")
            
            # Return detailed failure result
            return {
                'success': False,
                'provider_id': None,
                'error': error_msg
            }
