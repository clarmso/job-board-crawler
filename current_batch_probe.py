import csv, json, re, requests
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

SLUGS = '''inmobi,innovaccer,innovid,innoviz,inscribe,inscripta,insider,insider-intelligence,insightec,inspectify,inspirato,instacart,instagram,instamojo,instructure,insurstaq-ai,intapp,integral-ad-science,integrate,integrate-ai,intel,intelycare,intercom,intersect,interview-kickstart,intrinsic,introhive,intuit,inuitive,investcloud,invision,invitae,involves,iprice-group,iqiyi-smart,iress,iris-nova,irl,irobot,iron-ox,ironnet,ispecimen,jam-city,jama,jamf,jasper,jasper-health,jd-id,jellyfish,jellysmack,jetclosing,jetty,jimdo,jiobit,jiviai,jobcase,jodo,join,jokr,joonko,jounce-therapeutics,journera,jumia,jumio,jump,jumpcloud,jungle-scout,junglee-games,juni,juniper,juniper-networks,juniper-square,jupiterone,just-eat,just-eat-takeaway,juul,kaiyo,kaleidoscope,kaltura,kandela,kandji,kaodim,kape,kape-technologies,kapten-free-now,karakuki,karat,karat-financial,karbon,karhoo,karma,karshare,kaseya,kaspersky,kaspien,katana,katerra,kavak,kayak-opentable,kazoo'''.split(',')
NAME_OVERRIDES = {
    'insider-intelligence':'Insider Intelligence', 'integral-ad-science':'Integral Ad Science',
    'integrate-ai':'Integrate.ai', 'interview-kickstart':'Interview Kickstart', 'iron-ox':'Iron Ox',
    'jam-city':'Jam City', 'jasper-health':'Jasper Health', 'iprice-group':'iPrice Group', 'iqiyi-smart':'iQIYI Smart',
    'jounce-therapeutics':'Jounce Therapeutics', 'jungle-scout':'Jungle Scout', 'junglee-games':'Junglee Games',
    'juniper-networks':'Juniper Networks', 'juniper-square':'Juniper Square', 'just-eat-takeaway':'Just Eat Takeaway',
    'kape-technologies':'Kape Technologies', 'kapten-free-now':'FREE NOW', 'karat-financial':'Karat Financial',
    'kayak-opentable':'KAYAK OpenTable', 'iris-nova':'Iris Nova', 'jd-id':'JD.ID', 'intelycare':'IntelyCare',
    'instamojo':'Instamojo', 'insightec':'Insightec', 'introhive':'Introhive', 'instructure':'Instructure',
    'integrate':'Integrate', 'integrate-ai':'Integrate.ai', 'jiviai':'Jivi AI', 'jodo':'Jodo', 'jokr':'Jokr',
    'jiobit':'Jiobit', 'joonko':'Joonko', 'kaiyo':'Kaiyo', 'kandela':'Kandela', 'kandji':'Kandji', 'kaseya':'Kaseya',
    'kaspien':'Kaspien', 'kazoo':'Kazoo', 'just-eat':'Just Eat'
}
HQ = {'inmobi':'','innovaccer':'US','innovid':'US','innoviz':'','inscribe':'US','inscripta':'US','insider':'','insider-intelligence':'US','insightec':'','inspectify':'US','inspirato':'US','instacart':'US','instagram':'US','instamojo':'','instructure':'US','insurstaq-ai':'','intapp':'US','integral-ad-science':'US','integrate':'US','integrate-ai':'Canada','intel':'US','intelycare':'US','intercom':'US','intersect':'','interview-kickstart':'US','intrinsic':'US','introhive':'Canada','intuit':'US','inuitive':'','investcloud':'US','invision':'US','invitae':'US','involves':'','iprice-group':'','iqiyi-smart':'','iress':'','iris-nova':'US','irl':'US','irobot':'US','iron-ox':'US','ironnet':'US','ispecimen':'US','jam-city':'US','jama':'US','jamf':'US','jasper':'US','jasper-health':'US','jd-id':'','jellyfish':'US','jellysmack':'US','jetclosing':'US','jetty':'US','jimdo':'Germany','jiobit':'US','jiviai':'','jobcase':'US','jodo':'','join':'Germany','jokr':'US','joonko':'','jounce-therapeutics':'US','journera':'US','jumia':'Germany','jumio':'US','jump':'','jumpcloud':'US','jungle-scout':'US','junglee-games':'','juni':'Sweden','juniper':'US','juniper-networks':'US','juniper-square':'US','jupiterone':'US','just-eat':'UK','just-eat-takeaway':'Netherlands','juul':'US','kaiyo':'US','kaleidoscope':'US','kaltura':'US','kandela':'US','kandji':'US','kaodim':'','kape':'UK','kape-technologies':'UK','kapten-free-now':'Germany','karakuki':'','karat':'US','karat-financial':'US','karbon':'US','karhoo':'UK','karma':'US','karshare':'UK','kaseya':'US','kaspersky':'','kaspien':'US','katana':'Estonia','katerra':'US','kavak':'','kayak-opentable':'US','kazoo':'US'}
BOARD_OVERRIDES = {
    'instacart': [('greenhouse','instacart')],
    'inmobi': [('greenhouse','inmobi')],
    'jumio': [('greenhouse','jumio')],
    'kaseya': [('greenhouse','kaseya')],
    'jamf': [('greenhouse','jamf')],
    'jellyfish': [('greenhouse','jellyfish')],
    'juniper-square': [('greenhouse','junipersquare')],
    'jumpcloud': [('greenhouse','jumpcloud')],
    'juul': [('greenhouse','juullabs')],
    'kandji': [('ashby','kandji')],
    'karat': [('greenhouse','karat')],
    'karbon': [('lever','karbon')],
    'karhoo': [('greenhouse','karhoo')],
    'katana': [('ashby','katanamrp')],
}
UA={'User-Agent':'Mozilla/5.0'}
BLOCKED={'linkedin.com','indeed.com','glassdoor.com','welcometothejungle.com','wellfound.com','pitchbook.com','wikipedia.org','crunchbase.com','jobera.com','hyring.com','resumeset.com','ziprecruiter.com','facebook.com','instagram.com','x.com','youtube.com','rocketreach.co'}
SUPPORTED=[('greenhouse',['boards.greenhouse.io','job-boards.greenhouse.io','grnh.se','boards-api.greenhouse.io','greenhouse.io']),('lever',['jobs.lever.co','api.lever.co','lever.co']),('ashby',['jobs.ashbyhq.com','api.ashbyhq.com','ashbyhq.com']),('workable',['apply.workable.com','workable.com']),('recruitee',['recruitee.com']),('smartrecruiters',['smartrecruiters.com']),('rippling',['ats.rippling.com','rippling.com']),('gem',['jobs.gem.com','api.gem.com','job-boards.gem.com','gem.com/careers'])]
OTHER_HINTS=['myworkdayjobs.com','workday.com','wd1.myworkdaysite.com','wd5.myworkdaysite.com','icims.com','jobvite.com','successfactors.com','bamboohr.com','teamtailor.com','personio','oraclecloud.com','paylocity.com','applytojob.com','adp.com','taleo.net','careerplug.com','workforcenow.adp.com','comeet.co','jobylon.com','pinpointhq.com','beapplied.com','join.com','jobscore.com','breezy.hr']
session=requests.Session(); session.headers.update(UA)

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.href=None; self.text=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='a': self.href=attrs.get('href'); self.text=[]
    def handle_data(self, data):
        if self.href is not None: self.text.append(data)
    def handle_endtag(self, tag):
        if tag=='a' and self.href is not None:
            self.links.append((self.href,''.join(self.text).strip())); self.href=None; self.text=[]

