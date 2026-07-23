# Job Board Crawler

This repo queries the job boards of selected companies and saves the job posting for future analysis.

## Supported platforms

* [Greenhouse](https://boards-api.greenhouse.io) — JSON API with full job descriptions via `?content=true`
* [Lever](https://api.lever.co) — JSON API, includes descriptions by default
* [Ashby](https://api.ashbyhq.com) — JSON API, supports `?includeCompensation=true` for salary data
* [Workable](https://apply.workable.com) — JSON API, includes descriptions via `?details=true`
* [Recruitee](https://recruitee.com) — JSON API, includes descriptions by default
* [SmartRecruiters](https://api.smartrecruiters.com) — JSON API, paginated; job descriptions require per-posting fetch
* [Rippling](https://ats.rippling.com) — Next.js SSR; job list scraped from HTML, full job data extracted from `__NEXT_DATA__` on each posting page

### Sources

- Hacker News "Who is Hiring?" — [Nov 2025](https://news.ycombinator.com/item?id=45800465), [Dec 2025](https://news.ycombinator.com/item?id=46108941), [Jan 2026](https://news.ycombinator.com/item?id=46466074), [Feb 2026](https://news.ycombinator.com/item?id=46857488), [Mar 2026](https://news.ycombinator.com/item?id=47219668), [Apr 2026](https://news.ycombinator.com/item?id=47601859), [May 2026](https://news.ycombinator.com/item?id=47975571), [Jun 2026](https://news.ycombinator.com/item?id=48357725), [Jul 2026](https://news.ycombinator.com/item?id=48747976)
- [Communitech Work in Tech](https://www1.communitech.ca/companies) — Waterloo Region member directory
- [BetaKit](https://betakit.com) — Canadian tech news coverage
- [Terminal](https://www.terminal.io/success-stories) — nearshore talent platform customers
- [Oyster HR](https://www.oysterhr.com) — EOR platform customers
- [Deel](https://www.deel.com) — global payroll platform customers
- [8VC](https://8vc.com/companies) — VC portfolio
- [Accelerator Centre](https://www.acceleratorcentre.com/our-startups/) — Waterloo Region accelerator
- [DMZ Ventures](https://dmzventures.com/dmz-portfolio/) — Toronto Metropolitan University accelerator/fund
- [The Pragmatic Engineer Podcast](https://www.youtube.com/playlist?list=PLzwJJv8h-iciW53inSOkQA4mkG8TuQAUh) — sponsors