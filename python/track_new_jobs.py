"""Poll Greenhouse + Ashby boards once a day, diff on job id, print new postings.

Keeps state in a small SQLite file so each run only alerts on jobs it has
never seen before.

  python python/track_new_jobs.py anthropic openai
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from fetch_ashby import fetch as fetch_ashby
from fetch_greenhouse import fetch as fetch_greenhouse

DB_PATH = Path(__file__).with_name("seen_jobs.sqlite")

ASHBY_ORGS = {"openai", "notion", "linear", "perplexity", "vercel", "modal",
              "supabase", "replicate", "cursor"}


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            source   TEXT NOT NULL,
            slug     TEXT NOT NULL,
            job_id   TEXT NOT NULL,
            title    TEXT,
            location TEXT,
            url      TEXT,
            seen_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (source, slug, job_id)
        )
    """)
    return c


def _poll_one(slug: str) -> list[dict]:
    if slug in ASHBY_ORGS:
        return [{
            "source": "ashby",
            "slug": slug,
            "job_id": j["id"],
            "title": j["title"],
            "location": j.get("location") or "",
            "url": j["jobUrl"],
        } for j in fetch_ashby(slug, include_compensation=False)]
    return [{
        "source": "greenhouse",
        "slug": slug,
        "job_id": str(j["id"]),
        "title": j["title"],
        "location": (j.get("location") or {}).get("name", ""),
        "url": j["absolute_url"],
    } for j in fetch_greenhouse(slug)]


def main(slugs: list[str]) -> None:
    if not slugs:
        slugs = ["anthropic", "openai"]
    con = _conn()
    for slug in slugs:
        rows = _poll_one(slug)
        new = []
        for r in rows:
            cur = con.execute(
                "SELECT 1 FROM seen WHERE source=? AND slug=? AND job_id=?",
                (r["source"], r["slug"], r["job_id"]),
            ).fetchone()
            if cur is None:
                new.append(r)
                con.execute(
                    "INSERT INTO seen (source, slug, job_id, title, location, url) VALUES (?,?,?,?,?,?)",
                    (r["source"], r["slug"], r["job_id"], r["title"], r["location"], r["url"]),
                )
        con.commit()
        print(f"[{slug}] {len(rows)} open, {len(new)} new since last poll.")
        for r in new[:15]:
            print(f"  + {r['title']}  |  {r['location']}  |  {r['url']}")


if __name__ == "__main__":
    main(sys.argv[1:])
