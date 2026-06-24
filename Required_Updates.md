# Required Updates — VetApp GTM Outreach Pipeline

Living checklist of improvements discussed but not yet fully implemented. Each item includes **Reason** (why), **Idea** (what to build), and **Status**.

Last reviewed: 2026-06-24

---

## Summary

| # | Update | Priority | Status |
|---|--------|----------|--------|
| 1 | Keyword-first classifier | High | ✅ Done |
| 2 | Appointments table (positive / action-required leads) | High | ❌ Not implemented (README ahead of code) |
| 3 | `Reason` column for rejections | Medium | ❌ Not implemented |
| 4 | NLP feature toggles | Low | ❌ Not implemented |
| 5 | Lift hardcoded sentiment keywords to `config.py` | Low | ❌ Not implemented |
| 6 | Confidence threshold tuning + test harness | Medium | ⚠️ Partial (threshold exists; no test script) |
| 7 | Sync README with actual code | Low | ⚠️ README references appointments that don't exist yet |

---

## 1. Keyword-first classifier ✅ Done

### Reason
Most company names are self-describing (`Dr. Paws Veterinary Clinic`, `Happy Pets Store`). Running a ~90MB zero-shot model on every row is slow, non-deterministic, and unnecessary when a cheap substring check already knows the answer.

### Idea
1. Run `config.CLASSIFICATION_KEYWORDS` first.
2. If **exactly one** category matches → use it at confidence `1.0` (model never loads).
3. If **zero or multiple** matches → fall back to zero-shot model.
4. If model score < threshold or model unavailable → first keyword match at `0.5`, else `""` (fallback template).

### Status
Implemented in `classifier.py`. No further action unless you want a config knob like `CLASSIFY_KEYWORDS_FIRST = True`.

---

## 2. Appointments table — positive / action-required leads

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

## 3. `Reason` column — capture rejection explanations

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

## 4. NLP feature toggles

### Reason
Email and WhatsApp already have clean on/off flags (`EMAIL_ENABLED`, `WHATSAPP_ENABLED`). Classifier and sentiment always run when needed — no way to disable NLP for debugging or faster dry runs.

### Idea
Add to `config.py`:
```python
CLASSIFICATION_ENABLED = True
SENTIMENT_ENABLED = True