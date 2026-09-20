#!/usr/bin/env python3
"""
Generate docs/index.html — a fully static page listing jobs newly added
within the past LOOKBACK_HOURS, grouped by company, for the GitHub Pages
site. Also writes docs/new_jobs.json as a raw data snapshot.

crawl.yml can run more than once a day, so "new" is computed as a rolling
time window over git history (every commit that first created a data/*.json
file within the window), merged with any not-yet-committed additions from
the current run. This avoids missing jobs from earlier same-day runs and
avoids double-counting a job across multiple runs.

Must run AFTER `crawl.py` but BEFORE the crawl output is committed, since it
also inspects the working tree for the current run's not-yet-committed
additions.
"""

import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone

DATA_DIR = "data"
LOOKBACK_HOURS = 24

_CA_REMOTE_RE = re.compile(r"\bca\s*[-\u2013\u2014]?\s*remote\b|\bremote\s*[-\u2013\u2014]?\s*ca\b")

# Canadian province/territory postal abbreviations, as they appear after a
# city name in free-text location strings (e.g. "Kitchener-Waterloo, ON").
# Deliberately case-sensitive and requires a preceding comma: matching case-
# insensitively would false-positive on the common English word "on".
_CA_PROVINCE_RE = re.compile(
    r",\s*(ON|BC|QC|AB|MB|SK|NS|NB|PE|NL|YT|NT|NU)\b"
)


def _mentions_canada_explicit(*texts):
    """Keyword match for locations that explicitly reference Canada.

    Matches "Canada" itself, a Canadian province/territory abbreviation
    following a city name (e.g. "Kitchener-Waterloo, ON; Toronto, ON"), and
    the "CA Remote" / "Remote - CA" shorthand some companies use.

    A bare "CA" token on its own is deliberately NOT treated as Canada:
    that's ambiguous with the US postal abbreviation for California, which
    shows up constantly in greenhouse/gem/rippling location strings (e.g.
    "San Mateo, CA"). Only "CA" directly adjacent to "Remote" is matched,
    since that combination is how some ATS postings abbreviate
    "Canada Remote".
    """
    raw = " ".join(str(t) for t in texts if t)
    if not raw:
        return False
    if _CA_PROVINCE_RE.search(raw):
        return True
    if "canada" in raw.lower():
        return True
    return bool(_CA_REMOTE_RE.search(raw.lower()))


def _mentions_canada_broad(*texts):
    """Keyword match for broader regions a Canada-based candidate could
    reasonably apply under ("Global", "North America", "Americas"), but
    which aren't themselves an explicit Canada reference. When a posting
    with one of these is *also* remote, it's remote worldwide/regionally —
    not Canada-specific — so callers should not tag it as Canada in that
    case (see _is_canada_job).
    """
    raw = " ".join(str(t) for t in texts if t)
    if not raw:
        return False
    combined = raw.lower()
    return any(keyword in combined for keyword in ("global", "north america", "americas"))


def _mentions_canada(*texts):
    """Combined explicit-or-broad match, for callers that don't need to
    distinguish the two tiers (e.g. company-level "could a Canada-based
    candidate apply here at all" eligibility)."""
    return _mentions_canada_explicit(*texts) or _mentions_canada_broad(*texts)


