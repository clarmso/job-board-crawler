import base64, csv, html, json, re, time
from urllib.parse import quote_plus, unquote, urljoin, urlparse
import requests

SLUGS='''sunday,sundaysky,sunfolding,superhuman,superlearn,superloop,supernal,superops,superpedestrian,superrare,sure,surveymonkey,swappie,sweetescape,sweetgreen,swiggy,swing-education,sword-health,swvl,swyft,swyftx,syft-technologies,symend,synamedia,synapse,synapsefi,synapsica,synctera,synergysuite,synlogic,synopsys,synthego,syte,tabnine,taboola,tackle,tackle-io,tada,tails-com,tailwind-labs,take-two,take-two-interactive,takeoff,takl,talent-com,talis-biomedical,talkdesk,talkwalker,tally,tamara-mellon,tanium,tapas-media,tapps-games,taskus,taxbit,taxfix,tcr2,teachmint,teads,teampay,teamwork,techadvance,techcrunch,techtarget,tekion,teladoc-health,telenav,teleport,tempo-automation,tempus-ex,ten-square-games,tenable,tencent,tenurex,teradata,terminus,tesla,tessera,textio,textnow,the-appraisal-lane,the-athletic,the-gist,the-good-glamm-group,the-grommet,the-guild,the-iconic,the-meet-group,the-messenger,the-modist,the-mom-project,the-muse,the-org,the-predictive-index,the-realreal,the-sill,the-trade-desk,the-wing,the-zebra,thegist'''.split(',')

ATS_PATTERNS=[
    ('greenhouse',[r'greenhouse\.io',r'boards-api\.greenhouse\.io',r'boards\.greenhouse\.io',r'job-boards\.greenhouse\.io']),
    ('lever',[r'lever\.co']),
    ('ashby',[r'ashbyhq\.com']),
    ('workable',[r'workable\.com']),
    ('recruitee',[r'recruitee\.com']),
    ('smartrecruiters',[r'smartrecruiters\.com']),
    ('rippling',[r'rippling\.com']),
    ('gem',[r'jobs\.gem\.com', r'api\.gem\.com/job_board']),
]
EXCLUDE_DOMAINS=['linkedin.com','glassdoor.','indeed.','wellfound.','wikipedia.org','facebook.com','instagram.com','x.com','twitter.com','youtube.com','builtin.com','comparably.com','levels.fyi','crunchbase.com']
SESSION=requests.Session()
SESSION.headers.update({'User-Agent':'Mozilla/5.0'})

existing={}
with open('/Users/clare/Documents/workspace/job-board-crawler/companies.csv', newline='') as f:
    for row in csv.DictReader(f):
        existing[row['slug'].lower()] = row

MANUAL_HQ={
'sunday':'France','sundaysky':'US','sunfolding':'US','superhuman':'US','superlearn':'UK','superloop':'',
'supernal':'US','superops':'US','superpedestrian':'US','superrare':'US','sure':'US','surveymonkey':'US',
'swappie':'Finland','sweetescape':'','sweetgreen':'US','swiggy':'','swing-education':'US','sword-health':'Portugal',
'swvl':'','swyft':'US','swyftx':'','syft-technologies':'','symend':'Canada','synamedia':'UK','synapse':'US',
'synapsefi':'US','synapsica':'','synctera':'US','synergysuite':'Canada','synlogic':'US','synopsys':'US',
'synthego':'US','syte':'','tabnine':'','taboola':'US','tackle':'US','tackle-io':'US','tada':'',
'tails-com':'UK','tailwind-labs':'US','take-two':'US','take-two-interactive':'US','takeoff':'US','takl':'US',
'talent-com':'Canada','talis-biomedical':'US','talkdesk':'US','talkwalker':'Luxembourg','tally':'Belgium',
'tamara-mellon':'US','tanium':'US','tapas-media':'US','tapps-games':'','taskus':'US','taxbit':'US',
'taxfix':'Germany','tcr2':'US','teachmint':'','teads':'US','teampay':'US','teamwork':'Ireland',
'techadvance':'','techcrunch':'US','techtarget':'US','tekion':'US','teladoc-health':'US','telenav':'US',
'teleport':'US','tempo-automation':'US','tempus-ex':'US','ten-square-games':'Poland','tenable':'US','tencent':'',
'tenurex':'Canada','teradata':'US','terminus':'US','tesla':'US','tessera':'US','textio':'US','textnow':'Canada',
'the-appraisal-lane':'UK','the-athletic':'US','the-gist':'Canada','the-good-glamm-group':'','the-grommet':'US',
'the-guild':'US','the-iconic':'','the-meet-group':'US','the-messenger':'US','the-modist':'','the-mom-project':'US',
'the-muse':'US','the-org':'US','the-predictive-index':'US','the-realreal':'US','the-sill':'US','the-trade-desk':'US',
'the-wing':'US','the-zebra':'US','thegist':'Canada'
}

