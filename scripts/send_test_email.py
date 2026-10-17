"""
SMTP diagnostic: verifies your email configuration by sending a real test OTP email.

Usage:
    python scripts/send_test_email.py you@example.com
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from backend.settings import settings  # noqa: E402
from backend.email_service import send_verification_email, is_real_email_delivery  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/send_test_email.py you@example.com")
        return 2

    to = sys.argv[1].strip()
    print(f"SMTP_HOST      = {settings.smtp_host or '(not set)'}")
    print(f"SMTP_PORT      = {settings.smtp_port}")
    print(f"SMTP_USER      = {settings.smtp_user or '(not set)'}")
    print(f"SMTP_PASSWORD  = {'(set)' if settings.smtp_password and settings.smtp_password.get_secret_value().strip() else '(not set)'}")
    print(f"SMTP_FROM      = {settings.smtp_from or '(defaults to SMTP_USER)'}")
    print(f"TLS mode       = {settings.resolved_smtp_tls_mode()}")

    if not is_real_email_delivery():
        print("\nSMTP is not configured. Add SMTP_HOST, SMTP_USER and SMTP_PASSWORD to your .env file.")
        return 1

    ok = send_verification_email(to, "123456")
    print("\nRESULT:", "Sent successfully - check the inbox (and spam folder)." if ok else "FAILED - see the error above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
