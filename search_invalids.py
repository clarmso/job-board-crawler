import base64, csv, html, json, re, time
from urllib.parse import quote_plus, unquote, urljoin, urlparse
import requests

invalid = '''sunfolding,superlearn,superops,superrare,swappie,sweetescape,swing-education,sword-health,swyft,swyftx,syft-technologies,symend,synamedia,synapsefi,synapsica,synergysuite,synlogic,syte,tabnine,tackle,tackle-io,tails-com,tailwind-labs,take-two,take-two-interactive,takl,talent-com,talis-biomedical,tally,tamara-mellon,tapas-media,tapps-games,tcr2,teachmint,teads,teampay,techadvance,teladoc-health,telenav,tempo-automation,tempus-ex,ten-square-games,tenable,tencent,tenurex,tesla,tessera,the-appraisal-lane,the-athletic,the-gist,the-good-glamm-group,the-grommet,the-guild,the-iconic,the-meet-group,the-messenger,the-modist,the-mom-project,the-muse,the-org,the-predictive-index,the-realreal,the-sill,the-trade-desk,the-wing,the-zebra,thegist'''.split(',')
SESSION=requests.Session(); SESSION.headers.update({'User-Agent':'Mozilla/5.0'})
ATS_PATTERNS=[
    ('greenhouse',[r'greenhouse\.io',r'boards-api\.greenhouse\.io',r'boards\.greenhouse\.io',r'job-boards\.greenhouse\.io']),
    ('lever',[r'lever\.co']),('ashby',[r'ashbyhq\.com']),('workable',[r'workable\.com']),('recruitee',[r'recruitee\.com']),('smartrecruiters',[r'smartrecruiters\.com']),('rippling',[r'rippling\.com']),('gem',[r'jobs\.gem\.com', r'api\.gem\.com/job_board'])]
EXCLUDE=['linkedin.com','glassdoor.','indeed.','wikipedia.org','facebook.com','instagram.com','x.com','twitter.com','youtube.com','crunchbase.com','builtin.com','wellfound.','comparably.com']
MANUAL_NAME={'swing-education':'swing education','sword-health':'sword health','syft-technologies':'syft technologies','synapsefi':'synapsefi','tackle-io':'tackle io','tails-com':'tails.com','take-two':'take two','take-two-interactive':'take two interactive','talent-com':'talent.com','talis-biomedical':'talis biomedical','tapas-media':'tapas media','tapps-games':'tapps games','teladoc-health':'teladoc health','tempo-automation':'tempo automation','tempus-ex':'tempus ex machina','ten-square-games':'ten square games','the-appraisal-lane':'the appraisal lane','the-good-glamm-group':'the good glamm group','the-meet-group':'the meet group','the-mom-project':'the mom project','the-predictive-index':'the predictive index','the-realreal':'the realreal','the-trade-desk':'the trade desk','the-zebra':'the zebra','thegist':'the gist'}

def name(slug): return MANUAL_NAME.get(slug, slug.replace('-', ' '))

def decode_bing_href(href):
    href=html.unescape(href)
    m=re.search(r'[?&]u=([^&]+)', href)
    if not m: return href
    val=unquote(m.group(1))
    if val.startswith('a1'): val=val[2:]
    if val.startswith('http'): return val
    try:
        dec=base64.b64decode(val+'===').decode('utf-8','ignore')
        return dec
    except Exception:
        return href

def bing(query):
    text=SESSION.get('https://www.bing.com/search?q='+quote_plus(query),timeout=20).text
    out=[]
    for href,title in re.findall(r'<h2[^>]*><a [^>]*href="(.*?)"[^>]*>(.*?)</a></h2>', text, re.S):
        title=re.sub('<.*?>','',title)
        url=decode_bing_href(href)
        out.append((html.unescape(title).strip(),url))
    return out

def good(url):
    return url.startswith('http') and not any(x in urlparse(url).netloc.lower() for x in EXCLUDE)

def fetch(url):
    try:
        r=SESSION.get(url,timeout=20,allow_redirects=True)
        return r.status_code,r.url,r.text[:250000]
    except Exception:
        return 0,url,''

def ats(url,text):
    low=(url+'\n'+text).lower()
    for a,pats in ATS_PATTERNS:
        if any(re.search(p,low) for p in pats):
            if a=='ashby' and 'jobboard":null' in low:
                continue
            return a
    if any(x in low for x in ['workday','myworkdayjobs','icims','jobvite','successfactors','dayforce','bamboohr','teamtailor','greenhouse.io/embed','workforcenow','oraclecloud','ultipro','ukg','paylocity','paycomonline']):
        return 'other'
    return ''

def links(page_url,text):
    out=[]
    for href in re.findall(r'href=["\']([^"\']+)["\']', text, re.I):
        href=html.unescape(href)
        if href.startswith(('javascript:','mailto:')): continue
        full=urljoin(page_url,href)
        low=full.lower()
        if any(k in low for k in ['career','careers','job','jobs','join-us','work-with-us','lever.co','greenhouse','ashbyhq','workable','recruitee','smartrecruiters','rippling','jobs.gem.com']):
            out.append(full)
    seen=set(); res=[]
    for u in out:
        if u not in seen:
            seen.add(u); res.append(u)
    return res[:12]

def score(url,title,body,a):
    s=0
    low=(url+' '+title).lower()
    if a: s+=5
    if any(k in low for k in ['career','careers','jobs','join-us','work-with-us']): s+=2
    if any(k in low for k in ['greenhouse','lever.co','ashbyhq','workable','recruitee','smartrecruiters','rippling','jobs.gem.com']): s+=3
    if title and any(k in title.lower() for k in ['career','careers','jobs']): s+=2
    return s

res=[]
for slug in invalid:
    cands=[]
    for q in [f'{name(slug)} careers', f'{name(slug)} jobs']:
        for title,url in bing(q)[:10]:
            if good(url): cands.append(url)
        time.sleep(0.2)
    seen=set(); cands=[u for u in cands if not (u in seen or seen.add(u))]
    inspected=[]
    for u in cands[:6]:
        st,fu,body=fetch(u)
        if st!=200 or not good(fu):
            continue
        mt=re.search(r'<title>(.*?)</title>', body, re.I|re.S)
        title=re.sub(r'\s+',' ',re.sub('<.*?>','',mt.group(1))).strip() if mt else ''
        a=ats(fu,body[:80000])
        inspected.append((score(fu,title,body,a),a or '',fu,title))
        for link in links(fu,body):
            st2,fu2,body2=fetch(link)
            if st2!=200 or not good(fu2):
                continue
            mt2=re.search(r'<title>(.*?)</title>', body2, re.I|re.S)
            title2=re.sub(r'\s+',' ',re.sub('<.*?>','',mt2.group(1))).strip() if mt2 else ''
            a2=ats(fu2,body2[:80000])
            inspected.append((score(fu2,title2,body2,a2),a2 or '',fu2,title2))
        time.sleep(0.2)
    inspected=sorted(inspected, reverse=True)
    best=inspected[0] if inspected else None
    print('\nSLUG',slug)
    for item in inspected[:8]:
        print(item)
    if best:
        res.append({'slug':slug,'ats':best[1] or 'unknown','career_url':best[2],'title':best[3]})
    else:
        res.append({'slug':slug,'ats':'unknown','career_url':'','title':''})

json.dump(res, open('/Users/clare/Documents/workspace/job-board-crawler/search_invalids_results.json','w'), indent=2)
