# Stage 1: Base image with Python 3.11
FROM python:3.11-slim

# Avoid writing .pyc files and force unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies required for OpenCV and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch to minimize container size and build time
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend, src, and essential configuration files
COPY backend/ ./backend/
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY uploads/ ./uploads/

# Ensure upload directory exists
RUN mkdir -p uploads/menus

# Expose default API port
EXPOSE 8000

# Health check to ensure service is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Start FastAPI server binding to dynamic PORT provided by cloud hosts (Render, Railway, etc.)
CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
