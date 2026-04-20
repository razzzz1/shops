# backend/Dockerfile
# ────────────────────
# Multi-stage build for the Flask API.
#
# Stage 1 (base): installs system dependencies and Python packages.
# Stage 2 is not needed for development — we run directly from stage 1.
# For production, swap `python run.py` for gunicorn (see docker-compose.yml).

FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system packages needed by psycopg2 (PostgreSQL C adapter)
# --no-install-recommends keeps the image small
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer separately.
# If only source code changes (not requirements), this layer is reused
# and pip install is skipped, making rebuilds much faster.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code
COPY . .

# Expose the Flask development server port
EXPOSE 5000

# Default command — overridden in docker-compose.yml to run migrations first
CMD ["python", "run.py"]