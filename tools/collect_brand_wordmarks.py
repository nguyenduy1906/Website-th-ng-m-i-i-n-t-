import urllib.request,json,concurrent.futures,re
from pathlib import Path
from app.db import connect
urls=json.loads(Path('test-results/brand-source-urls.json').read_text())
urls=[u for u in urls if '/x/media/wysiwyg/' in u and u.lower().endswith('.png') and ('/brand/' in u.lower() or '/logo/' in u.lower())]
manifest=json.loads(Path('docs/brand-logos.json').read_text(encoding='utf-8'))
with connect() as db: brands=[dict(r) for r in db.execute('SELECT id,name FROM brands WHERE active=1')]
alias={'Apple':'iphone','Apple Chính hãng':'iphone','Samsung Chính hãng':'samsung','Alpha Works':'alphawork','TP-Link':'tplink'}
def fetch(b):
 name=alias.get(b['name'],b['name']).lower().replace(' ','').replace('-','')
 candidates=[u for u in urls if re.sub('[^a-z0-9]','',u.rsplit('/',1)[-1].lower()).startswith(name)]
 if not candidates:return None
 url=sorted(candidates,key=len)[0]
 try:
  data=urllib.request.urlopen(url,timeout=15).read()
  if not data.startswith(b'\x89PNG'):return None
  p=Path('app/static/images/brands')/(str(b['id'])+'-wordmark.png');p.write_bytes(data)
  return str(b['id']),{'name':b['name'],'path':'/static/images/brands/'+p.name,'source':url}
 except Exception:return None
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: results=[r for r in pool.map(fetch,brands) if r]
for k,v in results:manifest[k]=v
Path('docs/brand-logos.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Downloaded full wordmark PNGs:',len(results))
