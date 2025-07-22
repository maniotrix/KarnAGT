# CodeSandbox - Production Docker Image
FROM jupyter/minimal-notebook:latest

# Switch to root to install system packages
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (common data science libraries)
RUN pip install --no-cache-dir \
    fastapi>=0.100.0 \
    uvicorn[standard]>=0.20.0 \
    pydantic>=2.0.0 \
    httpx>=0.24.0 \
    jupyter-server>=2.0.0 \
    jupyter-client>=8.0.0 \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    plotly \
    scikit-learn \
    scipy \
    requests

# Create app directory
RUN mkdir -p /app
WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY *.py ./
COPY requirements.txt ./

# Install additional requirements if any
RUN pip install --no-cache-dir -r requirements.txt

# Create workspace directory
RUN mkdir -p /tmp/workspaces && chmod 777 /tmp/workspaces

# Switch back to jovyan user (from jupyter base image)
USER jovyan

# Environment variables
ENV ENVIRONMENT=production
ENV HOST=0.0.0.0
ENV PORT=8080
ENV JUPYTER_HOST=0.0.0.0  
ENV JUPYTER_PORT=8888
ENV JUPYTER_TOKEN=""
ENV JUPYTER_PASSWORD=""
ENV WORKSPACE_BASE_PATH=/tmp/workspaces

# Expose ports
EXPOSE 8080 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Start the application
CMD ["python", "run_server.py"] 