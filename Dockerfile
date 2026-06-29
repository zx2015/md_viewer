FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir . && \
    mkdir -p /data

# Note: we intentionally run as root inside the container so that
# read-only bind mounts of host directories owned by root (e.g. /root/AI学习,
# /media/data/git) remain readable to the app without requiring us
# to loosen permissions on the host.

ENV MDV_ROOT=/data \
    MDV_HOST=0.0.0.0 \
    MDV_PORT=8000

EXPOSE 8000

# Probe the lightweight /api/health endpoint (see src/md_viewer/api.py).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
  || exit 1

CMD ["python", "-m", "md_viewer", "serve"]