API_PROBES={
 'greenhouse':'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true',
 'lever':'https://api.lever.co/v0/postings/{slug}?mode=json',
 'ashby':'https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true',
 'workable':'https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true',
 'recruitee':'https://{slug}.recruitee.com/api/offers',
 'smartrecruiters':'https://api.smartrecruiters.com/v1/companies/{slug}/postings',
 'gem':'https://api.gem.com/job_board/v0/{slug}/job_posts/',
}

BOARD_URL={
 'greenhouse':'https://boards.greenhouse.io/{slug}',
 'lever':'https://jobs.lever.co/{slug}',
 'ashby':'https://jobs.ashbyhq.com/{slug}',
 'workable':'https://apply.workable.com/{slug}/',
 'recruitee':'https://{slug}.recruitee.com/',
 'smartrecruiters':'https://jobs.smartrecruiters.com/{slug}',
 'rippling':'https://ats.rippling.com/{slug}',
 'gem':'https://jobs.gem.com/{slug}',
}

def norm(s): return s.lower().strip()

def company_name(slug):
    specials={
        'sunday':'sunday app', 'sundaysky':'sunday sky', 'superops':'superops ai', 'surveymonkey':'survey monkey',
        'swing-education':'swing education', 'sword-health':'sword health', 'syft-technologies':'syft technologies',
        'synapsefi':'synapsefi', 'tackle-io':'tackle io', 'tails-com':'tails.com', 'take-two':'take two',
        'take-two-interactive':'take two interactive', 'talent-com':'talent.com', 'talis-biomedical':'talis biomedical',
        'tapas-media':'tapas media', 'tapps-games':'tapps games', 'teladoc-health':'teladoc health',
        'tempo-automation':'tempo automation', 'tempus-ex':'tempus ex machina', 'ten-square-games':'ten square games',
        'the-appraisal-lane':'the appraisal lane', 'the-good-glamm-group':'the good glamm group', 'the-meet-group':'the meet group',
        'the-mom-project':'the mom project', 'the-predictive-index':'the predictive index', 'the-realreal':'the realreal',
        'the-trade-desk':'the trade desk', 'the-zebra':'the zebra', 'thegist':'the gist'
    }
    return specials.get(slug, slug.replace('-', ' '))


def decode_bing_href(href):
    href=html.unescape(href)
    m=re.search(r'[?&]u=([^&]+)', href)
    if not m:
        return href
    val=unquote(m.group(1))
    if val.startswith('a1'):
        val=val[2:]
    if val.startswith('http'):
        return val
    try:
        decoded=base64.b64decode(val + '===').decode('utf-8','ignore')
        return decoded if decoded.startswith('http') else decoded
    except Exception:
        return href


def bing_search(query):
    url='https://www.bing.com/search?q='+quote_plus(query)
    try:
        text=SESSION.get(url, timeout=20).text
    except Exception:
        return []
    results=[]
    for href,title in re.findall(r'<h2[^>]*><a [^>]*href="(.*?)"[^>]*>(.*?)</a></h2>', text, re.S):
        title=re.sub('<.*?>','',title)
        link=decode_bing_href(href)
        results.append({'title':html.unescape(title).strip(), 'url':link})
    return results


