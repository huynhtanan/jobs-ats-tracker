# Jobs ATS tracker (Python)

Pull every open job at any company that uses **Greenhouse** or **Ashby** as its applicant tracking system. Both platforms publish a public JSON endpoint next to their React careers page — no auth, no scraping, no User-Agent tricks (except Ashby's TLS fingerprint check, which `curl_cffi` fixes).

Companies covered out of the box include **Anthropic (675 open roles)**, **OpenAI (808, 80 % with salary bands disclosed)**, **Stripe (731)**, **Airbnb (182)**, plus Notion, Linear, Perplexity, Vercel, Modal, Supabase, Replicate, Coinbase, Instacart, Datadog, and anywhere else running on those two ATS.

Code also exposes two ready-made Apify scrapers that wrap both endpoints with a normalised schema, salary filtering, and a Claude Desktop / Cursor MCP tool interface. $0.002 per job, with free monthly Apify credit (~$5) on new accounts.

- Greenhouse: [apify.com/zet46/greenhouse-jobs-scraper](https://apify.com/zet46/greenhouse-jobs-scraper)
- Ashby: [apify.com/zet46/ashby-jobs-scraper](https://apify.com/zet46/ashby-jobs-scraper)

## Setup

```bash
pip install curl_cffi
```

That is the only non-stdlib dependency. `fetch_greenhouse.py` uses `urllib`.

## 1. Every open role at Anthropic ([python/fetch_greenhouse.py](python/fetch_greenhouse.py))

```bash
python python/fetch_greenhouse.py
```

```
anthropic: 675 open roles, 64 Research-titled.

  Applied AI, Research Engineer                                        | San Francisco, CA | New York City, NY
  Engineering Manager, Research Data Platform                          | San Francisco, CA | New York City, NY
  [Expression of Interest] Research Engineer / Scientist, Alignment    | London, UK
  Machine Learning Infrastructure Engineer, Safeguards Research        | San Francisco, CA | New York City, NY
  ...
```

Change `slug = "anthropic"` to `"stripe"`, `"airbnb"`, `"coinbase"`, `"brex"`, etc. The endpoint is `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs`.

Add `?content=true` to also pull the full HTML job description for every row.

## 2. OpenAI research-engineer salary bands ([python/fetch_ashby.py](python/fetch_ashby.py))

```bash
python python/fetch_ashby.py
```

```
openai: 808 open roles, 643 with salary disclosed.

  Top Research Engineer bands at openai:
    Research Scientist / Research Engineer - Foundations, Search       | $380,000 - $850,000 USD
    Research Engineer, Retrieval & Search, Applied Engineering         | $293,000 - $585,000 USD
    Research Engineer / Research Scientist- Personal AGI (Post Training)| $380,000 - $500,000 USD
    ...
```

Change `org = "openai"` to `"notion"`, `"linear"`, `"perplexity"`, `"vercel"`, `"modal"`, etc. The endpoint is `https://api.ashbyhq.com/posting-api/job-board/<org>?includeCompensation=true`.

## 3. Rank companies by top salary band ([python/compare_salaries.py](python/compare_salaries.py))

```bash
python python/compare_salaries.py openai notion linear perplexity vercel modal
```

Hits every org in parallel, groups by `department`, and prints a side-by-side table. With no args it uses a sane default list of AI-first companies on Ashby.

```
org              open  w/salary  median max
----------------------------------------------
openai            808       653    $365,000
notion            135         0           -
linear             29         0           -

Top 3 bands per org (sorted by max):

  openai
    $380,000 - $850,000 USD  [Research                    ]  Research Scientist / Research Engineer - Foundations, Search
    $300,000 - $600,000 USD  [Research                    ]  Researcher, Training
    $293,000 - $585,000 USD  [Applied AI                  ]  Research Engineer, Retrieval & Search, Applied Engineering
```

Notion and Linear expose no salary data via Ashby; that is a real property of their boards, not a bug in the script.

## 4. "New jobs since last poll" alert ([python/track_new_jobs.py](python/track_new_jobs.py))

```bash
python python/track_new_jobs.py anthropic openai
```

Writes a tiny SQLite file next to the script and, on every subsequent run, only prints jobs that have appeared since. First run on Anthropic prints all 675; the next day it prints roughly 5 to 15 new ones.

```
[anthropic] 675 open, 0 new since last poll.
[openai] 808 open, 0 new since last poll.
```

Cron it or run from a GitHub Action every morning. Default polls Anthropic and OpenAI.

## 5. Zero-infra daily cron: GitHub Actions + Slack ([python/alert_slack.py](python/alert_slack.py))

Scheduling the diff in GitHub's free compute tier takes about 25 lines of YAML.
`alert_slack.py` reads the same SQLite file `track_new_jobs.py` writes, filters
to rows seen in the last N minutes, and POSTs a single bullet-list message to a
Slack incoming webhook. Without `SLACK_WEBHOOK_URL` it no-ops with a log line,
so wiring it in before you have a webhook ready is safe.

Copy this to `.github/workflows/daily-check.yml` in your fork:

```yaml
name: daily-ats-check

on:
  schedule:
    - cron: "15 7 * * *"  # 07:15 UTC
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install curl_cffi

      - name: Restore seen-jobs cache
        uses: actions/cache@v4
        with:
          path: python/seen_jobs.sqlite
          key: ats-seen-${{ github.run_id }}
          restore-keys: |
            ats-seen-

      - name: Poll Greenhouse + Ashby boards
        working-directory: python
        run: |
          python track_new_jobs.py \
            anthropic openai stripe airbnb notion linear perplexity vercel

      - name: Post new jobs to Slack
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        working-directory: python
        run: python alert_slack.py --window 1440
```

Add the webhook under *Repo settings → Secrets and variables → Actions* as
`SLACK_WEBHOOK_URL`. The `actions/cache` step persists `seen_jobs.sqlite`
between runs, so day two onwards you only hear about *new* postings.

Approximate daily output in a quiet week:

```
*5 new jobs in the last 1440 min*
• Research Engineer, Alignment — `anthropic` · London, UK
• Member of Technical Staff, Scaling — `openai` · San Francisco, CA
• Infrastructure Engineer, Payments — `stripe` · Remote US
• Senior ML Engineer, Pricing — `airbnb` · San Francisco, CA
• Developer Advocate — `vercel` · Remote
```

To run locally without Slack, point at a webhook-less environment:

```bash
python python/track_new_jobs.py anthropic openai
python python/alert_slack.py --window 1440   # prints "SLACK_WEBHOOK_URL not set"
```

## 6. Same thing as an MCP tool in Claude Desktop

Both Apify actors are exposed through Apify's hosted MCP server at `mcp.apify.com` with zero extra config. Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com",
      "headers": { "Authorization": "Bearer apify_api_..." }
    }
  }
}
```

Restart Claude Desktop and ask:

> *"Fetch every open Research Engineer role at Anthropic with a salary band of at least $400K, grouped by location."*

Claude discovers `zet46/greenhouse-jobs-scraper` and `zet46/ashby-jobs-scraper` through `search-actors` and calls them. You get back a table.

For Claude Code it is one line:

```bash
claude mcp add apify --transport http https://mcp.apify.com \
  --header "Authorization: Bearer apify_api_..."
```

## Related reading

Longer write-up on how both endpoints work: [dev.to/huynhtanan](https://dev.to/huynhtanan).

## License

MIT.
