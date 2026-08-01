import requests, re, csv, urllib.parse, xml.etree.ElementTree as ET, json, time
from urllib.parse import urlparse, urljoin

SLUGS='primer,prisma,pristyn-care,privitar,procore,product-hunt,productboard,progrexion,project-ronin,project44,propertyguru,propzy,prosus,protego-trust-bank,proterra,protocol-labs,proton-ai,protonn,provi,providoor,pubmatic,pudutech,pulse-secure,puppet,pure-storage,purse,q4,qin1,qoala,qomplx,qt-company,quadream,qualcomm,qualtrics,quandoo,quanergy-systems,quantcast,quanterix,quanto,quantum-si,quartz,quibi,quicko,quidax,quillt,quintoandar,quizac,quizlet,quizy,qumulo,quora,qwick,qyuki,r3,rackspace,rad-power-bikes,rain,rainfocus,raken,ranger-insurance,rangle,rapid,rapid7,rapyd,rasa,rategenius,rdx-works,ready-robotics,reali,realpage,realpha,realself,realtor-com,rebel-foods,rebellion-defense,rec-room,recast,received,recharge,recur,recur-forever,red-hat,redbox,redbubble,reddoorz,redesign-health,redfin,redis,redox,ree-automotive,reef,refinery29,reforge,refurbed,regrow-ag,relativity,relevel,reliance-jiomart,religion-of-sports,remarkable'.split(',')
NAME_OVERRIDES={
    'product-hunt':'Product Hunt','project-ronin':'Project Ronin','proton-ai':'Proton.ai','q4':'Q4 Inc','qin1':'Qin1','qomplx':'QOMPLX','qt-company':'Qt Group','qyuki':'Qyuki','r3':'R3','rad-power-bikes':'Rad Power Bikes','rdx-works':'RDX Works','realtor-com':'Realtor.com','rec-room':'Rec Room','ree-automotive':'REE Automotive','regrow-ag':'Regrow Ag','religion-of-sports':'Religion of Sports','pristyn-care':'Pristyn Care','protego-trust-bank':'Protego Trust','pure-storage':'Pure Storage','project44':'project44','quintoandar':'QuintoAndar','realpha':'reAlpha','recur-forever':'Recur Forever',
}
DOMAIN_OVERRIDES={
    'primer':'primer.com', 'prisma':'prisma.io','pristyn-care':'pristyncare.com','privitar':'privitar.com','procore':'procore.com','product-hunt':'producthunt.com','productboard':'productboard.com','progrexion':'progrexion.com','project-ronin':'projectronin.com','project44':'project44.com','propertyguru':'propertyguru.com.sg','propzy':'propzy.vn','prosus':'prosus.com','protego-trust-bank':'protego.com','proterra':'proterra.com','protocol-labs':'protocol.ai','proton-ai':'proton.ai','protonn':'protonn.com','provi':'provi.com','providoor':'providoor.com.au','pubmatic':'pubmatic.com','pudutech':'pudutech.com','pulse-secure':'pulsesecure.net','puppet':'puppet.com','pure-storage':'purestorage.com','purse':'purse.io','q4':'q4inc.com','qin1':'qin1.com','qoala':'qoala.app','qomplx':'qomplx.com','qt-company':'qt.io','quadream':'quadream.com','qualcomm':'qualcomm.com','qualtrics':'qualtrics.com','quandoo':'quandoo.com','quanergy-systems':'quanergy.com','quantcast':'quantcast.com','quanterix':'quanterix.com','quanto':'quantoapp.com','quantum-si':'quantum-si.com','quartz':'qz.com','quibi':'quibi.com','quicko':'quicko.com','quidax':'quidax.com','quillt':'quillt.io','quintoandar':'quintoandar.com.br','quizac':'quizac.com','quizlet':'quizlet.com','quizy':'quizy.in','qumulo':'qumulo.com','quora':'quora.com','qwick':'qwick.com','qyuki':'qyuki.com','r3':'r3.com','rackspace':'rackspace.com','rad-power-bikes':'radpowerbikes.com','rain':'rain.us','rainfocus':'rainfocus.com','raken':'rakenapp.com','ranger-insurance':'ranger.com','rangle':'rangle.io','rapid':'rapidapi.com','rapid7':'rapid7.com','rapyd':'rapyd.net','rasa':'rasa.com','rategenius':'rategenius.com','rdx-works':'rdxworks.com','ready-robotics':'ready-robotics.com','reali':'reali.com','realpage':'realpage.com','realpha':'realpha.com','realself':'realself.com','realtor-com':'realtor.com','rebel-foods':'rebelfoods.com','rebellion-defense':'rebelliondefense.com','rec-room':'recroom.com','recast':'getrecast.com','received':'received.ai','recharge':'rechargepayments.com','recur':'recurclub.com','recur-forever':'recurforever.com','red-hat':'redhat.com','redbox':'redbox.com','redbubble':'redbubble.com','reddoorz':'reddoorz.com','redesign-health':'redesignhealth.com','redfin':'redfin.com','redis':'redis.io','redox':'redoxengine.com','ree-automotive':'ree.auto','reef':'reef.io','refinery29':'refinery29.com','reforge':'reforge.com','refurbed':'refurbed.com','regrow-ag':'regrow.ag','relativity':'relativity.com','relevel':'relevel.com','reliance-jiomart':'jiomart.com','religion-of-sports':'religionofsports.com','remarkable':'remarkable.com'
}
HQ_OVERRIDES={
    'primer':'US','prisma':'Germany','privitar':'UK','procore':'US','product-hunt':'US','productboard':'US','progrexion':'US','project-ronin':'US','project44':'US','prosus':'Netherlands','proterra':'US','protocol-labs':'US','proton-ai':'US','provi':'US','pubmatic':'US','puppet':'US','pure-storage':'US','q4':'Canada','qomplx':'US','qt-company':'Finland','qualcomm':'US','qualtrics':'US','quandoo':'Germany','quantcast':'US','quanterix':'US','quantum-si':'US','quizlet':'US','qumulo':'US','quora':'US','qwick':'US','rackspace':'US','rad-power-bikes':'US','rain':'US','rainfocus':'US','rangle':'Canada','rapid':'US','rapid7':'US','rapyd':'UK','rasa':'Germany','rategenius':'US','ready-robotics':'US','realpage':'US','realpha':'US','realself':'US','realtor-com':'US','rebellion-defense':'US','rec-room':'US','recharge':'US','red-hat':'US','redesign-health':'US','redfin':'US','redis':'US','redox':'US','refinery29':'US','reforge':'US','refurbed':'Austria','regrow-ag':'US','relativity':'US','religion-of-sports':'US','remarkable':'Norway'
}
ATS_PATTERNS={
    'greenhouse':r'greenhouse\.io|gh_jid=',
    'lever':r'lever\.co',
    'ashby':r'ashbyhq\.com',
    'workable':r'workable\.com',
    'recruitee':r'recruitee\.com',
    'smartrecruiters':r'smartrecruiters\.com',
    'rippling':r'rippling\.com',
    'gem':r'gem\.com',
}
COMMON_PATHS=['/careers','/careers/','/jobs','/jobs/','/company/careers','/about/careers','/join-us','/join-us/','/company/jobs','/company/careers/','/work-with-us','/open-positions']
S=requests.Session(); S.headers['user-agent']='Mozilla/5.0'

