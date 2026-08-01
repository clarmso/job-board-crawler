import csv
import json
import re
import sys
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
from xml.etree import ElementTree as ET

SLUGS = '''payoneer,paypal,payscale,paysense,paystack,paytm,payu,pear-therapeutics,pebble,pebblepost,pecan-ai,peek,peerfit,peerspace,peerstreet,pegasystems,peloton,pendo,pentera,peoplegrove,pepper-pay,perceptive-automata,perfect-day,perimeter-81,perion,perkbox,perkspot,personalis,personetics,personio,perx-health,pesto,petal,petlove,phablecare,phantom-auto,pharmeasy,philips,phunware,physics-wallah,pickyourtrail,picnic,pico-interactive,picobrew,picsart,pie-insurance,pier,pilot,ping-identity,pinterest,pipe,pipedrive,pipl,pitch,pivo,pivot3,pix,placer-ai,plaid,planet,planetly,plato,plaxidityx,playdots,playtika,pleo,plerk,plex,pliops,plum,plume,pluralsight,plus-one-robotics,pocket-aces,pocket-fm,pocketmath,point,pokerstars,polarr,policygenius,politico-protocol,pollen,polygon,pomelo-fashion,poparazzi,popcore,popin,poppulo,poshmark,postmates,powerreviews,powerschool,practically,practo,prefect,prepladder,preply,presto,priceline,prime-trust'''.split(',')

HEADERS = {'User-Agent': 'Mozilla/5.0'}

ATS_PATTERNS = [
    ('greenhouse', re.compile(r'greenhouse\.io', re.I)),
    ('lever', re.compile(r'lever\.co', re.I)),
    ('ashby', re.compile(r'ashbyhq\.com', re.I)),
    ('workable', re.compile(r'workable\.com', re.I)),
    ('recruitee', re.compile(r'recruitee\.com', re.I)),
    ('smartrecruiters', re.compile(r'smartrecruiters\.com', re.I)),
    ('rippling', re.compile(r'rippling\.com', re.I)),
    ('gem', re.compile(r'gem\.com', re.I)),
]
BLOCK_DOMAINS = {
    'wikipedia.org','linkedin.com','facebook.com','instagram.com','x.com','twitter.com','youtube.com',
    'glassdoor.com','indeed.com','ziprecruiter.com','builtin.com','rocketreach.co'
}
CAREER_KEYWORDS = ['career', 'careers', 'jobs', 'join-us', 'joinus', 'open-positions', 'work-with-us', 'working-at', 'vacancies']

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self._href = attrs.get('href')
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self._href is not None:
            self.links.append((self._href, ''.join(self._text).strip()))
            self._href = None
            self._text = []


def domain(url):
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith('www.') else host
    except Exception:
        return ''


def clean_url(url):
    if not url:
        return ''
    return url.split('#', 1)[0]


def detect_ats(*texts):
    text = '\n'.join(t for t in texts if t)
    for ats, pat in ATS_PATTERNS:
        if pat.search(text):
            return ats
    if 'workday' in text.lower():
        return 'other'
    return 'unknown'


def fetch(url, method='GET'):
    try:
        r = requests.request(method, url, headers=HEADERS, timeout=20, allow_redirects=True)
        return r
    except Exception:
        return None


def bing_rss(query):
    try:
        r = requests.get('https://www.bing.com/search', params={'q': query, 'format': 'rss'}, headers=HEADERS, timeout=20)
        root = ET.fromstring(r.text)
        items = []
        for item in root.findall('.//item')[:10]:
            items.append({
                'title': item.findtext('title') or '',
                'link': item.findtext('link') or '',
                'description': item.findtext('description') or '',
            })
        return items
    except Exception:
        return []


def is_blocked(url):
    d = domain(url)
    return any(d == bd or d.endswith('.' + bd) for bd in BLOCK_DOMAINS)


