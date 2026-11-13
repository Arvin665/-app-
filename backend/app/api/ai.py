from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.deps import CurrentDevice
from app.schemas.ai import (
    AIExtractResponse,
    CommandRequest,
    CommandResponse,
    FieldParseRequest,
    FieldParseResponse,
)
from app.services.ai_extract import apply_command, extract_response, parse_field_value
from app.services.material_extract import extract_material

router = APIRouter(prefix="/ai", tags=["智能识别"])


@router.post("/extract", response_model=AIExtractResponse)
async def extract_material(
    device: CurrentDevice,
    module: str = Form(...),
    text: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
):
    """统一 OCR/ASR/NLP 入口；mock 模式不会伪造图片或音频中的文字。"""
    if module not in {"sale", "lease", "work", "inspiration"}:
        raise HTTPException(status_code=422, detail="module 参数不正确")
    if not text and file is None:
        raise HTTPException(status_code=422, detail="请至少提交文本或文件")

    provider_note = ""
    if file is not None and file.filename:
        content = await file.read()
        extraction = extract_material(content, file.filename, file.content_type, module)
        provider_note = f"文件 {file.filename}：{extraction['note']}"
        if extraction["text"]:
            text = f"{text or ''}\n{extraction['text']}".strip()

    response = extract_response(text or "", module, provider_note)
    return AIExtractResponse(**response)


@router.post("/apply-command", response_model=CommandResponse)
def apply_natural_language_command(body: CommandRequest, device: CurrentDevice):
    """修改卡片字段时使用同一接口，避免前端各自维护字段同义词。"""
    try:
        result = apply_command(body.module, body.current_fields, body.command.strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CommandResponse(**result)


@router.post("/parse-field", response_model=FieldParseResponse)
def parse_single_field(body: FieldParseRequest, device: CurrentDevice):
    """字段内麦克风使用：语音只说值，由后端按字段类型结构化。"""
    try:
        result = parse_field_value(body.module, body.field, body.text.strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FieldParseResponse(**result)


@router.get("/capabilities")
def ai_capabilities(device: CurrentDevice):
    """向两端暴露当前识别能力和替换边界，便于设置页显示真实状态。"""
    return {
        "provider": "mock",
        "ocr": {"available": False, "mode": "reserved"},
        "asr": {"available": False, "mode": "reserved"},
        "nlp": {"available": True, "mode": "local-rule"},
        "notice": "第三方能力未配置；文本结构化使用本地规则模拟，结果需人工核对。",
    }
