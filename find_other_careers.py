import requests,re,html,json,time
from urllib.parse import urljoin,urlparse
resolved=set('''sunday,sundaysky,superhuman,superloop,supernal,superpedestrian,sure,surveymonkey,sweetgreen,swing-education,sword-health,swvl,synapse,synapsefi,synctera,synopsys,synthego,taboola,tada,take-two,take-two-interactive,talent-com,talkdesk,talkwalker,tanium,taxbit,taxfix,teamwork,techcrunch,techtarget,tekion,teladoc-health,teleport,tempo-automation,ten-square-games,teradata,terminus,textio,textnow,the-athletic,the-grommet,the-guild,the-iconic,the-realreal,the-trade-desk'''.split(','))
slugs='''sunday,sundaysky,sunfolding,superhuman,superlearn,superloop,supernal,superops,superpedestrian,superrare,sure,surveymonkey,swappie,sweetescape,sweetgreen,swiggy,swing-education,sword-health,swvl,swyft,swyftx,syft-technologies,symend,synamedia,synapse,synapsefi,synapsica,synctera,synergysuite,synlogic,synopsys,synthego,syte,tabnine,taboola,tackle,tackle-io,tada,tails-com,tailwind-labs,take-two,take-two-interactive,takeoff,takl,talent-com,talis-biomedical,talkdesk,talkwalker,tally,tamara-mellon,tanium,tapas-media,tapps-games,taskus,taxbit,taxfix,tcr2,teachmint,teads,teampay,teamwork,techadvance,techcrunch,techtarget,tekion,teladoc-health,telenav,teleport,tempo-automation,tempus-ex,ten-square-games,tenable,tencent,tenurex,teradata,terminus,tesla,tessera,textio,textnow,the-appraisal-lane,the-athletic,the-gist,the-good-glamm-group,the-grommet,the-guild,the-iconic,the-meet-group,the-messenger,the-modist,the-mom-project,the-muse,the-org,the-predictive-index,the-realreal,the-sill,the-trade-desk,the-wing,the-zebra,thegist'''.split(',')
manual_domain={'superops':'superops.com','swappie':'swappie.com','swyftx':'swyftx.com','syft-technologies':'syft.com','symend':'symend.com','synamedia':'synamedia.com','synlogic':'synlogictx.com','syte':'syte.ai','tabnine':'tabnine.com','tackle':'tackle.io','tackle-io':'tackle.io','tails-com':'tails.com','tailwind-labs':'tailwindapp.com','tally':'tally.so','teampay':'teampay.co','telenav':'telenav.com','tenable':'tenable.com','tesla':'tesla.com','tessera':'tesseratx.com','the-muse':'themuse.com','the-org':'theorg.com','the-zebra':'thezebra.com','takeoff':'takeoff.com','teads':'teads.com','tencent':'tencent.com','teachmint':'teachmint.com','the-mom-project':'themomproject.com','the-sill':'thesill.com','tamara-mellon':'tamaramellon.com','the-predictive-index':'predictiveindex.com','the-gist':'thegistsports.com','thegist':'thegistsports.com','swyft':'swyftfilings.com'}
name_over={'tails-com':'tails','the-gist':'the gist','thegood-glamm-group':'the good glamm group'}
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0'})

def clearbit(name):
    try:
        r=s.get('https://autocomplete.clearbit.com/v1/companies/suggest',params={'query':name},timeout=20)
        if r.status_code==200:
            return r.json()
    except: pass
    return []

def fetch(url):
    try:
        r=s.get(url,timeout=20,allow_redirects=True)
        return r.status_code,r.url,r.text[:250000]
    except: return 0,url,''

def detect(url,text):
    low=(url+'\n'+text[:100000]).lower()
    for ats,kws in [('greenhouse',['greenhouse.io']),('lever',['lever.co']),('ashby',['ashbyhq.com']),('workable',['workable.com']),('recruitee',['recruitee.com']),('smartrecruiters',['smartrecruiters.com']),('rippling',['rippling.com']),('gem',['jobs.gem.com','api.gem.com/job_board'])]:
        if any(k in low for k in kws): return ats
    if any(k in low for k in ['workday','myworkdayjobs','icims','jobvite','successfactors','dayforce','bamboohr','teamtailor','workforcenow','oraclecloud','ultipro','ukg','paylocity','paycomonline','jobylon','adp.com','greenhouse embedded board']): return 'other'
    return ''

def extract_links(base,text):
    out=[]
    for href in re.findall(r'href=["\']([^"\']+)["\']', text, re.I):
        href=html.unescape(href)
        if href.startswith(('javascript:','mailto:','#')): continue
        full=urljoin(base,href)
        low=full.lower()
        if any(k in low for k in ['career','careers','jobs','join-us','joinus','work-with-us','workwithus','open-positions','opportunities','lever.co','greenhouse','ashbyhq','workable','recruitee','smartrecruiters','rippling','jobs.gem.com']):
            out.append(full)
    seen=[]
    for u in out:
        if u not in seen: seen.append(u)
    return seen[:15]

for slug in slugs:
    if slug in resolved: continue
    dom=manual_domain.get(slug)
    if not dom:
        sugg=clearbit(slug.replace('-',' '))
        if sugg:
            dom=sugg[0].get('domain')
    cands=[]
    if dom:
        cands+=[f'https://{dom}', f'https://www.{dom}']
    token=slug.replace('-','')
    for d in [f'{token}.com', f'{token}.ai', f'{token}.io', f'{token}.co']:
        cands.append('https://'+d)
    seen=[]
    for u in cands:
        if u not in seen: seen.append(u)
    best=None
    for u in seen[:6]:
        st,fu,body=fetch(u)
        if st!=200: continue
        d=detect(fu,body)
        links=extract_links(fu,body)
        if d and ('career' in fu or 'jobs' in fu):
            best=(d,fu); break
        for link in links[:8]:
            st2,fu2,body2=fetch(link)
            if st2!=200: continue
            d2=detect(fu2,body2)
            if d2 or any(k in fu2.lower() for k in ['career','jobs']):
                best=(d2 or 'other',fu2); break
        if best: break
        time.sleep(0.2)
    print(slug, best)
