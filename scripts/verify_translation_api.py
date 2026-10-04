"""Explicit live localhost check: only existing public verified PIB text is translated."""
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'http://localhost:3000/api/archive/'


def call(path, data=None):
    request = urllib.request.Request(BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, None


code, status = call('translation/status')
assert code == 200 and status['configured']
item = '8ce2df4c-c4e2-4ed1-bf9e-244881273e82'
code, detail = call(f'catalog/{item}')
assert code == 200
page = detail['pages'][0]
revision = detail['text_revision']
body = {'revision':revision,'sequence':page['sequence'],'target_language':'hi'}
code, result = call(f'documents/{item}/translation', body)
assert code == 200 and result['provider'] == 'bhashini'
assert result['machine_generated'] and result['review_status'] == 'unreviewed'
assert result['source']['text_sha256'] == hashlib.sha256(page['text'].encode()).hexdigest()
code, _ = call(f'documents/{item}/translation', {**body,'revision':revision+1})
assert code == 409
_, rows = call('catalog?origin=dataset&limit=200')
denials = []
for restricted in [rows[0]['id'], '509f9e25-2112-4737-887b-f5ce3202f17e']:
    code, _ = call(f'documents/{restricted}/translation', body)
    assert code == 404
    denials.append({'id':restricted,'status':code})
Path('outputs/bhashini-live-api.json').write_text(json.dumps({
    'base':BASE,'mocked':False,'success':True,'provider':result['provider'],
    'service_id':result['service_id'],'source':result['source'],
    'machine_generated':True,'review_status':'unreviewed',
    'translation':result['translation'],'stale_revision_status':409,
    'ineligible_denials':denials,'linguistic_accuracy_reviewed':False},indent=2),encoding='utf-8')
print('PASS: live public verified-text translation, exact source hash, stale revision and ineligible denials.')
