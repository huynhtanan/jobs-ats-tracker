"""Fetch every open job at a company that uses Greenhouse as its ATS.

Public endpoint, no auth, no User-Agent gymnastics:
  https://boards-api.greenhouse.io/v1/boards/<slug>/jobs

Known slugs (as of 2026-10): anthropic, stripe, airbnb, coinbase, instacart,
brex, plaid, ramp, scale, discord, datadog, pinterest, shopify.

Discovery: look at the "Apply" button URL on any job post.
"""
from __future__ import annotations

import json
import urllib.request

BOARDS_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def fetch(slug: str, with_content: bool = False) -> list[dict]:
    url = BOARDS_API.format(slug=slug)
    if with_content:
        url += "?content=true"
    data = json.loads(urllib.request.urlopen(url, timeout=20).read())
    return data["jobs"]


def main() -> None:
    slug = "anthropic"
    jobs = fetch(slug)
    research = [j for j in jobs if "Research" in j["title"]]
    print(f"{slug}: {len(jobs)} open roles, {len(research)} Research-titled.\n")
    for j in research[:10]:
        print(f"  {j['title']}  |  {j['location']['name']}  |  {j['absolute_url']}")


if __name__ == "__main__":
    main()