def choose_homepage(slug, items):
    slug_tokens = [t for t in re.split(r'[-\s]+', slug.lower()) if t]
    scored = []
    for it in items:
        url = it['link']
        d = domain(url)
        if not d or is_blocked(url):
            continue
        path = urlparse(url).path.lower()
        score = 0
        if path in ('', '/'):
            score += 3
        if all(tok in d.replace('.', '-') or tok in (it['title'] + ' ' + it['description']).lower() for tok in slug_tokens[:1]):
            score += 3
        if any(tok in d.replace('.', '-') for tok in slug_tokens):
            score += 2
        if 'career' in path or 'job' in path:
            score -= 1
        if 'login' in path or 'help' in path or 'support' in path:
            score -= 4
        scored.append((score, url, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else ''


def score_link(href, text):
    h = href.lower()
    t = text.lower()
    score = 0
    if any(k in h for k in CAREER_KEYWORDS):
        score += 4
    if any(k in t for k in ['career','careers','jobs','join us','open positions','open roles','vacancies']):
        score += 4
    ats = detect_ats(h)
    if ats != 'unknown':
        score += 5
    if h.startswith('mailto:') or h.startswith('tel:'):
        score -= 10
    if any(x in h for x in ['privacy', 'terms', 'blog', 'news', 'login', 'signup', 'investor']):
        score -= 3
    return score


def links_from_html(html_text, base_url):
    parser = LinkParser()
    try:
        parser.feed(html_text)
    except Exception:
        pass
    out = []
    for href, text in parser.links:
        if not href:
            continue
        full = clean_url(urljoin(base_url, unescape(href.strip())))
        if full.startswith('javascript:'):
            continue
        out.append((full, text.strip()))
    return out


def probe_paths(base):
    if not base:
        return []
    p = urlparse(base)
    origin = f'{p.scheme}://{p.netloc}'
    paths = ['/careers','/careers/','/jobs','/jobs/','/about/careers','/company/careers','/join-us','/joinus']
    urls = []
    for path in paths:
        urls.append(origin + path)
    return urls


def find_career(slug):
    queries = [f'{slug} careers', f'{slug} jobs']
    search_items = []
    for q in queries:
        search_items.extend(bing_rss(q))
    # direct ATS/search results first
    candidates = []
    for it in search_items:
        url = clean_url(it['link'])
        if not url or is_blocked(url):
            continue
        title_desc = (it['title'] + ' ' + it['description']).lower()
        score = 0
        if any(k in url.lower() for k in CAREER_KEYWORDS):
            score += 5
        if any(k in title_desc for k in ['careers', 'jobs', 'open positions', 'working at']):
            score += 4
        ats = detect_ats(url, title_desc)
        if ats != 'unknown':
            score += 6
        if score > 0:
            candidates.append((score, url, ats, 'search'))
    homepage = choose_homepage(slug, search_items)
    checked = set()
    pages = []
    if homepage:
        pages.append(homepage)
    pages.extend(probe_paths(homepage))
    best_page = None
    best_score = -999
    for page in pages:
        if page in checked:
            continue
        checked.add(page)
        r = fetch(page)
        if not r or r.status_code >= 400:
            continue
        final = clean_url(r.url)
        ats = detect_ats(final, r.text)
        page_score = 0
        if any(k in final.lower() for k in CAREER_KEYWORDS):
            page_score += 3
        if ats != 'unknown':
            page_score += 6
        if domain(final) == domain(homepage):
            page_score += 1
        links = links_from_html(r.text, final)
        for href, text in links:
            s = score_link(href, text)
            if s > 0:
                cand_ats = detect_ats(href, text)
                candidates.append((s + (2 if page == homepage else 0), href, cand_ats, 'link'))
        if page_score > best_score:
            best_score = page_score
            best_page = (final, ats)
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0]
        url, ats = best[1], best[2]
        if ats == 'unknown':
            r = fetch(url)
            if r and r.status_code < 400:
                detected = detect_ats(r.url, r.text)
                if detected != 'unknown':
                    return {'career_url': clean_url(r.url), 'ats': detected, 'homepage': homepage}
        return {'career_url': url, 'ats': ats if ats != 'unknown' else 'other', 'homepage': homepage}
    if best_page:
        return {'career_url': best_page[0], 'ats': best_page[1] if best_page[1] != 'unknown' else 'other', 'homepage': homepage}
    return {'career_url': homepage, 'ats': 'unknown', 'homepage': homepage}


if __name__ == '__main__':
    out = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(find_career, slug): slug for slug in SLUGS}
        for fut in as_completed(futures):
            slug = futures[fut]
            try:
                info = fut.result()
            except Exception as e:
                info = {'career_url': '', 'ats': 'unknown', 'homepage': '', 'error': str(e)}
            out.append({'slug': slug, **info})
            print(json.dumps(out[-1]), flush=True)
