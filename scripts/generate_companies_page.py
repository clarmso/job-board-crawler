#!/usr/bin/env python3
"""
Generate docs/companies.html — a static page listing every company tracked
in companies.csv, its ATS platform, HQ location, current open-role count,
how many of those openings can be based in Canada, and a link to its live
careers page. Also writes docs/companies.json as a raw data snapshot.

Unlike generate_new_jobs.py this isn't time-windowed: it reflects whatever
is currently in data/ (typically after `crawl.py` has just run), so it's
safe to run any time after (or independently of) a crawl.
"""

import csv
import glob
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

DATA_DIR = "data"
COMPANIES_CSV = "companies.csv"
JSON_OUTPUT_PATH = os.path.join("docs", "companies.json")
HTML_OUTPUT_PATH = os.path.join("docs", "companies.html")

# Platforms crawl.py knows how to fetch (kept in sync with src/crawl.PLATFORMS).
SUPPORTED_PLATFORMS = {
    "greenhouse", "lever", "ashby", "workable", "recruitee",
    "smartrecruiters", "gem", "rippling",
}

CAREERS_URL_BY_PLATFORM = {
    "greenhouse": "https://job-boards.greenhouse.io/{slug}",
    "lever": "https://jobs.lever.co/{slug}",
    "ashby": "https://jobs.ashbyhq.com/{slug}",
    "workable": "https://apply.workable.com/{slug}/",
    "recruitee": "https://{slug}.recruitee.com/",
    "smartrecruiters": "https://careers.smartrecruiters.com/{slug}/",
    "gem": "https://jobs.gem.com/{slug}",
    "rippling": "https://ats.rippling.com/{slug}/jobs",
}


def _careers_url(slug, platform):
    template = CAREERS_URL_BY_PLATFORM.get(platform)
    return template.format(slug=slug) if template else None


_CA_REMOTE_RE = re.compile(r"\bca\s*[-\u2013\u2014]?\s*remote\b|\bremote\s*[-\u2013\u2014]?\s*ca\b")

# Canadian province/territory postal abbreviations, as they appear after a
# city name in free-text location strings (e.g. "Kitchener-Waterloo, ON").
# Deliberately case-sensitive and requires a preceding comma: matching case-
# insensitively would false-positive on the common English word "on".
_CA_PROVINCE_RE = re.compile(
    r",\s*(ON|BC|QC|AB|MB|SK|NS|NB|PE|NL|YT|NT|NU)\b"
)


