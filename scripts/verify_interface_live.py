"""Opt-in live interface-only inference/cache check via localhost:3000."""
import json
import urllib.request
from pathlib import Path

BASE='http://localhost:3000/api/archive/interface/'
def request(path,body=None):
    req=urllib.request.Request(BASE+path,data=json.dumps(body).encode() if body else None,
                              headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as response:
        return json.load(response)

capability=request('languages')
assert capability['confirmed_pairs']==[['en','hi']], capability
catalog=json.loads(Path('frontend/src/interface-strings.json').read_text('utf-8'))
keys=list(catalog)
translated={}
missing=[]
for offset in range(0,len(keys),30):
    batch=request('translations',{'keys':keys[offset:offset+30],'target_language':'hi'})
    translated.update(batch['translations'])
    missing.extend(batch['missing'])
    print(f'Interface cache: {offset+len(keys[offset:offset+30])}/{len(keys)}, missing {len(missing)}',flush=True)
Path('outputs/interface-live.json').write_text(json.dumps({'mocked':False,
    'capability':capability,'registered_strings':len(keys),'translated':len(translated),
    'missing':{key:catalog[key] for key in missing},'private_or_archival_text_sent':False,
    'translations':translated},ensure_ascii=False,indent=2),encoding='utf-8')
print('Live interface translation audit saved.',flush=True)
