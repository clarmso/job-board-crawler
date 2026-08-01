import requests, json
hits = {
 'equityzen':['greenhouse'], 'eucalyptus':['greenhouse'], 'everlane':['greenhouse'], 'everquote':['greenhouse'], 'everlaw':['greenhouse'], 'expel':['greenhouse'], 'fandom':['greenhouse'], 'fanduel':['greenhouse'], 'fastly':['greenhouse'], 'feedzai':['greenhouse'], 'figure':['greenhouse'], 'fetch':['greenhouse','gem'], 'fireblocks':['greenhouse'], 'flex':['greenhouse'], 'exabeam':['greenhouse'], 'flexe':['greenhouse'],
 'everbridge':['lever'], 'farfetch':['lever'], 'filevine':['lever'], 'fiscalnote':['lever'], 'ezcater':['lever'],
 'evolve':['ashby'], 'fable':['ashby'], 'flink':['ashby'], 'ethereum-foundation':['ashby'],
 'fabric':['gem','rippling'], 'firehydrant':['rippling'], 'flatiron-school':['rippling']
}
headers={'User-Agent':'Mozilla/5.0'}
for slug,plats in hits.items():
  print('\n##', slug)
  for p in plats:
    if p=='greenhouse':
      url=f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true'
      r=requests.get(url,headers=headers)
      data=r.json(); jobs=data.get('jobs',[])
      first=jobs[0] if jobs else {}
      print('greenhouse total', data.get('meta',{}).get('total'), 'firstcompany?', first.get('metadata',[])[:1], 'title', first.get('title'), 'loc', first.get('location',{}).get('name'), 'abs', first.get('absolute_url'))
    elif p=='lever':
      url=f'https://api.lever.co/v0/postings/{slug}?mode=json'
      r=requests.get(url,headers=headers)
      data=r.json(); first=(data or [{}])[0]
      print('lever count', len(data), 'title', first.get('text'), 'hosted', first.get('hostedUrl'))
    elif p=='ashby':
      url=f'https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true'
      r=requests.get(url,headers=headers)
      data=r.json(); jobs=data.get('jobs',[])
      first=(jobs or [{}])[0]
      print('ashby count', len(jobs), 'company', data.get('boardName'), 'title', first.get('title'), 'url', first.get('jobUrl'))
    elif p=='gem':
      url=f'https://api.gem.com/job_board/v0/{slug}/job_posts/'
      r=requests.get(url,headers=headers)
      data=r.json(); first=(data or [{}])[0]
      print('gem count', len(data), 'company', first.get('company_name'), 'url', first.get('apply_url'))
    elif p=='rippling':
      url=f'https://ats.rippling.com/en-CA/{slug}/jobs'
      r=requests.get(url,headers=headers)
      print('rippling status', r.status_code, 'url', r.url, 'titlematch', ('<title>' in r.text and r.text[r.text.find('<title>'):r.text.find('</title>')+8]))
