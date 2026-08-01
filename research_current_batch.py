import csv, json, re, time, requests, urllib.parse
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

SLUGS = '''lighthouse-labs,lightico,lightricks,lightspeed-commerce,lilium,limeade,limelight,lingoace,linkedin,linkfire,linksquares,linktree,liongard,liv-up,liveperson,liveramp,livetiles,livevox,livspace,localize,loco,locomation,loft,loftium,loftsmart,log-9-materials,loggi,logically,logitech,loja-integrada,lola,longi,loom,loopme,lora-dicarlo,lordstown-motors,lsports,lucid-diagnostics,lucid-motors,lucid-software,lucira-health,ludeo,ludia,lululemon-studio,lumenad,lumina-networks,luminar,lummo,lunchbox,lunchtime,luno,lunya,lusha,luxury-presence,lyra-health,lyric,lyst,lytics,m1,made-com,made-renovation,madefire,madeiramadeira,magic-eden,magic-leap,magicbricks,magnite,mainstreet,mainvest,make-school,makemytrip,makerbot,malwarebytes,mamaearth,manhattan-associates,manomano,mapbox,mapify,mara,mariadb,marin-software,mark43,marketsource,markforged,marqeta,marvell,masse,masterclass,match-group,matrixport,matter-labs,matterport,maven,maven-clinic,mavenir,maxmilhas,may-mobility,mcmakler,me-poupe,meati'''.split(',')

NAME_OVERRIDES = {
    'm1': 'M1 Finance',
    'lola': 'Lola.com',
    'lightspeed-commerce': 'Lightspeed Commerce',
    'lightico': 'Lightico',
    'lightricks': 'Lightricks',
    'liv-up': 'Liv Up',
    'livetiles': 'LiveTiles',
    'livevox': 'LiveVox',
    'log-9-materials': 'Log9 Materials',
    'loja-integrada': 'Loja Integrada',
    'longi': 'LONGi',
    'lsports': 'LSports',
    'lucid-diagnostics': 'Lucid Diagnostics',
    'lucid-motors': 'Lucid Motors',
    'lucid-software': 'Lucid Software',
    'lululemon-studio': 'lululemon Studio',
    'lumenad': 'LumenAd',
    'lumina-networks': 'Lumina Networks',
    'luxury-presence': 'Luxury Presence',
    'lyra-health': 'Lyra Health',
    'made-com': 'Made.com',
    'made-renovation': 'Made Renovation',
    'magic-eden': 'Magic Eden',
    'magic-leap': 'Magic Leap',
    'manhattan-associates': 'Manhattan Associates',
    'marin-software': 'Marin Software',
    'mark43': 'Mark43',
    'match-group': 'Match Group',
    'matter-labs': 'Matter Labs',
    'maven-clinic': 'Maven Clinic',
    'may-mobility': 'May Mobility',
    'me-poupe': 'Me Poupe!',
}

HQ = {
    'lighthouse-labs':'Canada','lightico':'','lightricks':'','lightspeed-commerce':'Canada','lilium':'Germany','limeade':'US','limelight':'US','lingoace':'','linkedin':'US','linkfire':'Denmark','linksquares':'US','linktree':'','liongard':'US','liv-up':'','liveperson':'US','liveramp':'US','livetiles':'','livevox':'US','livspace':'','localize':'US','loco':'','locomation':'US','loft':'','loftium':'US','loftsmart':'','log-9-materials':'','loggi':'','logically':'UK','logitech':'Switzerland','loja-integrada':'','lola':'US','longi':'','loom':'US','loopme':'UK','lora-dicarlo':'US','lordstown-motors':'US','lsports':'','lucid-diagnostics':'US','lucid-motors':'US','lucid-software':'US','lucira-health':'US','ludeo':'','ludia':'Canada','lululemon-studio':'Canada','lumenad':'','lumina-networks':'US','luminar':'US','lummo':'','lunchbox':'US','lunchtime':'','luno':'UK','lunya':'US','lusha':'','luxury-presence':'US','lyra-health':'US','lyric':'US','lyst':'UK','lytics':'US','m1':'US','made-com':'UK','made-renovation':'US','madefire':'US','madeiramadeira':'','magic-eden':'US','magic-leap':'US','magicbricks':'','magnite':'US','mainstreet':'US','mainvest':'US','make-school':'US','makemytrip':'','makerbot':'US','malwarebytes':'US','mamaearth':'','manhattan-associates':'US','manomano':'France','mapbox':'US','mapify':'Germany','mara':'Canada','mariadb':'US','marin-software':'US','mark43':'US','marketsource':'US','markforged':'US','marqeta':'US','marvell':'US','masse':'','masterclass':'US','match-group':'US','matrixport':'','matter-labs':'Germany','matterport':'US','maven':'US','maven-clinic':'US','mavenir':'US','maxmilhas':'','may-mobility':'US','mcmakler':'Germany','me-poupe':'','meati':'US'
}

