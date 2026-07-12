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

# Setup Python 3.12 virtual environment AS ROOT so /venv is writable
ENV VIRTUAL_ENV=/venv
RUN python3.12 -m venv $VIRTUAL_ENV
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Create non-root user, own the venv and app dir, then switch
RUN useradd -m appuser \
    && chown -R appuser:appuser $VIRTUAL_ENV
USER appuser
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY --chown=appuser:appuser pyproject.toml requirements.txt* ./

# Install dependencies and update basic pip tools for 3.12 compatibility
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir fastapi[all] uvicorn pillow; \
    fi

# Install stable configurations matching Python 3.12 index bindings
RUN pip install --no-cache-dir \
            "paddlepaddle-gpu" \
            "paddleocr>=2.9" \
            --extra-index-url https://www.paddlepaddle.org.cn/packages/stable/cu118/

# Copy application source
COPY --chown=appuser:appuser . .

# Seed PaddleOCR model cache
# Create the target directory structure
RUN mkdir -p /home/appuser/.paddlex

# Copy the contents of your local .paddlex folder internally inside the container
RUN cp -r models/.paddlex/. /home/appuser/.paddlex/

# Pre-populate config
COPY --chown=appuser:appuser config.docker.yml /app/config.yml

EXPOSE 8000

CMD ["uvicorn", "start_api:app", "--host", "0.0.0.0", "--port", "8000"]