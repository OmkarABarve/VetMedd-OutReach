# Required Updates — VetApp GTM Outreach Pipeline

Living checklist of improvements **not yet implemented**. Each item includes **Reason** (why), **Idea** (what to build), and **Status**.

Last reviewed: 2026-06-24

---

## Summary

| # | Update | Priority | Status |
|---|--------|----------|--------|
| 1 | Appointments table (positive / action-required leads) | High | ❌ Not implemented (README ahead of code) |
| 2 | `Reason` column for rejections | Medium | ❌ Not implemented |
| 3 | Avoid spam folder (email deliverability) | High | ❌ Not implemented |
| 4 | SEO for outreach (subjects, links, landing page) | Medium | ❌ Not implemented |
| 5 | Confidence threshold tuning + test harness | Medium | ⚠️ Partial (threshold exists; no test script) |
| 6 | NLP feature toggles | Low | ❌ Not implemented |
| 7 | Lift hardcoded sentiment keywords to `config.py` | Low | ❌ Not implemented |
| 8 | Sync README with actual code | Low | ⚠️ README references appointments that don't exist yet |

---

## 1. Appointments table — positive / action-required leads

### Reason
When a contact replies positively or asks for more info (`"Tell me more"`, `"book a demo"`), that is a sales lead. Today those replies only affect message wording (engaged templates) and are never captured in a dedicated table. A daily-refreshed contacts sheet also makes a separate append-only table safer than a new column on contacts.

### Idea
- Add `appointments.py` + `config.APPOINTMENTS_ENABLED`, `APPOINTMENTS_FILE`, `ACTION_REQUIRED_KEYWORDS`.
- After sentiment runs on any free-text reply, book when:
  - sentiment == `positive` → reason `positive_response`, or
  - reply matches action keywords → reason `action_required`.
- Append to `Data/appointments.csv` with today's date. Dedupe on `(company_name, response)` so daily re-runs don't double-book.
- Run sentiment on **any** reply text, not only the `engaged` scenario (otherwise leads like City Animal Hospital — `Times=2`, one reply — miss detection because scenario resolves to `reminder`).

### Status
Documented in README knobs section but **not in code**. `config.py` has no `APPOINTMENTS_*` keys; `appointments.py` does not exist.

---

## 2. `Reason` column — capture rejection explanations

### Reason
Negative replies often contain useful CRM context (`"Not interested because we already use another tool"`). Today that text sits in `Responses` with no structured extraction. A `Reason` field helps sales/ops understand *why* someone declined without re-reading free text.

### Idea
- Add optional `Reason` column to contacts schema (or a separate `Data/rejections.csv` if daily refresh wipes columns).
- When sentiment is **negative** (or reply contains `"not interested"`, `"no thanks"`, etc.):
  - Extract text after **`because`** (primary).
  - Optionally fall back to **` as `** only when sentiment is already negative (avoids false hits like *"great as a starting point"*).
- Optionally auto-set `Don't Message = True` when a clear rejection is detected.

Example:

| Response | Extracted Reason |
|----------|------------------|
| `"Not interested because we already have a CRM"` | `we already have a CRM` |
| `"Not a fit as we are too small right now"` | `we are too small right now` |
| `"Not interested right now."` | *(empty — no because/as)* |

### Status
Not implemented. No `Reason` column in `REQUIRED_COLUMNS` or `loader.py`.

---

## 3. Avoid spam folder — email deliverability

### Reason
Cold outreach via SendGrid lands in **Promotions** or **Spam** when authentication, content, or sending patterns look bulk/automated. If messages never reach the inbox, the rest of the pipeline does not matter. Gmail and Outlook heavily filter unauthenticated senders, generic copy, and high-volume bursts from new domains.

### Idea

