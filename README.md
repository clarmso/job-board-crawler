# openings.info

<img src="docs/icons/favicon-512.png" alt="openings.info icon" width="100" height="100" align="center" />

[openings.info](https://openings.info) reports **new tech jobs posted in the last 2 days** daily. It crawls the public job boards (ATS) of a curated list of companies, find what's genuinely new, and publishes the result to the static site.

The job descriptions are saved for future analysis. Often, the companies remove the job descriptions once the openings are no longer available. We have limited ways to look at what a job descriptions looked like in the past. We may see how jobs have evolved in the near future. (Pie in the cloud. I know! ;-))

See [setup.md](setup.md) for requirements and how it works under the hood (crawl → detect new jobs → publish → social digest).

## Supported platforms

* [Greenhouse](https://boards-api.greenhouse.io)
* [Lever](https://api.lever.co)
* [Ashby](https://api.ashbyhq.com)
* [Workable](https://apply.workable.com)
* [Recruitee](https://recruitee.com)
* [SmartRecruiters](https://api.smartrecruiters.com)
* [Rippling](https://ats.rippling.com)
* [Gem](https://api.gem.com)
* [Breezy HR](https://breezy.hr)
* [BambooHR](https://bamboohr.com)
* [Personio](https://personio.com)
* [Trakstar](https://trakstar.com) (formerly Recruiterbox)

### Sources

- Hacker News "Who is Hiring?" — [Nov 2025](https://news.ycombinator.com/item?id=45800465), [Dec 2025](https://news.ycombinator.com/item?id=46108941), [Jan 2026](https://news.ycombinator.com/item?id=46466074), [Feb 2026](https://news.ycombinator.com/item?id=46857488), [Mar 2026](https://news.ycombinator.com/item?id=47219668), [Apr 2026](https://news.ycombinator.com/item?id=47601859), [May 2026](https://news.ycombinator.com/item?id=47975571), [Jun 2026](https://news.ycombinator.com/item?id=48357725), [Jul 2026](https://news.ycombinator.com/item?id=48747976), [Aug 2026](https://news.ycombinator.com/item?id=49156683)
- [Communitech Work in Tech](https://www1.communitech.ca/companies) — Waterloo Region member directory
- [BetaKit](https://betakit.com) — Canadian tech news coverage
- [Terminal](https://www.terminal.io/success-stories) — nearshore talent platform customers
- [Oyster HR](https://www.oysterhr.com) — EOR platform customers
- [Deel](https://www.deel.com) — global payroll platform customers
- [8VC](https://8vc.com/companies) — VC portfolio
- [Accelerator Centre](https://www.acceleratorcentre.com/our-startups/) — Waterloo Region accelerator
- [DMZ Ventures](https://dmzventures.com/dmz-portfolio/) — Toronto Metropolitan University accelerator/fund
- [The Pragmatic Engineer Podcast](https://www.youtube.com/playlist?list=PLzwJJv8h-iciW53inSOkQA4mkG8TuQAUh) — sponsors
- [Y Combinator Companies API](https://api.ycombinator.com/v0.1/companies) — all Active YC alumni (batches S05–W26), ATS auto-detected via platform APIs
- [DMZ Oh Canada Tech Directory](https://dmz.torontomu.ca/oh-canada-directory) — Canadian companies listed in DMZ's buy-Canadian tech showcase