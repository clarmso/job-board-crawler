import requests,re,json,concurrent.futures
headers={'User-Agent':'Mozilla/5.0'}
slugs='crowdstreet,cruise,crunchbase,crunchyroll,crypto-com,cs-disco,cto-ai,cue,cue-health,cuemath,cult-fit,culture-amp,culture-trip,curalie,curative,curbio,curefit,curology,currency,curve,cushion,cuyana,cvent,cyberark,cyberbit,cybercube,cybereason,cybergrx,cyberproof,cycognito,cypress-io,cyren,cyteir-therapeutics,d-id,d2iq,daily-harvest,dailypay,daloopa,dance,dandy,daniel-wellington,dapper-labs,daraz,dare,dark,darrow,dash,dastgyr,datagen,dataminr,datarails,datarobot,datastax,datera,datree,datto,dayforce,daylight,daytwo,dazn,dbt-labs,deadspin,dealshare,dealtale,decent,deep-instict,deep-instinct,deepverge,deepwatch,defined-ai,definitive-healthcare,degreed,dehaat,deliv,deliveroo,deliveroo-australia,delivery-hero,dell,demandbase,deputy,descartes-labs,desktop-metal,detectify,devo,dextrous-robotics,dhi-group,dialsource,dice,digg,digimarc,digital-currency-gruop,digital-river,digital-surge,digitalocean,discord,discourse,dispatch,dispatchhealth,divergent-3d,divvy'.split(',')
manual={'crypto-com':'crypto-com','cs-disco':'disco','cto-ai':'ctoai','cue-health':'cuehealth','cult-fit':'cultfit','culture-amp':'cultureamp','cyteir-therapeutics':'cyteir','d-id':'did','daily-harvest':'dailyharvest','dapper-labs':'dapperlabs','dark':'darktrace','dbt-labs':'dbtlabs','defined-ai':'definedai','definitive-healthcare':'definitivehealthcare','descartes-labs':'descarteslabs','desktop-metal':'desktopmetal','dextrous-robotics':'dextrousrobotics','dhi-group':'dhigroup','digital-currency-gruop':'digitalcurrencygroup','digital-river':'digitalriver','digitalocean':'digitalocean','dispatchhealth':'dispatchhealth','divergent-3d':'divergent3d','cypress-io':'cypress','culture-trip':'culturetrip','currency':'currencycloud','curve':'imaginecurve'}
patterns={
'greenhouse':['https://job-boards.greenhouse.io/{}','https://boards.greenhouse.io/{}'],
'ashby':['https://jobs.ashbyhq.com/{}'],
'workable':['https://apply.workable.com/{}'],
'smartrecruiters':['https://careers.smartrecruiters.com/{}'],
'rippling':['https://ats.rippling.com/{}'],
'gem':['https://jobs.gem.com/{}'],
}

def validate(ats,url,r,slug):
    text=r.text
    title=''
    m=re.search(r'<title>(.*?)</title>',text,re.I|re.S)
    if m: title=re.sub(r'\s+',' ',m.group(1)).strip()
    tl=title.lower(); final=r.url
    if ats=='greenhouse':
        ok=r.status_code==200 and 'page not found' not in tl and tl.startswith('jobs at ')
    elif ats=='ashby':
        ok=r.status_code==200 and title and tl!='jobs'
    elif ats=='workable':
        ok=r.status_code==200 and title and 'workable' not in tl[:25] and 'not found' not in tl
    elif ats=='smartrecruiters':
        ok=r.status_code==200 and final.rstrip('/')!='https://jobs.smartrecruiters.com' and 'careers at ' in tl and 'sandbox' not in tl and ' sbx' not in tl
    elif ats=='rippling':
        ok=r.status_code==200 and title and 'rippling' not in tl[:25] and 'not found' not in tl
    elif ats=='gem':
        ok=r.status_code==200 and title and 'jobs' in tl and 'page not found' not in tl
    else:
        ok=False
    if ok:
        return {'ats':ats,'career_url':final,'title':title}

def fetch(task):
    slug,ats,url=task
    try:
        r=requests.get(url,headers=headers,timeout=8,allow_redirects=True)
        return slug, validate(ats,url,r,slug)
    except Exception:
        return slug, None

tasks=[]
for slug in slugs:
    cands=[slug]
    cand2=slug.replace('-','')
    if cand2!=slug: cands.append(cand2)
    if slug in manual and manual[slug] not in cands: cands.append(manual[slug])
    for ats, pats in patterns.items():
        for cand in cands:
            for pat in pats:
                tasks.append((slug,ats,pat.format(cand)))

out={s:[] for s in slugs}
with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
    for slug,res in ex.map(fetch,tasks):
        if res and res not in out[slug]:
            out[slug].append(res)
for slug in slugs:
    print(slug, json.dumps(out[slug]))
