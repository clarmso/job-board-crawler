import re, requests, html, xml.etree.ElementTree as ET, json
from urllib.parse import quote, urlparse, urljoin

headers={'User-Agent':'Mozilla/5.0'}
ignore_domains = ['linkedin.com','glassdoor.com','indeed.com','ziprecruiter.com','joinhandshake.com','facebook.com','instagram.com','youtube.com','x.com','twitter.com','tiktok.com','wikipedia.org']
ats_patterns = {
    'greenhouse': [r'boards\.greenhouse\.io', r'job-boards\.greenhouse\.io', r'grnh\.se', r'greenhouse\.io'],
    'lever': [r'jobs\.lever\.co', r'lever\.co'],
    'ashby': [r'jobs\.ashbyhq\.com', r'ashbyhq\.com'],
    'workable': [r'apply\.workable\.com', r'workable\.com'],
    'recruitee': [r'recruitee\.com'],
    'smartrecruiters': [r'careers\.smartrecruiters\.com', r'smartrecruiters\.com'],
    'rippling': [r'ats\.rippling\.com'],
    'gem': [r'jobs\.gem\.com', r'job-boards\.gem\.com', r'gem\.com/.*/careers'],
}
unsupported_pat = r'workday|jobvite|icims|successfactors|myworkdayjobs|bamboohr|personio|taleo|oraclecloud|teamtailor|comeet|jobylon|pinpoint|beapplied|join\.com|jobs\.sap|greenhouse-candidates|adp\.com|ukg\.net|ultipro|recruitee\.com/careers|applytojob\.com|paylocity|eightfold|jobsoid|easyapply|apply\.be|careers-page\.com'

def detect_ats(text):
    if not text:
        return ''
    for ats, pats in ats_patterns.items():
        for pat in pats:
            if re.search(pat, text, re.I):
                return ats
    if re.search(unsupported_pat, text, re.I):
        return 'other'
    return ''


def search(query):
    url='https://www.bing.com/search?format=rss&q='+quote(query)
    try:
        text=requests.get(url,headers=headers,timeout=20).text
        root=ET.fromstring(text)
    except Exception:
        return []
    out=[]
    for item in root.findall('./channel/item'):
        out.append((item.findtext('title') or '', item.findtext('link') or '', item.findtext('description') or ''))
    return out


def fetch(url):
    try:
        r=requests.get(url,headers=headers,timeout=20,allow_redirects=True)
        return r.url, r.text[:300000], r.headers.get('content-type','')
    except Exception:
        return url, '', ''


def extract_links(base, page):
    links=[]
    for m in re.finditer(r'(?:href|src)=["\']([^"\']+)["\']', page, re.I):
        u=html.unescape(m.group(1).strip())
        if not u or u.startswith('mailto:') or u.startswith('tel:') or u.startswith('javascript:'):
            continue
        links.append(urljoin(base, u))
    # dedupe preserve order
    out=[]; seen=set()
    for u in links:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def choose_official(results, name=''):
    words=[w.lower() for w in re.findall(r'[a-zA-Z0-9]+', name) if len(w)>2]
    for title,link,desc in results:
        l=link.lower(); t=(title+' '+desc).lower()
        if any(d in l for d in ignore_domains):
            continue
        # prefer title mentioning company words or exact domain-like match
        if words and any(w in l or w in t for w in words):
            return link
    for title,link,desc in results:
        if not any(d in link.lower() for d in ignore_domains):
            return link
    return ''


def likely_career_links(base, page):
    ranked=[]
    for u in extract_links(base,page):
        lu=u.lower()
        score=0
        if any(d in lu for d in ignore_domains):
            continue
        if re.search(r'career|careers|jobs|join-us|joinus|job-openings|open-positions|work-with-us|hiring', lu): score += 6
        if re.search(r'about\.|company\.|jobs\.|careers\.', lu): score += 3
        if detect_ats(lu): score += 10
        if score:
            ranked.append((score,u))
    ranked=sorted(ranked, reverse=True)
    out=[]; seen=set()
    for score,u in ranked:
        if u not in seen:
            seen.add(u); out.append(u)
    return out[:8]


def inspect_url(url):
    final,page,ctype=fetch(url)
    text=final+'\n'+page
    ats=detect_ats(text)
    embeds=[]
    for u in extract_links(final,page)[:1500]:
        a=detect_ats(u)
        if a:
            embeds.append((a,u))
    if not ats and embeds:
        ats=embeds[0][0]
    return final,page,ats,embeds


def find(name):
    debug=[]
    # direct careers search first
    results=search(f'{name} careers')[:10]
    debug.append(('careers_results',len(results)))
    for title,link,desc in results:
        combo=' '.join([title,link,desc])
        ats=detect_ats(combo)
        if ats:
            return ats, link, {'stage':'search-direct','title':title,'link':link}
    for title,link,desc in results:
        if any(d in link.lower() for d in ignore_domains):
            continue
        if re.search(r'career|jobs|join|hiring', (title+' '+link+' '+desc), re.I):
            final,page,ats,embeds=inspect_url(link)
            if ats:
                return ats, final, {'stage':'inspect-careers-result','title':title,'embed':embeds[:2]}
            for u in likely_career_links(final,page)[:5]:
                f2,p2,a2,e2=inspect_url(u)
                if a2:
                    return a2, f2, {'stage':'follow-link-from-careers-result','from':final,'to':f2,'embed':e2[:2]}
            if page and detect_ats(page)== 'other':
                return 'other', final, {'stage':'other-careers-result','title':title}
    # homepage search
    home=choose_official(search(name)[:8], name)
    if home:
        final,page,ats,embeds=inspect_url(home)
        if ats:
            return ats, final, {'stage':'homepage-ats','embed':embeds[:2]}
        for u in likely_career_links(final,page):
            f2,p2,a2,e2=inspect_url(u)
            if a2:
                return a2, f2, {'stage':'follow-home-career','from':final,'to':f2,'embed':e2[:2]}
            if p2 and detect_ats(p2)=='other':
                return 'other', f2, {'stage':'follow-home-other','from':final,'to':f2}
    # search with jobs keyword, inspect officialish results
    for q in [f'{name} jobs', f'{name} join us', f'{name} hiring']:
        for title,link,desc in search(q)[:8]:
            if any(d in link.lower() for d in ignore_domains):
                continue
            final,page,ats,embeds=inspect_url(link)
            if ats:
                return ats, final, {'stage':'jobs-search-inspect','query':q,'title':title,'embed':embeds[:2]}
            for u in likely_career_links(final,page)[:4]:
                f2,p2,a2,e2=inspect_url(u)
                if a2:
                    return a2, f2, {'stage':'jobs-follow','query':q,'from':final,'to':f2,'embed':e2[:2]}
                if p2 and detect_ats(p2)=='other':
                    return 'other', f2, {'stage':'jobs-follow-other','query':q,'to':f2}
    return 'unknown','',{'stage':'none'}

for name in ['Glovo','GoFundMe','Graphcore','Help Scout','HelloFresh','Gong']:
    print(name, find(name))
