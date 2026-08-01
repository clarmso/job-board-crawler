import re, requests, urllib.parse, html, csv, time
from urllib.parse import urlparse, parse_qs, unquote

SLUGS = """inmobi,innovaccer,innovid,innoviz,inscribe,inscripta,insider,insider-intelligence,insightec,inspectify,inspirato,instacart,instagram,instamojo,instructure,insurstaq-ai,intapp,integral-ad-science,integrate,integrate-ai,intel,intelycare,intercom,intersect,interview-kickstart,intrinsic,introhive,intuit,inuitive,investcloud,invision,invitae,involves,iprice-group,iqiyi-smart,iress,iris-nova,irl,irobot,iron-ox,ironnet,ispecimen,jam-city,jama,jamf,jasper,jasper-health,jd-id,jellyfish,jellysmack,jetclosing,jetty,jimdo,jiobit,jiviai,jobcase,jodo,join,jokr,joonko,jounce-therapeutics,journera,jumia,jumio,jump,jumpcloud,jungle-scout,junglee-games,juni,juniper,juniper-networks,juniper-square,jupiterone,just-eat,just-eat-takeaway,juul,kaiyo,kaleidoscope,kaltura,kandela,kandji,kaodim,kape,kape-technologies,kapten-free-now,karakuki,karat,karat-financial,karbon,karhoo,karma,karshare,kaseya,kaspersky,kaspien,katana,katerra,kavak,kayak-opentable,kazoo""".split(',')
HQ = {'inmobi':'','innovaccer':'US','innovid':'US','innoviz':'','inscribe':'US','inscripta':'US','insider':'','insider-intelligence':'US','insightec':'','inspectify':'US','inspirato':'US','instacart':'US','instagram':'US','instamojo':'','instructure':'US','insurstaq-ai':'','intapp':'US','integral-ad-science':'US','integrate':'US','integrate-ai':'Canada','intel':'US','intelycare':'US','intercom':'US','intersect':'','interview-kickstart':'US','intrinsic':'US','introhive':'Canada','intuit':'US','inuitive':'','investcloud':'US','invision':'US','invitae':'US','involves':'','iprice-group':'','iqiyi-smart':'','iress':'','iris-nova':'US','irl':'US','irobot':'US','iron-ox':'US','ironnet':'US','ispecimen':'US','jam-city':'US','jama':'US','jamf':'US','jasper':'US','jasper-health':'US','jd-id':'','jellyfish':'US','jellysmack':'US','jetclosing':'US','jetty':'US','jimdo':'Germany','jiobit':'US','jiviai':'','jobcase':'US','jodo':'','join':'Germany','jokr':'US','joonko':'','jounce-therapeutics':'US','journera':'US','jumia':'Germany','jumio':'US','jump':'','jumpcloud':'US','jungle-scout':'US','junglee-games':'','juni':'Sweden','juniper':'US','juniper-networks':'US','juniper-square':'US','jupiterone':'US','just-eat':'UK','just-eat-takeaway':'Netherlands','juul':'US','kaiyo':'US','kaleidoscope':'US','kaltura':'US','kandela':'US','kandji':'US','kaodim':'','kape':'UK','kape-technologies':'UK','kapten-free-now':'Germany','karakuki':'','karat':'US','karat-financial':'US','karbon':'US','karhoo':'UK','karma':'US','karshare':'UK','kaseya':'US','kaspersky':'','kaspien':'US','katana':'Estonia','katerra':'US','kavak':'','kayak-opentable':'US','kazoo':'US'}
UA={'user-agent':'Mozilla/5.0'}
BLOCKED=['linkedin.com','indeed.com','glassdoor.com','welcometothejungle.com','wellfound.com','pitchbook.com','wikipedia.org','crunchbase.com','jobera.com','hyring.com','resumeset.com','ziprecruiter.com','facebook.com','instagram.com','x.com','youtube.com']
SUPPORTED=[('greenhouse',['greenhouse.io','boards.greenhouse.io','job-boards.greenhouse.io','grnh.se']),('lever',['jobs.lever.co','lever.co']),('ashby',['jobs.ashbyhq.com','ashbyhq.com']),('workable',['workable.com']),('recruitee',['recruitee.com']),('smartrecruiters',['smartrecruiters.com']),('rippling',['rippling-ats.com','ats.rippling.com']),('gem',['gem.com'])]
OTHER=['myworkdayjobs.com','workday.com','icims.com','jobvite.com','bamboohr.com','teamtailor.com','personio','paylocity.com','successfactors.com','oraclecloud.com','adp.com']
RESULT_RE=re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',re.I|re.S)

