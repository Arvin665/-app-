from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.material_extract import extract_material  # noqa: E402
from app.services.media_extract import ffmpeg_path  # noqa: E402

EXPECTED_TEXT = "上海写字楼买卖信息"


def find_chinese_font() -> Path:
    candidates = [
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("未找到可用于生成中文验收图片的字体")


def create_scan_fixtures(directory: Path) -> tuple[Path, Path]:
    font = ImageFont.truetype(str(find_chinese_font()), 74)
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    draw.text((110, 260), "上海写字楼", font=font, fill="#17221f")
    draw.text((110, 380), "买卖信息", font=font, fill="#17221f")
    draw.text((110, 720), "项目名称：静安中心", font=font, fill="#17221f")
    draw.text((110, 840), "客户预算：每平方米 6 万元", font=font, fill="#17221f")

    image_path = directory / "ocr-fixture.png"
    pdf_path = directory / "scan-fixture.pdf"
    image.save(image_path, format="PNG")
    image.save(pdf_path, "PDF", resolution=150.0)
    return image_path, pdf_path


def create_video_fixture(directory: Path, speech_wav: Path) -> Path:
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise RuntimeError("未找到 ffmpeg，无法生成音频和视频验收素材")
    with wave.open(str(speech_wav), "rb") as audio:
        duration = max(1.0, audio.getnframes() / audio.getframerate())
    video_path = directory / "speech-fixture.mp4"
    command = [
        str(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x17221f:s=640x360:r=25:d={duration:.3f}",
        "-i",
        str(speech_wav),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(video_path),
    ]
    result = subprocess.run(command, capture_output=True, timeout=120)
    if result.returncode != 0 or not video_path.is_file():
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"生成 MP4 验收素材失败：{detail[-500:]}")
    return video_path


def check_extraction(label: str, path: Path, content_type: str, tokens: list[str]) -> dict:
    result = extract_material(path.read_bytes(), path.name, content_type, "sale")
    text = str(result.get("text") or "")
    matched = [token for token in tokens if token in text]
    passed = result.get("status") == "extracted" and bool(matched)
    payload = {
        "label": label,
        "passed": passed,
        "status": result.get("status"),
        "file_type": result.get("file_type"),
        "matched": matched,
        "text_preview": text[:500],
        "note": result.get("note"),
        "metadata": result.get("metadata"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="真实 OCR、扫描 PDF、音频和视频提取验收")
    parser.add_argument("--speech-wav", type=Path, required=True, help="包含清晰中文语音的 WAV 文件")
    args = parser.parse_args()
    if not args.speech_wav.is_file():
        parser.error(f"语音验收文件不存在：{args.speech_wav}")

    with tempfile.TemporaryDirectory(prefix="asset-library-smoke-") as temp_dir:
        directory = Path(temp_dir)
        image_path, pdf_path = create_scan_fixtures(directory)
        video_path = create_video_fixture(directory, args.speech_wav)
        results = [
            check_extraction("图片 OCR", image_path, "image/png", ["上海", "写字楼"]),
            check_extraction("扫描 PDF OCR", pdf_path, "application/pdf", ["上海", "写字楼"]),
            check_extraction("音频 ASR", args.speech_wav, "audio/wav", ["上海", "写字楼"]),
            check_extraction("视频 ASR", video_path, "video/mp4", ["上海", "写字楼"]),
        ]

    failed = [result["label"] for result in results if not result["passed"]]
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("ALL_LOCAL_EXTRACTION_CHECKS_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
