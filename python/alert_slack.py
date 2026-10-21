"""Post a summary of newly-seen jobs to a Slack webhook.

Reads ``python/seen_jobs.sqlite`` that ``track_new_jobs.py`` writes. For every
job that was first seen in the last ``--window`` minutes, prints one bullet
line and posts the batch as a single Slack message.

    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ \
    python python/alert_slack.py --window 1440 --min-count 1

With no SLACK_WEBHOOK_URL in the environment the script no-ops with a short
log line, so it is safe to wire into a GitHub Actions job that may or may not
have the secret set yet.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

DB = Path(__file__).with_name("seen_jobs.sqlite")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--window",
        type=int,
        default=1440,
        help="Minutes to look back for freshly-seen jobs (default: 1440 = 24h)",
    )
    ap.add_argument(
        "--min-count",
        type=int,
        default=1,
        help="Skip the Slack post if fewer new jobs than this (default: 1)",
    )
    ap.add_argument(
        "--max-rows",
        type=int,
        default=30,
        help="Hard cap on how many jobs to list in the message (default: 30)",
    )
    args = ap.parse_args()

    url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        print("SLACK_WEBHOOK_URL not set; nothing to do.")
        return 0
    if not DB.exists():
        print(f"{DB} not found; run track_new_jobs.py first.")
        return 0

    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT slug, title, location, url FROM seen "
        "WHERE seen_at >= datetime('now', ?) "
        "ORDER BY slug, title",
        (f"-{args.window} minutes",),
    ).fetchall()
    if len(rows) < args.min_count:
        print(
            f"Only {len(rows)} new rows in the last {args.window} min; "
            f"threshold is {args.min_count}. Skipping Slack."
        )
        return 0

    lines = [f"*{len(rows)} new jobs in the last {args.window} min*"]
    for slug, title, loc, link in rows[: args.max_rows]:
        lines.append(f"• <{link}|{title}> — `{slug}` · {loc or '—'}")
    if len(rows) > args.max_rows:
        lines.append(f"...and {len(rows) - args.max_rows} more.")

    payload = {"text": "\n".join(lines)}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"Slack: HTTP {resp.status} ({len(rows)} jobs posted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
