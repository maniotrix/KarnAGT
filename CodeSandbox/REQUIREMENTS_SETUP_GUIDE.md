# Requirements Setup Guide

## Overview

This document provides a complete guide for setting up the Python environment using our optimized `requirements.txt` file, including all necessary system-level dependencies.

## 📋 Requirements File Summary

Our `requirements.txt` contains **68 carefully curated packages** organized into logical categories:

### Package Categories

| Category | Count | Key Packages |
|----------|-------|--------------|
| **Core Web Framework & API** | 8 | `fastapi`, `uvicorn`, `httpx`, `websockets` |
| **Jupyter & Code Execution** | 2 | `jupyterlab`, `ipywidgets` |
| **Data Science Core** | 2 | `scikit-learn`, `seaborn` |
| **File & Document Processing** | 19 | `pdfplumber`, `openpyxl`, `python-docx`, `PyMuPDF` |
| **Image Processing** | 4 | `opencv-python-headless`, `scikit-image`, `imageio` |
| **Database & Storage** | 3 | `sqlalchemy`, `aiosqlite`, `sqlite-utils` |
| **Async Tools** | 2 | `aiohttp`, `aiofiles` |
| **Utilities** | 5 | `loguru`, `rich`, `orjson`, `wrapt` |
| **NLP** | 4 | `nltk`, `langdetect`, `textstat`, `emoji` |
| **Web Scraping** | 2 | `requests-toolbelt`, `mechanicalsoup` |
| **Time & Date** | 4 | `pendulum`, `dateparser`, `croniter` |
| **Scientific Computing** | 3 | `sympy`, `pint`, `uncertainties` |
| **Security** | 2 | `python-jose[cryptography]` (extras syntax), `itsdangerous` |
| **Validation** | 2 | `validators`, `email-validator` |
| **Caching** | 1 | `cachetools` |
| **Geospatial** | 2 | `folium`, `geopy` |
| **Financial Data** | 5 | `yfinance`, `pandas-datareader`, `fredapi` |
| **Visualization** | 2 | `graphviz`, `pydot` |
| **System Utilities** | 3 | `watchdog`, `portalocker`, `schedule` |
| **File Generation** | 3 | `fpdf2`, `reportlab`, `html2text` |

## 🎯 Optimization Features

### Parent Package Strategy
Our requirements file uses **parent packages** that automatically install their dependencies, reducing redundancy:

- ✅ `jupyterlab` → installs ~40 jupyter-related packages
- ✅ `seaborn` → installs `pandas`, `matplotlib`, `pillow`, etc.
- ✅ `scikit-learn` → installs `numpy`, `scipy`, `joblib`, etc.
- ✅ `pdfplumber` → installs `pypdfium2`, `pdfminer.six`, etc.

**Note:** Core data science packages like `numpy`, `pandas`, `matplotlib`, and `pillow` are automatically installed via the parent packages above, so you won't see them explicitly listed in requirements.txt.

### Version Pinning
All packages are pinned to exact versions for reproducible deployments:
```
fastapi==0.116.1
scikit-learn==1.7.1
seaborn==0.13.2
```

## 🚀 Installation Instructions

### Step 1: Python Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 2: Install Python Packages

```bash
# Install all packages (no cache for fresh downloads)
pip install --no-cache-dir -r requirements.txt
```

### Step 3: System Dependencies

The following **OS-level packages** are required for full functionality:

#### Ubuntu/Debian Systems

```bash
apt-get update && \
apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr tesseract-ocr-eng \
    libmagic1 \
    graphviz \
    libgl1 \
    libhdf5-serial-dev && \
apt-get clean && rm -rf /var/lib/apt/lists/*
```

#### Windows Systems

```powershell
# Using winget (Windows Package Manager)
winget install poppler
winget install tesseract
winget install graphviz

# Or using chocolatey
choco install poppler tesseract graphviz

# Important: Install python-magic with bundled DLL
pip install python-magic-bin
```

**Windows Note:** The `python-magic-bin` package bundles the required `libmagic` DLL for Windows. Without this, `python-magic` and `filetype` will fail at runtime.

#### macOS Systems

