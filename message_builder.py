"""
message_builder.py - Decide which message to send and render it.

Decision tree (per row):
  Times Communicated == 0                       -> "first"    (first contact)
  Times >= 1 AND Responses == 0                 -> "reminder"
  Responses == Times Communicated (and > 0)     -> "engaged"  (sentiment-aware)
  otherwise                                     -> "reminder" (safe default nudge)

Template files live in templates/{prefix}_{scenario}.txt where prefix is derived
from the classification. If the classification is unknown/empty, we fall back to
templates/fallback_first.txt.

Each template's FIRST line is "Subject: ..."; everything after the following blank
line is the body. Placeholders: {company}, {location}, {sender_name}, {sentiment_clause}.
"""

from pathlib import Path

import config
import loader


# Sentiment-aware phrasing injected into "engaged" templates.
_SENTIMENT_CLAUSES = {
    "positive": " - it's great to hear your enthusiasm",
    "neutral": "",
    "negative": " - I appreciate your candor",
}


def decide_scenario(times_communicated: int, responses) -> str:
    """Return one of: 'first', 'reminder', 'engaged'."""
    replies = loader.response_count(responses)

    if times_communicated == 0:
        return "first"
    if replies == 0:
        return "reminder"
    if replies >= times_communicated:
        return "engaged"
    return "reminder"


def _template_path(classification: str, scenario: str) -> Path:
    """Resolve the template file, falling back to fallback_first when needed."""
    prefix = config.CLASSIFICATION_TO_PREFIX.get(classification)
    if prefix:
        candidate = config.TEMPLATES_DIR / f"{prefix}_{scenario}.txt"
        if candidate.exists():
            return candidate
    # Unknown classification or missing template -> generic fallback.
    return config.TEMPLATES_DIR / "fallback_first.txt"


def _split_subject_body(raw: str):
    """Split a template into (subject, body). Subject is the first 'Subject:' line."""
    lines = raw.splitlines()
    subject = ""
    body_start = 0
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body_start = 1
    body = "\n".join(lines[body_start:]).lstrip("\n")
    return subject, body


def build_message(row, scenario: str, sentiment: str = "neutral") -> dict:
    """Render the message for a contact row.

    Args:
        row: a pandas Series / dict-like contact row.
        scenario: 'first' | 'reminder' | 'engaged'.
        sentiment: 'positive' | 'neutral' | 'negative' (only used for 'engaged').

    Returns:
        {"subject": str, "body": str, "template": str}
    """
    classification = str(row.get("Classification", "")).strip().lower()
    template_path = _template_path(classification, scenario)
    raw = template_path.read_text(encoding="utf-8")
    subject_tmpl, body_tmpl = _split_subject_body(raw)

    fields = {
        "company": row.get("Company Name", "there") or "there",
        "location": row.get("Location", "your area") or "your area",
        "sender_name": config.SENDGRID_FROM_NAME,
        "sentiment_clause": _SENTIMENT_CLAUSES.get(sentiment, ""),
    }

    subject = subject_tmpl.format(**fields)
    body = body_tmpl.format(**fields)
    return {"subject": subject, "body": body, "template": template_path.name}