def fetch(url, timeout=20):
    try:
        r=S.get(url, timeout=timeout, allow_redirects=True)
        return r.status_code, r.url, r.text, r.headers.get('content-type','')
    except Exception:
        return None, None, None, None

def find_links(html, base):
    out=[]
    if not html: return out
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, re.I):
        href=href.strip()
        if href.startswith('mailto:') or href.startswith('javascript:') or href.startswith('#'): continue
        out.append(urljoin(base, href))
    return out

def detect_supported(text_or_url):
    s=(text_or_url or '').lower()
    for ats,pat in ATS_PATTERNS.items():
        if re.search(pat, s):
            return ats
    return None

def api_probe(slug):
    cands=[slug,slug.replace('-','')]
    if slug=='product-hunt': cands+=['producthunt']
    if slug=='pure-storage': cands+=['purestorage']
    if slug=='proton-ai': cands+=['protonai']
    if slug=='rebellion-defense': cands+=['rebelliondefense']
    if slug=='rad-power-bikes': cands+=['radpowerbikes']
    seen=set()
    for cand in cands:
        if cand in seen: continue
        seen.add(cand)
        # greenhouse
        st,u,txt,ct=fetch(f'https://boards-api.greenhouse.io/v1/boards/{cand}/jobs?content=true')
        if st==200:
            try:
                data=json.loads(txt)
                if 'jobs' in data:
                    board=f'https://job-boards.greenhouse.io/{cand}'
                    return 'greenhouse', board, 'api'
            except Exception: pass
        # lever
        st,u,txt,ct=fetch(f'https://api.lever.co/v0/postings/{cand}?mode=json')
        if st==200:
            try:
                data=json.loads(txt)
                if isinstance(data,list):
                    return 'lever', f'https://jobs.lever.co/{cand}', 'api'
            except Exception: pass
        # ashby
        st,u,txt,ct=fetch(f'https://api.ashbyhq.com/posting-api/job-board/{cand}?includeCompensation=true')
        if st==200:
            try:
                data=json.loads(txt)
                if 'jobs' in data:
                    return 'ashby', f'https://jobs.ashbyhq.com/{cand}', 'api'
            except Exception: pass
        # recruitee
        st,u,txt,ct=fetch(f'https://{cand}.recruitee.com/api/offers')
        if st==200:
            try:
                data=json.loads(txt)
                if 'offers' in data:
                    return 'recruitee', f'https://{cand}.recruitee.com', 'api'
            except Exception: pass
        # smartrecruiters valid only if totalFound > 0
        st,u,txt,ct=fetch(f'https://api.smartrecruiters.com/v1/companies/{cand}/postings?limit=1')
        if st==200:
            try:
                data=json.loads(txt)
                if data.get('totalFound',0)>0:
                    return 'smartrecruiters', f'https://jobs.smartrecruiters.com/{cand}', 'api'
            except Exception: pass
        # gem
        st,u,txt,ct=fetch(f'https://api.gem.com/job_board/v0/{cand}/job_posts/')
        if st==200:
            try:
                data=json.loads(txt)
                if isinstance(data,list):
                    return 'gem', f'https://jobs.gem.com/{cand}', 'api'
            except Exception: pass
        # rippling
        for path in [f'https://ats.rippling.com/{cand}/jobs',f'https://ats.rippling.com/en-CA/{cand}/jobs']:
            st,u,txt,ct=fetch(path)
            if st==200 and '__NEXT_DATA__' in txt:
                return 'rippling', u, 'api'
    return None,None,None

