import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Dict, Any
from backend.settings import settings

logger = logging.getLogger("nutrimenu.email")


class EmailMessage:
    def __init__(self, to: str, subject: str, text_body: str, html_body: str):
        self.to = to
        self.subject = subject
        self.text_body = text_body
        self.html_body = html_body


class BaseEmailBackend:
    def send(self, message: EmailMessage) -> bool:
        raise NotImplementedError


class ConsoleEmailBackend(BaseEmailBackend):
    """
    Development and test email backend.
    Records dispatched messages in memory for test assertions and logs to logger.
    """
    def __init__(self):
        self.outbox: List[EmailMessage] = []

    def send(self, message: EmailMessage) -> bool:
        self.outbox.append(message)
        logger.info("[DEV EMAIL OUTBOX] To: %s | Subject: %s", message.to, message.subject)
        return True

    def clear(self):
        self.outbox.clear()


class SMTPEmailBackend(BaseEmailBackend):
    """Production SMTP backend with STARTTLS/SSL support and timeouts."""
    def __init__(
        self,
        host: str,
        port: int,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        tls_mode: str = "starttls"
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email or user or "noreply@nutrimenu.ai"
        self.tls_mode = tls_mode

    def send(self, message: EmailMessage) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = f"NutriMenu AI <{self.from_email}>"
        msg["To"] = message.to

        part1 = MIMEText(message.text_body, "plain", "utf-8")
        part2 = MIMEText(message.html_body, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        try:
            if self.tls_mode == "ssl":
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                if self.tls_mode == "starttls":
                    server.starttls()

            if self.user and self.password:
                server.login(self.user, self.password)

            server.sendmail(self.from_email, [message.to], msg.as_string())
            server.quit()
            logger.info("Successfully sent transactional email to %s (Subject: %s)", message.to, message.subject)
            return True
        except Exception as e:
            logger.error("Failed to send transactional email to %s: %s", message.to, e)
            return False


# Singleton backend instance resolution
dev_email_backend = ConsoleEmailBackend()


def get_email_backend() -> BaseEmailBackend:
    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        return SMTPEmailBackend(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password.get_secret_value(),
            from_email=settings.smtp_from,
            tls_mode=settings.smtp_tls_mode,
        )
    return dev_email_backend


def _build_html_template(title: str, greeting: str, lead_text: str, code: Optional[str] = None, sub_text: str = "") -> str:
    code_block = ""
    if code:
        code_block = f"""
        <div style="margin: 24px 0; text-align: center;">
            <div style="display: inline-block; padding: 14px 28px; background-color: #f1f5f9; border-radius: 12px; border: 1px solid #cbd5e1; font-family: monospace; font-size: 28px; font-weight: 800; letter-spacing: 6px; color: #0f172a;">
                {code}
            </div>
            <p style="margin-top: 8px; font-size: 12px; color: #64748b;">This code expires in 10 minutes. Do not share it with anyone.</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 32px 16px;">
    <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 24px;">
            <h2 style="margin: 0; font-size: 20px; font-weight: 800; color: #0f172a;">🥗 NutriMenu AI</h2>
        </div>
        <h3 style="margin: 0 0 12px 0; font-size: 18px; font-weight: 700; color: #1e293b;">{title}</h3>
        <p style="margin: 0 0 12px 0; font-size: 14px; color: #475569; line-height: 1.5;">{greeting}</p>
        <p style="margin: 0 0 12px 0; font-size: 14px; color: #475569; line-height: 1.5;">{lead_text}</p>
        {code_block}
        {f'<p style="margin: 16px 0 0 0; font-size: 13px; color: #64748b; line-height: 1.5;">{sub_text}</p>' if sub_text else ''}
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 28px 0 16px 0;">
        <p style="margin: 0; font-size: 11px; color: #94a3b8; text-align: center;">
            NutriMenu AI — Clinical Food Recommendation Engine.<br>If you did not request this communication, please disregard this email.
        </p>
    </div>
</body>
</html>"""


# =====================================================================
# TRANSACTIONAL EMAIL DISPATCHERS
# =====================================================================

def send_verification_email(email: str, code: str) -> bool:
    subject = "Verify Your NutriMenu AI Account"
    lead = "Welcome to NutriMenu AI! Enter the 6-digit verification code below to verify your email address and activate your account."
    html = _build_html_template(
        title="Verify Your Account",
        greeting=f"Hello,",
        lead_text=lead,
        code=code,
    )
    text = f"Welcome to NutriMenu AI!\n\nYour 6-digit email verification code is: {code}\n\nThis code expires in 10 minutes."
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))


def send_password_reset_email(email: str, code: str) -> bool:
    subject = "Password Reset Verification Code"
    lead = "We received a request to reset your password. Enter the 6-digit verification code below to set a new password."
    html = _build_html_template(
        title="Password Reset Request",
        greeting="Hello,",
        lead_text=lead,
        code=code,
        sub_text="If you did not request a password reset, your account is still secure and no changes have been made.",
    )
    text = f"Password Reset Request\n\nYour 6-digit verification code is: {code}\n\nThis code expires in 10 minutes."
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))


