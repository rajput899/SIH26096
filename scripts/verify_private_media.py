"""Trusted local operator probe; grants only item-scoped temporary playback access."""
import hashlib,json,sys
from pathlib import Path
from uuid import UUID
from fastapi.testclient import TestClient
from app.config import Settings
from app.db import connect
from app.main import create_app
from app.archive import staff
from app.recordings import playback_cookie
c=Settings();path=Path('/tmp/sih-media-runtime-grants.json')
if '--close' in sys.argv:
 if path.exists():
  with connect(c) as db:
   for row in json.loads(path.read_text()):db.execute('DELETE FROM staff_playback_session WHERE token_hash=%s',(hashlib.sha256(row['cookie'].encode()).hexdigest(),))
  path.unlink()
 print('Temporary playback grants revoked')
else:
 with connect(c) as db:
  db.execute('SET TRANSACTION READ ONLY')
  user=db.execute("SELECT id,login,role FROM staff_user WHERE active AND role='admin' ORDER BY created_at LIMIT 1").fetchone()
  rows=db.execute("SELECT i.id,i.review_status,i.access_level,a.original_filename,a.mime_type,a.byte_size,a.checksum,a.storage_key,a.processing_provenance FROM archival_item i JOIN asset a ON a.item_id=i.id AND a.role='original' WHERE a.mime_type IN ('audio/mpeg','video/mp4') ORDER BY i.id").fetchall()
 app=create_app(c);app.dependency_overrides[staff]=lambda:user;grants=[]
 with TestClient(app) as client:
  for row in rows:
   id_=str(row['id']);base=f'/archive/staff/documents/{id_}'
   with (Path(c.archive_root)/row['storage_key']).open('rb') as f:matched=hashlib.file_digest(f,'sha256').hexdigest()==row['checksum']
   assert matched and row['review_status']!='published'
   assert client.get(f'/archive/documents/{id_}/playback').status_code==404
   assert client.get(f'/archive/documents/{id_}/recording').status_code==404
   grant=client.post(base+'/playback-session');assert grant.status_code==200
   cookie=grant.cookies.get(playback_cookie(row['id']))
   headers={'Cookie':f'{playback_cookie(row["id"])}={cookie}','Range':'bytes=0-31'}
   r=client.get(base+'/playback',headers=headers);assert r.status_code==206 and len(r.content)==32
   grants.append({'id':id_,'cookie_name':playback_cookie(row['id']),'cookie':cookie,'filename':row['original_filename'],'mime':row['mime_type'],'duration':row['processing_provenance']['duration_seconds'],'checksum_matches':matched})
 path.write_text(json.dumps(grants));path.chmod(0o600)
 print('PASS integrity, public exclusion and authorized byte ranges:',len(grants),'media files. Private grants saved; values not logged.')
