"""Reconcile every manifest file against actual localhost public APIs and original bytes."""
import concurrent.futures
import argparse
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = 'http://localhost:3000/api/archive/'
parser = argparse.ArgumentParser()
parser.add_argument('--output', default='outputs/dataset-release-public-audit.json')
args = parser.parse_args()
manifest = json.loads(Path('outputs/dataset-release-manifest.json').read_text(encoding='utf-8'))
applied = json.loads(Path('outputs/dataset-release-applied.json').read_text(encoding='utf-8-sig'))
by_path = {entry['path']:entry for entry in applied['files']}


def request(path, headers=None):
    try:
        return urllib.request.urlopen(urllib.request.Request(BASE + path,headers=headers or {}),
                                      timeout=120)
    except urllib.error.HTTPError as error:
        return error


def json_get(path):
    with request(path) as response:
        assert response.status == 200, (path,response.status)
        return json.load(response)


catalogue = json_get('catalog?limit=200')
catalogue_ids = {row['id'] for row in catalogue}


def check(entry):
    recorded = by_path[entry['path']]
    item = recorded['id']
    result = {'path':entry['path'],'sha256':entry['sha256'],'id':item,
              'collection':entry['collection'],'exclusion':recorded['exclusion']}
    if recorded['exclusion']:
        assert item not in catalogue_ids
        for suffix in [f'catalog/{item}',f'documents/{item}/original',
                       f'documents/{item}/thumbnail',f'documents/{item}/playback']:
            with request(suffix) as response:
                assert response.status == 404, (suffix,response.status)
        result['public'] = False
        return result
    assert item in catalogue_ids, entry['path']
    detail = json_get(f'catalog/{item}')
    assert detail['document']['checksum'] == entry['sha256']
    assert detail['document']['dataset_path'] == entry['path']
    assert detail['document']['dataset_authorization'] == manifest['authorization']
    # Display authorization must not certify existing machine text or source provenance.
    assert detail['document']['provenance_status'] == 'pending'
    assert detail['pages'] == []
    with request(f'documents/{item}/original') as response:
        assert response.status == 200, (item,response.status)
        digest = hashlib.sha256()
        length = 0
        while block := response.read(1024*1024):
            digest.update(block)
            length += len(block)
        assert digest.hexdigest() == entry['sha256'] and length == entry['bytes']
        assert response.headers['Cache-Control'] == 'no-store'
    result.update(public=True,original_status=200,original_hash_verified=True,bytes=length)
    if entry['mime'].startswith('image/'):
        with request(f'documents/{item}/thumbnail') as response:
            assert response.status == 200 and response.headers['Content-Type'].startswith('image/jpeg')
            assert response.read(2) == b'\xff\xd8'
        result['thumbnail_status'] = 200
    if entry['mime'].startswith(('video/','audio/')):
        with request(f'documents/{item}/playback', {'Range':'bytes=0-63'}) as response:
            assert response.status == 206, (item,response.status)
            assert len(response.read()) == 64
            assert response.headers['Content-Range'].startswith('bytes 0-63/')
        assert json_get(f'documents/{item}/recording') is None
        result['playback_range_status'] = 206
    with request(f'staff/documents/{item}/original') as response:
        assert response.status == 401
    return result


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(check,manifest['files']))
groups = {}
for name in ('manuscripts','photographs','videos'):
    rows = json_get('catalog?collection='+name+'&origin=dataset&limit=200')
    expected = {r['id'] for r in results if r['collection']==name and r['public']}
    assert {r['id'] for r in rows} == expected
    paged = []
    for offset in range(0,len(rows)+1,12):
        paged += json_get(f'catalog?collection={name}&origin=dataset&limit=12&offset={offset}')
    assert [r['id'] for r in paged] == [r['id'] for r in rows]
    groups[name] = len(rows)
photo = '509f9e25-2112-4737-887b-f5ce3202f17e'
for suffix in [f'catalog/{photo}',f'documents/{photo}/original',f'documents/{photo}/thumbnail',
               f'documents/{photo}/playback',f'documents/{photo}/recording']:
    with request(suffix) as response:
        assert response.status == 404
for suffix in ('staff/me','staff/documents','staff/corpus'):
    with request(suffix) as response:
        assert response.status == 401
dataset = json_get('catalog?origin=dataset&limit=200')
other = json_get('catalog?origin=other&limit=200')
assert {r['id'] for r in dataset} == {r['id'] for r in results if r['public']}
assert len(other) == 2 and not ({r['id'] for r in dataset}&{r['id'] for r in other})
report = {'base':BASE,'mocked':False,'files':results,'collections':groups,
          'registered_files':len(results),'published_files':sum(r['public'] for r in results),
          'public_catalogue_total':len(catalogue),'outside_dataset_public':len(other),
          'non_dataset_photo_protected':True,'staff_authentication_required':True}
Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
