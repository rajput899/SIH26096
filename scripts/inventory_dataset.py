"""Read-only inventory; never ingest, publish, modify originals or fetch source URLs."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def inspect(root, output, reuse=None):
    started = time.monotonic()
    rows = []
    previous = {}
    if reuse:
        previous = {r['sha256']: r for r in json.loads(reuse.read_text(encoding='utf-8-sig'))['files']}
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        row = {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
               'sha256': digest(path), 'type': path.suffix.lower(),
               'provenance_status': 'Not verified', 'rights_status': 'Not verified'}
        match = re.fullmatch(r'Volume_(\d+)(?:_(\d+))?', path.stem)
        if match:
            row.update(volume=int(match[1]), part=int(match[2]) if match[2] else None,
                       mapping_basis='filename only; edition/content not authenticated')
        try:
            if path.suffix.lower() == '.pdf':
                cached = previous.get(row['sha256'])
                if cached and 'pages' in cached and 'error' not in cached:
                    for field in ('pages', 'embedded_text_pages', 'sparse_or_no_text_pages',
                                  'embedded_text_characters', 'text_classification'):
                        if field in cached:
                            row[field] = cached[field]
                    row['inspection_basis'] = 'Prior read-only PDF inspection; current SHA-256 matches exactly'
                    rows.append(row)
                    continue
                with pdfium.PdfDocument(path) as pdf:
                    row['pages'] = len(pdf)
                    counts = []
                    for index in range(len(pdf)):
                        page = pdf[index]
                        text = page.get_textpage()
                        try:
                            counts.append(len(text.get_text_range().strip()))
                        finally:
                            text.close()
                            page.close()
                    row.update(embedded_text_pages=sum(n > 30 for n in counts),
                               sparse_or_no_text_pages=[i+1 for i,n in enumerate(counts) if n <= 30],
                               embedded_text_characters=sum(counts))
                    row['text_classification'] = ('embedded text on all pages' if all(n > 30 for n in counts)
                                                  else 'mixed or scanned/sparse pages; visual review required')
            elif path.suffix.lower() in {'.mp3', '.mp4', '.wav'}:
                if not shutil.which('ffprobe'):
                    row['probe_status'] = 'blocked: ffprobe not available in this runtime'
                else:
                    result = subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file',
                        '-show_entries','format=duration,format_name:stream=codec_name,codec_type',
                        '-of','json',str(path)],capture_output=True,timeout=30,check=True)
                    row['media'] = json.loads(result.stdout)
            elif path.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
                with Image.open(path) as image:
                    row['image'] = {'format': image.format, 'width': image.width,
                                    'height': image.height, 'mode': image.mode}
                    image.verify()
                with Image.open(path) as image:
                    image.load()
                row['status'] = 'Readable image; identity, provenance and display rights not verified'
            elif path.suffix.lower() == '.txt':
                row['status'] = 'reference notes, not independent rights evidence'
            else:
                row['status'] = 'unsupported file type; retained and reported'
        except Exception as exc:
            row['error'] = type(exc).__name__
        rows.append(row)
        output.write_text(json.dumps({'files':rows,'complete':False},indent=2),encoding='utf-8')
        print(row['path'], row.get('pages', row.get('probe_status','inspected')), flush=True)
    groups = {}
    for row in rows:
        groups.setdefault(row['sha256'], []).append(row['path'])
    report = {'complete':True, 'files':rows, 'exact_duplicates':[v for v in groups.values() if len(v)>1],
              'elapsed_seconds':round(time.monotonic()-started,2),
              'ingested':0, 'published':0,
              'note':'Text presence is not OCR accuracy or edition authentication. Every file is retained.'}
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--reuse', type=Path, help='Reuse PDF inspection only when a freshly computed hash matches')
    args=parser.parse_args()
    inspect(args.root.resolve(),args.output.resolve(),args.reuse)
