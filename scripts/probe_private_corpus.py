"""Local-only diagnostic on actual unreviewed extracts, isolated from public research."""
import json
import time
from uuid import uuid4

import httpx

from app.config import Settings
from app.db import connect
from app.llm import generate_grounded
from app.research import Answer, validate_answer
from app.research_index import chunks, embeddings, model_identity

config = Settings()
config.ai_provider = 'ollama'
name = 'private_diagnostic_' + uuid4().hex
url = str(config.qdrant_url).rstrip('/') + '/collections/' + name
report = {'public_eligibility': False, 'review_status': 'unreviewed machine text',
          'collection': name, 'samples': [], 'generation': 'not_attempted'}
created = False
try:
    with connect(config) as db:
        samples = []
        for filename in ['Volume_01.pdf', 'Volume_10.pdf', 'Volume_17_02.pdf']:
            row = db.execute("""SELECT f.relative_path,p.page_number,p.result->>'text' AS text
                FROM corpus_page p JOIN corpus_file f USING(checksum)
                WHERE f.relative_path=%s AND p.status='extracted'
                AND length(p.result->>'text')>1200 AND p.result->>'text' ILIKE '%%caste%%'
                ORDER BY p.page_number LIMIT 1""", (filename,)).fetchone()
            if row:
                # Keep the window containing the matching word, with an exact physical page.
                pieces = list(chunks(row['text']))
                text = next((p[2] for p in pieces if 'caste' in p[2].lower()), pieces[0][2])
                samples.append({**row, 'id': uuid4(), 'text': text})
    with httpx.Client(timeout=120, trust_env=False) as client:
        identity = model_identity(client, config)
        vectors = embeddings(client, config, [p['text'] for p in samples])
        response = client.put(url, json={'vectors': {'size': len(vectors[0]), 'distance': 'Cosine'}})
        response.raise_for_status()
        created = True
        client.put(url+'/points?wait=true',json={'points':[
            {'id':str(p['id']),'vector':v,'payload':{'file':p['relative_path'],
             'page':p['page_number'],'model':identity}} for p,v in zip(samples,vectors,strict=True)]}).raise_for_status()
        for p,v in zip(samples,vectors,strict=True):
            response=client.post(url+'/points/query',json={'query':v,'limit':1,'with_payload':True})
            response.raise_for_status()
            match=response.json()['result']['points'][0]
            report['samples'].append({'file':p['relative_path'],'page':p['page_number'],
                'dimensions':len(v),'retrieved_correct_page':match['id']==str(p['id'])})
        p=samples[0]
        started=time.monotonic()
        try:
            raw=generate_grounded(config,[{'passage_id':str(p['id']),'text':p['text']}],
                'State one short point this excerpt makes about caste. Give one paragraph and one exact short quote.',
                [],Answer.model_json_schema())
            answer=validate_answer(raw,[p])
            report['generation']='validated' if answer.paragraphs else 'insufficient_evidence'
            report['answer']=answer.model_dump(mode='json')
        except Exception as exc:
            report['generation']=type(exc).__name__
        report['generation_seconds']=round(time.monotonic()-started,2)
except Exception as exc:
    report['error']=type(exc).__name__
finally:
    if created:
        try:
            response=httpx.delete(url,timeout=10,trust_env=False)
            report['temporary_collection_removed']=response.is_success
        except httpx.HTTPError:
            report['temporary_collection_removed']=False
    print(json.dumps(report,indent=2))
