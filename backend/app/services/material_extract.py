from __future__ import annotations

import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from openpyxl import load_workbook
from PIL import Image

TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".log",
    ".html",
    ".htm",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ARCHIVE_SUFFIXES = {".zip", ".rar", ".7z", ".tar", ".gz"}
MAX_EXTRACTED_TEXT = 500_000


def classify_material(file_name: str, content_type: str | None) -> str:
    suffix = Path(file_name).suffix.lower()
    mime = (content_type or "").lower()
    if suffix in IMAGE_SUFFIXES or mime.startswith("image/"):
        return "image"
    if suffix == ".pdf" or mime == "application/pdf":
        return "pdf"
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return "excel"
    if suffix == ".csv":
        return "csv"
    if suffix in {".doc", ".docx"}:
        return "word"
    if suffix in {".ppt", ".pptx"}:
        return "presentation"
    if suffix in TEXT_SUFFIXES or mime.startswith("text/"):
        return "text"
    if suffix in AUDIO_SUFFIXES or mime.startswith("audio/"):
        return "audio"
    if suffix in VIDEO_SUFFIXES or mime.startswith("video/"):
        return "video"
    if suffix in ARCHIVE_SUFFIXES:
        return "archive"
    return "other"


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            decoded = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" not in decoded:
            return decoded
    # 未识别编码的文本仍可用于检索，但不能把二进制误判为有效正文。
    return content.decode("utf-8", errors="ignore")


def _looks_textual(content: bytes) -> bool:
    if not content:
        return False
    sample = content[:8192]
    if b"\x00" in sample:
        return False
    printable = sum(byte in b"\n\r\t" or 32 <= byte <= 126 or byte >= 128 for byte in sample)
    return printable / len(sample) >= 0.82


def _extract_xlsx(content: bytes) -> tuple[str, dict[str, Any]]:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    chunks: list[str] = []
    row_count = 0
    sheet_names: list[str] = []
    try:
        for sheet in workbook.worksheets:
            sheet_names.append(sheet.title)
            chunks.append(f"## {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                if not values:
                    continue
                chunks.append("\t".join(values))
                row_count += 1
                if row_count >= 5000:
                    chunks.append("[内容过长，已截取前 5000 行]")
                    return "\n".join(chunks), {"sheets": sheet_names, "rows": row_count, "truncated": True}
    finally:
        workbook.close()
    return "\n".join(chunks), {"sheets": sheet_names, "rows": row_count, "truncated": False}


def _xml_texts(content: bytes, member_pattern: re.Pattern[str], text_tag: str) -> tuple[str, int]:
    if not zipfile.is_zipfile(BytesIO(content)):
        raise ValueError("文件不是有效的 Office Open XML 压缩包")
    chunks: list[str] = []
    member_count = 0
    with zipfile.ZipFile(BytesIO(content)) as package:
        members = sorted(
            (name for name in package.namelist() if member_pattern.match(name)),
            key=lambda value: [int(part) for part in re.findall(r"\d+", value)],
        )
        for name in members[:200]:
            member_count += 1
            root = ElementTree.fromstring(package.read(name))
            texts = [node.text for node in root.iter() if node.tag.endswith(text_tag) and node.text]
            if texts:
                chunks.append(" ".join(texts))
    return "\n".join(chunks), member_count


def _extract_docx(content: bytes) -> tuple[str, dict[str, Any]]:
    if not zipfile.is_zipfile(BytesIO(content)):
        raise ValueError("文件不是有效的 DOCX 压缩包")
    with zipfile.ZipFile(BytesIO(content)) as package:
        root = ElementTree.fromstring(package.read("word/document.xml"))
    paragraphs: list[str] = []
    for paragraph in root.iter():
        if not paragraph.tag.endswith("}p"):
            continue
        text = "".join(node.text or "" for node in paragraph.iter() if node.tag.endswith("}t"))
        if text.strip():
            paragraphs.append(text.strip())
    return "\n".join(paragraphs), {"paragraphs": len(paragraphs)}


def _extract_pptx(content: bytes) -> tuple[str, dict[str, Any]]:
    pattern = re.compile(r"ppt/slides/slide\d+\.xml$")
    text, slide_count = _xml_texts(content, pattern, "}t")
    return text, {"slides": slide_count}


def _extract_pdf(content: bytes) -> tuple[str, dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF 解析依赖 pypdf 尚未安装") from exc
    reader = PdfReader(BytesIO(content))
    if reader.is_encrypted:
        raise ValueError("PDF 已加密，无法直接提取正文")
    pages: list[str] = []
    page_total = len(reader.pages)
    for page in list(reader.pages)[:100]:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages), {"pages": page_total, "extracted_pages": min(page_total, 100)}


def _extract_image(content: bytes) -> tuple[str, dict[str, Any]]:
    with Image.open(BytesIO(content)) as image:
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format or "",
        }
    return "", metadata