**Authentication (SendGrid + domain — highest impact)**
- Move beyond Single Sender Verification: set up **domain authentication** in SendGrid (SPF + DKIM; add **DMARC** on your DNS).
- Send from a real domain you control (e.g. `hello@vetapp.com`), not a bare Gmail address, once you scale past a handful of contacts.
- Keep `SENDGRID_FROM_NAME` human and consistent (e.g. `"Priya from VetApp"`, not `"VetApp Team"` alone).

**Content & template hygiene**
- Keep subjects short, specific, and non-salesy — use `{company}` and `{location}`; avoid ALL CAPS, `"FREE"`, `"Act now"`, excessive `!`, and multiple links in first contact.
- Add a one-line **plain-text opt-out** in every template footer: *"Reply 'stop' if you'd rather not hear from us."*
- Prefer **one clear CTA** per email; plain text only is good for deliverability (current setup).
- Vary reminder copy slightly across runs so identical repeated subjects do not trigger bulk filters.

**Sending behavior (pipeline knobs)**
- Keep `SEND_DELAY_SECONDS` ≥ 1–3s between sends; consider 5–10s on larger lists.
- **Warm up volume**: start with ~10–20 emails/day on a new sender/domain; increase gradually.
- Do not re-email contacts on hard bounces; log and skip.

**Monitoring**
- Use SendGrid **Activity Feed** and **Suppressions** (bounces, blocks, spam reports).
- Optionally log SendGrid `message_id` in `outreach_log.csv`.
- Test inbox placement on Gmail + Outlook before scaling.

**Code changes (optional)**
- Add `UNSUBSCRIBE_FOOTER` in `config.py` and append in `message_builder.build_message`.
- Add `List-Unsubscribe` header in `emailer.py` when you have a mailto or one-click URL.
- Add `MAX_EMAILS_PER_RUN` cap in config for daily safety.

### Status
Not implemented. Current setup: plain-text SendGrid, verified single sender, `SEND_DELAY_SECONDS=1.0`, no unsubscribe footer, no domain auth docs in repo.

---

## 4. SEO for outreach — opens, clicks, and landing page

### Reason
**SEO here means two things:** (1) **email optimization** — subject lines and preview text that get opened; (2) **web SEO** — a landing page that ranks and converts when prospects search or click through. Outreach performs better when subjects match what vet/pet businesses search for and when links point to focused, indexable pages.

### Idea

**Email-side (open & click optimization)**
- **Subject lines**: lead with relevance, not brand — e.g. `"Quick question about appointments at {company}"` vs `"Introducing VetApp"`.
- **Preview text**: add optional preheader line in templates or a `{preheader}` placeholder.
- **UTM parameters** on any link: `?utm_source=outreach&utm_medium=email&utm_campaign=vet_clinic_first`.
- **One canonical link** per email (demo or booking page) on your own HTTPS domain.

**Landing page SEO (VetApp site)**
- Dedicated pages per segment:
  - `/for-vet-clinics` — *vet clinic software*, *appointment reminders*
  - `/for-pet-shops` — *pet store management*
  - `/for-groomers` — *pet grooming booking*
- Each page: unique title tag, meta description, H1 with primary keyword, useful copy, FAQ schema where relevant.
- Fast mobile load, SSL, clear CTA above the fold.

**Pipeline integration**
- Add optional `{landing_url}` placeholder in `message_builder.py`, from `config.LANDING_URLS` keyed by classification.
- Document recommended subject/preview patterns in template comments or a `templates/README.md`.
- A/B test subjects on a small batch before full daily run.

### Status
Not implemented. Templates use generic subjects; no UTM links, preheader, or classification-specific landing URLs in config.

---

## 5. Confidence threshold tuning + test harness

### Reason
`NLP_CONFIDENCE_THRESHOLD` (default `0.6` in `.env`) controls when the zero-shot model's answer is trusted vs. falling back to keywords or `fallback_first.txt`. The wrong threshold causes misclassified outreach or too many generic fallback messages.

### Where the threshold applies

The threshold **only affects the zero-shot model path**. Unambiguous keyword hits always return confidence `1.0`.

