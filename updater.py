"""
updater.py - Safe write-back of the contacts sheet + append-only action logging.

Two responsibilities:

1) increment_and_save(): after a CONFIRMED successful send, bump that row's
   "Times Communicated" by 1 and persist the WHOLE DataFrame atomically:
       - write to a temp file in the same folder
       - os.replace(tmp, original)  -> atomic swap on the same filesystem
   This guarantees the real file is never left half-written, even if the process
   crashes mid-run.

2) log_action(): append a single row to logs/outreach_log.csv. Append-only with a
   header written once, so we never rewrite the whole log file.
"""

import csv
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

import config


LOG_HEADER = [
    "timestamp",
    "company_name",
    "classification",
    "channel",
    "scenario",
    "status",
    "notes",
]


def _write_atomic(df: pd.DataFrame, path: Path) -> None:
    """Write df to `path` atomically via a temp file + os.replace."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    if path.suffix.lower() == ".xlsx":
        df.to_excel(tmp, index=False, engine="openpyxl")
    else:
        df.to_csv(tmp, index=False)
    # Atomic on the same filesystem; replaces the original in one step.
    os.replace(tmp, path)


def increment_and_save(df: pd.DataFrame, row_index, path: Path) -> pd.DataFrame:
    """Increment Times Communicated for row_index and persist the full sheet.

    Returns the (mutated) DataFrame so the caller keeps an up-to-date copy.
    Raises on write failure (e.g. the .xlsx is open/locked in Excel) so the
    caller can log it as a failure instead of silently losing the increment.
    """
    df.at[row_index, "Times Communicated"] = (
        int(df.at[row_index, "Times Communicated"]) + 1
    )
    _write_atomic(df, path)
    return df


def log_action(
    company_name: str,
    classification: str,
    channel: str,
    scenario: str,
    status: str,
    notes: str = "",
) -> None:
    """Append one action row to logs/outreach_log.csv (creates header if new)."""
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = config.LOG_FILE.exists()

    with open(config.LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(LOG_HEADER)
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                company_name,
                classification,
                channel,
                scenario,
                status,
                notes,
            ]
        )