def send_login_2fa_email(email: str, code: str) -> bool:
    subject = "Your Two-Factor Authentication Login Code"
    lead = "Someone is signing into your NutriMenu AI account with two-factor authentication enabled. Use the code below to complete sign-in."
    html = _build_html_template(
        title="Two-Factor Sign-In Verification",
        greeting="Hello,",
        lead_text=lead,
        code=code,
    )
    text = f"Your NutriMenu AI two-factor authentication code is: {code}\n\nExpires in 10 minutes."
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))


def send_email_change_confirmation(new_email: str, code: str) -> bool:
    subject = "Confirm Your New Email Address"
    lead = f"You requested to change your NutriMenu AI account email to {new_email}. Enter the verification code below to confirm this change."
    html = _build_html_template(
        title="Confirm New Email",
        greeting="Hello,",
        lead_text=lead,
        code=code,
    )
    text = f"Confirm your new email address.\n\nVerification code: {code}\n\nExpires in 10 minutes."
    return get_email_backend().send(EmailMessage(to=new_email, subject=subject, text_body=text, html_body=html))


def send_email_change_notice(old_email: str, new_email: str) -> bool:
    subject = "Security Notice: Account Email Change Requested"
    lead = f"A request was submitted to update your account email address to <strong>{new_email}</strong>. A verification code has been dispatched to the new address."
    html = _build_html_template(
        title="Security Notice: Email Update",
        greeting="Hello,",
        lead_text=lead,
        sub_text="If you did NOT request this change, please sign in immediately and change your password.",
    )
    text = f"Security Notice: A request was submitted to update your account email address to {new_email}.\n\nIf you did not request this, please change your password immediately."
    return get_email_backend().send(EmailMessage(to=old_email, subject=subject, text_body=text, html_body=html))


def send_password_changed_alert(email: str) -> bool:
    subject = "Security Notice: Your Password Has Been Changed"
    lead = "Your NutriMenu AI account password was successfully updated. All other active sessions have been automatically terminated for your security."
    html = _build_html_template(
        title="Password Updated",
        greeting="Hello,",
        lead_text=lead,
        sub_text="If you did not authorize this change, please reset your password immediately.",
    )
    text = "Security Notice: Your NutriMenu AI account password was changed. All other sessions have been signed out."
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))


def send_new_device_alert(email: str, ip_address: str, device_label: str) -> bool:
    subject = "Security Notice: New Device Sign-In"
    lead = f"A new sign-in was detected on your NutriMenu AI account.<br><strong>Device:</strong> {device_label}<br><strong>IP Address:</strong> {ip_address}"
    html = _build_html_template(
        title="New Sign-In Detected",
        greeting="Hello,",
        lead_text=lead,
        sub_text="If this was you, no action is needed. If this wasn't you, review your active sessions and change your password.",
    )
    text = f"New sign-in detected on your account.\nDevice: {device_label}\nIP: {ip_address}"
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))


def send_account_locked_alert(email: str, lock_duration_minutes: int) -> bool:
    subject = "Security Alert: Account Temporarily Locked"
    lead = f"Too many consecutive failed login attempts were detected on your account. To prevent unauthorized access, sign-in has been temporarily locked for {lock_duration_minutes} minutes."
    html = _build_html_template(
        title="Account Temporarily Locked",
        greeting="Hello,",
        lead_text=lead,
        sub_text="You can reset your password at any time using the 'Forgot Password' link to regain immediate access.",
    )
    text = f"Security Alert: Your account is temporarily locked for {lock_duration_minutes} minutes due to multiple failed login attempts."
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))


def send_token_reuse_alert(email: str) -> bool:
    subject = "Urgent Security Alert: Session Token Reuse Detected"
    lead = "A revoked or previously used session refresh token was submitted. Because this can indicate token interception, all active sessions on your account have been revoked immediately."
    html = _build_html_template(
        title="Session Security Alert",
        greeting="Hello,",
        lead_text=lead,
        sub_text="Please sign in again and change your password if you suspect unauthorized activity.",
    )
    text = "Urgent Security Alert: Session token reuse was detected. All sessions on your account have been revoked."
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))


def send_deletion_scheduled_alert(email: str, scheduled_date_str: str) -> bool:
    subject = "Account Deletion Scheduled (14-Day Grace Period)"
    lead = f"Your request to permanently delete your NutriMenu AI account and all associated health records has been registered. Your account is scheduled for permanent deletion on <strong>{scheduled_date_str}</strong>."
    html = _build_html_template(
        title="Account Deletion Scheduled",
        greeting="Hello,",
        lead_text=lead,
        sub_text="If you change your mind, simply log in before this date and click 'Cancel Deletion' to restore your account.",
    )
    text = f"Your account deletion is scheduled for {scheduled_date_str}. You can cancel anytime before this date by logging in."
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))


def send_deletion_cancelled_alert(email: str) -> bool:
    subject = "Account Deletion Cancelled"
    lead = "Your pending account deletion has been cancelled. Your account and health history remain active and secure."
    html = _build_html_template(
        title="Account Restored",
        greeting="Hello,",
        lead_text=lead,
    )
    text = "Your pending account deletion was cancelled. Your account remains active."
    return get_email_backend().send(EmailMessage(to=email, subject=subject, text_body=text, html_body=html))