BOARD_OVERRIDES = {
    'lightspeed-commerce': [('ashby','lightspeedhq')],
    'magic-leap': [('greenhouse','magicleap')],
    'loom': [('greenhouse','loom')],
    'may-mobility': [('greenhouse','maymobility')],
    'lyra-health': [('greenhouse','lyrahealth')],
    'm1': [('lever','m1finance')],
    'markforged': [('greenhouse','markforged')],
    'luminar': [('lever','luminar')],
    'matterport': [('greenhouse','matterport')],
    'mainstreet': [('ashby','mainstreet')],
    'mainvest': [('greenhouse','mainvest')],
    'mapbox': [('greenhouse','mapbox')],
    'marqeta': [('greenhouse','marqeta')],
    'magnite': [('greenhouse','magnite')],
    'mcmakler': [('greenhouse','mcmakler')],
}

UA={'User-Agent':'Mozilla/5.0'}
BLOCKED={'linkedin.com','indeed.com','glassdoor.com','welcometothejungle.com','wellfound.com','pitchbook.com','wikipedia.org','crunchbase.com','jobera.com','hyring.com','resumeset.com','ziprecruiter.com','facebook.com','instagram.com','x.com','youtube.com','rocketreach.co'}
SUPPORTED=[('greenhouse',['boards.greenhouse.io','job-boards.greenhouse.io','grnh.se','boards-api.greenhouse.io','greenhouse.io']),('lever',['jobs.lever.co','api.lever.co','lever.co']),('ashby',['jobs.ashbyhq.com','api.ashbyhq.com','ashbyhq.com']),('workable',['apply.workable.com','workable.com']),('recruitee',['recruitee.com']),('smartrecruiters',['smartrecruiters.com']),('rippling',['ats.rippling.com','rippling.com']),('gem',['jobs.gem.com','api.gem.com','job-boards.gem.com'])]
OTHER_HINTS=['myworkdayjobs.com','workday.com','wd1.myworkdaysite.com','wd5.myworkdaysite.com','icims.com','jobvite.com','successfactors.com','bamboohr.com','teamtailor.com','personio','oraclecloud.com','paylocity.com','applytojob.com','adp.com','taleo.net','careerplug.com','workforcenow.adp.com','comeet.co','jobylon.com','pinpointhq.com','beapplied.com','join.com','jobscore.com','breezy.hr']

session=requests.Session(); session.headers.update(UA)

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.href=None; self.text=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='a':
            self.href=attrs.get('href'); self.text=[]
    def handle_data(self, data):
        if self.href is not None: self.text.append(data)
    def handle_endtag(self, tag):
        if tag=='a' and self.href is not None:
            self.links.append((self.href,''.join(self.text).strip())); self.href=None; self.text=[]

def domain(url):
    try:
        d=urlparse(url).netloc.lower()
        return d[4:] if d.startswith('www.') else d
    except: return ''

def clean_url(url):
    return url.split('#',1)[0] if url else ''

def is_blocked(url):
    d=domain(url)
    return any(d==b or d.endswith('.'+b) for b in BLOCKED)

def detect_ats(*texts):
    text='\n'.join(t for t in texts if t)
    low=text.lower()
    for ats,pats in SUPPORTED:
        if any(p in low for p in pats): return ats
    if any(h in low for h in OTHER_HINTS): return 'other'
    return 'unknown'

def fetch(url, method='GET'):
    try:
        r=session.request(method, url, timeout=18, allow_redirects=True)
        return r
    except Exception:
        return None

def bing_rss(query):
    try:
        r=session.get('https://www.bing.com/search', params={'q': query, 'format':'rss'}, timeout=18)
        root=ET.fromstring(r.text)
        out=[]
        for item in root.findall('.//item')[:10]:
            out.append({'title':item.findtext('title') or '', 'link':item.findtext('link') or '', 'description':item.findtext('description') or ''})
        return out
    except Exception:
        return []

def links_from_html(html_text, base_url):
    parser=LinkParser()
    try: parser.feed(html_text)
    except Exception: pass
    out=[]
    for href,text in parser.links:
        if not href: continue
        href=unescape(href.strip())
        if href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('tel:'): continue
        full=clean_url(urljoin(base_url, href))
        out.append((full,text.strip()))
    return out

def candidate_board_ids(slug):
    out=[]
    base=slug.lower()
    compact=base.replace('-','')
    tokens=base.split('-')
    vals=[base, compact]
    if len(tokens)>1:
        vals.append(tokens[0])
        vals.append(''.join(tokens[:2]))
    if base.endswith('-commerce'):
        vals.append(base.replace('-commerce',''))
    seen=[]
    for v in vals:
        if v and v not in seen: seen.append(v)
    return seen

