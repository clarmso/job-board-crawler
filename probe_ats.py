import requests,re,sys,json
from itertools import product
headers={'User-Agent':'Mozilla/5.0'}
slugs='crowdstreet,cruise,crunchbase,crunchyroll,crypto-com,cs-disco,cto-ai,cue,cue-health,cuemath,cult-fit,culture-amp,culture-trip,curalie,curative,curbio,curefit,curology,currency,curve,cushion,cuyana,cvent,cyberark,cyberbit,cybercube,cybereason,cybergrx,cyberproof,cycognito,cypress-io,cyren,cyteir-therapeutics,d-id,d2iq,daily-harvest,dailypay,daloopa,dance,dandy,daniel-wellington,dapper-labs,daraz,dare,dark,darrow,dash,dastgyr,datagen,dataminr,datarails,datarobot,datastax,datera,datree,datto,dayforce,daylight,daytwo,dazn,dbt-labs,deadspin,dealshare,dealtale,decent,deep-instict,deep-instinct,deepverge,deepwatch,defined-ai,definitive-healthcare,degreed,dehaat,deliv,deliveroo,deliveroo-australia,delivery-hero,dell,demandbase,deputy,descartes-labs,desktop-metal,detectify,devo,dextrous-robotics,dhi-group,dialsource,dice,digg,digimarc,digital-currency-gruop,digital-river,digital-surge,digitalocean,discord,discourse,dispatch,dispatchhealth,divergent-3d,divvy'.split(',')
name_overrides={'crypto-com':'crypto-com','cs-disco':'disco','cto-ai':'ctoai','cue-health':'cuehealth','cult-fit':'cultfit','culture-amp':'cultureamp','cyteir-therapeutics':'cyteir','d-id':'did','d2iq':'d2iq','daily-harvest':'dailyharvest','dapper-labs':'dapperlabs','dark':'darktrace','dastgyr':'dastgyr','dbt-labs':'dbtlabs','defined-ai':'definedai','definitive-healthcare':'definitivehealthcare','descartes-labs':'descarteslabs','desktop-metal':'desktopmetal','dextrous-robotics':'dextrousrobotics','dhi-group':'dhigroup','digital-currency-gruop':'digitalcurrencygroup','digital-river':'digitalriver','digitalocean':'digitalocean','dispatchhealth':'dispatchhealth','divergent-3d':'divergent3d','cybercube':'cybercube','cybergrx':'cybergrx','cyberproof':'cyberproof','cypress-io':'cypress','culture-trip':'culturetrip','currency':'currencycloud','curve':'imaginecurve'}
patterns={
'greenhouse':['https://job-boards.greenhouse.io/{}','https://boards.greenhouse.io/{}'],
'lever':['https://jobs.lever.co/{}'],
'ashby':['https://jobs.ashbyhq.com/{}'],
'workable':['https://apply.workable.com/{}'],
'smartrecruiters':['https://careers.smartrecruiters.com/{}'],
'rippling':['https://ats.rippling.com/{}'],
'gem':['https://jobs.gem.com/{}'],
}

def check(url,slug):
    try:
        r=requests.get(url,headers=headers,timeout=12,allow_redirects=True)
    except Exception:
        return None
    text=r.text
    title=''
    m=re.search(r'<title>(.*?)</title>',text,re.I|re.S)
    if m: title=re.sub(r'\s+',' ',m.group(1)).strip()
    tl=title.lower()
    final=r.url
    if 'greenhouse' in url:
        if r.status_code==200 and 'page not found' not in tl and 'error' not in tl and 'jobs at' in tl:
            return {'ats':'greenhouse','url':final,'title':title}
    if 'lever.co' in url:
        if r.status_code==200 and 'not found' not in tl and title:
            return {'ats':'lever','url':final,'title':title}
    if 'ashbyhq.com' in url:
        if r.status_code==200 and title and tl!='jobs':
            return {'ats':'ashby','url':final,'title':title}
    if 'workable.com' in url:
        if r.status_code==200 and 'workable' not in tl[:30] and title:
            return {'ats':'workable','url':final,'title':title}
    if 'smartrecruiters.com' in url:
        if r.status_code==200 and final.rstrip('/')!= 'https://jobs.smartrecruiters.com' and 'smartrecruiters job search' not in tl and 'careers at' in tl and 'sandbox' not in tl and 'sbx' not in tl:
            return {'ats':'smartrecruiters','url':final,'title':title}
    if 'rippling.com' in url:
        if r.status_code==200 and 'rippling' not in tl[:25] and title:
            return {'ats':'rippling','url':final,'title':title}
    if 'jobs.gem.com' in url:
        if r.status_code==200 and title and ('jobs' in tl or slug.replace('-','') in text.lower()):
            return {'ats':'gem','url':final,'title':title}
    return None

for slug in slugs:
    cands={slug,slug.replace('-',''),slug.replace('-','_'),slug.replace('-','.')}
    if slug in name_overrides: cands.add(name_overrides[slug])
    cands={c for c in cands if c}
    found=[]
    for ats, urls in patterns.items():
        for cand in sorted(cands):
            for pat in urls:
                res=check(pat.format(cand),slug)
                if res:
                    found.append(res)
    print(slug, json.dumps(found))