def derive_title(file_name: str, text: str) -> str:
    stem = Path(file_name).stem.strip()
    if stem:
        return stem[:255]
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:255] or "未命名资料"


def extract_material(content: bytes, file_name: str, content_type: str | None, module: str) -> dict[str, Any]:
    """提取可验证的正文，返回状态、结构和限制说明。

    OCR、ASR 和旧版二进制 Office 文档不会在这里伪造识别结果。
    """
    file_type = classify_material(file_name, content_type)
    suffix = Path(file_name).suffix.lower()
    metadata: dict[str, Any] = {"suffix": suffix, "content_type": content_type or ""}
    text = ""
    status = "stored"
    note = "文件已安全保存。"

    try:
        if suffix in TEXT_SUFFIXES or (file_type == "other" and _looks_textual(content)):
            text = _decode_text(content)
            status = "extracted" if text.strip() else "stored"
            note = "已提取文本正文。" if text.strip() else "文本文件为空。"
        elif suffix in {".xlsx", ".xlsm"}:
            text, sheet_metadata = _extract_xlsx(content)
            metadata.update(sheet_metadata)
            status = "extracted" if text.strip() else "stored"
            note = "已提取表格单元格内容。"
        elif suffix == ".docx":
            text, document_metadata = _extract_docx(content)
            metadata.update(document_metadata)
            status = "extracted" if text.strip() else "stored"
            note = "已提取 Word 文档正文。"
        elif suffix == ".pptx":
            text, presentation_metadata = _extract_pptx(content)
            metadata.update(presentation_metadata)
            status = "extracted" if text.strip() else "stored"
            note = "已提取演示文稿文字。"
        elif suffix == ".pdf":
            text, pdf_metadata = _extract_pdf(content)
            metadata.update(pdf_metadata)
            status = "extracted" if text.strip() else "unavailable"
            note = "已提取 PDF 文本层。" if text.strip() else "PDF 没有可提取文本层，可能是扫描件，需配置 OCR。"
        elif file_type == "image":
            _, image_metadata = _extract_image(content)
            metadata.update(image_metadata)
            status = "unavailable"
            note = "图片原件已保存；当前未配置 OCR，无法读取图片中的文字。"
        elif file_type == "audio":
            status = "unavailable"
            note = "音频原件已保存；当前未配置 ASR，无法转写语音内容。"
        elif file_type == "video":
            status = "unavailable"
            note = "视频原件已保存；当前未配置视频转写，无法生成文字。"
        elif suffix in {".xls", ".doc", ".ppt"}:
            status = "unavailable"
            note = "旧版二进制 Office 文件已保存；请另存为 xlsx/docx/pptx 后可自动提取。"
        elif file_type == "archive":
            status = "stored"
            note = "压缩包已保存；为避免安全风险不会自动解压。"
        else:
            status = "stored"
            note = "文件已按原格式保存；当前没有适配该格式的正文解析器。"
    except Exception as exc:
        status = "failed"
        note = f"原件已保存，但自动提取失败：{str(exc)[:160]}"

    text = text[:MAX_EXTRACTED_TEXT]
    structured: dict[str, Any] = {"fields": {}, "confidence": {}}
    if text.strip():
        try:
            from app.services.ai_extract import extract_text

            structured = extract_text(text[:50_000], module)
        except Exception:
            # 文档正文仍可检索；单模块规则失败不应导致上传失败。
            structured = {"fields": {}, "confidence": {}}

    metadata["text_length"] = len(text)
    metadata["extraction_status"] = status
    return {
        "file_type": file_type,
        "title": derive_title(file_name, text),
        "status": status,
        "text": text,
        "structured": structured,
        "metadata": metadata,
        "note": note,
    }


def json_dump(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
