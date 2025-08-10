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
├── docker_setup_config.json    # Environment configuration ✅ (committed)
├── .env.docker.dev.template    # Dev environment template ✅ (committed)
├── .env.docker.prod.template   # Prod environment template ✅ (committed)
├── .env.docker.dev             # Dev environment secrets ❌ (NOT committed)
├── .env.docker.prod            # Prod environment secrets ❌ (NOT committed)
└── docker_setup_and_run.py     # Minimal Docker manager script
```

## 🚀 **Usage**

### **Core Commands**
```bash
# Show available environments and their status
python docker_setup_and_run.py envs

# Validate environment setup (check files, Docker availability)
python docker_setup_and_run.py validate --env=dev
python docker_setup_and_run.py validate --prod  # shorthand

# Build image only
python docker_setup_and_run.py build --dev
python docker_setup_and_run.py build --env=prod

# Build and start containers (most common)
python docker_setup_and_run.py start --dev
python docker_setup_and_run.py start --prod

# Stop, rebuild, and start (fresh restart)
python docker_setup_and_run.py restart --dev
python docker_setup_and_run.py restart --prod
```

### **Development Mode** (with hot reload)
```bash
# Start development environment
python docker_setup_and_run.py start --dev

# View logs (use native Docker commands)
docker-compose -f docker-compose.dev.yml logs -f

# Open shell (use native Docker commands)  
docker-compose -f docker-compose.dev.yml exec codesandbox-dev bash

# Stop containers (use native Docker commands)
docker-compose -f docker-compose.dev.yml down
```

### **Production Mode** (optimized)
```bash
# Start production environment
python docker_setup_and_run.py start --prod

# View logs (use native Docker commands)
docker-compose -f docker-compose.prod.yml logs -f

# Open shell (use native Docker commands)
docker-compose -f docker-compose.prod.yml exec codesandbox-prod bash

# Stop containers (use native Docker commands)
docker-compose -f docker-compose.prod.yml down
```

### **Environment Validation**
The script provides detailed validation logging:
```bash
python docker_setup_and_run.py validate --dev
```
**Output:**
```
[14:23:45] 🔍 Validating 'dev' environment...
[14:23:45]    ✅ Environment 'dev' found in config
[14:23:45]    🐳 Checking Docker availability...
[14:23:45]    ✅ Docker and docker-compose are available
[14:23:45]    📁 Validating required files...
[14:23:45]    ✅ Docker Compose file: docker-compose.dev.yml
[14:23:45]    ✅ Dockerfile: Dockerfile.dev
[14:23:45]    ✅ Environment file: .env.docker.dev
[14:23:45] ✅ Environment 'dev' validation passed
```

## ⚙️ **Configuration**

### **JSON Configuration File**
The script uses `docker_setup_config.json` to define environments:
```json
{
  "project_name": "codesandbox",
  "environments": {
    "dev": {
      "compose_file": "docker-compose.dev.yml",
      "dockerfile": "Dockerfile.dev", 
      "env_file": ".env.docker.dev",
      "service_name": "codesandbox-dev"
    },
    "prod": {
      "compose_file": "docker-compose.prod.yml",
      "dockerfile": "Dockerfile.prod",
      "env_file": ".env.docker.prod", 
      "service_name": "codesandbox-prod"
    }
  },
  "default_environment": "prod"
}
```

To add new environments, simply add entries to the `environments` section.

## 🔒 **Security Notes**

### **✅ Safe to Commit (Templates & Config)**
- `docker_setup_config.json` ✅ (environment configuration)
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

### **Quick Environment Check**
```bash
# Check which environments are ready
python docker_setup_and_run.py envs
```
**Output:**
```
[14:26:30] 📋 Available Environments:
[14:26:30]    • dev: Development environment with hot reload
[14:26:30]      ✅ Ready
[14:26:30]    • prod (default): Production environment  
[14:26:30]      ❌ Missing: Env file
```

### **Local Development**
```bash
# Validate and start development
python docker_setup_and_run.py validate --dev  # Optional check first
python docker_setup_and_run.py start --dev
```

### **Production Deployment**
```bash
# On production server:
scp .env.docker.prod user@server:/app/.env.docker.prod  # Secure upload
ssh user@server "cd /app && python docker_setup_and_run.py validate --prod"  # Validate
ssh user@server "cd /app && python docker_setup_and_run.py start --prod"     # Deploy
```

## 🛠️ **Troubleshooting**

### **Environment Status Check**
First, always check environment status:
```bash
python docker_setup_and_run.py envs
```

### **Missing Environment Files**
```bash
❌ Environment file .env.docker.dev not found
💡 Create it by copying: cp .env.docker.dev.template .env.docker.dev
```

### **Missing Docker Files**  
```bash
❌ Dockerfile: Dockerfile.dev (NOT FOUND)
# Check if you're in the CodeSandbox directory
# Verify docker_setup_config.json points to correct file names
```

### **Configuration Issues**
```bash
❌ Config file not found: docker_setup_config.json
# Make sure you're in the correct directory
# The JSON config file defines all environment settings
```

### **Port Conflicts**
Both dev and prod use the same port (8080). Only run one at a time:
```bash
docker-compose -f docker-compose.dev.yml down    # Stop dev first
python docker_setup_and_run.py start --prod     # Then start prod
```

### **Docker Availability**
```bash
❌ Docker or docker-compose not available
# Install Docker and Docker Compose
# Ensure Docker daemon is running
```

## 📦 **Container Names**
- **Dev**: `codesandbox-development`
- **Prod**: `codesandbox-production` 

Check with: `docker ps`

## 🎯 **Minimal Script Philosophy**

This setup script follows a **minimal approach**:

### **✅ What It Does (Essential Operations)**
- ✅ **Validates** all required files before Docker operations
- ✅ **Builds** images using environment-specific configs  
- ✅ **Starts** containers with proper validation
- ✅ **Restarts** with fresh builds (down → build → up)
- ✅ **Shows environment status** at a glance

### **❌ What It Doesn't Do (By Design)**
- ❌ Log viewing (use `docker-compose logs -f`)
- ❌ Shell access (use `docker-compose exec`)
- ❌ Container stopping (use `docker-compose down`)  
- ❌ Complex cleanup operations (use native Docker commands)
- ❌ Port detection or health checks

### **💡 Design Benefits**
- **🚀 Fast**: Focused on core container lifecycle
- **🔧 Reliable**: Essential validation prevents cryptic failures
- **📁 Configurable**: JSON-driven, reusable across projects
- **🐳 Native**: Uses standard docker-compose commands
- **🧹 Clean**: No feature bloat, does one thing well

For advanced operations, use native Docker commands directly - the script gets your containers running, Docker handles the rest!

## 📋 **Environment Variables**

Configure your containers using `.env.docker.*` files:

**Common Variables:**
```bash
# In .env.docker.dev or .env.docker.prod
LOG_FORMAT=console    # or "json" for structured logging
DEBUG=true           # Enable debug mode (dev only)
PORT=8080           # Application port
ENVIRONMENT=development  # or "production"
```

Refer to your `.env.docker.*.template` files for complete variable lists.
