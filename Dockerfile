# syntax=docker/dockerfile:1

# ---------------- frontend build ----------------
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------------- runtime ----------------
FROM python:3.12-slim AS runtime

ARG APP_VERSION=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    PORT=5000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --system --uid 10001 appuser \
    && mkdir -p /var/log/blog /app/backend/uploads \
    && chown -R appuser:appuser /var/log/blog /app/backend/uploads

COPY --chown=appuser:appuser app.py ./
COPY --chown=appuser:appuser backend ./backend
COPY --chown=appuser:appuser --from=frontend /frontend/dist ./frontend/dist

USER appuser
EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)"

# Single worker keeps Prometheus counters exact across the process.  FastAPI
# runs sync endpoints in a threadpool, so concurrency is still fine.
CMD ["uvicorn", "app:app", \
     "--host", "0.0.0.0", \
     "--port", "5000", \
     "--workers", "1", \
     "--proxy-headers", "--forwarded-allow-ips", "*", \
     "--log-config", "backend/logging.json"]

# ---------------- test stage (tests are not part of the runtime image) ----------------
FROM runtime AS test
COPY --chown=appuser:appuser test_app.py ./
