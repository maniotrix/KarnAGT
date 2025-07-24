# CodeSandbox - Production Docker Image
FROM python:3.10.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (from REQUIREMENTS_SETUP_GUIDE.md)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        poppler-utils \
        tesseract-ocr tesseract-ocr-eng \
        libmagic1 \
        graphviz \
        libgl1 \
        libhdf5-serial-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Python dependencies first (better layer caching)
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy necessary application files
COPY app/ ./app/
COPY run_server.py ./
COPY .env ./

# Expose only FastAPI port
EXPOSE 8080

# Start the application
CMD ["python", "run_server.py"] 