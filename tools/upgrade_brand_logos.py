import urllib.request,json,concurrent.futures
from pathlib import Path
m=json.loads(Path('docs/brand-logos.json').read_text(encoding='utf-8'))
def fetch(item):
 key,b=item;slug=b['name'].lower().replace(' chính hãng','').replace(' ','').replace('-','');url='https://raw.githubusercontent.com/gilbarbara/logos/main/logos/'+slug+'.svg'
 try:
  data=urllib.request.urlopen(url,timeout=15).read()
  if b'<svg' not in data:return None
  path=Path('app/static/images/brands')/(key+'-full.svg');path.write_bytes(data);return key,{'name':b['name'],'path':'/static/images/brands/'+path.name,'source':url}
 except Exception:return None
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: results=[r for r in pool.map(fetch,m.items()) if r]
for key,value in results:m[key]=value
Path('docs/brand-logos.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print('Full-color replacement logos:',len(results))
for url in ['https://raw.githubusercontent.com/simple-icons/simple-icons/v15.0.0/_data/simple-icons.json','https://cdn.jsdelivr.net/npm/simple-icons@15.0.0/_data/simple-icons.json']:
 try:
  data=urllib.request.urlopen(url,timeout=15).read();Path('test-results/simple-icons-data.json').write_bytes(data);print('Color metadata downloaded');break
 except Exception:pass
