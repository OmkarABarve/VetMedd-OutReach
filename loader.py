"""
loader.py - Read and validate the contacts sheet.

Responsibilities:
  - Find and read Data/contacts.xlsx OR Data/contact.csv (config.CONTACT_FILE_CANDIDATES).
  - Enforce the required schema (raise a clear error before any sending happens).
  - Normalize messy values: coerce "Don't Message" to a strict bool, "Times
    Communicated" to int, and fill NaNs with sensible defaults.

Returns a tuple: (DataFrame, resolved_file_path) so the updater can write back
to the exact same file/format it was read from.
"""

from pathlib import Path

import pandas as pd

import config


# Values that should be treated as boolean True for the "Don't Message" column.
_TRUE_VALUES = {"true", "1", "yes", "y", "t"}


def _resolve_contact_file() -> Path:
    """Return the first existing contact file from the configured candidates."""
    for candidate in config.CONTACT_FILE_CANDIDATES:
        if candidate.exists():
            return candidate
    searched = "\n  - ".join(str(c) for c in config.CONTACT_FILE_CANDIDATES)
    raise FileNotFoundError(
        "No contact file found. Place a contacts.xlsx or contact.csv in the Data/ "
        f"folder. Searched:\n  - {searched}"
    )


def _coerce_dont_message(value) -> bool:
    """Coerce any spreadsheet value into a strict boolean (default False)."""
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    return str(value).strip().lower() in _TRUE_VALUES


def load_contacts():
    """Load, validate, and normalize the contact sheet.

    Returns:
        (df, path): the cleaned DataFrame and the resolved source file path.
    """
    path = _resolve_contact_file()

    if path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path, engine="openpyxl")
    else:
        df = pd.read_csv(path)

    # --- Schema validation -------------------------------------------------
    missing = [col for col in config.REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Contact file '{path.name}' is missing required column(s): {missing}. "
            f"Expected columns: {config.REQUIRED_COLUMNS}"
        )

    # --- Normalization -----------------------------------------------------
    df["Company Name"] = df["Company Name"].fillna("").astype(str).str.strip()

    # Times Communicated -> non-negative int.
    df["Times Communicated"] = (
        pd.to_numeric(df["Times Communicated"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )

    # Contact channels -> clean strings ("" when empty).
    df["Email ID"] = df["Email ID"].fillna("").astype(str).str.strip()
    df["WhatsApp Number"] = df["WhatsApp Number"].fillna("").astype(str).str.strip()
    df["Location"] = df["Location"].fillna("").astype(str).str.strip()
    df["Classification"] = (
        df["Classification"].fillna("").astype(str).str.strip().str.lower()
    )

    # Responses can be free text OR a count; keep raw, plus a parsed numeric view.
    df["Responses"] = df["Responses"].fillna("")

    # Don't Message -> strict bool.
    df["Don't Message"] = df["Don't Message"].apply(_coerce_dont_message)

    return df, path


def response_count(value) -> int:
    """Best-effort interpretation of the Responses cell as a reply count.

    - Numeric value      -> that number.
    - Non-empty free text -> counts as 1 reply.
    - Empty / NaN        -> 0.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    return 1


def has_response_text(value) -> bool:
    """True when Responses holds free-text (a real reply we can run sentiment on)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    text = str(value).strip()
    return bool(text) and not text.isdigit()
