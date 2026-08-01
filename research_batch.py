import csv, html, re, time
from urllib.parse import urljoin, urlparse
import requests
from ddgs import DDGS

SLUGS = """blueground,bluelearn,bluepad,bluestacks,bluevine,blume-global,bluprint,bm-technologies,bobble-ai,bolt,bolt-earth,bond,bonsai,bonterra,bonusly,bookclub,booking-com,booking-holdings,bookmyshow,booksy,booktopia,boost,boosted-commerce,boozt,bossa-nova,bounce,bouncex,bowery-farming,boxed,braid,brainbase,brainly,branch,branch-io,branch-metrics,brave-care,breadfast,breathe,breather,brex,bridge-connector,bridgit,bright-machines,bright-money,brightcove,brighte,brightline,brilliant,bringg,britishvolt,briza,broadcom,brodmann17,bryter,buenbit,builder,builder-ai,buildertrend,built-in,built-technologies,built-technologies-copy,bukalapak,bullhorn,bullish,bumble,bundle-africa,bungalow,bungie,bunnii,busbud,buser,business-insider,bustle-digital-group,butler-hospitality,butterfly-network,butterfly-network-copy,button,bux,buy-com-rakuten,buzzer,buzzfeed,bvaccel,bybit,byju-s,bytedance,byton,c2fo,c3-ai,c6-bank,cabify,cabin,cadre,cake-bikes,cake-group,calibrate,caliva,callisto-media,calm,cambricon,cameo""".split(',')

QUERY_OVERRIDE = {
    'bluestacks': 'BlueStacks careers',
    'bolt': 'Bolt company careers',
    'bond': 'Bond financial technologies careers',
    'bookclub': 'Bookclub careers company',
    'boost': 'Boost company careers',
    'bounce': 'Bounce company careers',
    'branch': 'Branch company careers',
    'braid': 'Braid company careers',
    'brilliant': 'Brilliant.org careers',
    'builder': 'Builder careers company',
    'bullish': 'Bullish careers company',
    'cabin': 'Cabin company careers',
    'cadre': 'Cadre careers company',
    'caliva': 'Caliva careers',
    'callisto-media': 'Callisto Media careers',
    'cake-group': 'Cake Group careers company',
}

HQ = {
'blueground':'US','bluelearn':'','bluepad':'','bluestacks':'US','bluevine':'US','blume-global':'US','bluprint':'US','bm-technologies':'US','bobble-ai':'','bolt':'Estonia','bolt-earth':'','bond':'US','bonsai':'US','bonterra':'US','bonusly':'US','bookclub':'US','booking-com':'Netherlands','booking-holdings':'US','bookmyshow':'','booksy':'US','booktopia':'','boost':'','boosted-commerce':'US','boozt':'Sweden','bossa-nova':'US','bounce':'US','bouncex':'US','bowery-farming':'US','boxed':'US','braid':'','brainbase':'US','brainly':'Poland','branch':'US','branch-io':'US','branch-metrics':'US','brave-care':'US','breadfast':'','breathe':'UK','breather':'Canada','brex':'US','bridge-connector':'','bridgit':'Canada','bright-machines':'US','bright-money':'US','brightcove':'US','brighte':'','brightline':'US','brilliant':'US','bringg':'','britishvolt':'UK','briza':'Canada','broadcom':'US','brodmann17':'Austria','bryter':'Germany','buenbit':'','builder':'','builder-ai':'UK','buildertrend':'US','built-in':'US','built-technologies':'US','built-technologies-copy':'US','bukalapak':'','bullhorn':'US','bullish':'','bumble':'US','bundle-africa':'','bungalow':'US','bungie':'US','bunnii':'','busbud':'Canada','buser':'','business-insider':'US','bustle-digital-group':'US','butler-hospitality':'US','butterfly-network':'US','butterfly-network-copy':'US','button':'US','bux':'Netherlands','buy-com-rakuten':'','buzzer':'US','buzzfeed':'US','bvaccel':'US','bybit':'','byju-s':'','bytedance':'','byton':'','c2fo':'US','c3-ai':'US','c6-bank':'','cabify':'Spain','cabin':'US','cadre':'US','cake-bikes':'Sweden','cake-group':'','calibrate':'US','caliva':'US','callisto-media':'US','calm':'US','cambricon':'','cameo':'US'}

BLOCKED = ['linkedin.com','indeed.com','glassdoor.com','welcometothejungle.com','builtin.com','wellfound.com','ziprecruiter.com','jobs.jobvite.com','crunchbase.com','pitchbook.com','jobspundit.com','weloveproduct.co','comparably.com','rocketreach.co','facebook.com','instagram.com','x.com','twitter.com']
SUPPORTED_PATTERNS = [
    ('greenhouse', ['greenhouse.io', 'boards.greenhouse.io', 'job-boards.greenhouse.io', 'grnh.se']),
    ('lever', ['jobs.lever.co', 'lever.co']),
    ('ashby', ['jobs.ashbyhq.com', 'ashbyhq.com']),
    ('workable', ['workable.com']),
    ('recruitee', ['recruitee.com']),
    ('smartrecruiters', ['smartrecruiters.com']),
    ('rippling', ['rippling-ats.com', 'ats.rippling.com']),
    ('gem', ['gem.com'])
]
OTHER_PATTERNS = ['myworkdayjobs.com','workday.com','icims.com','jobvite.com','bamboohr.com','teamtailor.com','personio.de','personio.com','paylocity.com','adp.com','successfactors.com','applytojob.com','recruiterbox.com','oraclecloud.com','hirehive.com','jobsoid.com','jobylon.com','pinpointhq.com','jobvite.com','notion.site/careers','culturehq.com']