session=requests.Session(); session.headers.update(UA)

def clean(href):
    if href.startswith('//'): href='https:'+href
    if 'duckduckgo.com/l/?' in href:
        qs=urllib.parse.urlparse(href).query
        u=parse_qs(qs).get('uddg')
        if u: return unquote(u[0])
    return href

def dom(u):
    try: return urlparse(u).netloc.lower().removeprefix('www.')
    except: return ''

def blocked(u):
    d=dom(u)
    return any(b in d for b in BLOCKED)

def detect(text,url=''):
    hay=(url+'\n'+(text or '')).lower()
    for ats,pats in SUPPORTED:
        if any(p in hay for p in pats): return ats
    if any(p in hay for p in OTHER): return 'other'
    return 'unknown'

def search(q):
    url='https://html.duckduckgo.com/html/?q='+urllib.parse.quote(q)
    txt=session.get(url,timeout=25).text
    out=[]
    for m in RESULT_RE.finditer(txt):
        href=clean(html.unescape(m.group(1)))
        title=re.sub('<.*?>','',html.unescape(m.group(2))).strip()
        out.append((title,href))
    return out

def fetch(u):
    try:
        r=session.get(u,timeout=25,allow_redirects=True)
        return r.url,r.text[:200000]
    except Exception:
        return u,''

def pick(slug,results):
    ats_direct=''; official=''; homepage=''
    for title,url in results:
        if blocked(url):
            continue
        d=dom(url); ul=url.lower(); tl=title.lower()
        if detect('',url)!='unknown' and not ats_direct:
            ats_direct=url
        if not official and any(k in tl or k in ul for k in ['career','careers','jobs','join','openings','hiring']):
            official=url
        if not homepage and slug.split('-')[0] in d.replace('.','-'):
            homepage=url
    return official or ats_direct or homepage or (results[0][1] if results else '')

rows=[]
for idx,slug in enumerate(SLUGS,1):
    results=search(slug.replace('-',' ')+' careers')
    picked=pick(slug,results)
    final,htmltxt=fetch(picked) if picked else ('','')
    ats=detect(htmltxt,final or picked)
    if ats=='unknown':
        for title,url in results[:10]:
            a=detect('',url)
            if a!='unknown':
                ats=a
                if not picked: picked=url
                break
    if ats=='unknown' and htmltxt:
        m=re.search(r'https?://[^"\'\s>]+', htmltxt)
        # no-op, but detect from entire HTML already tried
    if ats=='unknown' and (final or picked):
        ul=(final or picked).lower(); d=dom(final or picked)
        if any(x in ul for x in ['workday','icims','jobvite','bamboohr','teamtailor','personio']) or any(x in d for x in ['jobs.','careers.','apply.']):
            ats='other'
    rows.append({'slug':slug,'ats': '' if not (final or picked) else ats,'career_url': final or picked,'hq_country': HQ.get(slug,'')})
    print(idx, slug, rows[-1]['ats'], rows[-1]['career_url'])
    time.sleep(0.5)

with open('ats_results2.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['slug','ats','career_url','hq_country'])
    w.writeheader(); w.writerows(rows)
print('done',len(rows))