```
Company Name
     │
     ▼
Keyword match (exactly 1 category?) ──yes──► label, conf=1.0
     │ no (0 or 2+ matches)
     ▼
Zero-shot model
     ├── score >= threshold ──► label, conf=score
     └── score < threshold ──► first keyword at 0.5, or "" at 0.0
```

| Confidence | Meaning | Template |
|------------|---------|----------|
| `1.0` | Unambiguous keyword | Category-specific |
| `0.6–0.99` | Model confident (default threshold) | Category-specific |
| `0.5` | Ambiguous keywords; model below threshold or unavailable | First keyword (may be wrong) |
| `0.0` | No match | `fallback_first.txt` |

### Idea
- Add `scripts/test_classifier_thresholds.py` to sweep thresholds `[0.4, 0.5, 0.6, 0.7, 0.8]` against sample company names.
- Log classification confidence in `outreach_log.csv` for ongoing monitoring.
- Tune against 20–50 manually labeled real company names from your sheet.

### Threshold guidance

| Threshold | Effect | When to use |
|-----------|--------|-------------|
| **0.4** | Trust model more; fewer fallback sends | Many generic names; okay with occasional wrong template |
| **0.5** | Balanced | Alternative if 0.6 feels too strict |
| **0.6** | **Current default** | Good starting point for production |
| **0.7** | Stricter; more keyword-fallback / unknown | Wrong template worse than generic fallback |
| **0.8** | Very strict | High cost of misclassification |

### Status
Partial. `NLP_CONFIDENCE_THRESHOLD` exists in `.env` / `config.py`; no test script or confidence logging in outreach log.

---

## 6. NLP feature toggles

### Reason
Email and WhatsApp have on/off flags (`EMAIL_ENABLED`, `WHATSAPP_ENABLED`). Classifier and sentiment always run when needed — no way to disable NLP for debugging or faster dry runs.

### Idea
Add to `config.py`:
```python
CLASSIFICATION_ENABLED = True
SENTIMENT_ENABLED = True
```
Guard in `main._ensure_classification` and the sentiment block in `process_row`.

### Status
Not implemented.

---

## 7. Move sentiment keywords to config

### Reason
Classifier keywords live in `config.CLASSIFICATION_KEYWORDS` (easy to tune). Sentiment fallback words (`_POSITIVE_WORDS`, `_NEGATIVE_WORDS`) are hardcoded in `sentiment.py` — inconsistent and harder to change without a code edit.

### Idea
Move word lists to `config.py` alongside classifier keywords.

### Status
Not implemented.

---

## 8. README / code sync

### Reason
README Configuration Knobs section references `APPOINTMENTS_ENABLED`, `APPOINTMENTS_FILE`, and `ACTION_REQUIRED_KEYWORDS`, but those do not exist in `config.py` yet.

### Idea
Implement appointments (item #1) or remove/strike-through appointments knobs from README until implemented.

### Status
Out of sync as of 2026-06-24.

---

## Recommended implementation order

1. **Avoid spam folder** — protect deliverability before scaling volume.
2. **Confidence test script** — validate threshold on real company names.
3. **Appointments table** — highest business value for lead capture.
4. **SEO / landing URLs** — improve opens and conversion on clicks.
5. **`Reason` column** — useful for CRM, lower urgency.
6. **NLP toggles + config cleanup + README sync** — quality-of-life for operators.

---

## Deliverability + SEO checklist (before scaling)

| Check | Spam avoidance | SEO / outreach |
|-------|----------------|----------------|
| Domain SPF/DKIM/DMARC | ✅ Required | — |
| Personalized subject (`{company}`) | ✅ Helps | ✅ Helps opens |
| Plain text, single link | ✅ Helps | Use UTM on link |
| Unsubscribe / opt-out line | ✅ Required | — |
| Warm send volume | ✅ Required | — |
| Segment landing pages | — | ✅ Required |
| Keyword-rich page titles | — | ✅ Required |
| Track clicks (UTM) | Monitor complaints | ✅ Required |
