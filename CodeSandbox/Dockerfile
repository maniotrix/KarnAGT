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
ARG USERNAME=code_sandbox
ENV USERNAME=${USERNAME}
RUN useradd --create-home --shell /bin/bash ${USERNAME}

# Copy and install requirements as root (avoids PATH warnings)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Switch to user
USER ${USERNAME}

# Go to user home
WORKDIR /home/${USERNAME}

# Copy application files
COPY --chown=${USERNAME}:${USERNAME} app/ ./app/
COPY --chown=${USERNAME}:${USERNAME} run_server.py ./
COPY --chown=${USERNAME}:${USERNAME} .env ./

# Create workspace directory with proper permissions for non-root user
RUN mkdir -p /tmp/workspaces && chown ${USERNAME}:${USERNAME} /tmp/workspaces

# Expose only FastAPI port
EXPOSE 8080

# Start the application
CMD ["python", "run_server.py"] 