FROM python:3.11-slim

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

COPY . .

RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

ENV DATABASE_URL=sqlite+aiosqlite:////data/lea.db \
    HOST=0.0.0.0 \
    PORT=8000 \
    RENDER=true \
    LOG_LEVEL=info \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health', timeout=4).raise_for_status()"

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