def fetch(url):
    try:
        r=SESSION.get(url, timeout=20, allow_redirects=True)
        ct=r.headers.get('content-type','')
        if 'text/html' in ct or ct.startswith('text/') or ct=='':
            return r.url, r.status_code, r.text[:200000]
        return r.url, r.status_code, ''
    except Exception:
        return url, 0, ''


def ats_from_text(text):
    t=text.lower()
    for ats,pats in ATS_PATTERNS:
        for p in pats:
            if re.search(p, t):
                return ats
    if any(x in t for x in ['workday', 'myworkdayjobs', 'icims', 'dayforce', 'jobvite', 'bamboohr', 'workforcenow', 'adp', 'successfactors', 'sap.com/careers', 'oraclecloud', 'ultipro', 'ukg', 'jobylon', 'manatal', 'teamtailor', 'paylocity', 'paycomonline', 'greenhouse embedded board' ]):
        return 'other'
    return ''


def is_good_url(url):
    if not url or not url.startswith('http'):
        return False
    d=urlparse(url).netloc.lower()
    return not any(x in d for x in EXCLUDE_DOMAINS)


def extract_links(page_url, text):
    out=[]
    for href in re.findall(r'href=["\']([^"\']+)["\']', text, re.I):
        href=html.unescape(href)
        if href.startswith('javascript:') or href.startswith('mailto:'):
            continue
        full=urljoin(page_url, href)
        low=full.lower()
        if any(k in low for k in ['career','careers','job','jobs','join-us','work-with-us','greenhouse','lever.co','ashbyhq.com','workable.com','recruitee.com','smartrecruiters.com','rippling.com','jobs.gem.com']):
            out.append(full)
    # dedupe preserve order
    seen=set(); ded=[]
    for u in out:
        if u not in seen:
            seen.add(u); ded.append(u)
    return ded[:20]


def probe_exact(slug):
    hits=[]
    for ats,url in API_PROBES.items():
        try:
            r=SESSION.get(url.format(slug=slug), timeout=20)
            ok=False
            if ats=='greenhouse':
                ok=r.status_code==200 and 'jobs' in r.json()
            elif ats=='lever':
                ok=r.status_code==200 and isinstance(r.json(), list)
            elif ats=='ashby':
                ok=r.status_code==200 and 'jobs' in r.json()
            elif ats=='workable':
                ok=r.status_code==200 and 'jobs' in r.json()
            elif ats=='recruitee':
                ok=r.status_code==200 and 'offers' in r.json()
            elif ats=='smartrecruiters':
                data=r.json() if r.status_code==200 else {}
                ok=r.status_code==200 and isinstance(data,dict) and ('content' in data) and (data.get('content') or data.get('offset')==0 or data.get('totalFound')==0)
            elif ats=='gem':
                ok=r.status_code==200 and isinstance(r.json(), list)
            if ok:
                size=None
                try:
                    data=r.json()
                    if isinstance(data, dict):
                        for k in ['jobs','offers','content']:
                            if k in data:
                                size=len(data[k]); break
                    else:
                        size=len(data)
                except Exception:
                    pass
                # filter smartrecruiters false positive: pages often empty generic json for any slug
                if ats=='smartrecruiters' and not size:
                    continue
                hits.append((ats,size))
        except Exception:
            pass
    return hits


def evaluate_candidate(url):
    final,status,text=fetch(url)
    low = (final + '\n' + text[:60000]).lower()
    ats = ats_from_text(low)
    title=''
    m=re.search(r'<title>(.*?)</title>', text, re.I|re.S)
    if m: title=re.sub(r'\s+',' ',re.sub('<.*?>','',m.group(1))).strip()
    score=0
    if status==200: score+=1
    if ats: score+=5
    fl=final.lower()
    if any(k in fl for k in ['/careers','/career','/jobs','/job']): score+=2
    if any(k in fl for k in ['greenhouse','lever.co','ashbyhq','workable','recruitee','smartrecruiters','rippling','jobs.gem.com']): score+=3
    if title and any(k in title.lower() for k in ['career','careers','jobs']): score+=2
    return {'url':final, 'status':status, 'ats':ats, 'title':title, 'text':text, 'score':score}