def bing_rss(query):
    st,u,txt,ct=fetch('https://www.bing.com/search?format=rss&q='+urllib.parse.quote(query), timeout=18)
    if st!=200 or not txt: return []
    try:
        root=ET.fromstring(txt)
    except Exception:
        return []
    items=[]
    for it in root.findall('./channel/item'):
        items.append(((it.findtext('title') or ''),(it.findtext('link') or ''),(it.findtext('description') or '')))
    return items

def discover_site(slug,name,domain):
    career=''
    ats=''
    # search results first
    for q in [f'"{name}" careers', f'{name} jobs', f'site:{domain} careers' if domain else '']:
        if not q: continue
        for title,link,desc in bing_rss(q)[:8]:
            text=' '.join([title,link,desc])
            det=detect_supported(text)
            if det:
                return det, link, 'search'
            if domain and domain.replace('www.','') in urlparse(link).netloc.lower() and re.search(r'career|job|join|work', text, re.I):
                career=link
                break
        if career: break
    # official pages
    seeds=[]
    if career: seeds.append(career)
    if domain:
        seeds.extend(['https://'+domain,'https://www.'+domain])
        for base in ['https://'+domain,'https://www.'+domain]:
            for p in COMMON_PATHS:
                seeds.append(base+p)
    checked=set()
    for url in seeds:
        if not url or url in checked: continue
        checked.add(url)
        st,fu,html,ct=fetch(url)
        if not st or st>=400 or not html: continue
        det=detect_supported(fu) or detect_supported(html)
        if det:
            m=re.search(r'https?://[^"\'\s>]+(?:greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|recruitee\.com|smartrecruiters\.com|rippling\.com|gem\.com)[^"\'\s<]*', html, re.I)
            return det, (m.group(0) if m else fu), 'html'
        if not career and re.search(r'career|job|join|opening|position', fu+' '+html[:5000], re.I):
            career=fu
        # one hop follow links from homepage or career page
        if domain and (url.endswith(domain) or '/careers' in url or '/jobs' in url):
            for link in find_links(html, fu)[:80]:
                text=link.lower()
                if detect_supported(link):
                    return detect_supported(link), link, 'link'
                if domain.replace('www.','') in urlparse(link).netloc.lower() and re.search(r'career|job|join|work', text) and not career:
                    career=link
    if career:
        return 'other', career, 'career'
    return 'unknown','', 'none'

rows=[]
for slug in SLUGS:
    name=NAME_OVERRIDES.get(slug, slug.replace('-',' ').title())
    domain=DOMAIN_OVERRIDES.get(slug)
    ats,url,src=api_probe(slug)
    if not ats:
        ats,url,src=discover_site(slug,name,domain)
    hq=HQ_OVERRIDES.get(slug,'')
    rows.append((slug,ats,url,hq,src))
    print(slug, ats, url, hq, src)
    time.sleep(0.1)

with open('/Users/clare/Documents/workspace/job-board-crawler/research_output_v2.csv','w',newline='') as f:
    w=csv.writer(f)
    w.writerow(['slug','ats','career_url','hq_country','source'])
    w.writerows(rows)
