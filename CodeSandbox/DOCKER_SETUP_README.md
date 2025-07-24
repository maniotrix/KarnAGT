# Docker Setup Script Guide

## 🐳 Intelligent Docker Management

The `setup_and_run.py` script provides intelligent Docker image and container management for your CodeSandbox project.

## 🎯 How It Handles Images and Containers

### **Images - Built Only When Needed**
```python
# The script checks if rebuild is needed by:
1. Checking if image exists
2. Computing hash of: Dockerfile + requirements.txt + docker-compose.yml  
3. Comparing with previously stored hash
4. Rebuilds ONLY if files changed
```

**Result:** No unnecessary rebuilds - saves time and resources!

### **Containers - Reused When Possible**
```python
# Container management:
1. Checks if container already running → Skip start
2. Checks if container exists but stopped → Restart it
3. Creates new container only if needed
```

**Result:** Fast startup when containers already exist!

## 🚀 Usage Examples

### **Start Everything (Most Common)**
```bash
python setup_and_run.py start
```
**What it does:**
- ✅ Builds image (only if Dockerfile/requirements changed)
- ✅ Starts container (only if not already running)
- ✅ Shows status and optionally logs

### **View Logs**
```bash
python setup_and_run.py logs
```

### **Rebuild After Code Changes**
```bash
python setup_and_run.py rebuild
```
**Forces a complete rebuild even if files haven't changed**

### **Check Status**
```bash
python setup_and_run.py status
```
**Shows:**
- 🖼️ Image status and size
- 📦 Container status  
- 🌐 Service availability

### **Clean Up**
```bash
python setup_and_run.py cleanup       # Remove containers only
python setup_and_run.py cleanup --full # Remove containers + images
```

## 🔍 Smart Decision Making

### **Scenario 1: First Run**
```
📁 No image exists
🔨 Script builds image from scratch
🚀 Starts new container
✅ Ready!
```

### **Scenario 2: No Changes**
```  
📁 Image exists, files unchanged
✅ Skips build (saves 5-10 minutes!)
📦 Container already running  
✅ Ready instantly!
```

### **Scenario 3: Code Changes**
```
📁 Image exists, but Dockerfile/requirements changed
🔨 Rebuilds image (detects changes via hash)
🔄 Restarts container with new image
✅ Ready with latest changes!
```

### **Scenario 4: Container Crashed**
```
📁 Image exists and up-to-date
📦 Container stopped/failed
🚀 Restarts existing container
✅ Ready!
```

## 🛠️ Behind the Scenes

### **File Change Detection**
```python
# Creates hash from these files:
- Dockerfile
- requirements.txt  
- docker-compose.yml

# Stores hash in image label
# Compares on next run → Smart rebuilding!
```

### **System Commands Used**
```bash
docker images              # Check if image exists
docker ps -a               # Check container status  
docker-compose build       # Build when needed
docker-compose up -d       # Start containers
docker-compose logs -f     # Show logs
docker-compose down        # Stop containers
```

## ⚡ Performance Benefits

| Operation | Without Script | With Script |
|-----------|---------------|-------------|
| **First run** | 10-15 min | 10-15 min |
| **No changes** | 10-15 min | **5 seconds!** |
| **Small changes** | 10-15 min | 2-3 min |
| **Status check** | Manual commands | **Instant** |

## ⏱️ Rebuild Timing (Current 68-Package Setup)

| Change Type | Build Time | Why |
|-------------|------------|-----|
| **Added 1 Python package** | 7-12 minutes | Reinstalls all 68 packages |
| **Added system package (apt)** | 3-5 minutes | Updates system layer only |
| **Both Python + system** | 9-15 minutes | Both layers rebuild |
| **Hardware impact:** M1 Mac (4-6 min) vs Intel i5 (8-12 min) | | |

## 🎯 Production Features

### **Error Handling**
- ✅ Validates Docker availability
- ✅ Handles build failures gracefully  
- ✅ Provides clear error messages
- ✅ Supports interruption (Ctrl+C)

