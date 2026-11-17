from __future__ import annotations

import argparse
import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

MODEL_NAME = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    f"{MODEL_NAME}.tar.bz2"
)
DEFAULT_TARGET = Path(__file__).resolve().parents[1] / "models" / MODEL_NAME


def safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        resolved = (destination / member.name).resolve()
        if resolved != root and root not in resolved.parents:
            raise RuntimeError(f"模型压缩包包含不安全路径：{member.name}")
    archive.extractall(destination)


def ensure_model(target: Path = DEFAULT_TARGET, force: bool = False) -> Path:
    target = target.resolve()
    required = (target / "model.int8.onnx", target / "tokens.txt")
    if all(path.is_file() for path in required) and not force:
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    download_url = os.environ.get("SENSE_VOICE_MODEL_URL", MODEL_URL).strip() or MODEL_URL
    with tempfile.TemporaryDirectory(prefix="sense-voice-model-", dir=target.parent) as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / f"{MODEL_NAME}.tar.bz2"
        print(f"Downloading {download_url}")
        urllib.request.urlretrieve(download_url, archive_path)
        with tarfile.open(archive_path, "r:bz2") as archive:
            safe_extract(archive, temp_path)
        extracted = temp_path / MODEL_NAME
        if not all((extracted / path.name).is_file() for path in required):
            raise RuntimeError("SenseVoiceSmall 模型压缩包结构不正确")
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(extracted), target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="下载 Sherpa-ONNX SenseVoiceSmall 中文识别模型")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(ensure_model(args.target, args.force))


if __name__ == "__main__":
    main()
