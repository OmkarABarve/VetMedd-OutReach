"""
config.py - Central configuration for the VetApp outreach pipeline.

All tunable settings, file paths, feature flags, and account references live here
so you only ever have to change things in ONE place.

Secrets themselves are read from the .env file (see .env.example).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from .env into the environment.
load_dotenv()

# ----------------------------------------------------------------------------
#  PATHS
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "Data"
TEMPLATES_DIR = BASE_DIR / "templates"
LOGS_DIR = BASE_DIR / "logs"

# Input contact sheet. The loader accepts .xlsx OR .csv.
# It will use the first file that exists from this list (in order).
CONTACT_FILE_CANDIDATES = [
    # DATA_DIR / "contacts.xlsx",
    DATA_DIR / "contact.csv",
    DATA_DIR / "contacts.csv",
]

LOG_FILE = LOGS_DIR / "outreach_log.csv"

# ----------------------------------------------------------------------------
#  FEATURE FLAGS
# ----------------------------------------------------------------------------
# Email is the active channel right now.
EMAIL_ENABLED = True

# WhatsApp is fully implemented but OFF for now. Flip this to True later to
# enable WhatsApp fallback when a contact has no email address.
WHATSAPP_ENABLED = False

# Some contacts may have a SECOND WhatsApp number (optional "WhatsApp Number 2"
# column). Most won't. When this is True AND that column has a value, we ALSO
# message the second number. Requires WHATSAPP_ENABLED to be True as well.
WHATSAPP_NUMBER_2_ENABLED = False

# Franchise handling. When True, we look at the optional "Level" column (or a
# boolean "Franchise" column). If it says "Franchise", we use a franchise-specific
# template for that classification (clinic / shop / grooming). Most contacts won't
# be franchises, so this is off by default.
FRANCHISE_ENABLED = False

# ----------------------------------------------------------------------------
#  EMAIL ACCOUNT (SendGrid)
#  >>> To change the sending Gmail/host address, set SENDGRID_FROM_EMAIL in .env <<<
# ----------------------------------------------------------------------------
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "VetApp Team")

# ----------------------------------------------------------------------------
#  WHATSAPP ACCOUNT (Twilio)
#  >>> To change the WhatsApp sender number, set TWILIO_WHATSAPP_FROM in .env <<<
# ----------------------------------------------------------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")

# ----------------------------------------------------------------------------
#  NLP
# ----------------------------------------------------------------------------
ZERO_SHOT_MODEL = "valhalla/distilbart-mnli-12-1"
SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
NLP_CONFIDENCE_THRESHOLD = float(os.getenv("NLP_CONFIDENCE_THRESHOLD", "0.6"))

# Canonical classification labels used everywhere (zero-shot candidate labels
# and template filename prefixes).
CLASSIFICATION_LABELS = ["vet clinic", "pet shop", "grooming services"]

# Maps a (possibly messy) classification string to the template filename prefix.
# "multiple" is used when a contact spans more than one category (e.g. a place
# that is both a clinic and a shop) -> we pitch clinic + shop + grooming together.
CLASSIFICATION_TO_PREFIX = {
    "vet clinic": "vet_clinic",
    "pet shop": "petshop",
    "grooming services": "grooming",
    "multiple": "multiple",
}

# Keyword fallback used when the NLP model is not confident enough.
CLASSIFICATION_KEYWORDS = {
    "vet clinic": ["clinic", "hospital", "vet", "dr.", "doctor", "veterinary"],
    "pet shop": ["store", "shop", "supplies", "mart", "market"],
    "grooming services": ["groom", "salon", "spa", "wash", "bath"],
}

# ----------------------------------------------------------------------------
#  SCHEDULER
# ----------------------------------------------------------------------------
# "once"  -> run the pipeline a single time and exit (good for cron / Task Scheduler)
# "daily" -> stay alive and run every day at DAILY_RUN_TIME (uses the `schedule` lib)
RUN_MODE = "once"
DAILY_RUN_TIME = "09:00"  # 24h HH:MM, local time

# Optional pause between sends (seconds) to be gentle on API rate limits.
SEND_DELAY_SECONDS = 1.0

# ----------------------------------------------------------------------------
#  CONTACT SHEET SCHEMA
# ----------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "Company Name",
    "Times Communicated",
    "Email ID",
    "Location",
    "WhatsApp Number",
    "Classification",
    "Responses",
    "Don't Message",
]

# Optional columns. They are NOT required; the loader only normalizes them when
# they are present, and never adds them to a file that doesn't already have them.
#   "WhatsApp Number 2" -> a second WhatsApp number to also message (see WHATSAPP_NUMBER_2_ENABLED)
#   "Level"             -> contact tier; the value "Franchise" triggers franchise templates
#   "Franchise"         -> alternative boolean signal for franchise (TRUE/True/1/yes)
OPTIONAL_COLUMNS = [
    "WhatsApp Number 2",
    "Level",
    "Franchise",
]

# The word we look for (case-insensitive) to flag a contact as a franchise.
FRANCHISE_MARKER = "franchise"
