"""
emailer.py - Send outreach emails via SendGrid (the active primary channel).

========================= HOW TO CHANGE THE SENDING ACCOUNT =========================
The "host" email (e.g. your Gmail address) and API key are read from .env via
config.py. To switch accounts, edit these in your .env file:

    SENDGRID_FROM_EMAIL   <- the Gmail/host address mail is sent FROM
    SENDGRID_API_KEY      <- your SendGrid API key
    SENDGRID_FROM_NAME    <- display name shown to recipients

The from-email MUST be verified in SendGrid (Single Sender Verification works with
a Gmail address): https://app.sendgrid.com/settings/sender_auth
=====================================================================================

send_email() returns (success: bool, note: str). It never raises; failures are
returned so the caller can log them and continue.
"""

import config


class SendResult:
    """Lightweight result wrapper for send attempts."""

    def __init__(self, success: bool, note: str = ""):
        self.success = success
        self.note = note


def _validate_config() -> str:
    """Return an error string if email config is incomplete, else ''."""
    if not config.SENDGRID_API_KEY:
        return "SENDGRID_API_KEY is not set in .env"
    if not config.SENDGRID_FROM_EMAIL:
        return "SENDGRID_FROM_EMAIL is not set in .env"
    return ""


def send_email(to_email: str, subject: str, body: str) -> SendResult:
    """Send a plain-text email via SendGrid.

    Returns SendResult(success, note). Catches all errors so the pipeline keeps going.
    """
    if not config.EMAIL_ENABLED:
        return SendResult(False, "email channel disabled (config.EMAIL_ENABLED=False)")

    config_error = _validate_config()
    if config_error:
        return SendResult(False, config_error)

    if not to_email:
        return SendResult(False, "no recipient email address")

    try:
        # Imported lazily so the rest of the pipeline works even if sendgrid
        # isn't installed yet (e.g. while testing message logic).
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Content, Email, Mail, To

        message = Mail(
            from_email=Email(config.SENDGRID_FROM_EMAIL, config.SENDGRID_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", body),
        )
        client = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = client.send(message)

        if 200 <= response.status_code < 300:
            return SendResult(True, f"sendgrid status {response.status_code}")
        return SendResult(False, f"sendgrid status {response.status_code}")

    except Exception as exc:  # network error, auth error, etc.
        return SendResult(False, f"sendgrid exception: {exc}")