def _mentions_canada(*texts):
    """Keyword match for locations that plausibly cover Canada.

    Matches "Canada" itself plus broader regions a Canada-based candidate
    could reasonably apply under ("Global", "North America", "Americas"),
    plus the "CA Remote" / "Remote - CA" shorthand some companies use
    (e.g. "CA Remote (BC & ON only); U.S. Remote"), plus a Canadian
    province/territory abbreviation following a city name (e.g.
    "Kitchener-Waterloo, ON; Toronto, ON").

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
    combined = raw.lower()
    if any(keyword in combined for keyword in ("canada", "global", "north america", "americas")):
        return True
    return bool(_CA_REMOTE_RE.search(combined))


def _mode_from_text(text):
    """Best-effort guess of workplace mode from a free-text location string."""
    if not text:
        return ""
    lowered = str(text).lower()
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
    return ""


def _is_remote_job(platform, job):
    """Best-effort: is this specific opening fully remote?

    Mirrors the workplace-mode inference used by generate_new_jobs.py, using
    structured fields where the ATS provides them and falling back to
    keyword matching on free-text location fields.

    Note: this only signals "remote work mode" (vs. hybrid/on-site); it says
    nothing about geographic eligibility. Callers should treat a posting
    that's both remote *and* Canada-eligible (e.g. "Canada Remote") as
    Canada, not worldwide Remote — see _scan_company_jobs, which only counts
    a job as Remote when it is not already counted as Canada.
    """
    if platform == "greenhouse":
        location = (job.get("location") or {}).get("name", "")
        return _mode_from_text(location) == "Remote"

    if platform == "lever":
        categories = job.get("categories") or {}
        location = categories.get("location") or ", ".join(categories.get("allLocations") or [])
        mode = _normalize_mode(job.get("workplaceType")) or _mode_from_text(location)
        return mode == "Remote"

    if platform == "ashby":
        location = job.get("location", "")
        mode = _normalize_mode(job.get("workplaceType")) or _mode_from_text(location)
        return mode == "Remote"

    if platform == "workable":
        if job.get("telecommuting"):
            return True
        location = ", ".join(part for part in (job.get("city"), job.get("state"), job.get("country")) if part)
        return _mode_from_text(location) == "Remote"

    if platform == "smartrecruiters":
        loc = job.get("location") or {}
        if loc.get("remote"):
            return True
        location = loc.get("fullLocation") or loc.get("city", "")
        return _mode_from_text(location) == "Remote"

    if platform == "gem":
        location = (job.get("location") or {}).get("name", "")
        mode = _normalize_mode(job.get("location_type")) or _mode_from_text(location)
        return mode == "Remote"

    if platform == "rippling":
        location = ", ".join(job.get("workLocations") or [])
        return _mode_from_text(location) == "Remote"

    return False


def _is_canada_job(platform, job):
    """Best-effort: can this specific opening be based in Canada?

    Uses structured country fields where the ATS provides them, falling back
    to keyword matching on free-text location fields.
    """
    if platform == "greenhouse":
        return _mentions_canada((job.get("location") or {}).get("name"))

    if platform == "lever":
        if str(job.get("country") or "").strip().lower() == "ca":
            return True
        categories = job.get("categories") or {}
        return _mentions_canada(categories.get("location"), *(categories.get("allLocations") or []))

    if platform == "ashby":
        address = ((job.get("address") or {}).get("postalAddress") or {})
        if _mentions_canada(address.get("addressCountry")):
            return True
        if _mentions_canada(job.get("location")):
            return True
        for secondary in job.get("secondaryLocations") or []:
            secondary_address = ((secondary.get("address") or {}).get("postalAddress") or {})
            if _mentions_canada(secondary.get("location"), secondary_address.get("addressCountry")):
                return True
        return False

    if platform == "workable":
        if str(job.get("country") or "").strip().lower() == "canada":
            return True
        for loc in job.get("locations") or []:
            if str(loc.get("country") or "").strip().lower() == "canada" or str(loc.get("countryCode") or "").strip().lower() == "ca":
                return True
        # Fall back to free text for regional postings ("Global", "Americas", ...)
        # that don't map to a single ISO country field.
        location_texts = [job.get("country"), job.get("city"), job.get("state")]
        for loc in job.get("locations") or []:
            location_texts.extend([loc.get("country"), loc.get("city"), loc.get("region")])
        return _mentions_canada(*location_texts)

    if platform == "smartrecruiters":
        loc = job.get("location") or {}
        if str(loc.get("country") or "").strip().lower() == "ca":
            return True
        return _mentions_canada(loc.get("fullLocation"), loc.get("city"))

    if platform == "gem":
        return _mentions_canada((job.get("location") or {}).get("name"))

    if platform == "rippling":
        return _mentions_canada(*(job.get("workLocations") or []))

    return False


def _scan_company_jobs(slug, platform):
    """Single pass over a company's crawled job files.

    Returns (sample_company_name, job_count, canada_job_count, remote_job_count).
    """
    path = os.path.join(DATA_DIR, slug)
    if not os.path.isdir(path):
        return None, 0, 0, 0

    sample_name = None
    job_count = 0
    canada_job_count = 0
    remote_job_count = 0
    for match in glob.glob(os.path.join(path, "**", "*.json"), recursive=True):
        try:
            with open(match) as f:
                job = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        job_count += 1
        is_canada = _is_canada_job(platform, job)
        if is_canada:
            canada_job_count += 1
        # "Remote" here specifically means remote *worldwide* (no location
        # restriction) — a posting explicitly scoped to Canada (e.g. "Canada
        # Remote", "Toronto, ON") is tagged Canada only, not double-counted
        # as Remote too.
        if not is_canada and _is_remote_job(platform, job):
            remote_job_count += 1

        if sample_name is None:
            sample_name = (
                job.get("company_name")
                or job.get("companyName")
                or (job.get("company") or {}).get("name")
            )

    return sample_name, job_count, canada_job_count, remote_job_count


def _display_name(slug, sample_name):
    if sample_name:
        return sample_name
    return slug.replace("-", " ").replace("_", " ").title()


def _build_manifest():
    with open(COMPANIES_CSV, newline="") as f:
        rows = [row for row in csv.DictReader(f) if row.get("slug") and row.get("ats")]

    companies = []
    for row in rows:
        slug = row["slug"]
        platform = row["ats"]
        supported = platform in SUPPORTED_PLATFORMS
        sample_name, job_count, canada_job_count, remote_job_count = (
            _scan_company_jobs(slug, platform) if supported else (None, 0, 0, 0)
        )
        companies.append({
            "slug": slug,
            "name": _display_name(slug, sample_name),
            "ats": platform,
            "hq_country": row.get("hq_country") or "",
            "job_count": job_count,
            "canada_job_count": canada_job_count,
            "remote_job_count": remote_job_count,
            "careers_url": _careers_url(slug, platform),
            "supported": supported,
        })

    companies.sort(key=lambda c: c["name"].lower())

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_companies": len(companies),
        "total_open_jobs": sum(c["job_count"] for c in companies),
        "companies": companies,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Companies — Job Board Crawler</title>
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
    max-width: 900px;
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
    margin-bottom: 0.75rem;
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
  #search {{
    width: 100%;
    padding: 0.6rem 0.8rem;
    font-size: 0.95rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 0.75rem;
  }}
  #canada-toggle, #remote-toggle {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.9rem;
    color: #374151;
    margin-bottom: 1.25rem;
    margin-right: 1.25rem;
    cursor: pointer;
  }}
  #canada-toggle input, #remote-toggle input {{ cursor: pointer; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92rem;
  }}
  thead th {{
    text-align: left;
    color: var(--muted);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.03em;
    border-bottom: 1px solid var(--border);
    padding: 0.5rem 0.6rem;
  }}
  tbody td {{
    padding: 0.55rem 0.6rem;
    border-bottom: 1px dashed var(--border);
    vertical-align: middle;
  }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover {{ background: #f9fafb; }}
  td.jobs, th.jobs {{ text-align: right; }}
  a.company-link {{
    color: #111827;
    text-decoration: none;
    font-weight: 500;
  }}
  a.company-link:hover {{ color: var(--accent); text-decoration: underline; }}
  .badge {{
    display: inline-block;
    padding: 0.05rem 0.5rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    font-size: 0.75rem;
    color: var(--muted);
  }}
  .badge.unsupported {{ color: #b91c1c; border-color: #fecaca; background: #fef2f2; }}
  .badge.canada {{ color: #047857; border-color: #a7f3d0; background: #ecfdf5; }}
  .badge.remote {{ color: #4338ca; border-color: #c7d2fe; background: #eef2ff; }}
  #empty-filter {{
    display: none;
    color: var(--muted);
    padding: 1.5rem 0;
  }}
</style>
</head>
<body>
  <header id="top">
    <h1>Companies</h1>
    <div id="meta">{meta}</div>
    <nav id="nav"><a href="index.html">&larr; New Jobs</a></nav>
  </header>

  <input id="search" type="search" placeholder="Filter by company or ATS..." autocomplete="off" />
  <label id="canada-toggle">
    <input type="checkbox" id="canada-only" /> Only show companies with openings based in Canada
  </label>
  <label id="remote-toggle">
    <input type="checkbox" id="remote-only" /> Only show companies with worldwide-remote openings
  </label>

  <table id="companies-table">
    <thead>
      <tr>
        <th>Company</th>
        <th>ATS</th>
        <th>HQ</th>
        <th class="jobs">Open jobs</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
  <p id="empty-filter">No companies match your filter.</p>

  <script>
    const input = document.getElementById("search");
    const canadaOnly = document.getElementById("canada-only");
    const remoteOnly = document.getElementById("remote-only");
    const rows = Array.from(document.querySelectorAll("#companies-table tbody tr"));
    const emptyMsg = document.getElementById("empty-filter");

    function applyFilters() {{
      const q = input.value.trim().toLowerCase();
      let visible = 0;
      rows.forEach((row) => {{
        const matchesSearch = row.dataset.search.includes(q);
        const matchesCanada = !canadaOnly.checked || row.dataset.canada === "true";
        const matchesRemote = !remoteOnly.checked || row.dataset.remote === "true";
        const match = matchesSearch && matchesCanada && matchesRemote;
        row.style.display = match ? "" : "none";
        if (match) visible++;
      }});
      emptyMsg.style.display = visible === 0 ? "block" : "none";
    }}

    input.addEventListener("input", applyFilters);
    canadaOnly.addEventListener("change", applyFilters);
    remoteOnly.addEventListener("change", applyFilters);
  </script>
</body>
</html>
"""


