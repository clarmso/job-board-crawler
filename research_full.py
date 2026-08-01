import re, requests, html, xml.etree.ElementTree as ET, csv
from urllib.parse import quote, urljoin

slugs = 'gloat,gloo,glorifi,glossier,glovo,glowforge,goat-group,gobear,gobolt,gocanvas,godaddy,gofundme,gohealth,gojek,gokada,gokwik,golemon,gomechanic,gong,gonuts,goodfood,goodgood,goodrx,goodworker,google,goop,gopro,gopuff,gorillas,gospotcheck,gostudent,goto,goto-group,gousto,gowild,grab,grabango,grabcad,grail,grailed,gramophone,graphcore,graphy,graymeta,green-labs,greenhouse,greenikk,greenlight,grin,gro-intelligence,groundgame-health,group-nine-media,groupon,grove-collaborative,grover,grubhub,gsr,guardant-health,guesty,guideline,guidewire,guild,gumgum,gupshup,gupy,gympass,hackerearth,hackerone,hailo,halcyon-health,halodoc,happay,happy-money,harappa,hash,haus,haven-technologies,havenly,head-digital-works,headspace,health-iq,healthcare-com,healthifyme,healthmatch,healthy-io,hedvig,hellofresh,help-com,help-scout,her-campus-media,here,hermd,heroes,heureka-group,hewlett-packard-enterprise,heycar,heygo,heyjobs,hibob,highradius'.split(',')

name_overrides = {
    'goat-group': 'GOAT Group','gocanvas': 'GoCanvas','godaddy': 'GoDaddy','gofundme': 'GoFundMe','gohealth': 'GoHealth','gojek': 'Gojek','gokwik': 'GoKwik','gomechanic': 'GoMechanic','goodrx': 'GoodRx','google': 'Google','gopro': 'GoPro','gospotcheck': 'GoSpotCheck','gostudent': 'GoStudent','goto': 'GoTo','goto-group': 'GoTo Group','grail': 'GRAIL','gsr': 'GSR','gupy': 'Gupy','gympass': 'Gympass','healthcare-com': 'HealthCare.com','healthy-io': 'Healthy.io','help-com': 'Help.com','help-scout': 'Help Scout','here': 'HERE Technologies','hewlett-packard-enterprise': 'Hewlett Packard Enterprise','hibob': 'HiBob','head-digital-works': 'Head Digital Works','health-iq': 'Health IQ','halcyon-health': 'Halcyon Health','green-labs': 'Green Labs','gro-intelligence': 'Gro Intelligence','groundgame-health': 'GroundGame Health','goodgood': 'Good Good','goodworker': 'GoodWorker','gonuts': 'GoNuts','gowild': 'GoWild','graymeta': 'GrayMeta','gloo': 'Gloo','gloat': 'Gloat','gramophone': 'Gramophone'
}

manual_country = {
    'gloat':'US','gloo':'US','glorifi':'US','glossier':'US','glovo':'Spain','glowforge':'US','goat-group':'US','gobolt':'Canada','gocanvas':'US','godaddy':'US','gofundme':'US','gohealth':'US','golemon':'US','gong':'US','goodfood':'Canada','goodworker':'UK','goodrx':'US','google':'US','goop':'US','gopro':'US','gopuff':'US','gorillas':'Germany','gospotcheck':'US','gostudent':'Austria','goto':'US','gousto':'UK','gowild':'US','grabango':'US','grabcad':'US','grail':'US','grailed':'US','gramophone':'US','graphcore':'UK','graymeta':'US','greenhouse':'US','greenlight':'US','grin':'US','gro-intelligence':'US','groundgame-health':'US','group-nine-media':'US','groupon':'US','grove-collaborative':'US','grover':'Germany','grubhub':'US','gsr':'UK','guardant-health':'US','guideline':'US','guidewire':'US','guild':'US','gumgum':'US','hackerone':'US','hailo':'UK','halcyon-health':'US','happy-money':'US','hash':'UK','haus':'US','haven-technologies':'US','havenly':'US','headspace':'US','health-iq':'US','healthcare-com':'US','healthy-io':'UK','hedvig':'Sweden','hellofresh':'Germany','help-com':'US','help-scout':'US','her-campus-media':'US','here':'Netherlands','hermd':'US','heroes':'UK','heureka-group':'Czech Republic','hewlett-packard-enterprise':'US','heycar':'Germany','heygo':'UK','heyjobs':'Germany','hibob':'UK','highradius':'US'
}

headers={'User-Agent':'Mozilla/5.0'}
ignore_domains = ['linkedin.com','glassdoor.com','indeed.com','ziprecruiter.com','joinhandshake.com','facebook.com','instagram.com','youtube.com','x.com','twitter.com','tiktok.com','wikipedia.org','play.google.com','apps.apple.com']
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
unsupported_pat = r'workday|jobvite|icims|successfactors|myworkdayjobs|bamboohr|personio|taleo|oraclecloud|teamtailor|comeet|jobylon|pinpoint|beapplied|join\.com|jobs\.sap|greenhouse-candidates|adp\.com|ukg\.net|ultipro|paylocity|eightfold|jobsoid|applytojob\.com|phenompeople|jobtrain|recruitcrm|homerun\.co|jobtoolz|avature|cornerstoneondemand|csod|careers-page\.com|dayforcehcm|smartjobboard|manatal|zoho\s+recruit'