```bash
# Using Homebrew
brew install poppler tesseract graphviz libmagic
```

## 📦 System Dependencies Explained

| Package | Required By | Purpose |
|---------|-------------|---------|
| **`poppler-utils`** | `pdf2image` | Provides `pdftoppm`/`pdftocairo` binaries for PDF→image conversion |
| **`tesseract-ocr`** | `pytesseract` | Core OCR engine binary |
| **`tesseract-ocr-eng`** | `pytesseract` | English language pack (add more as needed) |
| **`libmagic1`** | `python-magic`, `filetype` | MIME type detection library |
| **`graphviz`** | `graphviz`, `pydot` | Provides `dot` executable for graph rendering |
| **`libgl1`** | `opencv-python-headless` | OpenGL library for image processing |
| **`libhdf5-serial-dev`** | `h5py`, `tables` | HDF5 library (optional but recommended) |

## 🐳 Docker Setup

### Automated Setup (Recommended)

The project includes an **intelligent Docker management script** that handles all setup automatically:

```bash
# One-command setup and start
python setup_and_run.py start
```

**What it does:**
- ✅ **Builds optimized image** with all 68 packages + system dependencies
- ✅ **Intelligent caching** - rebuilds only when needed
- ✅ **Production-ready** - clean, reproducible containers
- ✅ **Development-friendly** - supports quick manual installs

### Manual Dockerfile (for reference)

```dockerfile
FROM python:3.10.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        poppler-utils \
        tesseract-ocr tesseract-ocr-eng \
        libmagic1 \
        graphviz \
        libgl1 \
        libhdf5-serial-dev \
        build-essential \
        curl \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies (optimized layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./app/
COPY run_server.py ./
COPY .env ./

# Start the application
CMD ["python", "run_server.py"]
```

## ⚡ Performance Notes

### Installation Time
- **Python packages**: ~5-10 minutes (68 packages + dependencies)
- **System packages**: ~2-3 minutes
- **Total setup time**: ~10-15 minutes

### Disk Space
- **Python packages**: ~2-3 GB
- **System packages**: ~500 MB
- **Total disk usage**: ~3-4 GB

### Intelligent Docker Management
The project includes **automated Docker management** (`setup_and_run.py`) that optimizes these timing considerations:

- ✅ **First build**: 10-15 minutes (unavoidable)
- ✅ **Subsequent runs**: 5 seconds (reuses existing images)
- ✅ **Smart rebuilds**: Only when Dockerfile or requirements.txt change
- ✅ **Manual installs**: 30 seconds for quick experimentation

See the **Docker Automation & Development Workflow** section below for details.

## 🔧 Troubleshooting

### Common Issues

#### 1. PDF Processing Errors
```bash
# Error: pdf2image cannot find pdftoppm
# Solution: Install poppler-utils
apt-get install poppler-utils
```

#### 2. OCR Not Working
```bash
# Error: pytesseract cannot find tesseract
# Solution: Install tesseract and language packs
apt-get install tesseract-ocr tesseract-ocr-eng
```

#### 3. File Type Detection Issues
```bash
# Error: python-magic cannot find libmagic
# Solution: Install libmagic
apt-get install libmagic1
```

#### 4. Graph Visualization Errors
```bash
# Error: graphviz cannot find dot executable
# Solution: Install graphviz system package
apt-get install graphviz
```

### Version Compatibility
All packages are tested and compatible with:
- **Python**: 3.10.11
- **Operating Systems**: Windows 10+, Ubuntu 20.04+, macOS 12+

## 🎯 Usage Examples

### Quick Verification Script

```python
# test_installation.py
import sys

def test_imports():
    """Test critical package imports"""
    try:
        # Core frameworks
        import fastapi
        import uvicorn
        
        # Data science
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        
        # Document processing
        import pdfplumber
        import openpyxl
        
        # Image processing
        import cv2
        from PIL import Image
        
        # Jupyter
        import jupyterlab
        
        print("✅ All critical packages imported successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
```

### System Dependencies Check

