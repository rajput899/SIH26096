"""Resumable local image OCR using existing extraction; never writes to the database."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.extraction import extract  # noqa: E402

out = ROOT / "outputs/dataset-image-review"
out.mkdir(exist_ok=True)
summary = []
for path in sorted((ROOT / "Dataset").rglob("*")):
    if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        continue
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    target = out / f"{checksum}.json"
    row = dict(path=path.relative_to(ROOT / "Dataset").as_posix(), sha256=checksum,
               rights="unverified", review="unverified", published=False)
    try:
        if target.exists():
            prior = json.loads(target.read_text(encoding="utf-8"))
            assert prior["sha256"] == checksum and "extraction" in prior
            row["status"] = "reused matching local extraction"
        else:
            data = extract(path, "image/png" if path.suffix.lower() == ".png" else "image/jpeg", checksum)
            target.write_text(json.dumps({**row, "extraction": data}, ensure_ascii=False, indent=2), encoding="utf-8")
            row["status"] = "extracted for local review only"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum
    except Exception as exc:
        row["status"] = "blocked"
        row["error_type"] = type(exc).__name__
    summary.append(row)
    (out / "inventory.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(row["path"], row["status"], flush=True)
print("Completed", len(summary), "images; database unchanged", flush=True)
