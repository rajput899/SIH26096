"""Read-only Docker probes. Input is mounted read-only; outputs are local review derivatives."""
import hashlib,json,subprocess,time
from pathlib import Path
from PIL import Image
from app.extraction import recognized
root=Path('/dataset'); output=Path('/review'); rows=[]
for p in sorted(root.rglob('*')):
 if p.suffix.lower() not in {'.mp4','.mp3'}: continue
 try:
  r=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file','-show_entries','format=duration,format_name:stream=codec_name,codec_type','-of','json',str(p)],capture_output=True,timeout=30,check=True)
  rows.append({'path':p.relative_to(root).as_posix(),'probe':json.loads(r.stdout),'identity':'Not verified','rights':'Not verified'})
 except Exception as e: rows.append({'path':p.relative_to(root).as_posix(),'error':type(e).__name__})
(output/'dataset-media-probe.json').write_text(json.dumps(rows,indent=2))
p=output/'dataset-sample/page-1.png'; started=time.monotonic()
import numpy as np
result=recognized(np.array(Image.open(p).convert('RGB')),1)
result.update(elapsed_seconds=round(time.monotonic()-started,2),status='Machine OCR only; not curator verified',original_modified=False)
(output/'dataset-sample/page-1-ocr.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'media_probed':len(rows),'media_errors':sum('error' in r for r in rows),'ocr_characters':len(result['text']),'ocr_confidence':result['confidence'],'ocr_seconds':result['elapsed_seconds']}))
