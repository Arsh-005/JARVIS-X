FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

RUN addgroup --system jarvis && adduser --system --ingroup jarvis jarvis

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY static ./static
COPY data ./data
COPY workspace ./workspace

RUN python -m pip install --upgrade pip && \
    pip install ".[enterprise]" && \
    chown -R jarvis:jarvis /app

USER jarvis

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '10000') + '/health', timeout=3)"

CMD ["sh", "-c", "uvicorn jarvis.api:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --proxy-headers"]