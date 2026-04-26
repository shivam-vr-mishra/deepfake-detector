FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/models_cache \
    TRANSFORMERS_CACHE=/models_cache

# System deps:
#   libmagic1   -> python-magic content sniffing
#   ffmpeg      -> librosa / opencv codecs
#   libgl1      -> opencv runtime
#   libsndfile1 -> soundfile / librosa
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libmagic1 \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libsndfile1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY backend/requirements.txt /srv/requirements.txt

# Install CPU-only PyTorch first (much smaller than the default CUDA build)
RUN pip install --upgrade pip && \
    pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 && \
    pip install -r requirements.txt

# Copy backend app + sibling ai-services package so workers can import it
COPY backend /srv
COPY ai-services /srv/ai-services

ENV PYTHONPATH=/srv:/srv/ai-services

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
