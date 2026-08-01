import csv, json, re, sys, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

slugs = '''equitybee,equityzen,ericsson,ermetic,eroad,eruditus,esh-group,esme-learning,etermax,ethereum-foundation,ethos-life,etoro,etsy,eucalyptus,euler-motors,eurora,evbox,eventbrite,eventus,everbridge,everc,everlane,everlaw,everledger,evernote,everquote,everybuddy,evgo,eviation-aircraft,evolve,exabeam,examedi,exodus,exosonic,exotel,expedia,expel,expert360,exterro,extrahop,extramarks,eyeem,eyowo,ezcater,ezoic,f-secure,f5,fabhotels,fable,fabric,facily,factorial,fanclash,fandom,fanduel,fareportal,fareye,farfetch,fashinza,fast,fastly,fate-therapeutics,favo,faze-medicines,feather,feedzai,femtech-health,fetch,fi-money,fifth-season,figure,filevine,filmic,finastra,finite-state,finleap-connect,fintechos,fipola,fireblocks,firebolt,firehydrant,firework,first-aml,first-mode,fiscalnote,fishbrain,fisker,fission,fit-analytics,fittr,fiverr,flash-coffee,flatiron-health,flatiron-school,flex,flex-ai,flexcar,flexe,flightstats,flink'''.split(',')

session = requests.Session()
session.headers.update({'User-Agent':'Mozilla/5.0'})
platforms = {
    'greenhouse': ('https://boards-api.greenhouse.io/v1/boards/{}/jobs?content=true', lambda r: r.status_code==200 and 'jobs' in r.text),
    'lever': ('https://api.lever.co/v0/postings/{}?mode=json', lambda r: r.status_code==200 and r.text.strip().startswith('[')),
    'ashby': ('https://api.ashbyhq.com/posting-api/job-board/{}?includeCompensation=true', lambda r: r.status_code==200 and 'jobs' in r.text),
    'workable': ('https://apply.workable.com/api/v1/widget/accounts/{}?details=true', lambda r: r.status_code==200 and 'jobs' in r.text),
    'recruitee': ('https://{}.recruitee.com/api/offers', lambda r: r.status_code==200 and 'offers' in r.text),
    'smartrecruiters': ('https://api.smartrecruiters.com/v1/companies/{}/postings', lambda r: r.status_code==200 and 'content' in r.text),
    'gem': ('https://api.gem.com/job_board/v0/{}/job_posts/', lambda r: r.status_code==200 and (r.text.strip().startswith('[') or 'job_posts' in r.text)),
    'rippling': ('https://ats.rippling.com/en-CA/{}/jobs', lambda r: r.status_code==200 and ('__NEXT_DATA__' in r.text or '/jobs/' in r.text)),
}

career_urls = {
    'greenhouse': 'https://boards.greenhouse.io/{}',
    'lever': 'https://jobs.lever.co/{}',
    'ashby': 'https://jobs.ashbyhq.com/{}',
    'workable': 'https://apply.workable.com/{}',
    'recruitee': 'https://{}.recruitee.com/',
    'smartrecruiters': 'https://careers.smartrecruiters.com/{}',
    'gem': 'https://www.gem.com/careers/{}',
    'rippling': 'https://ats.rippling.com/{}/jobs',
}

def probe_slug(slug):
    out=[]
    for name,(url,check) in platforms.items():
        try:
            r=session.get(url.format(slug), timeout=15, allow_redirects=True)
            ok=check(r)
            size=len(r.text)
            if ok:
                out.append((name, r.status_code, r.url, size))
        except Exception as e:
            pass
    return slug,out

with ThreadPoolExecutor(max_workers=16) as ex:
    futs=[ex.submit(probe_slug, s) for s in slugs]
    for fut in as_completed(futs):
        slug,out=fut.result()
        print(slug, json.dumps(out))
