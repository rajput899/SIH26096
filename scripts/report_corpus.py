"""Read-only operator report; never expose credentials or alter review states."""
import json
from app.config import Settings
from app.db import connect

with connect(Settings()) as db:
    rows=db.execute("""SELECT f.relative_path,f.checksum,f.page_count,f.state,f.metadata,
      i.id,i.review_status,i.access_level,i.current_text_revision,
      count(p.page_number) AS checkpointed_pages,
      count(*) FILTER(WHERE p.status='extracted') AS extracted_pages,
      count(*) FILTER(WHERE p.status='ocr_pending') AS ocr_pending,
      count(*) FILTER(WHERE p.status='failed') AS failed_pages,
      count(*) FILTER(WHERE p.status='extracted' AND p.result->>'extraction_method'='rapidocr') AS ocr_pages,
      count(*) FILTER(WHERE p.status='extracted' AND length(trim(p.result->>'text'))=0) AS empty_pages
      FROM corpus_file f LEFT JOIN corpus_page p USING(checksum)
      LEFT JOIN archival_item i ON i.id=f.item_id
      GROUP BY f.checksum,i.id ORDER BY f.relative_path""").fetchall()
    totals=db.execute("""SELECT
      (SELECT count(*) FROM archival_item) AS items,
      (SELECT count(*) FROM archival_item WHERE review_status='published') AS published,
      (SELECT count(*) FROM passage) AS passages,
      (SELECT count(*) FROM passage_embedding) AS embedded_passages,
      (SELECT count(*) FROM text_segment) AS revision_segments""").fetchone()
    letters=db.execute("SELECT review_status,access_level FROM archival_item WHERE title='Letters'").fetchall()
    print(json.dumps({'totals':totals,'letters':letters,'files':rows},indent=2,default=str))