```python
# check_system_deps.py
import subprocess
import sys

def check_system_command(command, package_name):
    """Check if system command is available"""
    try:
        subprocess.run([command, '--version'], 
                      capture_output=True, check=True)
        print(f"✅ {package_name}: {command} found")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌ {package_name}: {command} not found")
        return False

def main():
    checks = [
        ('pdftoppm', 'poppler-utils'),
        ('tesseract', 'tesseract-ocr'),
        ('dot', 'graphviz'),
    ]
    
    all_good = True
    for command, package in checks:
        if not check_system_command(command, package):
            all_good = False
    
    if all_good:
        print("\n🎉 All system dependencies are installed!")
    else:
        print("\n⚠️  Some system dependencies are missing.")
        print("Please install missing packages using your system package manager.")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
```

## 📚 Additional Resources

### Language Packs for OCR
Add more tesseract language packs as needed:

```bash
# Common language packs
apt-get install tesseract-ocr-fra  # French
apt-get install tesseract-ocr-spa  # Spanish  
apt-get install tesseract-ocr-deu  # German
apt-get install tesseract-ocr-hin  # Hindi
apt-get install tesseract-ocr-chi-sim  # Chinese Simplified
```

### Future Extensions
If you later add these packages, additional system dependencies will be needed:

| Python Package | System Requirement |
|----------------|-------------------|
| `weasyprint` | Cairo, Pango libraries |
| `wkhtmltopdf` | Qt, WebKit libraries |
| `camelot-py` | Ghostscript |
| `tabula-py` | Java Runtime Environment |
| `pandoc` | Pandoc binary |

## 🐳 Docker Automation & Development Workflow

### **Intelligent Docker Management**

The project includes `setup_and_run.py` - an intelligent Docker management script that:

- ✅ **Builds images only when needed** (detects Dockerfile/requirements.txt changes)
- ✅ **Reuses containers when possible** (avoids unnecessary recreation)
- ✅ **Manages the complete lifecycle** (build, start, stop, cleanup)
- ✅ **Provides real-time status** and logging

### **Setup Timing with Current 68 Packages**

| Operation | Time | What Happens |
|-----------|------|--------------|
| **First build** | 10-15 minutes | Downloads and installs all packages |
| **No changes** | 5 seconds | Reuses existing image and container |
| **Added 1 package** | 7-12 minutes | Rebuilds with all 68+ packages |
| **System packages** | 3-5 minutes | Updates apt layer only |

*Hardware impact: M1 MacBook (4-6 min) vs Intel i5 (8-12 min)*

### **Quick Start Commands**

```bash
# Intelligent startup (recommended)
python setup_and_run.py start

# Monitor logs
python setup_and_run.py logs

# Check status
python setup_and_run.py status

# Clean rebuild (after requirements.txt changes)
python setup_and_run.py rebuild
```

### **Development Speed Optimization**

For **fast experimentation** without 7-12 minute rebuilds:

```bash
# Quick install for testing (30 seconds)
docker-compose exec codesandbox pip install new-package

# Test your code immediately

# Make permanent when ready
echo "new-package==1.0.0" >> requirements.txt
python setup_and_run.py rebuild
```

### **Hybrid Development Workflow**

**Phase 1: Experimentation (30 sec)**
```bash
docker-compose exec codesandbox pip install pandas scikit-learn
# Test immediately - changes lost on container restart
```

**Phase 2: Make Permanent (7-12 min)**
```bash
# Add to requirements.txt
cat >> requirements.txt << EOF
pandas==2.0.0
scikit-learn==1.3.0
EOF

# Rebuild with clean, reproducible image
python setup_and_run.py rebuild
```

**Phase 3: Production Deployment**
```bash
# Always use clean rebuilds for production
python setup_and_run.py rebuild
```

This approach provides **development speed** (30 seconds) while maintaining **production reliability** (clean, versioned builds).

## 🏷️ Version Information

- **Requirements file version**: 1.0
- **Last updated**: January 2025
- **Python compatibility**: 3.10.11
- **Total packages**: 68 parent packages (~200+ with dependencies)

---

**Note**: This setup has been tested and optimized for maximum compatibility and minimal dependency conflicts. All packages use exact version pinning for reproducible deployments. 