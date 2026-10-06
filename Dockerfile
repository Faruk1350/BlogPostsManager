# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ARG APP_VERSION=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    LOG_FILE=/var/log/blog/app.log \
    LOG_LEVEL=INFO

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------- test stage ----------------
FROM base AS test
COPY . .
RUN python -m pytest -q

# ---------------- runtime stage ----------------
FROM base AS runtime

LABEL org.opencontainers.image.title="blog-posts-manager" \
      org.opencontainers.image.version="${APP_VERSION}"

RUN useradd --system --uid 10001 appuser \
    && mkdir -p /var/log/blog \
    && chown -R appuser:appuser /var/log/blog

COPY --chown=appuser:appuser app.py ./
COPY --chown=appuser:appuser templates ./templates

USER appuser
EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)"

# Single worker keeps prometheus metrics exact (no cross-worker aggregation needed).
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--threads", "4", \
     "--access-logfile", "/var/log/blog/access.log", \
     "--access-logformat", "%(h)s \"%(r)s\" %(s)s bytes=%(b)s duration=%(L)sus", \
     "--error-logfile", "-", \
     "app:app"]
