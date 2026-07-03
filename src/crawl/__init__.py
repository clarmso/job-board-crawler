"""Generic ATS job board crawler."""

import glob
import json
import os
from datetime import datetime
from enum import Enum

from src.http import fetch_json


class DateFormat(Enum):
    ISO = "iso"
    UNIX_MS = "unix_ms"
    DATETIME_UTC = "datetime_utc"


PLATFORMS = {
    "greenhouse": {
        "url": "https://boards-api.greenhouse.io/v1/boards/{}/jobs?content=true",
        "jobs_key": "jobs",
        "id_field": "id",
        "date_field": "updated_at",
        "date_format": DateFormat.ISO,
    },
    "lever": {
        "url": "https://api.lever.co/v0/postings/{}?mode=json",
        "jobs_key": None,
        "id_field": "id",
        "date_field": "createdAt",
        "date_format": DateFormat.UNIX_MS,
    },
    "ashby": {
        "url": "https://api.ashbyhq.com/posting-api/job-board/{}?includeCompensation=true",
        "jobs_key": "jobs",
        "id_field": "id",
        "date_field": "publishedDate",
        "date_format": DateFormat.ISO,
    },
    "workable": {
        "url": "https://apply.workable.com/api/v1/widget/accounts/{}?details=true",
        "jobs_key": "jobs",
        "id_field": "shortcode",
        "date_field": "published_on",
        "date_format": DateFormat.ISO,
    },
    "recruitee": {
        "url": "https://{}.recruitee.com/api/offers",
        "jobs_key": "offers",
        "id_field": "id",
        "date_field": "created_at",
        "date_format": DateFormat.DATETIME_UTC,
    },
    "smartrecruiters": {
        "url": "https://api.smartrecruiters.com/v1/companies/{}/postings",
        "jobs_key": "content",
        "id_field": "id",
        "date_field": "releasedDate",
        "date_format": DateFormat.ISO,
        "paginated": True,
    },
}


def _parse_date(value, fmt):
    if fmt == DateFormat.UNIX_MS:
        return datetime.fromtimestamp(value / 1000)
    if fmt == DateFormat.DATETIME_UTC:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S %Z")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _fetch_jobs(config, company):
    url = config["url"].format(company)

    if config.get("paginated"):
        jobs = []
        offset = 0
        limit = 100
        while True:
            data = fetch_json(f"{url}?offset={offset}&limit={limit}")
            page = data.get(config["jobs_key"], [])
            jobs.extend(page)
            if len(page) < limit:
                break
            offset += limit
        return jobs

    data = fetch_json(url)
    if config["jobs_key"] is None:
        return data
    return data.get(config["jobs_key"], [])


def crawl(platform, company, output_dir):
    """Fetch all jobs for a company from the given platform and save each as JSON."""
    config = PLATFORMS[platform]
    print(f"  Fetching job list for board: {company}")
    jobs = _fetch_jobs(config, company)
    print(f"  Found {len(jobs)} jobs")

    os.makedirs(output_dir, exist_ok=True)

    id_field = config["id_field"]
    date_field = config["date_field"]
    date_format = config["date_format"]

    saved = 0
    updated = 0

    for job in jobs:
        job_id = str(job[id_field])
        date_val = job.get(date_field)
        if date_val:
            dt = _parse_date(date_val, date_format)
            year_dir = os.path.join(output_dir, str(dt.year))
        else:
            year_dir = os.path.join(output_dir, str(datetime.now().year))

        for old in glob.glob(os.path.join(output_dir, "*", f"{job_id}.json")):
            if os.path.dirname(old) != year_dir:
                os.remove(old)

        os.makedirs(year_dir, exist_ok=True)
        filepath = os.path.join(year_dir, f"{job_id}.json")

        existing = None
        if os.path.exists(filepath):
            with open(filepath) as f:
                existing = json.load(f)

        if existing != job:
            with open(filepath, "w") as f:
                json.dump(job, f, indent=2, ensure_ascii=False)
                f.write("\n")
            if existing is None:
                saved += 1
            else:
                updated += 1

    print(f"  New: {saved}, Updated: {updated}")
    return len(jobs)
