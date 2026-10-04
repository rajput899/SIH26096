"""Live retrieval and citation integrity, without calling any generation provider."""
import json

from app.config import Settings
from app.db import connect
from app.research import Question, citation, retrieve
from app.research_index import ELIGIBLE

config = Settings()
with connect(config) as db:
    db.execute('SET TRANSACTION READ ONLY')
    eligible = db.execute('SELECT i.id FROM archival_item i JOIN text_revision r '
                          'ON r.item_id=i.id AND r.revision=i.current_text_revision WHERE '
                          + ELIGIBLE).fetchall()
    dataset = db.execute('SELECT i.id,i.current_text_revision,r.status AS text_status '
                         'FROM archival_item i LEFT JOIN text_revision r ON r.item_id=i.id '
                         'AND r.revision=i.current_text_revision '
                         'WHERE i.dataset_release_id IS NOT NULL').fetchall()
    assert len(dataset) == 91
    assert not {r['id'] for r in eligible} & {r['id'] for r in dataset}
rows, warning = retrieve(config, Question(question='Ambedkar Chairman Drafting Committee'))
assert rows, 'Existing approved sources must still be retrievable'
citations = []
with connect(config) as db:
    db.execute('SET TRANSACTION READ ONLY')
    for row in rows:
        assert row['item_id'] in {r['id'] for r in eligible}
        segment = db.execute('SELECT text FROM text_segment WHERE id=%s',
                             (row['segment_id'],)).fetchone()
        assert segment['text'][row['char_start']:row['char_end']] == row['text']
        source = citation(row)
        citations.append({k:v for k,v in source.items() if k!='excerpt'})
    # Same scoped retrieval path used by public RAG must reject newly displayed unreviewed text.
    candidate = next(r for r in dataset if r['current_text_revision'] is not None)
scoped, _ = retrieve(config, Question(question='Ambedkar',item_id=candidate['id']))
assert scoped == []
print(json.dumps({'generation_called':False,'live_retrieval':True,'warning':warning,
                  'eligible_items':[str(r['id']) for r in eligible],
                  'dataset_originals_public_but_text_unreviewed':len(dataset),
                  'scoped_unreviewed_retrieval_empty':True,'exact_segment_offsets_verified':True,
                  'citations':citations},indent=2,default=str))
