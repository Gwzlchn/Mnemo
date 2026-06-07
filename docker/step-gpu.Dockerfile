# GPU 步骤镜像:Whisper 语音转写,CUDA 运行时 + faster-whisper。
# 需宿主装 NVIDIA Container Toolkit;docker 执行器对 pool=gpu 的步骤透传 --gpus all。
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# 默认用 USTC 镜像源(国内构建快);海外 CI 传 --build-arg USE_USTC_MIRROR=0 用官方源。
ARG USE_USTC_MIRROR=1
ENV DEBIAN_FRONTEND=noninteractive

RUN if [ "$USE_USTC_MIRROR" = "1" ]; then \
        sed -i 's|archive.ubuntu.com|mirrors.ustc.edu.cn|g; s|security.ubuntu.com|mirrors.ustc.edu.cn|g' /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends python3.11 python3-pip curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3

RUN if [ "$USE_USTC_MIRROR" = "1" ]; then \
        pip config set global.index-url https://mirrors.ustc.edu.cn/pypi/web/simple; \
    fi

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir --break-system-packages . \
    && pip install --no-cache-dir --break-system-packages "faster-whisper>=1.0,<2"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY shared/ shared/
COPY steps/ steps/
