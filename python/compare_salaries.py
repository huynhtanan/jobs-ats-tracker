"""Rank Ashby-hosted companies by top research/engineering salary bands.

Hits the public posting-api for each org, pulls every job with a yearly salary
band, groups by `department`, and prints the top three bands per org side-by-side.

  python python/compare_salaries.py openai notion linear perplexity vercel modal

With no args it uses a sane default list of AI-first companies on Ashby.

Requires curl_cffi (Ashby's edge checks TLS):

  pip install curl_cffi
"""
from __future__ import annotations

import statistics
import sys
from typing import Iterable

from fetch_ashby import fetch

DEFAULT_ORGS = [
    "openai",
    "notion",
    "linear",
    "perplexity",
    "vercel",
    "modal",
    "supabase",
    "replicate",
    "cursor",
]


def _yearly_bands(jobs: list[dict]) -> list[tuple[str, str, int, int, str]]:
    out = []
    for j in jobs:
        comp = j.get("compensation") or {}
        for tier in comp.get("compensationTiers", []):
            for c in tier.get("components", []):
                if c.get("compensationType") != "Salary":
                    continue
                if c.get("interval") != "1 YEAR":
                    continue
                if c.get("maxValue") is None:
                    continue
                dept = j.get("department") or "-"
                out.append((j["title"], dept, c["minValue"], c["maxValue"], c["currencyCode"]))
    return out


def _summarise(org: str) -> dict:
    jobs = fetch(org, include_compensation=True)
    bands = _yearly_bands(jobs)
    maxes = [hi for _, _, _, hi, _ in bands]
    return {
        "org": org,
        "total_roles": len(jobs),
        "with_salary": len(bands),
        "median_max": int(statistics.median(maxes)) if maxes else None,
        "top3": sorted(bands, key=lambda b: -b[3])[:3],
    }


def _fmt_band(b: tuple) -> str:
    title, dept, lo, hi, cur = b
    return f"${lo:>7,} - ${hi:>7,} {cur}  [{dept:<28}]  {title}"


def main(orgs: Iterable[str]) -> None:
    orgs = list(orgs) or DEFAULT_ORGS
    print(f"{'org':<14} {'open':>6} {'w/salary':>9} {'median max':>11}")
    print("-" * 46)
    summaries = []
    for org in orgs:
        try:
            s = _summarise(org)
        except Exception as exc:  # noqa: BLE001
            print(f"{org:<14} ERR {exc}")
            continue
        med = f"${s['median_max']:,}" if s["median_max"] else "-"
        print(f"{org:<14} {s['total_roles']:>6} {s['with_salary']:>9} {med:>11}")
        summaries.append(s)

    print()
    print("Top 3 bands per org (sorted by max):")
    for s in summaries:
        if not s["top3"]:
            continue
        print(f"\n  {s['org']}")
        for b in s["top3"]:
            print(f"    {_fmt_band(b)}")


if __name__ == "__main__":
    main(sys.argv[1:])
