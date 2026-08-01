import requests, re, html, base64, json, sys, time
from urllib.parse import quote, urlparse, parse_qs, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

SLUGS = 'remedy,remesh,remote-year,renmoney,renorun,rent-the-runway,repertoire-immune-medicines,replicated,researchgate,reserve,reshamandi,restaurant365,retention-com,retool,retrain-ai,rev-com,revel,revelate,reverb,revolut,rewire,reynen-court,rhino,rhumbix,ribbon,ridecell,rigetti-computing,rigup,ringcentral,riot-games,ripl,riseup,riskified,rivian,rivos,robin-ai,roblox-china,rock-content,rocket-companies,roku,roof-stacks,roofstock,root-insurance,route,rover,rows,ruangguru,rubica,rubicon-project,rubicon-technologies,rubius,rubrik,running-tide,runtastic,rupeek,saarthi-ai,sabi,sabre,sada,sadapay,safegraph,sage-therapeutics,sage-therapeutics-copy,saks-com,sales-boomerang,salesforce,salesloft,salsify,salto,sama,sambanova,sami,sampler,samsara,samsung,sana,sana-benefits,sanar,sandbox-vr,sandvine,sap,sap-labs,sapiens,sarcos,sas,satellogic,sauce-labs,sayurbox,scale-ai,scalefactor,scalefocus,scaler,schoolmint,science-37,scifi-foods,scoop,scope3,scoro,scribe-media,sea'.split(',')

DISPLAY = {
    'rev-com':'Rev.com','riot-games':'Riot Games','roof-stacks':'RoofStacks','scale-ai':'Scale AI','science-37':'Science 37',
    'sage-therapeutics-copy':'Sage Therapeutics','sap-labs':'SAP Labs','sandbox-vr':'Sandbox VR','sana-benefits':'Sana Benefits',
    'root-insurance':'Root Insurance','rocket-companies':'Rocket Companies','rent-the-runway':'Rent the Runway',
    'repertoire-immune-medicines':'Repertoire Immune Medicines','remote-year':'Remote Year','retention-com':'Retention.com',
    'reynen-court':'Reynen Court','rigetti-computing':'Rigetti Computing','roblox-china':'Roblox China','rock-content':'Rock Content',
    'rubicon-project':'Rubicon Project','rubicon-technologies':'Rubicon Technologies','running-tide':'Running Tide','saarthi-ai':'Saarthi AI',
    'safegraph':'SafeGraph','sales-boomerang':'Sales Boomerang','sami':'Sami','sanar':'Sanar','scifi-foods':'SciFi Foods',
    'scribe-media':'Scribe Media','sea':'Sea Limited'
}

HEADERS={'User-Agent':'Mozilla/5.0'}
KNOWN = {
    'greenhouse':['greenhouse.io'],
    'lever':['lever.co'],
    'ashby':['ashbyhq.com'],
    'workable':['workable.com'],
    'recruitee':['recruitee.com'],
    'smartrecruiters':['smartrecruiters.com'],
    'rippling':['ats.rippling.com','rippling-ats.com'],
    'gem':['gem.com'],
}
API_PLATFORMS={
    'greenhouse':'https://boards-api.greenhouse.io/v1/boards/{}/jobs',
    'lever':'https://api.lever.co/v0/postings/{}?mode=json',
    'ashby':'https://api.ashbyhq.com/posting-api/job-board/{}',
    'recruitee':'https://{}.recruitee.com/api/offers',
    'gem':'https://api.gem.com/job_board/v0/{}/job_posts/',
}

def display_name(slug):
    return DISPLAY.get(slug) or slug.replace('-copy','').replace('-com','.com').replace('-', ' ').title().replace('.Com','.com').replace(' Ai',' AI').replace(' Vr',' VR')

def decode_bing(href):
    if 'bing.com/ck/a' not in href:
        return href
    try:
        u=parse_qs(urlparse(href).query).get('u',[''])[0]
        if u.startswith('a1'): u=u[2:]
        return base64.b64decode(u+'='*(-len(u)%4)).decode('utf-8','ignore')
    except Exception:
        return href

def bing_results(query):
    try:
        text=requests.get('https://www.bing.com/search?q='+quote(query),headers=HEADERS,timeout=20).text
    except Exception:
        return []
    pattern=re.compile(r'<li class="b_algo".*?<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>(.*?)(?=</li>)', re.S)
    out=[]
    for href,title,rest in pattern.findall(text):
        url=decode_bing(html.unescape(href))
        title_txt=re.sub('<.*?>','',html.unescape(title)).strip()
        m=re.search(r'<p[^>]*>(.*?)</p>', rest, re.S)
        snippet=re.sub('<.*?>','',html.unescape(m.group(1) if m else '')).strip()
        out.append((url,title_txt,snippet))
    return out

def detect_ats_from_text(url,text):
    low=(url+'\n'+text[:200000]).lower()
    for ats, doms in KNOWN.items():
        if any(d in low for d in doms):
            return ats
    if '/careers/' in low and 'myworkdayjobs.com' in low:
        return 'other'
    return ''

