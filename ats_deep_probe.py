import re, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
import requests

ATS_PATTERNS=[('greenhouse',r'greenhouse\.io'),('lever',r'lever\.co'),('ashby',r'ashbyhq\.com'),('workable',r'workable\.com'),('recruitee',r'recruitee\.com'),('smartrecruiters',r'smartrecruiters\.com'),('rippling',r'rippling\.com'),('gem',r'gem\.com')]
OTHER=r'(myworkdayjobs|workday|icims|jobvite|bamboohr|successfactors|oraclecloud|taleo|jobylon|teamtailor)'
requests.packages.urllib3.disable_warnings()
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0'})
rows=json.load(open('careers_probe_fast.json'))

def fetch(url):
    try:
        r=s.get(url,timeout=8,verify=False,allow_redirects=True)
        return r.text[:200000], r.url
    except Exception:
        return '', url

def detect(text):
    for name,pat in ATS_PATTERNS:
        if re.search(pat,text,re.I): return name
    if re.search(OTHER,text,re.I): return 'other'
    return ''

for row in rows:
    if row['ats']:
        continue
    url=row['career_url']
    if not url: continue
    html,final=fetch(url)
    text='\n'.join([html,final])
    ats=detect(text)
    title=''
    if not ats and html:
        m=re.search(r'<title[^>]*>(.*?)</title>', html, re.I|re.S)
        title=re.sub(r'\s+',' ',m.group(1)).strip() if m else ''
        links=re.findall(r'''(?:href|src)=[\"']([^\"']+)[\"']''', html, re.I)
        abslinks=[]
        for v in links[:400]:
            abslinks.append(urljoin(final,v))
        joined='\n'.join(abslinks)
        ats=detect(joined)
        # fetch up to 5 scripts if same host or known ATS host
        script_urls=[]
        for v in abslinks:
            if v.endswith('.js') or 'api' in v.lower() or any(k in v.lower() for k,_ in ATS_PATTERNS):
                script_urls.append(v)
        extra=[]
        for su in script_urls[:5]:
            body,fu=fetch(su)
            extra.append(fu+'\n'+body[:50000])
        if not ats:
            ats=detect('\n'.join(extra))
    row['deep_ats']=ats
    row['title']=title

json.dump(rows, open('ats_deep_probe.json','w'), indent=2)
print('wrote ats_deep_probe.json')
