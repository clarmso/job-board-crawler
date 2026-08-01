import re, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import requests

slugs='0g,100-thieves,10x-genomics,123milhas,1k-kirana,1stdibs,23andme,2tm,2u,54gene,5b-solar,6sense,80-acres-farms,888,8x8,91trucks,98point6,99,aakash,abbyy,abl,abra,absci,absolute-software,acast,accolade,acko,acorns,acronis,actifio,activecampaign,activefence,actyv-ai,acxiom,ada-health,ada-support,adaptive-biotechnologies,adara,adda247,addepar,addi,adjust,adobe,adp,adroll,advata,advisor-credit-exchange,adwerx,aeye,affirm,afterverse,agentsync,agility-robotics,agoda,ahead,ai-fleet,ai21-labs,air,airlift,airmap,airmeet,airslate,airtable,airtame,airtasker,airthings,airtime,airy-rooms,aiven,ajaib,akerna,akili-interactive,akili-labs,akseleran,akudo,akulaku,alarum,albert,alegion,aleph-alpha,aleph-farms,alerzo,algorand-foundation,ali-technologies,alibaba-cloud,alice,aliexpress-russia,allbirds,alle,allyo,alma,almanac,alteryx,alto-pharmacy,altruist,alza,amazon,amber-group,ambev-tech,amd'.split(',')
manual_domains = {
    '100-thieves':'100thieves.com','10x-genomics':'10xgenomics.com','1k-kirana':'1knetworks.in','5b-solar':'5b.com.au','80-acres-farms':'80acresfarms.com','99':'99app.com','aakash':'aakash.ac.in','absolute-software':'absolutesoftware.com','actyv-ai':'actyv.ai','ada-health':'ada.com','ada-support':'ada.cx','adp':'adp.com','adroll':'nextroll.com','advisor-credit-exchange':'advisorcreditexchange.com','afterverse':'afterverse.com','agility-robotics':'agilityrobotics.com','ai-fleet':'fleet.ai','ai21-labs':'ai21.com','air':'air.inc','airlift':'airlift.co','akili-interactive':'akiliinteractive.com','akili-labs':'akiliinteractive.com','alibaba-cloud':'alibabacloud.com','aliexpress-russia':'aliexpress.ru','alto-pharmacy':'alto.com','amber-group':'ambergroup.io','ambev-tech':'ambevtech.com'
}
ATS_PATTERNS=[('greenhouse',[r'greenhouse\.io']),('lever',[r'lever\.co']),('ashby',[r'ashbyhq\.com']),('workable',[r'workable\.com']),('recruitee',[r'recruitee\.com']),('smartrecruiters',[r'smartrecruiters\.com']),('rippling',[r'rippling\.com']),('gem',[r'gem\.com'])]
requests.packages.urllib3.disable_warnings()
HEADERS={'User-Agent':'Mozilla/5.0'}
session=requests.Session(); session.headers.update(HEADERS)

def domains(slug):
    base=slug.replace('-','')
    c=[]
    if slug in manual_domains: c.append(manual_domains[slug])
    c += [slug+'.com', base+'.com']
    out=[]; seen=set()
    for x in c:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

def urls_for(slug):
    urls=[]
    for d in domains(slug):
        urls += [f'https://www.{d}/careers' if not d.startswith('www.') else f'https://{d}/careers', f'https://{d}/careers', f'https://{d}/jobs']
    ded=[]; seen=set()
    for u in urls:
        u=u.replace('https://www.www.','https://www.')
        if u not in seen:
            ded.append(u); seen.add(u)
    return ded[:6]

def fetch(url):
    try:
        r=session.get(url, timeout=6, allow_redirects=True, verify=False)
        return url, r.status_code, r.url, r.text[:120000]
    except Exception as e:
        return url, None, '', ''

def score(item):
    url, status, final, text = item
    if status is None: return -999
    s=0
    if status<400: s+=50
    elif status in (401,403): s+=20
    elif status==404: s-=10
    lf=final.lower()
    lt=text.lower()
    if any(x in lf for x in ['/careers','/career','/jobs']): s+=20
    if any(x in lt for x in ['career','join our team','open positions','jobs']): s+=10
    if any(x in lf for x in ['greenhouse','lever','ashbyhq','workable','recruitee','smartrecruiters','rippling','gem.com','myworkdayjobs','workday']): s+=20
    return s

def detect(html, final):
    hay='\n'.join([html, final])
    for ats,pats in ATS_PATTERNS:
        if any(re.search(p, hay, re.I) for p in pats):
            return ats
    if re.search(r'(myworkdayjobs|workday|icims|jobvite|bamboohr|successfactors)', hay, re.I):
        return 'other'
    return ''

all_urls=[(slug,u) for slug in slugs for u in urls_for(slug)]
results={slug:[] for slug in slugs}
with ThreadPoolExecutor(max_workers=20) as ex:
    futs={ex.submit(fetch,u):(slug,u) for slug,u in all_urls}
    for fut in as_completed(futs):
        slug,u=futs[fut]
        results[slug].append(fut.result())

out=[]
for slug in slugs:
    cand=sorted(results[slug], key=score, reverse=True)
    best=cand[0] if cand else ('',None,'','')
    ats=detect(best[3], best[2]) if best[1] else ''
    if not ats and best[3]:
        vals=re.findall(r'''(?:href|src)=[\"']([^\"']+)[\"']''', best[3], re.I)
        joined='\n'.join(urljoin(best[2],v) for v in vals[:500])
        ats=detect(joined, best[2])
    out.append({'slug':slug,'career_url':best[2],'ats':ats,'tried':[x[:3] for x in cand[:4]]})

with open('careers_probe_fast.json','w') as f: json.dump(out,f,indent=2)
print('wrote careers_probe_fast.json')
