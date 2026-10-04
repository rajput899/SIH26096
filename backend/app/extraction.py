"""Local-only page extraction. This module never writes the original or fetches URLs."""

import hashlib
import json
import sys
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

MAX_PAGES = 50
MAX_PIXELS = 20_000_000


@lru_cache(maxsize=1)
def ocr_engine():
    import rapidocr
    from rapidocr import RapidOCR

    # Explicit bundled paths prohibit fallback model downloads during processing.
    root = Path(rapidocr.__file__).parent / "models"
    models = {
        "Det": "PP-OCRv6_det_small.onnx",
        "Rec": "PP-OCRv6_rec_small.onnx",
        "Cls": "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    }
    if not all((root / name).is_file() for name in models.values()):
        raise RuntimeError("Pinned OCR model files are missing")
    return RapidOCR(
        params={
            **{f"{kind}.model_path": str(root / name) for kind, name in models.items()},
            "EngineConfig.onnxruntime.intra_op_num_threads": 2,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        }
    )


def recognized(image, page_number):
    result = ocr_engine()(image)
    texts = list(result.txts) if result.txts is not None else []
    scores = list(result.scores) if result.scores is not None else []
    confidence = float(min(scores)) if scores else None
    text = "\n".join(texts)
    warning = "OCR output requires comparison with the original"
    if not text.strip():
        warning = (
            "No text recognized; blank, illegible or unsupported page. Manual review required."
        )
    elif confidence is not None and confidence < 0.8:
        warning = "Low-confidence OCR; manual correction required"
    return {
        "sequence": page_number,
        "page_number": page_number,
        "text": text,
        "extraction_method": "rapidocr",
        "confidence": confidence,
        "warning": warning,
    }


def extract(path: Path, mime: str, checksum: str, mode: str = "auto"):
    if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
        raise ValueError("Original checksum mismatch")
    pages = []
    if mime == "application/pdf":
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(path) as document:
            if not 0 < len(document) <= MAX_PAGES:
                raise ValueError("PDF must contain 1 to 50 pages")
            for index in range(len(document)):
                page = document[index]
                try:
                    textpage = page.get_textpage()
                    try:
                        text = textpage.get_text_range().strip() if mode == "auto" else ""
                    finally:
                        textpage.close()
                    if text:
                        pages.append(
                            {
                                "sequence": index + 1,
                                "page_number": index + 1,
                                "text": text,
                                "extraction_method": "pdf_text",
                                "warning": "Embedded PDF text requires source comparison",
                            }
                        )
                    else:
                        width, height = page.get_size()
                        if width * height * 4 > MAX_PIXELS:
                            raise ValueError("Rendered PDF page exceeds pixel limit")
                        bitmap = page.render(scale=2)
                        try:
                            pages.append(recognized(bitmap.to_pil().convert("RGB"), index + 1))
                        finally:
                            bitmap.close()
                finally:
                    page.close()
    elif mime in {"image/png", "image/jpeg"}:
        from PIL import Image

        with Image.open(path) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("Image exceeds pixel limit")
            pages = [recognized(image.convert("RGB"), 1)]
    elif mime == "text/plain" and mode == "auto":
        pages = [
            {
                "sequence": 1,
                "page_number": None,
                "text": path.read_text(encoding="utf-8"),
                "extraction_method": "plain_text",
                "warning": "Unpaginated original; document locator only, not a physical page",
            }
        ]
    else:
        raise ValueError("Unsupported original format or mode")
    if any(len(p["text"]) > 100000 or "\x00" in p["text"] for p in pages):
        raise ValueError("Extracted text exceeds limits or contains NUL characters")
    if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
        raise ValueError("Original changed during processing")
    provenance = {
        "mode": mode,
        "original_sha256": checksum,
        "render_scale": 2,
        "rapidocr_version": version("rapidocr"),
        "onnxruntime_version": version("onnxruntime"),
        "pypdfium2_version": version("pypdfium2"),
    }
    # Fingerprint the installed model bytes, not only the Python package version.
    if any(p["extraction_method"] == "rapidocr" for p in pages):
        import rapidocr

        model_root = Path(rapidocr.__file__).parent / "models"
        provenance["model_sha256"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in model_root.glob("*.onnx")
        }
    return {"pages": pages, "provenance": provenance}


if __name__ == "__main__":
    parameters = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = extract(
        Path(parameters["path"]), parameters["mime"], parameters["checksum"], parameters["mode"]
    )
    Path(sys.argv[2]).write_text(json.dumps(result), encoding="utf-8")
