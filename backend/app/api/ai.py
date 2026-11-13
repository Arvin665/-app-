import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentDevice
from app.schemas.ai import (
    AIExtractResponse,
    CommandRequest,
    CommandResponse,
    FieldParseRequest,
    FieldParseResponse,
    TranscriptionResponse,
)
from app.services.ai_extract import apply_command, extract_response, parse_field_value
from app.services.local_asr import LocalAsrUnavailable, local_asr_status, transcribe_wav
from app.services.media_extract import media_status
from app.services.material_extract import extract_material
from app.services.ocr_extract import ocr_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["智能识别"])


@router.post("/extract", response_model=AIExtractResponse)
async def extract_ai_material(
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
        extraction = await run_in_threadpool(
            extract_material, content, file.filename, file.content_type, module
        )
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
    asr = local_asr_status()
    ocr = ocr_status()
    media = media_status()
    unavailable = []
    if not ocr["available"]:
        unavailable.append("图片/扫描 PDF OCR")
    if not asr["available"]:
        unavailable.append("语音转写")
    if not media["available"]:
        unavailable.append("音视频转码")
    notice = (
        "图片 OCR、扫描 PDF OCR、文字文档提取和音视频语音转写均在服务器本地完成；结果需人工核对。"
        if not unavailable
        else f"当前缺少：{'、'.join(unavailable)}。原件仍会安全保存。"
    )
    return {
        "provider": "local",
        "ocr": ocr,
        "asr": asr,
        "media": media,
        "nlp": {"available": True, "mode": "local-rule"},
        "notice": notice,
    }


@router.get("/asr-status")
def asr_status(device: CurrentDevice):
    return local_asr_status()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(device: CurrentDevice, file: UploadFile = File(...)):
    """接收浏览器录制的 WAV，调用当前服务器的离线中文识别引擎。"""
    content = await file.read(30 * 1024 * 1024 + 1)
    if len(content) > 30 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="录音文件不能超过 30MB")
    if len(content) < 44:
        raise HTTPException(status_code=422, detail="录音内容为空")
    try:
        result = await run_in_threadpool(transcribe_wav, content)
    except LocalAsrUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Local speech recognition failed")
        raise HTTPException(status_code=500, detail="语音识别失败，请重新录制") from exc
    return TranscriptionResponse(**result)
