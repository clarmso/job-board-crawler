#!/usr/bin/env python3
"""
Generate docs/new_jobs.json — a manifest of jobs newly added within the past
LOOKBACK_HOURS, grouped by company, for display on the GitHub Pages site.

crawl.yml can run more than once a day, so "new" is computed as a rolling
time window over git history (every commit that first created a data/*.json
file within the window), merged with any not-yet-committed additions from
the current run. This avoids missing jobs from earlier same-day runs and
avoids double-counting a job across multiple runs.

Must run AFTER `crawl.py` but BEFORE the crawl output is committed, since it
also inspects the working tree for the current run's not-yet-committed
additions.
"""

import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

DATA_DIR = "data"
OUTPUT_PATH = os.path.join("docs", "new_jobs.json")
LOOKBACK_HOURS = 24


def _load_ats_by_slug(companies_csv="companies.csv"):
    ats_by_slug = {}
    with open(companies_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("slug") and row.get("ats"):
                ats_by_slug[row["slug"]] = row["ats"]
    return ats_by_slug


def _commits_since(hours):
    result = subprocess.run(
        ["git", "log", f"--since={hours}.hours.ago", "--pretty=format:%H", "--", DATA_DIR],
        capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _files_added_in_commit(commit):
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r",
         "--diff-filter=A", commit, "--", DATA_DIR],
        capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line.endswith(".json")]


def _added_data_files():
    """Return paths (relative to repo root) of files under data/ that were
    first created within the past LOOKBACK_HOURS, across however many crawl
    runs/commits happened in that window, plus any not-yet-committed
    additions from the run currently in progress."""
    added = set()

    for commit in _commits_since(LOOKBACK_HOURS):
        added.update(_files_added_in_commit(commit))

    # Not-yet-committed additions from this run (working tree vs last commit).
    result = subprocess.run(
        ["git", "diff", "--diff-filter=A", "--name-only", "--", DATA_DIR],
        capture_output=True, text=True, check=True,
    )
    added.update(line for line in result.stdout.splitlines() if line.endswith(".json"))

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", DATA_DIR],
        capture_output=True, text=True, check=True,
    )
    added.update(line for line in untracked.stdout.splitlines() if line.endswith(".json"))

    # Only keep files that still exist (job postings that have since been
    # removed shouldn't be advertised as "new").
    return sorted(path for path in added if os.path.exists(path))


def _extract(platform, job):
    """Return (title, url, company_name) normalized across ATS platforms."""
    if platform == "greenhouse":
        return job.get("title"), job.get("absolute_url"), job.get("company_name")
    if platform == "lever":
        return job.get("text"), job.get("hostedUrl"), None
    if platform == "ashby":
        return job.get("title"), job.get("jobUrl"), None
    if platform == "workable":
        return job.get("title"), job.get("url"), None
    if platform == "smartrecruiters":
        company = job.get("company", {})
        identifier = company.get("identifier")
        url = f"https://jobs.smartrecruiters.com/{identifier}/{job.get('id')}" if identifier else None
        return job.get("name"), url, company.get("name")
    if platform == "gem":
        return job.get("title"), job.get("absolute_url"), None
    if platform == "rippling":
        return job.get("name"), job.get("url"), job.get("companyName")
    return None, None, None


def _display_name(slug, extracted_name):
    if extracted_name:
        return extracted_name
    return slug.replace("-", " ").replace("_", " ").title()


def main():
    ats_by_slug = _load_ats_by_slug()
    added_files = _added_data_files()

    companies = {}  # slug -> {"name": str, "jobs": [...]}

    for path in added_files:
        parts = path.split(os.sep)
        if len(parts) < 3 or parts[0] != DATA_DIR:
            continue
        slug = parts[1]
        platform = ats_by_slug.get(slug)
        if not platform:
            continue

        try:
            with open(path) as f:
                job = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        title, url, name = _extract(platform, job)
        if not title or not url:
            continue

        entry = companies.setdefault(slug, {"name": _display_name(slug, name), "jobs": []})
        entry["jobs"].append({"title": title, "url": url})

    manifest = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_new_jobs": sum(len(c["jobs"]) for c in companies.values()),
        "companies": [
            {"slug": slug, "name": data["name"], "jobs": sorted(data["jobs"], key=lambda j: j["title"])}
            for slug, data in sorted(companies.items(), key=lambda kv: kv[1]["name"].lower())
        ],
    }

    os.makedirs("docs", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {OUTPUT_PATH}: {manifest['total_new_jobs']} new jobs across {len(manifest['companies'])} companies")


if __name__ == "__main__":
    sys.exit(main())
