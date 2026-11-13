from __future__ import annotations

import threading
from io import BytesIO
from typing import Iterable

from PIL import Image

from app.core.config import settings

_engine = None
_engine_lock = threading.Lock()
_engine_error: str | None = None


def _load_engine():
    global _engine, _engine_error
    if _engine is not None:
        return _engine
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        _engine_error = "rapidocr-onnxruntime 未安装"
        raise RuntimeError(_engine_error) from exc
    with _engine_lock:
        if _engine is None:
            _engine = RapidOCR()
    return _engine


def ocr_status() -> dict:
    try:
        _load_engine()
        available = True
        error = None
    except Exception as exc:
        available = False
        error = str(exc)[:180]
    pdf_render_available = True
    try:
        import fitz  # noqa: F401
    except ImportError:
        pdf_render_available = False
    return {
        "available": bool(settings.ocr_enabled and available and pdf_render_available),
        "provider": "rapidocr-onnxruntime",
        "mode": "local-offline",
        "languages": ["zh-CN", "en"],
        "engine": available,
        "pdf_renderer": pdf_render_available,
        "error": error,
    }


def _ocr_image(image: Image.Image) -> tuple[str, float]:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("图片 OCR 缺少 numpy 依赖") from exc
    engine = _load_engine()
    rgb = image.convert("RGB")
    array = np.asarray(rgb)[:, :, ::-1].copy()
    with _engine_lock:
        result, _ = engine(array)
    if not result:
        return "", 0.0
    lines: list[str] = []
    scores: list[float] = []
    for item in result:
        if len(item) < 3:
            continue
        text = str(item[1] or "").strip()
        if not text:
            continue
        lines.append(text)
        try:
            scores.append(float(item[2]))
        except (TypeError, ValueError):
            pass
    confidence = round(sum(scores) / len(scores), 4) if scores else 0.0
    return "\n".join(lines), confidence


def ocr_image(content: bytes) -> dict:
    with Image.open(BytesIO(content)) as image:
        image.load()
        text, confidence = _ocr_image(image)
        width, height = image.size
        image_format = image.format or ""
    return {
        "text": text[:500_000],
        "confidence": confidence,
        "width": width,
        "height": height,
        "format": image_format,
    }


def ocr_pdf_pages(content: bytes, page_indexes: Iterable[int]) -> dict:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("扫描 PDF OCR 需要安装 PyMuPDF") from exc

    indexes = sorted(set(page_indexes))
    if not indexes:
        return {"text": "", "confidence": 0.0, "pages": [], "processed": 0}
    document = fitz.open(stream=content, filetype="pdf")
    chunks: list[str] = []
    scores: list[float] = []
    processed_pages: list[int] = []
    try:
        for index in indexes:
            if index < 0 or index >= len(document):
                continue
            page = document.load_page(index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), colorspace=fitz.csRGB, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            text, confidence = _ocr_image(image)
            if text.strip():
                chunks.append(f"[第 {index + 1} 页]\n{text}")
                if confidence:
                    scores.append(confidence)
            processed_pages.append(index + 1)
    finally:
        document.close()
    return {
        "text": "\n\n".join(chunks)[:500_000],
        "confidence": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "pages": processed_pages,
        "processed": len(processed_pages),
    }
