from pathlib import Path
import urllib.request, json, concurrent.futures
from app.db import connect
folder=Path('app/static/images/brands');folder.mkdir(exist_ok=True)
with connect() as db: brands=[dict(r) for r in db.execute('SELECT id,name FROM brands WHERE active=1')]
alias={'HP':'hp','Apple Chính hãng':'apple','Samsung Chính hãng':'samsung','TP-Link':'tplink','MSI':'msi','NEU':'neu'}
def fetch(b):
 slug=alias.get(b['name'],b['name'].lower().replace(' ', '').replace('-',''))
 try:
  data=urllib.request.urlopen('https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/'+slug+'.svg',timeout=20).read()
  if b'<svg' not in data:return None
  path=folder/(str(b['id'])+'.svg');path.write_bytes(data)
  return str(b['id']),{'name':b['name'],'path':'/static/images/brands/'+path.name,'source':'https://github.com/simple-icons/simple-icons/blob/develop/icons/'+slug+'.svg'}
 except Exception:return None
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: results=[r for r in pool.map(fetch,brands) if r]
Path('docs/brand-logos.json').write_text(json.dumps(dict(results),ensure_ascii=False,indent=2),encoding='utf-8')
print('Downloaded',len(results),'brand logos')
