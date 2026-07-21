# Stage 1: Build Python dependencies
FROM python:3.12-slim AS python-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Prune unnecessary files from site-packages to reduce container size
RUN find /usr/local/lib/python3.12/site-packages -type d \( \
        -name "test" -o -name "tests" -o -name "testing" \
        -o -name "benchmark" -o -name "benchmarks" -o -name "examples" \
        -o -name "__pycache__" \
    \) -exec rm -rf {} + \
    && find /usr/local/lib/python3.12/site-packages -type f \( \
        -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" -o -name "*.exe" \
        -o -name "*.md" -o -name "README*" -o -name "LICENSE*" \
        -o -name "COPYING*" -o -name "CHANGELOG*" \
    \) -exec rm -f {} +


# Stage 2: Get Caddy server
FROM caddy:2-alpine AS caddy


# Stage 3: Final lightweight container image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    UPLOADS_ROOT=/data/uploads

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy built site-packages and binary scripts from builder stage
COPY --from=python-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy Caddy server binary from caddy stage
COPY --from=caddy /usr/bin/caddy /usr/bin/caddy

RUN useradd -r -s /bin/false appuser

WORKDIR /app

# Copy application code and config files
COPY wanshitong ./wanshitong
COPY app.py ./app.py
COPY babel.cfg ./babel.cfg
COPY Caddyfile ./Caddyfile
COPY docker-entrypoint.sh ./docker-entrypoint.sh

# Set up permissions for non-root user appuser
RUN chmod +x /app/docker-entrypoint.sh \
    && mkdir -p /data/uploads \
    && chown -R appuser:appuser /data/uploads /app

USER appuser

VOLUME ["/data/uploads"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD caddy validate --config /app/Caddyfile --adapter caddyfile || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker-entrypoint.sh"]
