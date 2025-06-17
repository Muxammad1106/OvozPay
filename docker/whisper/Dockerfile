# Whisper Voice Recognition Microservice
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Audio processing
    ffmpeg \
    libsndfile1-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    # Build tools
    build-essential \
    git \
    curl \
    wget \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python packages
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    python-multipart==0.0.6 \
    openai-whisper==20240930 \
    torch==2.7.1 \
    torchaudio==2.7.1 \
    numpy==1.26.4 \
    librosa==0.10.1 \
    soundfile==0.12.1 \
    pydub==0.25.1

# Create models directory and download Whisper models
RUN mkdir -p /app/models

# Download Whisper models (base model for production, add others as needed)
RUN python -c "import whisper; whisper.load_model('base')"

# Copy service files
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/whisper /app/logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash whisper && \
    chown -R whisper:whisper /app /tmp/whisper /root/.cache/whisper
USER whisper

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Start Whisper service
CMD ["uvicorn", "whisper_service:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"] 