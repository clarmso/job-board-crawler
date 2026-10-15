# How it works

## Requirements

* **Python 3.12+** (see [`crawl.yml`](.github/workflows/crawl.yml) for the exact version used in CI).
* **Repository secrets** (set under Settings → Secrets and variables → Actions):
  * `COPILOT_PAT` — a GitHub Personal Access Token (not the default Actions `GITHUB_TOKEN`) with Copilot access, used to authenticate the `copilot` CLI headlessly in CI (see [Automate Copilot CLI with GitHub Actions](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/automate-with-actions)). Generate a PAT on your account, then add it as this secret. Consumed by `scripts/ai_canada.py` for AI Canada-badge classification. If unset, the AI classification step is skipped and jobs keep their regex-based Canada-badge result from `_is_canada_job` instead.
  * `MASTODON_INSTANCE_URL`, `MASTODON_ACCESS_TOKEN` — for posting the daily digest to Mastodon.
  * `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` — for posting the daily digest to Bluesky.
  * `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` — OAuth 1.0a credentials (Consumer Key/Secret + Access Token/Secret, from the X Developer Portal's "Keys & Tokens" → OAuth 1.0 section) for posting the daily digest to X/Twitter.

## Pipeline

1. **Crawl** (`crawl.py`, daily via [`crawl.yml`](.github/workflows/crawl.yml)) — fetches current job postings for every company in [`companies.csv`](companies.csv) from its ATS, one JSON file per job under `data/` (git history is the source of truth for when a job was first/last seen). [`TODO-companies.csv`](TODO-companies.csv) holds candidate companies that haven't been vetted/added to `companies.csv` yet — they are not crawled.
2. **Detect new jobs** (`scripts/generate_new_jobs.py`) — compares today's postings to prior crawls to find jobs that appeared in the last 2 days, then (optionally, via an AI call) classifies whether each job is Canada-based using the job title, location field, and any platform-specific metadata/custom fields as signal. Ambiguous cases default to **no** Canada badge.
3. **Publish** — writes `docs/new_jobs.json` and `docs/companies.json`/`companies.html` (`scripts/generate_companies_page.py`), which [`pages.yml`](.github/workflows/pages.yml) deploys to GitHub Pages as the live site.
4. **Social digest** (`scripts/post_social.py`, after the Pages deploy succeeds) — posts a short digest of the day's new jobs to Mastodon and Bluesky (and soon X/Twitter), linking back to the site. A posted-jobs record in `state/` prevents duplicate posts.
