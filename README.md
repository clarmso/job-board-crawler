# Job Board Crawler

This repo queries the job boards of selected companies and saves the job posting for future analysis.

## Supported platforms

* [Greenhouse](https://boards-api.greenhouse.io) — JSON API with full job descriptions via `?content=true`
* [Lever](https://api.lever.co) — JSON API, includes descriptions by default
* [Ashby](https://api.ashbyhq.com) — JSON API, supports `?includeCompensation=true` for salary data
* [Workable](https://apply.workable.com) — JSON API, includes descriptions via `?details=true`
* [Recruitee](https://recruitee.com) — JSON API, includes descriptions by default
* [SmartRecruiters](https://api.smartrecruiters.com) — JSON API, paginated; job descriptions require per-posting fetch

## Companies included
* Mozilla