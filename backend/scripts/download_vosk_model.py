from __future__ import annotations

import argparse
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

MODEL_NAME = "vosk-model-small-cn-0.22"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
DEFAULT_TARGET = Path(__file__).resolve().parents[1] / "models" / MODEL_NAME


def safe_extract(package: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in package.infolist():
        resolved = (destination / member.filename).resolve()
        if resolved != root and root not in resolved.parents:
            raise RuntimeError(f"压缩包包含不安全路径：{member.filename}")
    package.extractall(destination)


def ensure_model(target: Path = DEFAULT_TARGET, force: bool = False) -> Path:
    target = target.resolve()
    if (target / "conf" / "model.conf").is_file() and not force:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vosk-model-", dir=target.parent) as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / f"{MODEL_NAME}.zip"
        print(f"Downloading {MODEL_URL}")
        urllib.request.urlretrieve(MODEL_URL, archive_path)
        with zipfile.ZipFile(archive_path) as package:
            safe_extract(package, temp_path)
        extracted = temp_path / MODEL_NAME
        if not (extracted / "conf" / "model.conf").is_file():
            raise RuntimeError("Vosk 模型压缩包结构不正确")
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(extracted), target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="下载 Vosk 中文离线语音识别模型")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(ensure_model(args.target, args.force))


if __name__ == "__main__":
    main()