### **User Experience**
- 🎨 Colored output for clarity
- ⏰ Timestamps on all logs
- 📊 Detailed status reporting
- 🤔 Interactive log viewing option

### **Flexibility**
- 🔧 Multiple operation modes
- 🧹 Different cleanup levels  
- 📋 Comprehensive help system
- ⚙️ Environment detection

## 🚀 Quick Start

1. **Make executable:**
   ```bash
   chmod +x setup_and_run.py
   ```

2. **Start everything:**
   ```bash
   python setup_and_run.py start
   ```

3. **View logs:**
   ```bash
   python setup_and_run.py logs
   ```

4. **Stop when done:**
   ```bash
   python setup_and_run.py stop
   ```

## 🏆 Best Practices

### **Development Workflow**
```bash
# Daily development
python setup_and_run.py start     # Quick start
python setup_and_run.py logs      # Monitor

# After changing requirements.txt  
python setup_and_run.py rebuild   # Force rebuild

# End of day
python setup_and_run.py stop      # Clean stop
```

### **Troubleshooting**
```bash
# Check what's running
python setup_and_run.py status

# Clean slate
python setup_and_run.py cleanup --full

# Fresh start  
python setup_and_run.py start
```

## 🚀 Quick Development: Manual Package Installation

For **fast experimentation** without rebuilding (7-12 minute) images:

### **Install Python Packages Temporarily**
```bash
# Single package
docker-compose exec codesandbox pip install pandas

# Multiple packages
docker-compose exec codesandbox pip install pandas requests boto3

# From a temp file
echo -e "pandas\nrequests\nboto3" > temp_packages.txt
docker-compose exec codesandbox pip install -r temp_packages.txt
```

### **Install System Tools Temporarily**
```bash
# Update and install
docker-compose exec codesandbox apt-get update
docker-compose exec codesandbox apt-get install -y vim htop

# One-liner
docker-compose exec codesandbox bash -c "apt-get update && apt-get install -y vim"
```

### **Interactive Development**
```bash
# Get shell access for complex work
docker-compose exec codesandbox bash

# Then inside container:
pip install whatever-package
apt-get install whatever-tool
```

## 🎯 Hybrid Development Workflow

### **Phase 1: Quick Experimentation (30 seconds)**
```bash
# Start with script (intelligent startup)
python setup_and_run.py start

# Quick install for testing
docker-compose exec codesandbox pip install some-new-library

# Test your code immediately
```

### **Phase 2: Make Permanent (when ready)**
```bash
# Add to requirements.txt manually
echo "some-new-library==1.0.0" >> requirements.txt

# Rebuild when ready (script handles intelligently)
python setup_and_run.py rebuild
```

### **Phase 3: Production Deployment**
```bash
# Always use clean rebuilds for deployment
python setup_and_run.py rebuild
```

## 📋 Quick Reference Commands

```bash
# === Script Commands (Infrastructure) ===
python setup_and_run.py start      # Smart startup
python setup_and_run.py status     # Check status  
python setup_and_run.py logs       # View logs
python setup_and_run.py rebuild    # Clean rebuild
python setup_and_run.py stop       # Stop containers

# === Manual Commands (Quick Development) ===
docker-compose exec codesandbox pip install <package>      # Install Python pkg
docker-compose exec codesandbox apt-get install -y <tool>  # Install system tool
docker-compose exec codesandbox bash                       # Interactive shell
docker-compose exec codesandbox pip list                   # Check installed
```

## 💡 When to Use Which Approach

| Situation | Method | Time | Permanence |
|-----------|--------|------|------------|
| **Trying new package** | Manual install | 30 sec | ❌ Lost on restart |
| **Adding to project** | Add to requirements.txt + rebuild | 7-12 min | ✅ Permanent |
| **System debugging** | Manual apt install | 1-2 min | ❌ Lost on restart |
| **Production deploy** | Always rebuild | 7-12 min | ✅ Clean & reproducible |

This approach gives you **speed during development** while maintaining **reliability for production**! 🎯 