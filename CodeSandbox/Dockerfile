# CodeSandbox - Production Docker Image
FROM python:3.10.11-slim

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

# Create non-root user
ARG CS_USER=code_sandbox
ENV CS_USER=${CS_USER}
RUN useradd --create-home --shell /bin/bash ${CS_USER}

# Copy and install requirements as root (avoids PATH warnings)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Switch to user
USER ${CS_USER}

# Go to user home
WORKDIR /home/${CS_USER}

# Copy application files
COPY --chown=${CS_USER}:${CS_USER} app/ ./app/
COPY --chown=${CS_USER}:${CS_USER} run_server.py ./
COPY --chown=${CS_USER}:${CS_USER} .env ./

# Create workspace and logs directories with proper permissions for non-root user
RUN mkdir -p /tmp/workspaces && chown ${CS_USER}:${CS_USER} /tmp/workspaces && \
    mkdir -p /tmp/logs && chown ${CS_USER}:${CS_USER} /tmp/logs

# Expose only FastAPI port
EXPOSE 8080

# Start the application
CMD ["python", "run_server.py"] 