def _is_canada_job(platform, job, is_remote=False):
    """Best-effort: should this specific opening be tagged Canada?

    An explicit Canada reference (city, province, "Canada", "Canada Remote")
    always counts. A broader regional reference ("Global", "North America",
    "Americas") only counts when the posting is *not* remote — once it's
    also remote, it reads as remote-worldwide/regional rather than
    Canada-specific, so it should get the Remote tag instead, not Canada.

    Kept in sync with generate_companies_page.py's _is_canada_job.
    """
    if platform == "greenhouse":
        texts = [(job.get("location") or {}).get("name")]
        return _mentions_canada_explicit(*texts) or (
            _mentions_canada_broad(*texts) and not is_remote
        )

    if platform == "lever":
        if str(job.get("country") or "").strip().lower() == "ca":
            return True
        categories = job.get("categories") or {}
        texts = [categories.get("location"), *(categories.get("allLocations") or [])]
        return _mentions_canada_explicit(*texts) or (
            _mentions_canada_broad(*texts) and not is_remote
        )

    if platform == "ashby":
        address = ((job.get("address") or {}).get("postalAddress") or {})
        texts = [address.get("addressCountry"), job.get("location")]
        for secondary in job.get("secondaryLocations") or []:
            secondary_address = ((secondary.get("address") or {}).get("postalAddress") or {})
            texts.extend([secondary.get("location"), secondary_address.get("addressCountry")])
        return _mentions_canada_explicit(*texts) or (
            _mentions_canada_broad(*texts) and not is_remote
        )

    if platform == "workable":
        if str(job.get("country") or "").strip().lower() == "canada":
            return True
        for loc in job.get("locations") or []:
            if str(loc.get("country") or "").strip().lower() == "canada" or str(loc.get("countryCode") or "").strip().lower() == "ca":
                return True
        location_texts = [job.get("country"), job.get("city"), job.get("state")]
        for loc in job.get("locations") or []:
            location_texts.extend([loc.get("country"), loc.get("city"), loc.get("region")])
        return _mentions_canada_explicit(*location_texts) or (
            _mentions_canada_broad(*location_texts) and not is_remote
        )

    if platform == "smartrecruiters":
        loc = job.get("location") or {}
        if str(loc.get("country") or "").strip().lower() == "ca":
            return True
        texts = [loc.get("fullLocation"), loc.get("city")]
        return _mentions_canada_explicit(*texts) or (
            _mentions_canada_broad(*texts) and not is_remote
        )

    if platform == "gem":
        texts = [(job.get("location") or {}).get("name")]
        return _mentions_canada_explicit(*texts) or (
            _mentions_canada_broad(*texts) and not is_remote
        )

    if platform == "rippling":
        texts = list(job.get("workLocations") or [])
        return _mentions_canada_explicit(*texts) or (
            _mentions_canada_broad(*texts) and not is_remote
        )

    return False


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


def _mode_from_text(text):
    """Best-effort guess of workplace mode from a free-text location string."""
    if not text:
        return ""
    lowered = text.lower()
    if "remote" in lowered:
        return "Remote"
    if "hybrid" in lowered:
        return "Hybrid"
    return "On-site"


def _normalize_mode(raw):
    """Normalize an ATS-provided workplace-type value to Remote/Hybrid/On-site."""
    if not raw:
        return ""
    lowered = str(raw).lower()
    if "remote" in lowered:
        return "Remote"
    if "hybrid" in lowered:
        return "Hybrid"
    if lowered in ("onsite", "on-site", "office"):
        return "On-site"
    return str(raw).title()


def _extract(platform, job):
    """Return (title, url, company_name, location, mode) normalized across ATS platforms.

    `location` is a human-readable string and `mode` is one of
    "Remote" / "Hybrid" / "On-site" (or "" when unknown).
    """
    if platform == "greenhouse":
        location = (job.get("location") or {}).get("name", "")
        return (
            job.get("title"), job.get("absolute_url"), job.get("company_name"),
            location, _mode_from_text(location),
        )
    if platform == "lever":
        categories = job.get("categories") or {}
        location = categories.get("location") or ", ".join(categories.get("allLocations") or [])
        mode = _normalize_mode(job.get("workplaceType")) or _mode_from_text(location)
        return job.get("text"), job.get("hostedUrl"), None, location, mode
    if platform == "ashby":
        location = job.get("location", "")
        mode = _normalize_mode(job.get("workplaceType")) or _mode_from_text(location)
        return job.get("title"), job.get("jobUrl"), None, location, mode
    if platform == "workable":
        location = ", ".join(part for part in (job.get("city"), job.get("state"), job.get("country")) if part)
        mode = "Remote" if job.get("telecommuting") else _mode_from_text(location) or "On-site"
        return job.get("title"), job.get("url"), None, location, mode
    if platform == "smartrecruiters":
        company = job.get("company", {})
        identifier = company.get("identifier")
        url = f"https://jobs.smartrecruiters.com/{identifier}/{job.get('id')}" if identifier else None
        loc = job.get("location") or {}
        location = loc.get("fullLocation") or loc.get("city", "")
        if loc.get("remote"):
            mode = "Remote"
        elif loc.get("hybrid"):
            mode = "Hybrid"
        else:
            mode = "On-site"
        return job.get("name"), url, company.get("name"), location, mode
    if platform == "gem":
        location = (job.get("location") or {}).get("name", "")
        mode = _normalize_mode(job.get("location_type")) or _mode_from_text(location)
        return job.get("title"), job.get("absolute_url"), None, location, mode
    if platform == "rippling":
        location = ", ".join(job.get("workLocations") or [])
        return job.get("name"), job.get("url"), job.get("companyName"), location, _mode_from_text(location)
    return None, None, None, "", ""