def fetch(url):
    try:
        r=requests.get(url,headers=HEADERS,timeout=20,allow_redirects=True)
        return r.status_code, r.url, r.text
    except Exception:
        return None, url, ''

def domain(u):
    try: return urlparse(u).netloc.lower()
    except: return ''

def homepage_for(slug):
    q=display_name(slug)
    res=bing_results(q)
    bad={'linkedin.com','facebook.com','instagram.com','x.com','twitter.com','youtube.com','wikipedia.org','crunchbase.com','glassdoor.com'}
    for url,title,snip in res:
        d=domain(url)
        if not d or any(b in d for b in bad):
            continue
        if q.split()[0].lower().replace('.com','') in (d+title.lower()):
            return url
    for url,title,snip in res:
        d=domain(url)
        if d and not any(b in d for b in bad):
            return url
    return ''

def candidate_career_urls(home):
    c=[]
    if not home: return c
    home=home.rstrip('/')+'/'
    for path in ['careers','jobs','join-us','company/careers','about/careers','careers/','jobs/']:
        c.append(urljoin(home,path))
    st,final,text=fetch(home)
    for href in re.findall(r'href=["\']([^"\']+)["\']', text, re.I):
        full=urljoin(final, html.unescape(href))
        low=full.lower()
        if any(k in low for k in ['career','job','join-us','joinus','open-roles','openroles','hiring']) or any(dom in low for v in KNOWN.values() for dom in v):
            c.append(full)
    seen=[]
    for u in c:
        if u not in seen:
            seen.append(u)
    return seen[:20]

def api_probe(slug):
    variants={slug, slug.replace('-',''), slug.replace('-','_')}
    if slug.endswith('-com'):
        variants.add(slug[:-4])
    if slug.endswith('-copy'):
        variants.add(slug[:-5])
    matches=[]
    for token in variants:
        for ats,tmpl in API_PLATFORMS.items():
            try:
                r=requests.get(tmpl.format(token),headers=HEADERS,timeout=15)
                if r.status_code!=200 or 'json' not in r.headers.get('content-type',''):
                    continue
                j=r.json()
                ok=False; count=0
                if ats=='greenhouse' and isinstance(j,dict) and 'jobs' in j:
                    ok=True; count=len(j['jobs'])
                elif ats=='lever' and isinstance(j,list):
                    ok=True; count=len(j)
                elif ats=='ashby' and isinstance(j,dict) and ('jobs' in j or 'jobBoard' in j):
                    ok=True; count=len(j.get('jobs',[]))
                elif ats=='recruitee' and isinstance(j,dict) and 'offers' in j:
                    ok=True; count=len(j['offers'])
                elif ats=='gem' and isinstance(j,list):
                    ok=True; count=len(j)
                if ok:
                    matches.append((ats,token,count))
            except Exception:
                pass
    # prefer non-zero counts, then exact token order
    pref=sorted(matches, key=lambda t: ((t[2]<=0), t[0] not in ['greenhouse','lever','ashby','gem','recruitee'], t[1]!=slug, len(t[1])) )
    return pref[0] if pref else None

def board_url(ats, token):
    return {
        'greenhouse':f'https://job-boards.greenhouse.io/{token}',
        'lever':f'https://jobs.lever.co/{token}',
        'ashby':f'https://jobs.ashbyhq.com/{token}',
        'recruitee':f'https://{token}.recruitee.com/',
        'gem':f'https://www.gem.com/careers/{token}',
    }.get(ats,'')

def research(slug):
    result={'slug':slug,'ats':'','career_url':'','homepage':'','query':display_name(slug)}
    ap=api_probe(slug)
    if ap:
        ats,token,count=ap
        result['ats']=ats
        result['career_url']=board_url(ats, token)
    home=homepage_for(slug)
    result['homepage']=home
    cands=[]
    # search result candidates from career query first
    for url,title,snip in bing_results(display_name(slug)+' careers')[:10]:
        low=url.lower()
        if any(d in low for v in KNOWN.values() for d in v) or any(k in low for k in ['/careers','/jobs','careers.','jobs.','join-us']):
            cands.append(url)
    cands += candidate_career_urls(home)
    seen=[]
    for u in cands:
        if u not in seen: seen.append(u)
    for u in seen[:10]:
        st,final,text=fetch(u)
        ats=detect_ats_from_text(final,text)
        if ats:
            result['ats']=result['ats'] or ats
            result['career_url']=final
            return result
        if st and st < 400 and ('career' in final.lower() or 'job' in final.lower()):
            result['career_url']=final
    return result

rows=[]
for i,slug in enumerate(SLUGS,1):
    r=research(slug)
    rows.append(r)
    print(i, slug, r['ats'], r['career_url'], file=sys.stderr)

with open('research_results.json','w') as f:
    json.dump(rows,f,indent=2)
print('done', file=sys.stderr)
