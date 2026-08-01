import requests,re,json
slugs='''sunday,sundaysky,sunfolding,superhuman,superlearn,superloop,supernal,superops,superpedestrian,superrare,sure,surveymonkey,swappie,sweetescape,sweetgreen,swiggy,swing-education,sword-health,swvl,swyft,swyftx,syft-technologies,symend,synamedia,synapse,synapsefi,synapsica,synctera,synergysuite,synlogic,synopsys,synthego,syte,tabnine,taboola,tackle,tackle-io,tada,tails-com,tailwind-labs,take-two,take-two-interactive,takeoff,takl,talent-com,talis-biomedical,talkdesk,talkwalker,tally,tamara-mellon,tanium,tapas-media,tapps-games,taskus,taxbit,taxfix,tcr2,teachmint,teads,teampay,teamwork,techadvance,techcrunch,techtarget,tekion,teladoc-health,telenav,teleport,tempo-automation,tempus-ex,ten-square-games,tenable,tencent,tenurex,teradata,terminus,tesla,tessera,textio,textnow,the-appraisal-lane,the-athletic,the-gist,the-good-glamm-group,the-grommet,the-guild,the-iconic,the-meet-group,the-messenger,the-modist,the-mom-project,the-muse,the-org,the-predictive-index,the-realreal,the-sill,the-trade-desk,the-wing,the-zebra,thegist'''.split(',')
manual={
 'superops':['superopsai'], 'sword-health':['swordhealth'], 'tails-com':['tailscom','tails'], 'take-two':['taketwo'], 'take-two-interactive':['taketwointeractive','taketwo'],
 'talent-com':['talentcom','talent'], 'tamara-mellon':['tamaramellon'], 'tapas-media':['tapasmedia','tapas'], 'teladoc-health':['teladochealth','teladoc'], 'tempo-automation':['tempoautomation','tempo'], 'tempus-ex':['tempusexmachina','tempus'], 'ten-square-games':['tensquaregames'],
 'the-athletic':['theathletic'], 'the-gist':['thegist'], 'the-good-glamm-group':['thegoodglammgroup'], 'the-iconic':['theiconic'], 'the-meet-group':['themeetgroup'], 'the-mom-project':['themomproject'], 'the-muse':['themuse'], 'the-org':['theorg'], 'the-predictive-index':['thepredictiveindex'], 'the-realreal':['therealreal'], 'the-trade-desk':['thetradedesk'], 'the-zebra':['thezebra'], 'swing-education':['swingeducation'], 'teads':['teadstv'], 'synapsefi':['synapsefi','synapse'], 'tcr2':['tcr2therapeutics'], 'teampay':['teampay'], 'techadvance':['techadv'], 'tenurex':['tenurex'], 'the-grommet':['grommet'], 'the-guild':['guild'], 'superrare':['superrarelabs']
}
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0'})

def get(url):
    try: return s.get(url,timeout=20,allow_redirects=True)
    except: return None

def variants(slug):
    base=[slug, slug.replace('-',''), slug.replace('-','_'), slug.replace('-','.')]
    toks=slug.split('-')
    if len(toks)>1:
        base.append(''.join(toks))
        base.append(''.join(t.title() for t in toks))
    base+=manual.get(slug,[])
    out=[]
    for v in base:
        if v and v not in out: out.append(v)
    return out

for slug in slugs:
    found=[]
    for v in variants(slug):
        # greenhouse
        r=get(f'https://boards-api.greenhouse.io/v1/boards/{v}/jobs?content=true')
        if r is not None and r.status_code==200:
            try:
                data=r.json();
                if 'jobs' in data:
                    found.append((v,'greenhouse',len(data['jobs']),f'https://job-boards.greenhouse.io/{v}'))
                    break
            except: pass
        # lever
        r=get(f'https://api.lever.co/v0/postings/{v}?mode=json')
        if r is not None and r.status_code==200:
            try:
                data=r.json();
                if isinstance(data,list):
                    found.append((v,'lever',len(data),f'https://jobs.lever.co/{v}'))
                    break
            except: pass
        # ashby
        r=get(f'https://api.ashbyhq.com/posting-api/job-board/{v}?includeCompensation=true')
        if r is not None and r.status_code==200:
            try:
                data=r.json();
                if isinstance(data,dict) and 'jobs' in data:
                    found.append((v,'ashby',len(data['jobs']),f'https://jobs.ashbyhq.com/{v}'))
                    break
            except: pass
        # workable
        r=get(f'https://apply.workable.com/api/v1/widget/accounts/{v}?details=true')
        if r is not None and r.status_code==200:
            try:
                data=r.json();
                if isinstance(data,dict) and 'jobs' in data:
                    found.append((v,'workable',len(data['jobs']),f'https://apply.workable.com/{v}/'))
                    break
            except: pass
        # recruitee
        r=get(f'https://{v}.recruitee.com/api/offers')
        if r is not None and r.status_code==200:
            try:
                data=r.json();
                if isinstance(data,dict) and 'offers' in data:
                    found.append((v,'recruitee',len(data['offers']),f'https://{v}.recruitee.com/'))
                    break
            except: pass
        # gem
        r=get(f'https://api.gem.com/job_board/v0/{v}/job_posts/')
        if r is not None and r.status_code==200:
            try:
                data=r.json();
                if isinstance(data,list):
                    found.append((v,'gem',len(data),f'https://jobs.gem.com/{v}'))
                    break
            except: pass
        # smartrecruiters direct validate title
        r=get(f'https://careers.smartrecruiters.com/{v}')
        if r is not None and r.status_code==200:
            m=re.search(r'<title>(.*?)</title>',r.text,re.I|re.S)
            title=m.group(1).strip() if m else ''
            if title.startswith('Careers at '):
                found.append((v,'smartrecruiters',None,r.url))
                break
        # rippling direct validate next data
        r=get(f'https://ats.rippling.com/{v}')
        if r is not None and r.status_code==200 and '__NEXT_DATA__' in r.text:
            found.append((v,'rippling',None,r.url))
            break
    if found:
        print(slug, found[0])
