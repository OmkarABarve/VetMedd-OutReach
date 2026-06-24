"""
main.py - Orchestrator for the VetApp outreach pipeline.

Flow per run:
    load contacts -> for each row:
        GUARD 1: Don't Message == True            -> skip (skipped_flag)
        fill Classification if empty (classifier)
        decide scenario (first / reminder / engaged)
        run sentiment on Responses (engaged only)
        build message
        GUARD 2: pick a channel (email preferred; WhatsApp only if enabled)
            no channel available                  -> skip (skipped_no_channel /
                                                          skipped_whatsapp_disabled)
        send -> on success: increment Times Communicated + save atomically
             -> on failure: log failed (no increment)
        log every action

Run modes (config.RUN_MODE):
    "once"  -> single pass then exit (use with cron / Windows Task Scheduler)
    "daily" -> stay alive, run every day at config.DAILY_RUN_TIME (schedule lib)
"""

import time

import config
import classifier
import loader
import message_builder
import sentiment
import updater
from emailer import send_email
from whatsapp import send_whatsapp


def _ensure_classification(row, df, row_index) -> str:
    """Fill Classification in-place if empty. Returns the (possibly new) value."""
    classification = str(row.get("Classification", "")).strip().lower()
    if classification:
        return classification

    inferred, confidence = classifier.classify(row.get("Company Name", ""))
    if inferred:
        df.at[row_index, "Classification"] = inferred
        print(f"  classified '{row['Company Name']}' as '{inferred}' (conf={confidence:.2f})")
        return inferred

    print(f"  could not classify '{row['Company Name']}' -> using fallback template")
    return ""


def _select_channel(row):
    """Decide which channel to use. Returns (channel, recipient, skip_reason).

    channel is 'email' | 'whatsapp' | None. When None, skip_reason explains why.
    """
    email = str(row.get("Email ID", "")).strip()
    whatsapp_number = str(row.get("WhatsApp Number", "")).strip()

    # Prefer email.
    if config.EMAIL_ENABLED and email:
        return "email", email, ""

    # Fall back to WhatsApp only if the feature flag is on.
    if whatsapp_number:
        if config.WHATSAPP_ENABLED:
            return "whatsapp", whatsapp_number, ""
        # Has a number but WhatsApp is off for now: make the reason explicit so a
        # future re-run (after enabling the flag) will pick these up.
        return None, "", "skipped_whatsapp_disabled"

    return None, "", "skipped_no_channel"


def process_row(df, row_index, path) -> str:
    """Process a single contact row. Returns the final status string."""
    row = df.loc[row_index]
    company = row.get("Company Name", "")
    classification = str(row.get("Classification", "")).strip().lower()

    # --- GUARD 1: Don't Message --------------------------------------------
    if bool(row.get("Don't Message", False)):
        updater.log_action(company, classification, "-", "-", "skipped_flag",
                            "Don't Message = True")
        print(f"[SKIP] {company}: Don't Message flag set")
        return "skipped_flag"

    # --- Classification (fill if empty) ------------------------------------
    classification = _ensure_classification(row, df, row_index)
    row = df.loc[row_index]  # refresh after potential update

    # --- Decision tree -----------------------------------------------------
    times = int(row.get("Times Communicated", 0))
    responses = row.get("Responses", "")
    scenario = message_builder.decide_scenario(times, responses)

    # --- Sentiment (engaged scenario only) ---------------------------------
    tone = "neutral"
    if scenario == "engaged" and loader.has_response_text(responses):
        tone = sentiment.detect_sentiment(responses)

    # --- Build message -----------------------------------------------------
    msg = message_builder.build_message(row, scenario, tone)

    # --- GUARD 2: channel selection ----------------------------------------
    channel, recipient, skip_reason = _select_channel(row)
    if channel is None:
        updater.log_action(company, classification, "-", scenario, skip_reason,
                            "no usable channel")
        print(f"[SKIP] {company}: {skip_reason}")
        return skip_reason

    # --- Send --------------------------------------------------------------
    if channel == "email":
        result = send_email(recipient, msg["subject"], msg["body"])
    else:
        result = send_whatsapp(recipient, f"{msg['subject']}\n\n{msg['body']}")

    if not result.success:
        updater.log_action(company, classification, channel, scenario, "failed", result.note)
        print(f"[FAIL] {company} via {channel}: {result.note}")
        return "failed"

    # --- Success: increment + persist atomically ---------------------------
    try:
        updater.increment_and_save(df, row_index, path)
    except Exception as exc:
        # Send succeeded but write failed (e.g. file open in Excel). Log clearly.
        updater.log_action(company, classification, channel, scenario, "sent_no_save",
                           f"send ok but write-back failed: {exc}")
        print(f"[WARN] {company}: sent but could not save count: {exc}")
        return "sent_no_save"

    updater.log_action(company, classification, channel, scenario, "sent", result.note)
    print(f"[SENT] {company} via {channel} ({scenario}/{msg['template']})")
    return "sent"


def run_pipeline() -> None:
    """Single full pass over the contact sheet."""
    print("=" * 60)
    print("VetApp outreach run starting")
    print("=" * 60)

    df, path = loader.load_contacts()
    print(f"Loaded {len(df)} contacts from {path.name}")

    for row_index in df.index:
        process_row(df, row_index, path)
        if config.SEND_DELAY_SECONDS:
            time.sleep(config.SEND_DELAY_SECONDS)

    print("Run complete. See logs/outreach_log.csv for details.")


def main() -> None:
    if config.RUN_MODE == "daily":
        import schedule

        schedule.every().day.at(config.DAILY_RUN_TIME).do(run_pipeline)
        print(f"Daily mode: will run every day at {config.DAILY_RUN_TIME}. Ctrl+C to stop.")
        # Run once immediately on startup, then wait for the daily trigger.
        run_pipeline()
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        run_pipeline()


if __name__ == "__main__":
    main()