session = requests.Session()
session.headers.update(headers)
cache_search = {}
cache_fetch = {}

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
    if query in cache_search:
        return cache_search[query]
    url='https://www.bing.com/search?format=rss&q='+quote(query)
    try:
        text=session.get(url,timeout=20).text
        root=ET.fromstring(text)
        out=[(item.findtext('title') or '', item.findtext('link') or '', item.findtext('description') or '') for item in root.findall('./channel/item')]
    except Exception:
        out=[]
    cache_search[query]=out
    return out


def fetch(url):
    if url in cache_fetch:
        return cache_fetch[url]
    try:
        r=session.get(url,timeout=20,allow_redirects=True)
        res=(r.url, r.text[:300000])
    except Exception:
        res=(url,'')
    cache_fetch[url]=res
    return res


def extract_links(base, page):
    links=[]
    for m in re.finditer(r'(?:href|src)=["\']([^"\']+)["\']', page, re.I):
        u=html.unescape(m.group(1).strip())
        if not u or u.startswith(('mailto:','tel:','javascript:','#','data:')):
            continue
        links.append(urljoin(base,u))
    out=[]; seen=set()
    for u in links:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def likely_official(link, name=''):
    ll=link.lower()
    if any(d in ll for d in ignore_domains):
        return False
    words=[w.lower() for w in re.findall(r'[a-zA-Z0-9]+', name) if len(w)>2]
    return not words or any(w in ll for w in words)


def likely_career_links(base, page):
    ranked=[]
    for u in extract_links(base,page):
        lu=u.lower()
        if any(d in lu for d in ignore_domains):
            continue
        score=0
        if detect_ats(lu): score += 12
        if re.search(r'career|careers|jobs|join-us|joinus|job-openings|open-positions|work-with-us|hiring|vacancies|openings', lu): score += 7
        if re.search(r'about\.|company\.|jobs\.|careers\.', lu): score += 3
        if score:
            ranked.append((score,u))
    ranked.sort(reverse=True)
    out=[]; seen=set()
    for score,u in ranked:
        if u not in seen:
            seen.add(u); out.append(u)
    return out[:10]


def inspect(url):
    final,page=fetch(url)
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


def find_result(name):
    checked=[]
    # 1. inspect careers search results directly
    careers_results=search(f'{name} careers')[:10]
    for title,link,desc in careers_results:
        if any(d in link.lower() for d in ignore_domains):
            continue
        combo=' '.join([title,link,desc])
        a=detect_ats(combo)
        if a:
            return a,link
        if likely_official(link,name) or re.search(r'career|job|join|hiring', combo, re.I):
            checked.append(link)
    # 2. inspect general search results including corporate/about domains
    for title,link,desc in search(name)[:8]:
        if any(d in link.lower() for d in ignore_domains):
            continue
        if likely_official(link,name):
            checked.append(link)
    # dedupe preserve order
    uniq=[]; seen=set()
    for link in checked:
        if link not in seen:
            seen.add(link); uniq.append(link)
    checked=uniq[:8]

    for link in checked:
        final,page,ats,embeds=inspect(link)
        if ats:
            return ats,final
        for u in likely_career_links(final,page)[:6]:
            f2,p2,a2,e2=inspect(u)
            if a2:
                return a2,f2
            # second hop from careers page
            for u2 in likely_career_links(f2,p2)[:4]:
                f3,p3,a3,e3=inspect(u2)
                if a3:
                    return a3,f3
    # 3. search jobs/join us and inspect results
    for q in [f'{name} jobs', f'{name} join us', f'{name} hiring']:
        for title,link,desc in search(q)[:8]:
            if any(d in link.lower() for d in ignore_domains):
                continue
            combo=' '.join([title,link,desc])
            a=detect_ats(combo)
            if a:
                return a,link
            if likely_official(link,name) or re.search(r'career|job|join|hiring', combo, re.I):
                final,page,ats,embeds=inspect(link)
                if ats:
                    return ats,final
                for u in likely_career_links(final,page)[:5]:
                    f2,p2,a2,e2=inspect(u)
                    if a2:
                        return a2,f2
    return 'unknown',''

rows=[]
for slug in slugs:
    name = name_overrides.get(slug, slug.replace('-', ' '))
    ats, career_url = find_result(name)
    rows.append([slug, ats, career_url, manual_country.get(slug,'')])

out='/Users/clare/Documents/workspace/job-board-crawler/research_full.csv'
with open(out,'w',newline='') as f:
    w=csv.writer(f)
    w.writerow(['slug','ats','career_url','hq_country'])
    w.writerows(rows)
print(out)
