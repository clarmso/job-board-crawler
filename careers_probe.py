import re, json, time
from urllib.parse import urljoin
import requests

slugs='0g,100-thieves,10x-genomics,123milhas,1k-kirana,1stdibs,23andme,2tm,2u,54gene,5b-solar,6sense,80-acres-farms,888,8x8,91trucks,98point6,99,aakash,abbyy,abl,abra,absci,absolute-software,acast,accolade,acko,acorns,acronis,actifio,activecampaign,activefence,actyv-ai,acxiom,ada-health,ada-support,adaptive-biotechnologies,adara,adda247,addepar,addi,adjust,adobe,adp,adroll,advata,advisor-credit-exchange,adwerx,aeye,affirm,afterverse,agentsync,agility-robotics,agoda,ahead,ai-fleet,ai21-labs,air,airlift,airmap,airmeet,airslate,airtable,airtame,airtasker,airthings,airtime,airy-rooms,aiven,ajaib,akerna,akili-interactive,akili-labs,akseleran,akudo,akulaku,alarum,albert,alegion,aleph-alpha,aleph-farms,alerzo,algorand-foundation,ali-technologies,alibaba-cloud,alice,aliexpress-russia,allbirds,alle,allyo,alma,almanac,alteryx,alto-pharmacy,altruist,alza,amazon,amber-group,ambev-tech,amd'.split(',')

manual_domains = {
    '100-thieves':'100thieves.com',
    '10x-genomics':'10xgenomics.com',
    '1k-kirana':'1kkirana.com',
    '5b-solar':'5b.com.au',
    '80-acres-farms':'80acresfarms.com',
    '98point6':'98point6.com',
    '99':'99app.com',
    'aakash':'aakash.ac.in',
    'absolute-software':'absolutesoftware.com',
    'actyv-ai':'actyv.ai',
    'ada-health':'ada.com',
    'ada-support':'ada.cx',
    'adobe':'adobe.com',
    'adp':'adp.com',
    'adroll':'nextroll.com',
    'advata':'advata.com',
    'advisor-credit-exchange':'advisorcreditexchange.com',
    'adwerx':'adwerx.com',
    'afterverse':'afterverse.com',
    'agility-robotics':'agilityrobotics.com',
    'ai-fleet':'fleet.ai',
    'ai21-labs':'ai21.com',
    'air':'air.inc',
    'airlift':'airlift.co',
    'airmeet':'airmeet.com',
    'airslate':'airslate.com',
    'airy-rooms':'airyrooms.com',
    'akerna':'akerna.com',
    'akili-interactive':'akiliinteractive.com',
    'akili-labs':'akiliinteractive.com',
    'actifio':'actifio.com',
    'ali-technologies':'ali-technologies.com',
    'alibaba-cloud':'alibabacloud.com',
    'aliexpress-russia':'aliexpress.ru',
    'alto-pharmacy':'alto.com',
    'ambev-tech':'ambevtech.com',
    'amber-group':'ambergroup.io',
}

HEADERS={'User-Agent':'Mozilla/5.0'}
ATS_PATTERNS=[
    ('greenhouse',[r'boards\.greenhouse\.io',r'job-boards\.greenhouse\.io',r'greenhouse\.io/embed',r'greenhouse\.io']),
    ('lever',[r'jobs\.lever\.co',r'lever\.co/embed',r'lever\.co']),
    ('ashby',[r'jobs\.ashbyhq\.com',r'ashbyhq\.com']),
    ('workable',[r'jobs\.workable\.com',r'apply\.workable\.com',r'workable\.com']),
    ('recruitee',[r'jobs\.recruitee\.com',r'recruitee\.com/o/']),
    ('smartrecruiters',[r'careers\.smartrecruiters\.com',r'smartrecruiters\.com']),
    ('rippling',[r'jobs\.rippling\.com',r'rippling\.com']),
    ('gem',[r'gem\.com', r'jobs\.gem\.com'])
]

session=requests.Session()
session.headers.update(HEADERS)
requests.packages.urllib3.disable_warnings()

def candidates(slug):
    base=slug.replace('-','')
    ds=[]
    if slug in manual_domains:
        ds.append(manual_domains[slug])
    ds.extend([slug+'.com', 'www.'+slug+'.com', base+'.com', 'www.'+base+'.com'])
    # some known alt tlds/aliases by name hyphen removal
    if slug not in manual_domains and '-' in slug:
        ds.extend([slug.replace('-','')+'.io', slug.replace('-','')+'.ai', slug.replace('-','')+'.co'])
    out=[]; seen=set()
    for d in ds:
        d=d.replace('www.www.','www.')
        if d not in seen:
            seen.add(d); out.append(d)
    return out

def fetch(url):
    try:
        r=session.get(url, timeout=12, allow_redirects=True, verify=False)
        return r
    except Exception:
        return None

def detect_ats(text, urls):
    hay='\n'.join([text or '']+urls)
    for ats,pats in ATS_PATTERNS:
        for p in pats:
            if re.search(p, hay, re.I):
                return ats
    return ''

def score_response(r, domain):
    if not r: return -999
    score = 0
    if r.status_code < 400: score += 50
    elif r.status_code in (401,403): score += 20
    elif r.status_code == 404: score -= 10
    final=r.url.lower()
    if domain.replace('www.','') in final: score += 20
    if '/careers' in final or '/career' in final or '/jobs' in final: score += 20
    txt=(r.text[:5000] if getattr(r,'text',None) else '').lower()
    if any(k in txt for k in ['career','join our team','open positions','jobs']): score += 15
    if any(k in final for k in ['greenhouse','lever','ashbyhq','workable','recruitee','smartrecruiters','rippling','gem.com']): score += 25
    return score

results=[]
for slug in slugs:
    tried=[]
    best=None; bestscore=-999
    for domain in candidates(slug):
        if '://' in domain:
            urls=[domain]
        else:
            urls=[f'https://{domain}/careers', f'https://{domain}/jobs', f'https://{domain}/careers/']
        for u in urls:
            r=fetch(u)
            tried.append((u, None if not r else r.status_code, None if not r else r.url))
            s=score_response(r, domain if '://' not in domain else u)
            if s>bestscore:
                bestscore=s; best=(u,r)
    career_url=''; ats=''; note=''
    if best and best[1]:
        r=best[1]
        career_url=r.url
        html=r.text[:200000]
        ats=detect_ats(html,[career_url])
        if not ats:
            # parse links/scripts/iframes
            vals=re.findall(r'''(?:href|src)=["']([^"']+)["']''', html, re.I)
            urls=[urljoin(career_url,v) for v in vals]
            ats=detect_ats('\n'.join(urls), urls)
            if not ats and any(k in career_url.lower() for k in ['myworkdayjobs','workday']):
                ats='other'
            if not ats and any(k in html.lower() for k in ['myworkdayjobs','workday']):
                ats='other'
            if not ats and any(k in career_url.lower() for k in ['jobvite','bamboohr','icims','successfactors']):
                ats='other'
            if not ats and any(k in html.lower() for k in ['jobvite','bamboohr','icims','successfactors']):
                ats='other'
    results.append({'slug':slug,'best_url':career_url,'ats':ats,'tried':tried[:8]})

with open('careers_probe_results.json','w') as f:
    json.dump(results,f,indent=2)
print('wrote careers_probe_results.json')
