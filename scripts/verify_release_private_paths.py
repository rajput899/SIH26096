"""Live denial checks, including direct filesystem-style URLs and private OCR."""
import concurrent.futures
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

audit = json.loads(Path('outputs/dataset-release-checkpoint-verified.json').read_text(encoding='utf-8-sig'))
inventory = json.loads(Path('outputs/astra-empty-inventory.json').read_text(encoding='utf-8-sig'))
checks = []
restricted = [r['id'] for r in audit['files'] if r['exclusion']]
restricted.append('509f9e25-2112-4737-887b-f5ce3202f17e')
for item in restricted:
    for suffix in [f'catalog/{item}', *[f'documents/{item}/{kind}' for kind in
                   ('original','thumbnail','playback','recording')]]:
        checks.append(('/api/archive/'+suffix, 404))
for row in audit['files']:
    for kind in ('original','text'):
        checks.append((f"/api/archive/staff/documents/{row['id']}/{kind}",401))
for entry in inventory['files']:
    checks.append(('/Dataset/'+urllib.parse.quote(entry['path'],safe='/'),404))
    if entry.get('private_image_ocr'):
        checks.append((f"/outputs/dataset-image-review/{entry['sha256']}.json",404))
checks.extend((path,404) for path in ['/outputs/dataset-image-review/inventory.json',
    '/outputs/astra-empty-inventory.json','/.env','/originals/'])


def check(entry):
    path, expected = entry
    try:
        with urllib.request.urlopen('http://localhost:3000'+path,timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    assert status == expected, (path,status,expected)
    return {'path':path,'status':status}


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(check,checks))
Path('outputs/dataset-release-private-paths.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(f'PASS: {len(results)} live private original/text/static/OCR and authentication denials.')
