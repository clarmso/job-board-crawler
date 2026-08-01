import csv, html, re, time
from urllib.parse import urljoin, urlparse
import requests
from ddgs import DDGS

SLUGS='thepeer,theskimm,thewrap,thimble,thinx,thirdlove,thirty-madison,thoughtspot,thoughtworks,thrasio,thread,thredup,thrive,thriver,thumbtack,thursday,tia,tibber,tickertape,ticketmaster,ticketswap,tidal,tidepool,tiendanube,tier-mobility,tifin,tiki,tiktok,tiktok-india,tilia,till-payments,tilting-point,times-internet,tipalti,titan-medical,toast,tokopedia,tome,tome-biosciences,tomo,tomorrow,tomtom,tonal,tonik,tonkean,tools-for-humanity,toothsi,toplyne,toppr,toptal,tor,torii,toshiba,totango,toucan,tract,tractable,tractive,trade-republic,tradewindow,transmit-security,travelbank,traveloka,traveltriangle,trax,tray-io,treasure-financial,treasury-prime,treehouse,trell,trellix,trend-micro,trendsales,tricida,trigo,tripactions,tripadvisor,tripbam,triplebyte,triplelift,tripwire,trivago,tropic,trove-recommerce,truck-it-in,truckstop-com,true-anomaly,truecaller,truecar,truelayer,truepill,truiloo,truss-works,trustly,trybe,tufin,tuft-needle,tul,turnitin,turntide'.split(',')
NAME={'thepeer':'Thepeer','theskimm':'theSkimm','thewrap':'TheWrap','thimble':'Thimble','thinx':'THINX','thirdlove':'ThirdLove','thirty-madison':'Thirty Madison','thoughtspot':'ThoughtSpot','thoughtworks':'Thoughtworks','thrasio':'Thrasio','thread':'Thread','thredup':'thredUP','thrive':'Thrive Global','thriver':'Thriver','thumbtack':'Thumbtack','thursday':'Thursday','tia':'Tia','tibber':'Tibber','tickertape':'Tickertape','ticketmaster':'Ticketmaster','ticketswap':'TicketSwap','tidal':'TIDAL','tidepool':'Tidepool','tiendanube':'Tiendanube','tier-mobility':'TIER Mobility','tifin':'TIFIN','tiki':'Tiki','tiktok':'TikTok','tiktok-india':'TikTok India','tilia':'Tilia','till-payments':'Till Payments','tilting-point':'Tilting Point','times-internet':'Times Internet','tipalti':'Tipalti','titan-medical':'Titan Medical','toast':'Toast','tokopedia':'Tokopedia','tome':'Tome','tome-biosciences':'Tome Biosciences','tomo':'Tomo','tomorrow':'Tomorrow.io','tomtom':'TomTom','tonal':'Tonal','tonik':'Tonik','tonkean':'Tonkean','tools-for-humanity':'Tools for Humanity','toothsi':'Toothsi','toplyne':'Toplyne','toppr':'Toppr','toptal':'Toptal','tor':'Tor Project','torii':'Torii','toshiba':'Toshiba','totango':'Totango','toucan':'Toucan','tract':'Tract','tractable':'Tractable','tractive':'Tractive','trade-republic':'Trade Republic','tradewindow':'TradeWindow','transmit-security':'Transmit Security','travelbank':'TravelBank','traveloka':'Traveloka','traveltriangle':'TravelTriangle','trax':'Trax','tray-io':'Tray.io','treasure-financial':'Treasure Financial','treasury-prime':'Treasury Prime','treehouse':'Treehouse','trell':'Trell','trellix':'Trellix','trend-micro':'Trend Micro','trendsales':'Trendsales','tricida':'Tricida','trigo':'Trigo','tripactions':'TripActions','tripadvisor':'Tripadvisor','tripbam':'Tripbam','triplebyte':'Triplebyte','triplelift':'TripleLift','tripwire':'Tripwire','trivago':'trivago','tropic':'Tropic','trove-recommerce':'Trove Recommerce','truck-it-in':'Truck It In','truckstop-com':'Truckstop.com','true-anomaly':'True Anomaly','truecaller':'Truecaller','truecar':'TrueCar','truelayer':'TrueLayer','truepill':'Truepill','truiloo':'Trulioo','truss-works':'Truss Works','trustly':'Trustly','trybe':'Trybe','tufin':'Tufin','tuft-needle':'Tuft & Needle','tul':'Tul','turnitin':'Turnitin','turntide':'Turntide'}
HQ={'thepeer':'','theskimm':'US','thewrap':'US','thimble':'US','thinx':'US','thirdlove':'US','thirty-madison':'US','thoughtspot':'US','thoughtworks':'US','thrasio':'US','thread':'UK','thredup':'US','thrive':'US','thriver':'Canada','thumbtack':'US','thursday':'UK','tia':'US','tibber':'Norway','tickertape':'','ticketmaster':'US','ticketswap':'Netherlands','tidal':'US','tidepool':'US','tiendanube':'','tier-mobility':'Germany','tifin':'US','tiki':'','tiktok':'','tiktok-india':'','tilia':'US','till-payments':'','tilting-point':'US','times-internet':'','tipalti':'US','titan-medical':'Canada','toast':'US','tokopedia':'','tome':'US','tome-biosciences':'US','tomo':'US','tomorrow':'US','tomtom':'Netherlands','tonal':'US','tonik':'','tonkean':'US','tools-for-humanity':'US','toothsi':'','toplyne':'','toppr':'','toptal':'US','tor':'US','torii':'US','toshiba':'','totango':'US','toucan':'US','tract':'UK','tractable':'UK','tractive':'Austria','trade-republic':'Germany','tradewindow':'','transmit-security':'US','travelbank':'US','traveloka':'','traveltriangle':'','trax':'','tray-io':'US','treasure-financial':'US','treasury-prime':'US','treehouse':'US','trell':'','trellix':'US','trend-micro':'','trendsales':'Denmark','tricida':'US','trigo':'','tripactions':'US','tripadvisor':'US','tripbam':'US','triplebyte':'US','triplelift':'US','tripwire':'US','trivago':'Germany','tropic':'US','trove-recommerce':'US','truck-it-in':'','truckstop-com':'US','true-anomaly':'US','truecaller':'Sweden','truecar':'US','truelayer':'UK','truepill':'US','truiloo':'Canada','truss-works':'US','trustly':'Sweden','trybe':'','tufin':'','tuft-needle':'US','tul':'','turnitin':'US','turntide':'US'}
BAD='linkedin.com indeed.com glassdoor.com builtin.com wellfound.com ziprecruiter.com jobs2careers.com verjobs.com remotejobsfinder.co talent.com rocketreach.co comparably.com theladders.com simplify.jobs startup.jobs reddit.com'.split()
ATS=[('greenhouse',['greenhouse.io','grnh.se']),('lever',['lever.co']),('ashby',['ashbyhq.com']),('workable',['workable.com']),('recruitee',['recruitee.com']),('smartrecruiters',['smartrecruiters.com']),('rippling',['ats.rippling.com','rippling.com']),('gem',['gem.com'])]
OTHER=['myworkdayjobs.com','workday.com','icims.com','jobvite.com','bamboohr.com','teamtailor.com','personio','paylocity.com','successfactors.com','applytojob.com','greenhouse-jobboard?','applytojob','careerplug.com','oraclecloud.com','pinpointhq.com','jobs.personio.com']
S=requests.Session(); S.headers.update({'User-Agent':'Mozilla/5.0'})

