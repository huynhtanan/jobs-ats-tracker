"""Fetch every open job at a company that uses Ashby as its ATS.

Public endpoint:
  https://api.ashbyhq.com/posting-api/job-board/<org>?includeCompensation=true

Known orgs: openai, notion, linear, perplexity, vercel, modal, supabase,
replicate, cursor, pika, braintrust, stytch.

Catch: Ashby's edge is behind Cloudflare with TLS fingerprinting. Plain
`requests` or `urllib` returns 403. Fix is `curl_cffi`, which impersonates
a real Chrome TLS handshake.

  pip install curl_cffi
"""
from __future__ import annotations

from curl_cffi import requests as cc

POSTING_API = "https://api.ashbyhq.com/posting-api/job-board/{org}"


def fetch(org: str, include_compensation: bool = True) -> list[dict]:
    params = {"includeCompensation": "true"} if include_compensation else {}
    r = cc.get(
        POSTING_API.format(org=org),
        params=params,
        impersonate="chrome124",
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["jobs"]


def _yearly_salary(job: dict) -> tuple[int | None, int | None, str | None]:
    comp = job.get("compensation") or {}
    for tier in comp.get("compensationTiers", []):
        for c in tier.get("components", []):
            if c["compensationType"] == "Salary" and c["interval"] == "1 YEAR":
                return c["minValue"], c["maxValue"], c["currencyCode"]
    return None, None, None


def main() -> None:
    org = "openai"
    jobs = fetch(org)
    with_salary = [j for j in jobs if _yearly_salary(j)[1] is not None]
    print(f"{org}: {len(jobs)} open roles, {len(with_salary)} with salary disclosed.\n")

    research = [j for j in jobs if "Research Engineer" in j["title"]]
    research.sort(key=lambda j: -(_yearly_salary(j)[1] or 0))
    print(f"  Top Research Engineer bands at {org}:")
    for j in research[:5]:
        lo, hi, cur = _yearly_salary(j)
        if hi:
            band = f"${lo:,} - ${hi:,} {cur}"
        else:
            band = "no band listed"
        print(f"    {j['title']}  |  {band}")


if __name__ == "__main__":
    main()
