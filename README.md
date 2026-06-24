# 🐾 VetApp GTM Outreach Pipeline

A Python-based automated outreach system for VetApp that sends personalized emails and WhatsApp messages to vet clinics, pet shops, and grooming services — and tracks all communication in a daily-refreshed Excel sheet.

---

## Architecture

```
contacts.xlsx (daily refresh)
       │
       ▼
┌─────────────┐
│  loader.py  │  Reads & validates Excel. Enforces schema. Flags issues.
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  classifier.py   │  If Classification is empty → zero-shot NLP model
│  (HuggingFace)   │  assigns: vet clinic / pet shop / grooming services
└──────┬───────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│            GUARD CHECKS                 │
│  ① Don't Message == True  → SKIP        │
│  ② No email AND no WhatsApp → SKIP      │
└──────┬──────────────────────────────────┘
       │
       ▼
┌──────────────────────┐
│  sentiment.py        │  If Responses column has text → detect tone
│                      │  (positive / neutral / negative)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐     Message Decision Tree:
│  message_builder.py  │  ─── Times Communicated == 0        → first_contact
│                      │  ─── Times >= 1, Responses == 0     → reminder
│                      │  ─── Responses == Times Communicated → engaged
└──────┬───────────────┘     Template: templates/{classification}_{scenario}.txt
       │
       ▼
┌──────────────────────────────────────┐
│        Outreach Engine               │
│  Primary:  emailer.py  (SendGrid)    │
│  Fallback: whatsapp.py (Twilio/Meta) │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────┐
│    updater.py        │  On SUCCESS → Times Communicated += 1
│                      │  Writes back to contacts.xlsx safely (atomic)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│    logs/             │  Appends row to outreach_log.csv:
│    outreach_log.csv  │  timestamp, company, channel, status, scenario
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│    dashboard.py      │  Streamlit app — run separately
│    (Streamlit)       │  Monitor all companies, statuses, filters
└──────────────────────┘
```

---

## Folder Structure

```
outreach_pipeline/
│
├── main.py                  # Orchestrator — runs full pipeline, schedulable
├── config.py                # Constants, model names, confidence thresholds
├── .env                     # API keys (never commit this)
├── requirements.txt         # All pip dependencies
├── README.md                # This file
│
├── contacts.xlsx            # Daily-refreshed contact sheet (manual for now)
│
├── loader.py                # Read Excel, validate columns, return clean DataFrame
├── classifier.py            # Zero-shot NLP to fill empty Classification cells
├── sentiment.py             # Detect tone of Responses text (pos/neu/neg)
├── message_builder.py       # Picks correct template based on decision tree
├── emailer.py               # SendGrid email sender
├── whatsapp.py              # Twilio WhatsApp sender
├── updater.py               # Safely increments Times Communicated in Excel
├── dashboard.py             # Streamlit monitoring dashboard
│
├── templates/
│   ├── vet_clinic_first.txt
│   ├── vet_clinic_reminder.txt
│   ├── vet_clinic_engaged.txt
│   ├── petshop_first.txt
│   ├── petshop_reminder.txt
│   ├── petshop_engaged.txt
│   ├── grooming_first.txt
│   ├── grooming_reminder.txt
│   ├── grooming_engaged.txt
│   └── fallback_first.txt   # Used when classification is unknown/low-confidence
│
└── logs/
    └── outreach_log.csv     # Appended after every run
```

---

## Contact Sheet Schema

| Column | Type | Notes |
|---|---|---|
| Company Name | string | Required |
| Times Communicated | int | Starts at 0, auto-incremented on send |
| Email ID | string | Primary outreach channel |
| Location | string | City/region |
| WhatsApp Number | string | Fallback if no email. Include country code e.g. +91XXXXXXXXXX |
| Classification | string | vet clinic / pet shop / grooming services. Auto-filled if empty |
| Responses | string/int | Free text reply OR count of replies |
| Don't Message | boolean | TRUE = skip this company entirely |

---

## Message Decision Logic

```
Don't Message == True          →  SKIP (log as "skipped_flag")
Times Communicated == 0        →  first_contact
Times >= 1, Responses == 0     →  reminder
Responses == Times Communicated →  engaged (sentiment-aware)
Otherwise                      →  follow_up (generic nudge)

Channel priority:
  Email ID present  →  Send via email (SendGrid)
  No email          →  Send via WhatsApp (Twilio)
  Neither present   →  SKIP (log as "skipped_no_channel")
```

---

## NLP Models Used

| Task | Model | Size | Notes |
|---|---|---|---|
| Classification | `cross-encoder/nli-MiniLM2-L6-H768` | ~90MB | Zero-shot, no training needed |
| Sentiment | `cardiffnlp/twitter-roberta-base-sentiment` | ~500MB | Pos/Neu/Neg on reply text |

Both run locally via HuggingFace `transformers`. No external API cost.

**Fallback:** If NLP confidence < 0.6 on classification, use keyword matching:
- `clinic / hospital / vet / dr.` → vet clinic
- `store / shop / supplies` → pet shop
- `groom / salon / spa / wash` → grooming services
- No match → use `fallback_first.txt` template

---

## APIs Required

### Email — SendGrid
```
pip install sendgrid
```
- Sign up at sendgrid.com → free 100 emails/day
- Get API key → add to `.env` as `SENDGRID_API_KEY`
- Set a verified sender email

### WhatsApp — Twilio
```
pip install twilio
```
- Sign up at twilio.com → WhatsApp Sandbox for testing
- Get `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`
- For production: apply for WhatsApp Business API approval

---

## Environment Variables (.env)

```env
SENDGRID_API_KEY=your_key_here
SENDGRID_FROM_EMAIL=you@yourdomain.com

TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

NLP_CONFIDENCE_THRESHOLD=0.6
```

---

## Running the Pipeline

```bash
# Install dependencies
pip install -r requirements.txt

# Run once manually
python main.py

# Run dashboard
streamlit run dashboard.py
```

### Schedule Daily (Linux/Mac cron)
```bash
# Run every day at 9:00 AM
0 9 * * * cd /path/to/outreach_pipeline && python main.py
```

### Schedule Daily (Windows Task Scheduler)
Point to `python.exe` with argument `main.py` and set daily trigger at 9:00 AM.

---

## Log Format (outreach_log.csv)

```
timestamp, company_name, classification, channel, scenario, status, notes
2024-01-15 09:01:22, Dr. Paws Clinic, vet clinic, email, first_contact, sent,
2024-01-15 09:01:25, Happy Pets Store, pet shop, whatsapp, reminder, sent,
2024-01-15 09:01:26, Fluffy Groom, grooming services, email, skipped_flag, skipped, Don't Message = True
```

---

## Requirements (requirements.txt)

```
pandas
openpyxl
sendgrid
twilio
transformers
torch
streamlit
python-dotenv
schedule
```

---

## Build Order (Recommended)

1. `loader.py` — get data loading + validation solid first
2. `message_builder.py` + templates — test logic with print statements
3. `updater.py` — safe write-back to Excel
4. `emailer.py` — SendGrid integration
5. `whatsapp.py` — Twilio sandbox
6. `classifier.py` — NLP classifier for unknowns
7. `sentiment.py` — tone detection on replies
8. `dashboard.py` — Streamlit monitoring
9. `main.py` — wire everything together
10. Cron/scheduler — automate daily run