def domain(url):
    try:
        d=urlparse(url).netloc.lower(); return d[4:] if d.startswith('www.') else d
    except: return ''

def clean_url(url): return url.split('#',1)[0] if url else ''
def is_blocked(url):
    d=domain(url); return any(d==b or d.endswith('.'+b) for b in BLOCKED)

def detect_ats(*texts):
    text='\n'.join(t for t in texts if t); low=text.lower()
    for ats,pats in SUPPORTED:
        if any(p in low for p in pats): return ats
    if any(h in low for h in OTHER_HINTS): return 'other'
    return 'unknown'

def fetch(url, method='GET'):
    try: return session.request(method, url, timeout=18, allow_redirects=True)
    except: return None

def bing_rss(query):
    try:
        r=session.get('https://www.bing.com/search', params={'q':query, 'format':'rss'}, timeout=18)
        root=ET.fromstring(r.text)
        return [{'title':i.findtext('title') or '', 'link':i.findtext('link') or '', 'description':i.findtext('description') or ''} for i in root.findall('.//item')[:10]]
    except: return []

def links_from_html(html_text, base_url):
    p=LinkParser()
    try: p.feed(html_text)
    except: pass
    out=[]
    for href,text in p.links:
        if not href: continue
        href=unescape(href.strip())
        if href.startswith(('javascript:','mailto:','tel:')): continue
        out.append((clean_url(urljoin(base_url, href)), text.strip()))
    return out

