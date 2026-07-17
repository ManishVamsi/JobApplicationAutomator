# ---------- Build stage ----------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system deps for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ---------- Production stage ----------
FROM python:3.12-slim

WORKDIR /app

# Runtime deps only (libpq for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create uploads directory for local storage provider
RUN mkdir -p /app/data/uploads

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
