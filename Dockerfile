# syntax=docker/dockerfile:1
FROM docker.io/nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python 3.12 + system dependencies
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Detroit

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        python3-pip \
        build-essential \
        ca-certificates \
        curl \
        gcc \
        libgomp1 \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PADDLE_DISABLE_ONEDNN=1
ENV FLAGS_use_mkldnn=0
ENV FLAGS_enable_pir_api=0
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
ENV PADDLE_MODEL_CACHE_DIR=/home/appuser/.paddlex

WORKDIR /app

# Create non-root user and runtime directories before dependency install to avoid large chown layers
RUN useradd -m appuser \
    && mkdir -p /venv /app /home/appuser/.paddlex \
    && chown -R appuser:appuser /venv /app /home/appuser/.paddlex
USER appuser

# Setup Python 3.12 virtual environment
ENV VIRTUAL_ENV=/venv
RUN python3.12 -m venv $VIRTUAL_ENV
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml ./

# Install dependencies first, then remove build-only apt packages in the same layer.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir fastapi[all] uvicorn pillow \
    && pip install --no-cache-dir \
        "paddlepaddle-gpu" \
        "paddleocr>=2.9" \
        --extra-index-url https://www.paddlepaddle.org.cn/packages/stable/cu118/ \
    && rm -rf /home/appuser/.cache/pip

# Return to root only for apt cleanup of build-only packages
USER root
RUN apt-get purge -y --auto-remove \
        build-essential \
        curl \
        gcc \
        python3.12-dev \
        software-properties-common \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip
USER appuser

# Copy only runtime app files to avoid bringing unnecessary build context into layers
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser start_api.py /app/start_api.py

# Seed PaddleOCR model cache directly (avoids duplicate copy under /app/models)
COPY --chown=appuser:appuser models/.paddlex/ /home/appuser/.paddlex/

# Pre-populate config
COPY --chown=appuser:appuser config.docker.yml /app/config.yml

# Warm OCR caches at build-time so first request does not trigger model downloads.
RUN python -c "import sys; sys.path.insert(0, '/app/src'); from caption_extractor.config_manager import ConfigManager; from caption_extractor.ocr.ocr_processor import OCRProcessor; cfg = ConfigManager('/app/config.yml').config; OCRProcessor(cfg); print('OCR model warmup complete')"

EXPOSE 8000

CMD ["uvicorn", "start_api:app", "--host", "0.0.0.0", "--port", "8000"]