def dom(u):
    try:return urlparse(u).netloc.lower().removeprefix('www.')
    except:return ''

def blocked(u): return any(b in dom(u) or b in u.lower() for b in BAD)

def ats(text,url=''):
    h=(url+'\n'+(text or '')).lower()
    for k,pp in ATS:
        if any(p in h for p in pp): return k
    if any(p in h for p in OTHER): return 'other'
    return 'unknown'

def fetch(u):
    try:
        r=S.get(u,timeout=20,allow_redirects=True)
        return r.url,r.text[:250000]
    except: return u,''

def score(slug,title,href):
    s=0; u=href.lower(); t=(title or '').lower(); key=slug.replace('-','')
    if blocked(href): return -999
    if ats('',href)!='unknown': s+=50
    if any(x in u or x in t for x in ['career','careers','jobs','join','hiring','open roles','positions']): s+=20
    if key in re.sub(r'[^a-z0-9]','',u+t): s+=20
    for tok in [x for x in slug.split('-') if len(x)>2 and x not in {'com','india'}]:
        if tok in u or tok in t: s+=4
    return s

def find_link(base,page):
    for m in re.finditer(r"href=[\"']([^\"']+)[\"']",page,re.I):
        h=html.unescape(m.group(1))
        if h.startswith(('mailto:','javascript:')): continue
        if re.search(r'career|jobs|join-us|joinus|open-roles|positions',h,re.I): return urljoin(base,h)
    return ''

out=[]
for i,slug in enumerate(SLUGS,1):
    q=f"{NAME[slug]} careers"
    print(i,slug,q,flush=True)
    try: res=list(DDGS().text(q,max_results=8))
    except Exception as e:
        print(' search_err',e,flush=True); res=[]
    res=sorted(res,key=lambda r:score(slug,r.get('title',''),r.get('href','')),reverse=True)
    career=''; a='unknown'
    for r in res[:6]:
        href=r.get('href',''); title=r.get('title','')
        if not href or blocked(href): continue
        au=ats('',href)
        if au!='unknown': career,a=href,au; break
        fu,pg=fetch(href)
        au=ats(pg,fu)
        if au=='unknown':
            lk=' '.join(re.findall(r'href=["\']([^"\']+)["\']',pg,re.I)[:800])
            au=ats(lk)
            if au!='unknown':
                m=re.search(r'https?://[^"\'\s>]+(?:greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|recruitee\.com|smartrecruiters\.com|rippling\.com|gem\.com|myworkdayjobs\.com|icims\.com|jobvite\.com|bamboohr\.com|teamtailor\.com|personio[^"\'\s>]*)[^"\'\s<]*',pg,re.I)
                if m: fu=m.group(0)
        if au=='unknown' and not re.search(r'career|jobs|join|hiring',fu,re.I):
            maybe=find_link(fu,pg)
            if maybe:
                fu2,pg2=fetch(maybe); au2=ats(pg2,fu2)
                if au2=='unknown':
                    lk=' '.join(re.findall(r'href=["\']([^"\']+)["\']',pg2,re.I)[:800]); au2=ats(lk)
                if au2!='unknown' or re.search(r'career|jobs|join|hiring',fu2,re.I): fu,pg,au=fu2,pg2,au2
        if au!='unknown': career,a=fu,au; break
        if not career and re.search(r'career|jobs|join|hiring',fu+title,re.I): career=fu; a='other'
    out.append({'slug':slug,'ats':a if career else 'unknown','career_url':career,'hq_country':HQ[slug]})
    time.sleep(0.5)
with open('research_t_results.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['slug','ats','career_url','hq_country']); w.writeheader(); w.writerows(out)
