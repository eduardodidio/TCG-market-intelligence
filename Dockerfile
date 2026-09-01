# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# Stage 2: Download Litestream
FROM debian:bookworm-slim AS litestream
ARG LITESTREAM_VERSION=0.3.13
ADD https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-v${LITESTREAM_VERSION}-linux-amd64.tar.gz /tmp/litestream.tar.gz
RUN tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz && rm /tmp/litestream.tar.gz

# Stage 3: Python runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

# System deps for curl_cffi (needs libcurl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libcurl4-openssl-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Litestream binary
COPY --from=litestream /usr/local/bin/litestream /usr/local/bin/litestream

# Install Python deps
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directory for persistent disk
RUN mkdir -p /data

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

# Copy start scripts and Litestream config
COPY litestream.yml render-start.sh render-start-app.sh ./
# Render sets $PORT dynamically; default to 8000
CMD ["sh", "render-start.sh"]
