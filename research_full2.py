import re, requests, html, xml.etree.ElementTree as ET, csv
from urllib.parse import quote, urljoin, urlparse

slugs = 'gloat,gloo,glorifi,glossier,glovo,glowforge,goat-group,gobear,gobolt,gocanvas,godaddy,gofundme,gohealth,gojek,gokada,gokwik,golemon,gomechanic,gong,gonuts,goodfood,goodgood,goodrx,goodworker,google,goop,gopro,gopuff,gorillas,gospotcheck,gostudent,goto,goto-group,gousto,gowild,grab,grabango,grabcad,grail,grailed,gramophone,graphcore,graphy,graymeta,green-labs,greenhouse,greenikk,greenlight,grin,gro-intelligence,groundgame-health,group-nine-media,groupon,grove-collaborative,grover,grubhub,gsr,guardant-health,guesty,guideline,guidewire,guild,gumgum,gupshup,gupy,gympass,hackerearth,hackerone,hailo,halcyon-health,halodoc,happay,happy-money,harappa,hash,haus,haven-technologies,havenly,head-digital-works,headspace,health-iq,healthcare-com,healthifyme,healthmatch,healthy-io,hedvig,hellofresh,help-com,help-scout,her-campus-media,here,hermd,heroes,heureka-group,hewlett-packard-enterprise,heycar,heygo,heyjobs,hibob,highradius'.split(',')
name_overrides = {'goat-group':'GOAT Group','gocanvas':'GoCanvas','godaddy':'GoDaddy','gofundme':'GoFundMe','gohealth':'GoHealth','gojek':'Gojek','gokwik':'GoKwik','gomechanic':'GoMechanic','goodrx':'GoodRx','google':'Google','gopro':'GoPro','gospotcheck':'GoSpotCheck','gostudent':'GoStudent','goto':'GoTo','goto-group':'GoTo Group','grail':'GRAIL','gsr':'GSR','gupy':'Gupy','gympass':'Gympass','healthcare-com':'HealthCare.com','healthy-io':'Healthy.io','help-com':'Help.com','help-scout':'Help Scout','here':'HERE Technologies','hewlett-packard-enterprise':'Hewlett Packard Enterprise','hibob':'HiBob','head-digital-works':'Head Digital Works','health-iq':'Health IQ','halcyon-health':'Halcyon Health','green-labs':'Green Labs','gro-intelligence':'Gro Intelligence','groundgame-health':'GroundGame Health','goodgood':'Good Good','goodworker':'GoodWorker','gonuts':'GoNuts','gowild':'GoWild','graymeta':'GrayMeta','gloo':'Gloo','gloat':'Gloat','gramophone':'Gramophone'}
manual_country = {'gloat':'US','gloo':'US','glorifi':'US','glossier':'US','glovo':'Spain','glowforge':'US','goat-group':'US','gobolt':'Canada','gocanvas':'US','godaddy':'US','gofundme':'US','gohealth':'US','golemon':'US','gong':'US','goodfood':'Canada','goodworker':'UK','goodrx':'US','google':'US','goop':'US','gopro':'US','gopuff':'US','gorillas':'Germany','gospotcheck':'US','gostudent':'Austria','goto':'US','gousto':'UK','gowild':'US','grabango':'US','grabcad':'US','grail':'US','grailed':'US','gramophone':'US','graphcore':'UK','graymeta':'US','greenhouse':'US','greenlight':'US','grin':'US','gro-intelligence':'US','groundgame-health':'US','group-nine-media':'US','groupon':'US','grove-collaborative':'US','grover':'Germany','grubhub':'US','gsr':'UK','guardant-health':'US','guideline':'US','guidewire':'US','guild':'US','gumgum':'US','hackerone':'US','hailo':'UK','halcyon-health':'US','happy-money':'US','hash':'UK','haus':'US','haven-technologies':'US','havenly':'US','headspace':'US','health-iq':'US','healthcare-com':'US','healthy-io':'UK','hedvig':'Sweden','hellofresh':'Germany','help-com':'US','help-scout':'US','her-campus-media':'US','here':'Netherlands','hermd':'US','heroes':'UK','heureka-group':'Czech Republic','hewlett-packard-enterprise':'US','heycar':'Germany','heygo':'UK','heyjobs':'Germany','hibob':'UK','highradius':'US'}
headers={'User-Agent':'Mozilla/5.0'}
ignore_domains=['linkedin.com','glassdoor.com','indeed.com','ziprecruiter.com','joinhandshake.com','facebook.com','instagram.com','youtube.com','x.com','twitter.com','tiktok.com','wikipedia.org','play.google.com','apps.apple.com']
ats_patterns={'greenhouse':[r'boards\.greenhouse\.io',r'job-boards\.greenhouse\.io',r'grnh\.se'], 'lever':[r'jobs\.lever\.co',r'lever\.co'], 'ashby':[r'jobs\.ashbyhq\.com',r'ashbyhq\.com'], 'workable':[r'apply\.workable\.com',r'workable\.com'], 'recruitee':[r'recruitee\.com'], 'smartrecruiters':[r'careers\.smartrecruiters\.com',r'smartrecruiters\.com'], 'rippling':[r'ats\.rippling\.com'], 'gem':[r'jobs\.gem\.com',r'job-boards\.gem\.com',r'gem\.com/.*/careers']}
unsupported_pat=r'workday|jobvite|icims|successfactors|myworkdayjobs|bamboohr|personio|taleo|oraclecloud|teamtailor|comeet|jobylon|pinpoint|beapplied|join\.com|jobs\.sap|adp\.com|ukg\.net|ultipro|paylocity|eightfold|jobsoid|applytojob\.com|phenompeople|jobtrain|recruitcrm|homerun\.co|jobtoolz|avature|cornerstoneondemand|csod|careers-page\.com|dayforcehcm|smartjobboard|manatal'
s=requests.Session(); s.headers.update(headers)
cache_search={}; cache_fetch={}

