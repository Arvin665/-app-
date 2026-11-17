FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
RUN python scripts/download_sense_voice_model.py
RUN python scripts/download_vosk_model.py
RUN mkdir -p /app/uploads

ENV ASR_ENGINE=sensevoice \
    SENSE_VOICE_MODEL_PATH=/app/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 \
    VOSK_MODEL_PATH=/app/models/vosk-model-small-cn-0.22

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