ALIASES = {
    'branch-io':'branch', 'branch-metrics':'branch', 'buy-com-rakuten':'rakuten', 'booking-com':'booking',
    'booking-holdings':'booking holdings', 'butterfly-network-copy':'butterfly network',
    'built-technologies-copy':'built technologies'
}

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

def norm(s):
    return re.sub(r'[^a-z0-9]+', '', s.lower())

def domain(u):
    try:
        return urlparse(u).netloc.lower().removeprefix('www.')
    except Exception:
        return ''

def blocked(u):
    d = domain(u)
    return any(b in d for b in BLOCKED)

def detect_ats(text, url=''):
    hay = (url + '\n' + (text or '')).lower()
    for ats, pats in SUPPORTED_PATTERNS:
        if any(p in hay for p in pats):
            return ats
    if any(p in hay for p in OTHER_PATTERNS):
        return 'other'
    return 'unknown'

def fetch(url):
    try:
        r = session.get(url, timeout=20, allow_redirects=True)
        return r.url, r.text[:250000]
    except Exception:
        return url, ''

def find_careers_link(base_url, html_text):
    if not html_text:
        return ''
    pats = [r'href=["\']([^"\']+)["\'][^>]*>[^<]*(careers?|jobs?|join us|open positions)',
            r'href=["\']([^"\']*(?:careers?|jobs?|join-us|joinus|work-with-us|open-positions)[^"\']*)["\']']
    for pat in pats:
        for m in re.finditer(pat, html_text, re.I):
            href = html.unescape(m.group(1))
            if href.startswith('mailto:') or href.startswith('javascript:'):
                continue
            return urljoin(base_url, href)
    return ''

def score_result(slug, title, url):
    d = domain(url)
    t = (title or '').lower()
    u = url.lower()
    s = 0
    if blocked(url):
        return -999
    ats = detect_ats('', url)
    if ats != 'unknown':
        s += 60 if ats != 'other' else 25
    if any(k in t or k in u for k in ['career','careers','jobs','join','hiring','work with us','open positions']):
        s += 20
    key = ALIASES.get(slug, slug).replace('-', '')
    if key and key in norm(t + ' ' + d):
        s += 25
    toks = [x for x in slug.split('-') if x not in {'io','ai','com','copy'}]
    for tok in toks:
        if tok and tok in d.replace('.','-'):
            s += 8
    if any(x in d for x in ['careers.','jobs.']):
        s += 5
    return s


def choose_result(slug, results):
    results = sorted(results, key=lambda r: score_result(slug, r.get('title',''), r.get('href','')), reverse=True)
    return results

rows=[]
for i, slug in enumerate(SLUGS,1):
    query = QUERY_OVERRIDE.get(slug, slug.replace('-', ' ') + ' careers')
    print('SEARCH', i, slug, query)
    try:
        results = list(DDGS().text(query, max_results=8, backend='html'))
    except Exception as e:
        print(' search error', e)
        results = []
    candidates = choose_result(slug, results)
    career_url = ''
    ats = 'unknown'
    for r in candidates[:5]:
        href = r.get('href','')
        title = r.get('title','')
        if blocked(href):
            continue
        final_url, page = fetch(href)
        detected = detect_ats(page, final_url)
        # If homepage, try to find careers link.
        if detected == 'unknown' and not any(k in final_url.lower() for k in ['career','jobs','join','hiring']) and domain(final_url):
            maybe = find_careers_link(final_url, page)
            if maybe and domain(maybe):
                final2, page2 = fetch(maybe)
                det2 = detect_ats(page2, final2)
                if det2 != 'unknown' or any(k in final2.lower() for k in ['career','jobs','join']):
                    final_url, page, detected = final2, page2, det2
        print(' cand', score_result(slug,title,href), detected, final_url)
        if detected != 'unknown':
            career_url, ats = final_url, detected
            break
        if not career_url and any(k in final_url.lower() for k in ['career','jobs','join']):
            career_url = final_url
    if not career_url and candidates:
        # fallback to best result url even if unknown ATS
        href = candidates[0].get('href','')
        if not blocked(href):
            career_url = href
            ats = detect_ats('', href)
            if ats == 'unknown':
                ats = 'unknown'
    rows.append({'slug':slug,'ats': '' if not career_url else ats,'career_url':career_url,'hq_country':HQ.get(slug,'')})
    time.sleep(0.8)

with open('/Users/clare/Documents/workspace/job-board-crawler/research_batch_results.csv','w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['slug','ats','career_url','hq_country'])
    w.writeheader(); w.writerows(rows)
print('wrote', len(rows))