def probe_direct(slug):
    candidates=[]
    for ats,board in BOARD_OVERRIDES.get(slug,[]):
        candidates.append((ats,board))
    for board in candidate_board_ids(slug):
        for ats in ['greenhouse','lever','ashby','workable','recruitee','smartrecruiters','gem','rippling']:
            candidates.append((ats,board))
    for ats,board in candidates:
        try:
            if ats=='greenhouse':
                url=f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs'
                r=fetch(url)
                if r and r.status_code==200 and 'jobs' in r.text:
                    return ats, f'https://boards.greenhouse.io/{board}'
            elif ats=='lever':
                url=f'https://api.lever.co/v0/postings/{board}?mode=json'
                r=fetch(url)
                if r and r.status_code==200 and r.text.strip().startswith('['):
                    return ats, f'https://jobs.lever.co/{board}'
            elif ats=='ashby':
                url=f'https://api.ashbyhq.com/posting-api/job-board/{board}'
                r=fetch(url)
                if r and r.status_code==200 and 'jobs' in r.text:
                    return ats, f'https://jobs.ashbyhq.com/{board}'
            elif ats=='workable':
                url=f'https://apply.workable.com/api/v1/widget/accounts/{board}?details=true'
                r=fetch(url)
                if r and r.status_code==200 and 'jobs' in r.text:
                    return ats, f'https://apply.workable.com/{board}'
            elif ats=='recruitee':
                url=f'https://{board}.recruitee.com/api/offers'
                r=fetch(url)
                if r and r.status_code==200 and 'offers' in r.text:
                    return ats, f'https://{board}.recruitee.com'
            elif ats=='smartrecruiters':
                board_url=f'https://jobs.smartrecruiters.com/{board}'
                r=fetch(board_url)
                if r and r.status_code==200:
                    final=clean_url(r.url)
                    if 'smartrecruiters.com' in domain(final) and final.rstrip('/') not in ['https://jobs.smartrecruiters.com','https://careers.smartrecruiters.com'] and board.lower() in final.lower():
                        return ats, final
            elif ats=='gem':
                url=f'https://api.gem.com/job_board/v0/{board}/job_posts/'
                r=fetch(url)
                if r and r.status_code==200 and (r.text.strip().startswith('[') or 'job_posts' in r.text):
                    return ats, f'https://jobs.gem.com/{board}'
            elif ats=='rippling':
                for lang in ['en-US','en-CA','en']:
                    url=f'https://ats.rippling.com/{lang}/{board}/jobs' if lang!='en' else f'https://ats.rippling.com/{board}/jobs'
                    r=fetch(url)
                    if r and r.status_code==200 and ('__NEXT_DATA__' in r.text or '/jobs/' in r.text):
                        return ats, clean_url(r.url)
        except Exception:
            pass
    return None, ''

def choose_homepage(slug, items):
    tokens=[t for t in re.split(r'[-\s]+', slug.lower()) if t]
    scored=[]
    for it in items:
        url=clean_url(it['link'])
        if not url or is_blocked(url): continue
        d=domain(url); path=urlparse(url).path.lower(); title_desc=(it['title']+' '+it['description']).lower()
        score=0
        if path in ('','/'): score+=4
        if any(tok in d.replace('.','-') for tok in tokens[:2]): score+=3
        if all(tok in (d.replace('.','-')+' '+title_desc) for tok in tokens[:1]): score+=2
        if any(x in path for x in ['career','job','join']): score-=2
        if any(x in path for x in ['login','support','help']): score-=3
        scored.append((score,url))
    scored.sort(reverse=True)
    return scored[0][1] if scored else ''

def probe_paths(homepage):
    if not homepage: return []
    p=urlparse(homepage); origin=f'{p.scheme}://{p.netloc}'
    return [origin+s for s in ['/careers','/careers/','/jobs','/jobs/','/about/careers','/company/careers','/join-us','/joinus','/careers/jobs']]

def find_career(slug):
    name=NAME_OVERRIDES.get(slug, slug.replace('-', ' '))
    # direct ATS API probe first
    ats,url=probe_direct(slug)
    if ats:
        return {'slug':slug,'ats':ats,'career_url':url,'hq_country':HQ.get(slug,''),'source':'direct'}
    items=[]
    for q in [f'{name} careers', f'{name} jobs']:
        items.extend(bing_rss(q))
    # direct ATS result from search results
    candidates=[]
    for it in items:
        url=clean_url(it['link'])
        if not url or is_blocked(url): continue
        title_desc=(it['title']+' '+it['description'])
        ats=detect_ats(url, title_desc)
        score=0
        if ats!='unknown': score+=8
        if re.search(r'career|jobs|hiring|open positions|work with us', title_desc, re.I): score+=4
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
        links=links_from_html(text, final)
        for href,txt in links[:500]:
            sats=detect_ats(href,txt)
            s=0
            if re.search(r'career|jobs|join us|open positions|hiring', href+' '+txt, re.I): s+=4
            if sats!='unknown': s+=6
            if s>0: candidates.append((s+1, href if sats!='unknown' else final, sats if sats!='unknown' else ats))
        if score>best_page[2]: best_page=(final, ats, score)
    if candidates:
        candidates.sort(key=lambda x:x[0], reverse=True)
        url,ats=candidates[0][1], candidates[0][2]
        if ats=='unknown':
            r=fetch(url)
            if r and r.status_code<400:
                ats=detect_ats(r.url, r.text)
                url=clean_url(r.url)
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
with open('/Users/clare/Documents/workspace/job-board-crawler/research_current_batch.csv','w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['slug','ats','career_url','hq_country'])
    w.writeheader()
    for r in rows:
        w.writerow({k:r[k] for k in ['slug','ats','career_url','hq_country']})
print('DONE', len(rows))
