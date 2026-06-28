FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd -m -u 1000 mdv

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir . && \
    mkdir -p /data && chown mdv:mdv /data

USER mdv

ENV MDV_ROOT=/data \
    MDV_HOST=0.0.0.0 \
    MDV_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
  || exit 1

CMD ["python", "-m", "md_viewer", "serve"]
