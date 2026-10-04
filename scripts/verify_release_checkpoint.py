"""Read-only checkpoint reconciliation; never applies migrations or releases."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from app.config import Settings
from app.dataset_release import manifest_hash
from app.db import connect

config = Settings()
manifest = json.loads(Path('/audit/dataset-release-manifest.json').read_text())
with connect(config) as db:
    db.execute('SET TRANSACTION READ ONLY')
    migrations = db.execute('SELECT version FROM schema_migration ORDER BY version').fetchall()
    release = db.execute('SELECT id,manifest_sha256 FROM dataset_release WHERE id=%s',
                         (manifest['id'],)).fetchone()
    assert release['manifest_sha256'] == manifest_hash(manifest)
    rows = db.execute('''SELECT m.relative_path,m.collection,m.exclusion,m.checksum,
        m.byte_size,i.id,i.review_status,i.access_level,i.material_type,i.dataset_release_id,
        i.rights_statement,i.current_text_revision,r.status AS text_status,
        s.verification_status AS provenance_status,a.original_filename,a.storage_key,
        a.checksum AS original_checksum,a.byte_size AS original_size,f.state AS ingestion_status,
        f.page_count,(SELECT count(*) FROM corpus_page p WHERE p.checksum=m.checksum)
        AS processing_checkpoints,
        (SELECT count(*) FROM recording_revision rr WHERE rr.item_id=i.id) AS transcript_revisions
        FROM dataset_member m JOIN archival_item i ON i.id=m.item_id
        JOIN source s ON s.id=i.source_id JOIN asset a ON a.item_id=i.id AND a.role='original'
        LEFT JOIN text_revision r ON r.item_id=i.id AND r.revision=i.current_text_revision
        LEFT JOIN corpus_file f ON f.item_id=i.id WHERE m.release_id=%s ORDER BY m.relative_path''',
        (manifest['id'],)).fetchall()
    counts = db.execute('SELECT review_status,access_level,count(*) AS count '
                        'FROM archival_item GROUP BY review_status,access_level').fetchall()
assert '010_dataset_release.sql' in [r['version'] for r in migrations]
assert len(rows) == len(manifest['files']) == 92
by_path = {r['relative_path']:r for r in rows}
assert {p.relative_to(Path('/dataset')).as_posix() for p in Path('/dataset').rglob('*')
        if p.is_file()} == set(by_path)
for entry in manifest['files']:
    row = by_path[entry['path']]
    assert row['checksum'] == row['original_checksum'] == entry['sha256']
    assert row['byte_size'] == row['original_size'] == entry['bytes']
    for path in [Path('/dataset') / entry['path'],
                 Path(config.archive_root) / row['storage_key']]:
        with path.open('rb') as source:
            assert hashlib.file_digest(source, 'sha256').hexdigest() == entry['sha256']
    if row['exclusion']:
        assert row['review_status'] != 'published' and row['access_level'] == 'staff'
    else:
        assert row['review_status'] == 'published' and row['access_level'] == 'public'
        assert row['dataset_release_id'] == manifest['id']
    del row['storage_key']
print(json.dumps({'read_only':True,'migrations':migrations,'release':release,
    'total_registered_dataset':len(rows),'public_dataset':sum(not r['exclusion'] for r in rows),
    'database_counts':counts,'both_supplied_and_stored_hashes_verified':True,
    'text_statuses':dict(Counter(r['text_status'] or 'none' for r in rows)),
    'files':rows},indent=2,default=str))
