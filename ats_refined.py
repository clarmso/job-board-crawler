import json,re,requests,urllib3
from urllib.parse import urljoin
urllib3.disable_warnings()
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0'})
rows=json.load(open('ats_deep_probe.json'))
known={
 'adaptive-biotechnologies':'https://www.adaptivebiotech.com/career-listings/',
 'adobe':'https://careers.adobe.com/us/en',
 'aeye':'https://www.aeye.ai/careers/',
 'afterverse':'https://afterverse.co/careers',
 'algorand-foundation':'https://algorand.co/algorand-foundation/careers',
 'alza':'https://www.alza.cz/kariera'
}
ats_rules=[
 ('greenhouse',[r'boards\.greenhouse\.io',r'job-boards\.greenhouse\.io',r'grnhse_app']),
 ('lever',[r'jobs\.lever\.co',r'lever-jobs',r'lever-via']),
 ('ashby',[r'jobs\.ashbyhq\.com',r'data-ashby-',r'ashby-job']),
 ('workable',[r'jobs\.workable\.com',r'apply\.workable\.com']),
 ('recruitee',[r'jobs\.recruitee\.com',r'recruitee\.com/o/']),
 ('smartrecruiters',[r'careers\.smartrecruiters\.com']),
 ('rippling',[r'ats\.rippling\.com',r'ripplingcdn\.com/ats',r'rr-job-board']),
 ('gem',[r'jobs\.gem\.com',r'gem\.com/jobs'])
]
other_pat=r'(myworkdayjobs|workday|icims|jobvite|bamboohr|successfactors|oraclecloud|taleo|teamtailor|jobylon|personio)'

def fetch(url):
    try:
        r=s.get(url,timeout=12,verify=False,allow_redirects=True)
        return r.url,r.text[:250000]
    except Exception:
        return url,''

def detect(text):
    for ats,pats in ats_rules:
        if any(re.search(p,text,re.I) for p in pats):
            return ats
    if re.search(other_pat,text,re.I):
        return 'other'
    return ''

for row in rows:
    if row['slug'] in known:
        row['career_url']=known[row['slug']]
    url=row['career_url']
    if not url:
        row['refined_ats']='unknown'
        continue
    final,html=fetch(url)
    row['career_url']=final
    text='\n'.join([final,html])
    ats=detect(text)
    if not ats and html:
        vals=re.findall(r'''(?:href|src)=[\"']([^\"']+)[\"']''', html, re.I)
        joined='\n'.join(urljoin(final,v) for v in vals[:500])
        ats=detect(joined)
        # fetch a few likely script URLs
        if not ats:
            likely=[urljoin(final,v) for v in vals if any(x in v.lower() for x in ['greenhouse','lever','ashby','workable','smartrecruiters','recruitee','rippling','workday','jobvite','myworkdayjobs'])]
            extra=[]
            for su in likely[:5]:
                fu,body=fetch(su)
                extra.append(fu+'\n'+body[:60000])
            ats=detect('\n'.join(extra))
    row['refined_ats']=ats or 'unknown'
json.dump(rows, open('ats_refined.json','w'), indent=2)
print('wrote ats_refined.json')
