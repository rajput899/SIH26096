"""Render the read-only JSON inventory as an operator report; never publish source text."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path


def cell(value):
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def render(data):
    files = data["files"]
    pdfs = [f for f in files if f["format"] == ".pdf"]
    pages = [f["corpus"] for f in pdfs if f["corpus"]]
    images = [f for f in files if f.get("private_image_ocr")]
    volumes = [m for f in pdfs if (m := re.fullmatch(r"Volume_(\d+)(?:_(\d+))?\.pdf", f["path"]))]
    candidate_numbers = sorted({int(m[1]) for m in volumes})
    def total(key):
        return sum(p[key] for p in pages)
    lines = [
        "# SIH26096 content inventory",
        "",
        "Operator-only audit of local files and database state. No source text is reproduced.",
        f"Snapshot started (UTC): {data.get('observed_at', 'see inventory file timestamp')}.",
        "Filename themes and volume numbers are candidates, not verified archival identities.",
        "",
        f"- Dataset files: {len(files)}; registered: {data['summary']['dataset_ingested_files']}.",
        f"- Root volume/part PDFs: {len(volumes)}; candidate volume numbers: "
        f"{', '.join(map(str, candidate_numbers))}. This does not establish edition completeness.",
        f"- Registered record types: {dict(Counter(r['material_type'] for r in data['records']))}.",
        f"- Record review states: {dict(Counter(r['review_status'] for r in data['records']))}.",
        "- Current text states: "
        f"{dict(Counter(r['text_status'] or 'missing' for r in data['records']))}.",
        "- Letters are not a separate registered type. The 25 letters-folder images are "
        "unverified candidates, not 25 authenticated letters; no manuscript/speech classification "
        "has been established for them.",
        f"- Physical PDF pages: {data['summary']['physical_pdf_pages']}; "
        "includes a held overlapping compilation, not unique historical pages.",
        f"- Extracted: {total('extracted')}; OCR-processed: {total('ocr_processed')}; "
        f"OCR pending: {total('ocr_pending')}; failed: {total('failed')}.",
        f"- Empty extraction: {total('empty')}; low OCR confidence (<0.8): "
        f"{total('low_confidence')}. These are review flags, not verified blank pages.",
        f"- Private image derivatives: {len(images)}; with extracted text: "
        f"{sum(f['private_image_ocr']['has_text'] for f in images)}. All require review.",
        f"- Public records: {data['summary']['public_records']}; public recordings: "
        f"{data['summary']['public_recordings']}. Public catalogue matches publication SQL: "
        f"{data['summary']['public_catalog_matches_database']}.",
        "",
        "## PDF coverage",
        "",
        "All dataset PDFs require source/rights and text review before publication or public RAG.",
        "The compilation is **awaiting curator identity and scope verification**. "
        "Do not OCR, import, index, publish or modify it.",
        "Release requires reliable source/edition documentation, a curator assessment of its "
        "relationship to the separate volumes, and an explicit intended-scope decision. "
        "Filename and apparent overlap are not proof of identity. The database checkpoint "
        "state is retained unchanged; the hold below is an operator restriction.",
        "Physical page numbers are preserved; printed-page/section mappings are not inferred.",
        "",
        "| File | Pages | Extracted | OCR processed | Pending | Failed | Empty | "
        "Low confidence | State |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for f in pdfs:
        p = f["corpus"] or {}
        values = [f["path"], f["physical_pages"]] + [p.get(k) for k in
                  ["extracted", "ocr_processed", "ocr_pending", "failed", "empty",
                   "low_confidence"]] + [f.get("operator_hold", {}).get("status", p.get("state"))]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    lines += ["", "## Every dataset file", "",
              "Hashes, byte sizes, record IDs, provenance, rights statements and page-level "
              "quality flags are retained in the adjacent content-inventory.json.", "",
              "| File | Format | Ingestion / extraction | Review / access | Public | "
              "Indexed passages |",
              "|---|---|---|---|---|---:|"]
    for f in files:
        r, c = f["record"], f["corpus"]
        stage = f.get("operator_hold", {}).get("status", c["state"] if c else "not ingested")
        if f.get("private_image_ocr"):
            stage += "; private OCR derivative (unverified)"
        review = (f"{r['review_status']} / {r['access_level']}; "
                  f"text: {r['text_status'] or 'missing'}; "
                  f"provenance: {r['provenance_status']}" if r else "not reviewed")
        values = [f["path"], f["format"], stage, review, f["public"],
                  r["embeddings"] if r else 0]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    lines += ["", "## Registered records, including non-dataset sources", "",
              "| Title | Registered type | Review | Access | Text | Provenance | Embeddings |",
              "|---|---|---|---|---|---|---:|"]
    for r in data["records"]:
        lines.append("| " + " | ".join(cell(r[k]) for k in ["title", "material_type",
                     "review_status", "access_level", "text_status", "provenance_status",
                     "embeddings"]) + " |")
    lines += ["", "## Why material is absent from public pages", "",
              "- The only published sources are two modern PIB excerpts, not original manuscripts.",
              "- Dataset PDFs and recordings are registered but lack publication eligibility.",
              "- The 61 image candidates have private OCR derivatives but are not registered "
              "items; "
              "classification, provenance and rights require curator decisions.",
              "- The existing photograph titled Letters remains unpublished; its earlier rights "
              "label is not independent permission evidence.",
              "- No approved eligible source is missing from the catalogue. Two passages are "
              "indexed; new machine text cannot be added to public RAG before review.",
              "- Experience contains five published activities on Life and Constitution. "
              "Other topic names would not establish available reviewed content.",
              "- Historical recording transcripts, timing alignment and automatic ASR remain "
              "unavailable. Synthetic playback tests are not historical-media acceptance.",
              "- BHASHINI has no configured credentials or working adapter. The unavailable "
              "message is retained; no translation or voice API result is claimed.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(render(json.loads(args.inventory.read_text(encoding="utf-8-sig"))),
                           encoding="utf-8")