def detect(text):
    if not text: return ''
    for ats,pats in ats_patterns.items():
        for pat in pats:
            if re.search(pat,text,re.I): return ats
    if re.search(unsupported_pat,text,re.I): return 'other'
    return ''

def search(q):
    if q in cache_search: return cache_search[q]
    try:
        xml=s.get('https://www.bing.com/search?format=rss&q='+quote(q),timeout=20).text
        root=ET.fromstring(xml)
        res=[(i.findtext('title') or '',i.findtext('link') or '',i.findtext('description') or '') for i in root.findall('./channel/item')]
    except Exception:
        res=[]
    cache_search[q]=res; return res

def fetch(url):
    if url in cache_fetch: return cache_fetch[url]
    try:
        r=s.get(url,timeout=20,allow_redirects=True)
        res=(r.url,r.text[:300000])
    except Exception:
        res=(url,'')
    cache_fetch[url]=res; return res

def links(base,page):
    out=[]; seen=set()
    for m in re.finditer(r'(?:href|src)=["\']([^"\']+)["\']',page,re.I):
        u=html.unescape(m.group(1).strip())
        if not u or u.startswith(('mailto:','tel:','javascript:','#','data:')): continue
        u=urljoin(base,u)
        if u not in seen: seen.add(u); out.append(u)
    return out

def inspect(url):
    final,page=fetch(url)
    a=detect(final+'\n'+page)
    if not a:
        for u in links(final,page)[:1500]:
            a=detect(u)
            if a: break
    return final,page,a

def career_candidates(base,page):
    cands=[]; seen=set()
    for u in links(base,page):
        lu=u.lower()
        if any(d in lu for d in ignore_domains): continue
        score=0
        if detect(lu): score+=10
        if re.search(r'career|careers|jobs|join-us|joinus|job-openings|open-positions|work-with-us|hiring|vacancies|openings',lu): score+=6
        if re.search(r'about\.|company\.|jobs\.|careers\.',lu): score+=3
        if score and u not in seen:
            seen.add(u); cands.append((score,u))
    return [u for _,u in sorted(cands, reverse=True)[:10]]

def official_results(name):
    words=[w.lower() for w in re.findall(r'[a-zA-Z0-9]+',name) if len(w)>2]
    res=[]
    for q in [f'{name} careers',name,f'{name} jobs']:
        for t,l,d in search(q)[:10]:
            ll=l.lower(); td=(t+' '+d).lower()
            if any(x in ll for x in ignore_domains): continue
            if words and not any(w in ll or w in td for w in words):
                continue
            if l not in res: res.append(l)
    return res[:8]

def domain_candidates(url):
    p=urlparse(url)
    host=p.netloc
    host=host[4:] if host.startswith('www.') else host
    scheme=p.scheme or 'https'
    c=[]
    for h in [host,'www.'+host,'careers.'+host,'jobs.'+host,'about.'+host]:
        c.append(f'{scheme}://{h}')
        c.append(f'{scheme}://{h}/careers')
        c.append(f'{scheme}://{h}/jobs')
    # keep unique sensible
    out=[]; seen=set()
    for u in c:
        if u not in seen:
            seen.add(u); out.append(u)
    return out[:12]

def find(name):
    res=official_results(name)
    for link in res:
        combo=' '.join(link)
    for link in res:
        a=detect(link)
        if a: return a,link
        f,p,a=inspect(link)
        if a: return a,f
        for u in career_candidates(f,p)[:6]:
            f2,p2,a2=inspect(u)
            if a2: return a2,f2
            for u2 in career_candidates(f2,p2)[:4]:
                f3,p3,a3=inspect(u2)
                if a3: return a3,f3
        for u in domain_candidates(f):
            f2,p2,a2=inspect(u)
            if a2: return a2,f2
            for u2 in career_candidates(f2,p2)[:3]:
                f3,p3,a3=inspect(u2)
                if a3: return a3,f3
    return 'unknown',''

rows=[]
for slug in slugs:
    name=name_overrides.get(slug,slug.replace('-',' '))
    ats,url=find(name)
    rows.append([slug,ats,url,manual_country.get(slug,'')])

with open('/Users/clare/Documents/workspace/job-board-crawler/research_full2.csv','w',newline='') as f:
    csv.writer(f).writerows([['slug','ats','career_url','hq_country'],*rows])
print('/Users/clare/Documents/workspace/job-board-crawler/research_full2.csv')
