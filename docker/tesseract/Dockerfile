# Tesseract OCR Microservice
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install Tesseract and language packs
RUN apt-get update && apt-get install -y \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    tesseract-ocr-uzb \
    # Image processing
    libtesseract-dev \
    libpng-dev \
    libjpeg-dev \
    # Python dependencies
    python3-dev \
    build-essential \
    # Web server tools
    curl \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract installation
RUN tesseract --version && \
    tesseract --list-langs

# Create app directory
WORKDIR /app

# Install Python packages
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    python-multipart==0.0.6 \
    Pillow==10.4.0 \
    opencv-python==4.10.0.84 \
    pytesseract==0.3.10 \
    numpy==1.26.4

# Copy OCR service files
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/ocr /app/logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash ocr && \
    chown -R ocr:ocr /app /tmp/ocr
USER ocr

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start OCR service
CMD ["uvicorn", "ocr_service:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"] 