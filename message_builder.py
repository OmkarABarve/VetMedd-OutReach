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

Special cases:
  - Franchise contacts (is_franchise=True) use templates/{prefix}_franchise.txt,
    overriding the scenario, so we pitch a multi-location rollout.
  - A classification containing "multiple" maps to the "multiple" prefix, which
    pitches clinic + shop + grooming together.

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


def _classification_prefix(classification: str):
    """Map a classification string to a template prefix (or None if unknown).

    A value containing "multiple" routes to the combined "multiple" pitch.
    """
    classification = (classification or "").strip().lower()
    if not classification:
        return None
    if "multiple" in classification:
        return "multiple"
    return config.CLASSIFICATION_TO_PREFIX.get(classification)


def _template_path(classification: str, scenario: str, is_franchise: bool = False) -> Path:
    """Resolve the template file, falling back to fallback_first when needed.

    Franchise contacts use {prefix}_franchise.txt (scenario is overridden); if that
    file is missing we gracefully fall back to the normal scenario template.
    """
    prefix = _classification_prefix(classification)
    if prefix:
        if is_franchise:
            franchise_candidate = config.TEMPLATES_DIR / f"{prefix}_franchise.txt"
            if franchise_candidate.exists():
                return franchise_candidate
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


def build_message(row, scenario: str, sentiment: str = "neutral",
                  is_franchise: bool = False) -> dict:
    """Render the message for a contact row.

    Args:
        row: a pandas Series / dict-like contact row.
        scenario: 'first' | 'reminder' | 'engaged'.
        sentiment: 'positive' | 'neutral' | 'negative' (only used for 'engaged').
        is_franchise: when True, prefer the franchise template for the classification.

    Returns:
        {"subject": str, "body": str, "template": str}
    """
    classification = str(row.get("Classification", "")).strip().lower()
    template_path = _template_path(classification, scenario, is_franchise)
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
