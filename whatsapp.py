"""
whatsapp.py - Send outreach messages via Twilio WhatsApp.

>>> THIS CHANNEL IS DISABLED FOR NOW <<<
It is fully implemented but gated behind config.WHATSAPP_ENABLED (currently False).
Flip that flag to True later to activate WhatsApp fallback for contacts without an
email address. No other code changes are needed.

========================= HOW TO CHANGE THE WHATSAPP ACCOUNT =========================
The WhatsApp sender ID and Twilio credentials are read from .env via config.py.
To switch accounts, edit these in your .env file:

    TWILIO_WHATSAPP_FROM  <- the WhatsApp number messages are sent FROM (keep "whatsapp:" prefix)
    TWILIO_ACCOUNT_SID    <- your Twilio Account SID
    TWILIO_AUTH_TOKEN     <- your Twilio Auth Token
=====================================================================================

send_whatsapp() returns a SendResult and never raises.
"""

import config
from emailer import SendResult  # reuse the same result wrapper


def _validate_config() -> str:
    """Return an error string if WhatsApp config is incomplete, else ''."""
    if not config.TWILIO_ACCOUNT_SID:
        return "TWILIO_ACCOUNT_SID is not set in .env"
    if not config.TWILIO_AUTH_TOKEN:
        return "TWILIO_AUTH_TOKEN is not set in .env"
    if not config.TWILIO_WHATSAPP_FROM:
        return "TWILIO_WHATSAPP_FROM is not set in .env"
    return ""


def send_whatsapp(to_number: str, body: str) -> SendResult:
    """Send a WhatsApp message via Twilio.

    Returns SendResult(success, note). Respects the WHATSAPP_ENABLED feature flag.
    """
    if not config.WHATSAPP_ENABLED:
        return SendResult(False, "whatsapp channel disabled (config.WHATSAPP_ENABLED=False)")

    config_error = _validate_config()
    if config_error:
        return SendResult(False, config_error)

    if not to_number:
        return SendResult(False, "no recipient WhatsApp number")

    try:
        from twilio.rest import Client

        # Twilio expects the "whatsapp:" prefix on both ends.
        to_formatted = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"

        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=config.TWILIO_WHATSAPP_FROM,
            to=to_formatted,
            body=body,
        )
        return SendResult(True, f"twilio sid {message.sid}")

    except Exception as exc:
        return SendResult(False, f"twilio exception: {exc}")
