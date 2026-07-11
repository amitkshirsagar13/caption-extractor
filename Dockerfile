# syntax=docker/dockerfile:1
FROM docker.io/nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python + system dependencies
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Detroit

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.10 \
        python3.10-venv \
        python3-pip \
        build-essential \
        ca-certificates \
        curl \
        gcc \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Setup Python virtual environment AS ROOT so /venv is writable
ENV VIRTUAL_ENV=/venv
RUN python3.10 -m venv $VIRTUAL_ENV
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Create non-root user, own the venv and app dir, then switch
RUN useradd -m appuser \
    && chown -R appuser:appuser $VIRTUAL_ENV
USER appuser
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY --chown=appuser:appuser pyproject.toml requirements.txt* ./

# Install dependencies
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir --upgrade pip setuptools wheel; \
        pip install --no-cache-dir fastapi[all] uvicorn pillow; \
    fi

RUN pip install --no-cache-dir \
            "paddlepaddle-gpu==3.0.0" \
            "paddleocr>=2.9" \
            --extra-index-url https://www.paddlepaddle.org.cn/packages/stable/cu118/

# Copy application source
COPY --chown=appuser:appuser . .

# Seed PaddleOCR model cache
RUN if [ -d /app/models/.paddleocr ]; then \
        mkdir -p /home/appuser/.paddleocr && \
        cp -r /app/models/.paddleocr/. /home/appuser/.paddleocr/; \
    fi

# Pre-populate config
COPY --chown=appuser:appuser config.docker.yml /app/config.yml

EXPOSE 8000

CMD ["uvicorn", "start_api:app", "--host", "0.0.0.0", "--port", "8000"]