def _render_row(c):
    name = html.escape(c["name"])
    ats = html.escape(c["ats"])
    hq = html.escape(c["hq_country"]) if c["hq_country"] else "&mdash;"
    search_key = html.escape(f"{c['name']} {c['ats']} {c['hq_country']}".lower())
    is_canada = "true" if c["canada_job_count"] > 0 else "false"
    is_remote = "true" if c["remote_job_count"] > 0 else "false"

    if c["careers_url"]:
        name_cell = (
            f'<a class="company-link" href="{html.escape(c["careers_url"])}" '
            f'target="_blank" rel="noopener noreferrer">{name}</a>'
        )
    else:
        name_cell = name

    if c["supported"]:
        jobs_cell = str(c["job_count"])
        if c["canada_job_count"] > 0:
            jobs_cell += ' <span class="badge canada">Canada</span>'
        if c["remote_job_count"] > 0:
            jobs_cell += ' <span class="badge remote">Remote</span>'
    else:
        jobs_cell = '<span class="badge unsupported">not yet supported</span>'

    return (
        f'      <tr data-search="{search_key}" data-canada="{is_canada}" data-remote="{is_remote}">\n'
        f"        <td>{name_cell}</td>\n"
        f"        <td>{ats}</td>\n"
        f"        <td>{hq}</td>\n"
        f'        <td class="jobs">{jobs_cell}</td>\n'
        f"      </tr>"
    )


def _render_html(manifest):
    generated = datetime.strptime(manifest["generated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    meta = (
        f"{manifest['total_companies']} companies tracked &middot; "
        f"{manifest['total_open_jobs']} open jobs &middot; "
        f"as of {generated.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    rows = "\n".join(_render_row(c) for c in manifest["companies"])
    return HTML_TEMPLATE.format(meta=meta, rows=rows)


def main():
    manifest = _build_manifest()

    os.makedirs("docs", exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(HTML_OUTPUT_PATH, "w") as f:
        f.write(_render_html(manifest))

    print(f"Wrote {HTML_OUTPUT_PATH} and {JSON_OUTPUT_PATH}: "
          f"{manifest['total_companies']} companies, {manifest['total_open_jobs']} open jobs")


if __name__ == "__main__":
    sys.exit(main())
