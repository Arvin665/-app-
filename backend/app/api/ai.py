from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.deps import CurrentDevice
from app.schemas.ai import AIExtractResponse, CommandRequest, CommandResponse
from app.services.ai_extract import apply_command, extract_response

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
        suffix = Path(file.filename).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            provider_note = f"已接收图片 {file.filename}；mock OCR 不生成文字，需同时填写文本或切换真实 OCR 服务。"
        elif suffix in {".mp3", ".wav", ".m4a", ".aac", ".ogg"}:
            provider_note = f"已接收音频 {file.filename}；mock ASR 不生成转写，需同时填写文本或切换真实 ASR 服务。"
        else:
            provider_note = f"已接收文件 {file.filename}；当前 mock 接口仅解析文本。"

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
