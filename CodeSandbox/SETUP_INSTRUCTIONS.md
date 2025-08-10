# 🐳 CodeSandbox Docker Setup Instructions

## 📋 **First-Time Setup**

### **1. Create Environment Files**
```bash
# Copy templates and edit with real values
cp .env.docker.dev.template .env.docker.dev
cp .env.docker.prod.template .env.docker.prod

# Edit the files with your actual values
nano .env.docker.dev    # or use your preferred editor
nano .env.docker.prod   # or use your preferred editor
```

### **2. Available Files**
After setup, your directory should have:
```
CodeSandbox/
├── Dockerfile.dev              # Development container
├── Dockerfile.prod             # Production container  
├── docker-compose.dev.yml      # Dev compose config
├── docker-compose.prod.yml     # Prod compose config
├── .env.docker.dev.template    # Dev environment template ✅ (committed)
├── .env.docker.prod.template   # Prod environment template ✅ (committed)
├── .env.docker.dev             # Dev environment secrets ❌ (NOT committed)
├── .env.docker.prod            # Prod environment secrets ❌ (NOT committed)
└── docker_setup_and_run.py            # Smart deployment script
```

## 🚀 **Usage**

### **Development Mode** (with hot reload)
```bash
python docker_setup_and_run.py start --dev
python docker_setup_and_run.py logs --dev
python docker_setup_and_run.py shell --dev
python docker_setup_and_run.py stop --dev
```

### **Production Mode** (optimized)
```bash
python docker_setup_and_run.py start --prod
python docker_setup_and_run.py logs --prod
python docker_setup_and_run.py shell --prod
python docker_setup_and_run.py stop --prod
```

### **Advanced Commands**
```bash
# Clean rebuild
python docker_setup_and_run.py rebuild --clean --dev
python docker_setup_and_run.py rebuild --clean --prod

# Full cleanup (removes images)
python docker_setup_and_run.py cleanup --full --dev
python docker_setup_and_run.py cleanup --full --prod

# Help
python docker_setup_and_run.py help
```

## 🔒 **Security Notes**

### **✅ Safe to Commit (Templates)**
- `.env.docker.dev.template`
- `.env.docker.prod.template`  
- `Dockerfile.dev`
- `Dockerfile.prod`
- `docker-compose.*.yml`
- `docker_setup_and_run.py`

### **❌ Never Commit (Real Values)**  
- `.env.docker.dev`
- `.env.docker.prod`
- `.env` (any real environment files)

## 🚀 **Deployment Workflow**

### **Local Development**
```bash
# Use your local .env.docker.dev
python docker_setup_and_run.py start --dev
```

### **Production Deployment**
```bash
# On production server:
scp .env.docker.prod user@server:/app/.env.docker.prod  # Secure upload
ssh user@server "cd /app && python docker_setup_and_run.py start --prod"
```

## 🛠️ **Troubleshooting**

### **Missing Environment Files**
```bash
❌ Environment file .env.docker.dev not found
💡 Create it by copying: cp .env.docker.dev.template .env.docker.dev
```

### **Missing Dockerfile**  
```bash
❌ Dockerfile Dockerfile.dev not found
# Check if you're in the CodeSandbox directory
```

### **Port Conflicts**
Both dev and prod use the same port (8080). Only run one at a time:
```bash
python docker_setup_and_run.py stop --dev    # Stop dev first
python docker_setup_and_run.py start --prod  # Then start prod
```

## 📦 **Container Names**
- **Dev**: `codesandbox-development`
- **Prod**: `codesandbox-production` 

Check with: `docker ps`

## 📋 **Logging Configuration**

### **Log Format Control**
You can control log formatting using the `LOG_FORMAT` environment variable:

**In your `.env.docker.dev`:**
```bash
LOG_FORMAT=console    # Human-readable colored logs (default for dev)
```

**In your `.env.docker.prod`:**
```bash
LOG_FORMAT=console    # Human-readable logs in production
# OR
LOG_FORMAT=json       # Machine-parsable JSON logs (default for prod)
```

**Examples:**
- **Console Format**: `14:45:58 INFO RUN_SERVER | 🚀 Starting FastAPI server`
- **JSON Format**: `{"timestamp": "2025-08-10T09:15:58", "level": "INFO", "logger": "RUN_SERVER", "message": "🚀 Starting FastAPI server"}`

**Industry Standards:**
- **Development**: Console format for easy reading and debugging
- **Production**: JSON format for log aggregation tools (ELK, Splunk, Datadog)
- **Override**: Use `LOG_FORMAT=console` in production if you prefer human-readable logs