def _display_name(slug, extracted_name):
    if extracted_name:
        return extracted_name
    # Slugs can be URL-encoded (e.g. Ashby org names with spaces, stored as
    # "Superhuman%20Platform%20Inc" so the crawler builds a valid URL);
    # decode for display purposes until real job data supplies a sample_name.
    decoded = urllib.parse.unquote(slug)
    return decoded.replace("-", " ").replace("_", " ").title()


def _build_manifest():
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

        title, url, name, location, mode = _extract(platform, job)
        if not title or not url:
            continue

        entry = companies.setdefault(slug, {"name": _display_name(slug, name), "jobs": []})
        entry["jobs"].append({
            "title": title, "url": url, "location": location, "mode": mode,
            "canada": _is_canada_job(platform, job, is_remote=(mode == "Remote")),
        })

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_new_jobs": sum(len(c["jobs"]) for c in companies.values()),
        "companies": [
            {"slug": slug, "name": data["name"], "jobs": sorted(data["jobs"], key=lambda j: j["title"])}
            for slug, data in sorted(companies.items(), key=lambda kv: kv[1]["name"].lower())
        ],
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>New Jobs — Job Board Crawler</title>
<style>
  :root {{
    --border: #e2e2e2;
    --muted: #6b7280;
    --accent: #2563eb;
    --bg: #ffffff;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    max-width: 860px;
    margin: 0 auto;
    padding: 2rem 1.25rem 4rem;
    color: #111827;
    background: var(--bg);
  }}
  header h1 {{
    margin: 0 0 0.25rem;
    font-size: 1.75rem;
  }}
  #meta {{
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
  }}
  #nav {{
    margin-bottom: 1.5rem;
    font-size: 0.9rem;
  }}
  #nav a {{
    color: var(--accent);
    text-decoration: none;
  }}
  #nav a:hover {{ text-decoration: underline; }}
  #toc {{
    background: #f9fafb;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 2rem;
  }}
  #toc h2 {{
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--muted);
    margin: 0 0 0.5rem;
  }}
  #toc ul {{
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 0.75rem;
  }}
  #toc a {{
    color: var(--accent);
    text-decoration: none;
    font-size: 0.95rem;
  }}
  #toc a:hover {{ text-decoration: underline; }}
  .company {{
    margin-bottom: 2rem;
    scroll-margin-top: 1rem;
  }}
  .company h2 {{
    font-size: 1.2rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.4rem;
    margin-bottom: 0.6rem;
  }}
  .company h2 .count {{
    color: var(--muted);
    font-weight: normal;
    font-size: 0.9rem;
  }}
  .company ul {{
    list-style: none;
    padding: 0;
    margin: 0;
  }}
  .company li {{
    padding: 0.4rem 0;
    border-bottom: 1px dashed var(--border);
  }}
  .company li:last-child {{ border-bottom: none; }}
  .company a {{
    color: #111827;
    text-decoration: none;
  }}
  .company a:hover {{ color: var(--accent); text-decoration: underline; }}
  .job-meta {{
    color: var(--muted);
    font-size: 0.85rem;
    margin-left: 0.5rem;
    white-space: nowrap;
  }}
  .job-mode {{
    display: inline-block;
    margin-left: 0.4rem;
    padding: 0.05rem 0.5rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    font-size: 0.75rem;
  }}
  .job-mode.remote {{ color: #047857; border-color: #a7f3d0; background: #ecfdf5; }}
  .job-mode.hybrid {{ color: #b45309; border-color: #fde68a; background: #fffbeb; }}
  .job-mode.on-site {{ color: #4338ca; border-color: #c7d2fe; background: #eef2ff; }}
  .job-canada {{
    display: inline-block;
    margin-left: 0.4rem;
    padding: 0.05rem 0.5rem;
    border-radius: 999px;
    border: 1px solid #fecaca;
    background: #fef2f2;
    color: #b91c1c;
    font-size: 0.75rem;
  }}
  #empty {{
    color: var(--muted);
    padding: 2rem 0;
  }}
  a.top {{
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    background: var(--accent);
    color: #fff;
    padding: 0.5rem 0.9rem;
    border-radius: 999px;
    text-decoration: none;
    font-size: 0.85rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }}
</style>
</head>
<body>
  <header id="top">
    <h1>New Jobs</h1>
    <div id="meta">{meta}</div>
    <nav id="nav"><a href="companies.html">Companies crawled &rarr;</a></nav>
  </header>

{toc}
  <main id="results">
{results}
  </main>

  <a class="top" href="#top">↑ Top</a>
</body>
</html>
"""


def _render_job_item(job):
    title = html.escape(job["title"])
    url = html.escape(job["url"])
    location = job.get("location") or ""
    mode = job.get("mode") or ""
    is_canada = job.get("canada")

    badges = []
    if is_canada:
        badges.append('<span class="job-canada">🇨🇦 Canada</span>')
    if mode:
        mode_class = mode.lower().replace(" ", "-")
        badges.append(f'<span class="job-mode {mode_class}">{html.escape(mode)}</span>')
    badges_html = " ".join(badges)

    meta_parts = []
    if location:
        meta_parts.append(html.escape(location))
    if badges_html:
        meta_parts.append(badges_html)
    meta = f'<span class="job-meta">{" ".join(meta_parts)}</span>' if meta_parts else ""

    return (
        f'        <li><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>{meta}</li>'
    )


def _render_html(manifest):
    generated = datetime.strptime(manifest["generated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    total = manifest["total_new_jobs"]
    companies = manifest["companies"]
    meta = (
        f"Jobs posted in the last 24 hours (as of {generated.strftime('%Y-%m-%d %H:%M UTC')}) "
        f"&middot; {total} new job{'' if total == 1 else 's'} across "
        f"{len(companies)} compan{'y' if len(companies) == 1 else 'ies'}"
    )

    if not companies:
        toc = ""
        results = '    <p id="empty">No new jobs in the most recent crawl. Check back soon!</p>'
    else:
        toc_items = "\n".join(
            f'      <li><a href="#company-{html.escape(c["slug"])}">{html.escape(c["name"])} ({len(c["jobs"])})</a></li>'
            for c in companies
        )
        toc = f"""  <nav id="toc">
    <h2>Jump to company</h2>
    <ul id="toc-list">
{toc_items}
    </ul>
  </nav>
"""

        sections = []
        for c in companies:
            job_items = "\n".join(_render_job_item(j) for j in c["jobs"])
            sections.append(
                f'    <section class="company" id="company-{html.escape(c["slug"])}">\n'
                f'      <h2>{html.escape(c["name"])} <span class="count">({len(c["jobs"])})</span></h2>\n'
                f"      <ul>\n{job_items}\n      </ul>\n"
                f"    </section>"
            )
        results = "\n".join(sections)

    return HTML_TEMPLATE.format(meta=meta, toc=toc, results=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", default="docs",
        help="Directory to write index.html/new_jobs.json into "
             "(default: docs). Use e.g. docs/staging for a preview build.",
    )
    args = parser.parse_args()

    json_output_path = os.path.join(args.out_dir, "new_jobs.json")
    html_output_path = os.path.join(args.out_dir, "index.html")

    manifest = _build_manifest()

    os.makedirs(args.out_dir, exist_ok=True)
    with open(json_output_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(html_output_path, "w") as f:
        f.write(_render_html(manifest))

    print(f"Wrote {html_output_path} and {json_output_path}: "
          f"{manifest['total_new_jobs']} new jobs across {len(manifest['companies'])} companies")


if __name__ == "__main__":
    sys.exit(main())