def candidate_board_ids(slug):
    base=slug.lower(); compact=base.replace('-',''); toks=base.split('-')
    vals=[base,compact]
    if len(toks)>1:
        vals += [toks[0], ''.join(toks[:2]), '-'.join(toks[:2])]
    if base.endswith('-networks'): vals.append(base.replace('-networks',''))
    if base.endswith('-science'): vals.append(base.replace('-science',''))
    seen=[]
    for v in vals:
        if v and v not in seen: seen.append(v)
    return seen

def probe_direct(slug):
    candidates=[]
    candidates.extend(BOARD_OVERRIDES.get(slug,[]))
    for board in candidate_board_ids(slug):
        for ats in ['greenhouse','lever','ashby','workable','recruitee','smartrecruiters','gem','rippling']:
            candidates.append((ats,board))
    seen=set()
    for ats,board in candidates:
        if (ats,board) in seen: continue
        seen.add((ats,board))
        try:
            if ats=='greenhouse':
                r=fetch(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true')
                if r and r.status_code==200 and '"jobs":[' in r.text and 'absolute_url' in r.text:
                    return ats, f'https://job-boards.greenhouse.io/{board}'
            elif ats=='lever':
                r=fetch(f'https://api.lever.co/v0/postings/{board}?mode=json')
                if r and r.status_code==200 and r.text.strip().startswith('[') and len(r.text)>2:
                    return ats, f'https://jobs.lever.co/{board}'
            elif ats=='ashby':
                r=fetch(f'https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true')
                if r and r.status_code==200 and '"jobs"' in r.text and len(r.text)>40:
                    return ats, f'https://jobs.ashbyhq.com/{board}'
            elif ats=='workable':
                r=fetch(f'https://apply.workable.com/api/v1/widget/accounts/{board}?details=true')
                if r and r.status_code==200 and '"jobs"' in r.text and len(r.text)>20:
                    return ats, f'https://apply.workable.com/{board}'
            elif ats=='recruitee':
                r=fetch(f'https://{board}.recruitee.com/api/offers')
                if r and r.status_code==200 and 'offers' in r.text and len(r.text)>20:
                    return ats, f'https://{board}.recruitee.com'
            elif ats=='smartrecruiters':
                r=fetch(f'https://api.smartrecruiters.com/v1/companies/{board}/postings?limit=1')
                if r and r.status_code==200 and '"content"' in r.text and 'totalFound' in r.text and 'company' in r.text:
                    return ats, f'https://jobs.smartrecruiters.com/{board}'
            elif ats=='gem':
                r=fetch(f'https://api.gem.com/job_board/v0/{board}/job_posts/')
                if r and r.status_code==200 and (r.text.strip().startswith('[') or 'job_posts' in r.text):
                    return ats, f'https://jobs.gem.com/{board}'
            elif ats=='rippling':
                for url in [f'https://ats.rippling.com/{board}/jobs', f'https://ats.rippling.com/en-US/{board}/jobs', f'https://ats.rippling.com/en-CA/{board}/jobs']:
                    r=fetch(url)
                    if r and r.status_code==200 and ('__NEXT_DATA__' in r.text or '/jobs/' in r.text):
                        return ats, clean_url(r.url)
        except: pass
    return None, ''

def choose_homepage(slug, items):
    tokens=[t for t in re.split(r'[-\s]+', slug.lower()) if t]
    scored=[]
    for it in items:
        url=clean_url(it['link'])
        if not url or is_blocked(url): continue
        d=domain(url); path=urlparse(url).path.lower(); td=(it['title']+' '+it['description']).lower()
        score=0
        if path in ('','/'): score+=4
        if any(tok in d.replace('.','-') for tok in tokens[:2]): score+=3
        if all(tok in (d.replace('.','-')+' '+td) for tok in tokens[:1]): score+=2
        if any(x in path for x in ['career','job','join']): score-=2
        scored.append((score,url))
    scored.sort(reverse=True)
    return scored[0][1] if scored else ''

def probe_paths(homepage):
    if not homepage: return []
    p=urlparse(homepage); origin=f'{p.scheme}://{p.netloc}'
    return [origin+s for s in ['/careers','/careers/','/jobs','/jobs/','/about/careers','/company/careers','/join-us','/joinus','/careers/jobs']]

def find_career(slug):
    ats,url=probe_direct(slug)
    if ats:
        return {'slug':slug,'ats':ats,'career_url':url,'hq_country':HQ.get(slug,''),'source':'direct'}
    name=NAME_OVERRIDES.get(slug, slug.replace('-', ' '))
    items=[]
    for q in [f'{name} careers', f'{name} jobs']:
        items.extend(bing_rss(q))
    candidates=[]
    for it in items:
        url=clean_url(it['link'])
        if not url or is_blocked(url): continue
        td=it['title']+' '+it['description']
        ats=detect_ats(url, td)
        score=0
        if ats!='unknown': score+=8
        if re.search(r'career|jobs|hiring|open positions|work with us', td, re.I): score+=4
        if re.search(r'/careers?|/jobs?|/join-us', url, re.I): score+=5
        if score>0: candidates.append((score,url,ats))
    homepage=choose_homepage(slug, items)
    pages=[]
    if homepage: pages.append(homepage)
    pages.extend(probe_paths(homepage))
    best_page=('','unknown',-999)
    checked=set()
    for page in pages[:10]:
        if page in checked: continue
        checked.add(page)
        r=fetch(page)
        if not r or r.status_code>=400: continue
        final=clean_url(r.url); text=r.text[:250000]
        ats=detect_ats(final,text)
        score=0
        if re.search(r'/careers?|/jobs?|/join-us', final, re.I): score+=4
        if ats!='unknown': score+=7
        for href,txt in links_from_html(text, final)[:500]:
            sats=detect_ats(href,txt)
            s=0
            if re.search(r'career|jobs|join us|open positions|hiring', href+' '+txt, re.I): s+=4
            if sats!='unknown': s+=6
            if s>0: candidates.append((s+1, href if sats!='unknown' else final, sats if sats!='unknown' else ats))
        if score>best_page[2]: best_page=(final,ats,score)
    if candidates:
        candidates.sort(key=lambda x:x[0], reverse=True)
        url,ats=candidates[0][1], candidates[0][2]
        if ats=='unknown':
            r=fetch(url)
            if r and r.status_code<400:
                ats=detect_ats(r.url,r.text); url=clean_url(r.url)
        if ats=='unknown': ats='other' if url else 'unknown'
        return {'slug':slug,'ats':ats,'career_url':url,'hq_country':HQ.get(slug,''),'source':'search'}
    if best_page[0]:
        ats=best_page[1]
        if ats=='unknown': ats='other' if re.search(r'careers?|jobs?', best_page[0], re.I) else 'unknown'
        return {'slug':slug,'ats':ats,'career_url':best_page[0],'hq_country':HQ.get(slug,''),'source':'page'}
    return {'slug':slug,'ats':'unknown','career_url':'','hq_country':HQ.get(slug,''),'source':'none'}

rows=[]
with ThreadPoolExecutor(max_workers=8) as ex:
    futs={ex.submit(find_career, slug): slug for slug in SLUGS}
    for fut in as_completed(futs):
        row=fut.result(); rows.append(row); print(json.dumps(row), flush=True)
rows.sort(key=lambda r: SLUGS.index(r['slug']))
with open('current_batch_probe.csv','w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['slug','ats','career_url','hq_country'])
    w.writeheader(); [w.writerow({k:r[k] for k in ['slug','ats','career_url','hq_country']}) for r in rows]
print('DONE',len(rows))