results=[]
for i,slug in enumerate(SLUGS,1):
    row={'slug':slug,'ats':'','career_url':'','hq_country':MANUAL_HQ.get(slug,'')}
    if slug in existing and existing[slug].get('hq_country') and not row['hq_country']:
        row['hq_country']=existing[slug]['hq_country']
    hits=probe_exact(slug)
    if hits:
        # prefer non-zero jobs, then existing mapping order
        hits.sort(key=lambda x:(-(x[1] or 0), ['greenhouse','lever','ashby','workable','recruitee','smartrecruiters','rippling','gem'].index(x[0])))
        row['ats']=hits[0][0]
        row['career_url']=BOARD_URL[hits[0][0]].format(slug=slug)
        results.append(row)
        print(i,slug,'EXACT',row['ats'],row['career_url'])
        continue
    # try direct board page patterns for rippling and smartrecruiters/job pages with exact slug even if api not useful
    direct_candidates=[BOARD_URL['rippling'].format(slug=slug), BOARD_URL['smartrecruiters'].format(slug=slug), BOARD_URL['gem'].format(slug=slug), BOARD_URL['ashby'].format(slug=slug), BOARD_URL['lever'].format(slug=slug), BOARD_URL['greenhouse'].format(slug=slug), BOARD_URL['workable'].format(slug=slug), BOARD_URL['recruitee'].format(slug=slug)]
    evals=[]
    for u in direct_candidates:
        ev=evaluate_candidate(u)
        if ev['status']==200 and ev['score']>=5:
            evals.append(ev)
    if evals:
        evals.sort(key=lambda e:e['score'], reverse=True)
        best=evals[0]
        row['ats']=best['ats'] or 'other'
        row['career_url']=best['url']
        results.append(row)
        print(i,slug,'DIRECT',row['ats'],row['career_url'])
        continue
    name=company_name(slug)
    queries=[f'{name} careers', f'{name} jobs']
    candidates=[]
    for q in queries:
        for res in bing_search(q)[:8]:
            u=res['url']
            if not is_good_url(u):
                continue
            candidates.append(u)
    # de-dup
    seen=set(); candidates=[u for u in candidates if not (u in seen or seen.add(u))]
    # evaluate search results, plus homepage-discovered career links from first candidate/homepage
    inspected=[]
    for u in candidates[:5]:
        ev=evaluate_candidate(u)
        inspected.append(ev)
        if ev['status']==200 and ev['text']:
            for link in extract_links(ev['url'], ev['text'])[:10]:
                inspected.append(evaluate_candidate(link))
        time.sleep(0.2)
    inspected=[x for x in inspected if x['status']==200 and is_good_url(x['url'])]
    inspected.sort(key=lambda e:e['score'], reverse=True)
    best=inspected[0] if inspected else None
    if best and best['score']>=3:
        row['ats']=best['ats'] or ('other' if any(k in (best['url']+best['text'][:10000]).lower() for k in ['workday','icims','jobvite','bamboohr','successfactors','dayforce','ultipro','teamtailor','paylocity','oraclecloud']) else 'unknown')
        row['career_url']=best['url']
        print(i,slug,'SEARCH',row['ats'],row['career_url'])
    else:
        row['ats']='unknown'
        print(i,slug,'UNKNOWN')
    results.append(row)

with open('/Users/clare/Documents/workspace/job-board-crawler/research_results.json','w') as f:
    json.dump(results,f,indent=2)

with open('/Users/clare/Documents/workspace/job-board-crawler/research_results.csv','w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['slug','ats','career_url','hq_country'])
    w.writeheader(); w.writerows(results)
print('WROTE research_results.csv')
