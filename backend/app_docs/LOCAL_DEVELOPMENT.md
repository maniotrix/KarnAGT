# 🚀 Local Development Setup

This guide covers setting up **modern local development** where database services run in Docker containers while the backend application runs locally on your host machine using **uv** for fast package management.

> **💡 New in 2024:** This guide now uses **uv** for 10x faster package installation and platform-specific requirements for better compatibility.

The default values in backend/app/core/config.py use settings as per local env example and docker compose files.

## 📋 **Prerequisites**

- Docker & Docker Compose installed
- Python 3.10.11+
- **uv package manager** ([Install Guide](UV_PACKAGE_MANAGEMENT_GUIDE.md#-installation--setup))
- Git

## 🔧 **Quick Setup**

### **1. Setup Environment Variables**
```bash
# Copy the local template to create your .env file
cp env.local.example .env

# Edit .env and add your API keys (especially OPENAI_API_KEY)
nano .env  # or your preferred editor

# CRITICAL: Update MinIO configuration for dual endpoint strategy
# Add to your .env file:
# S3_ENDPOINT_URL=http://localhost:9000
# S3_PRESIGNED_URL_ENDPOINT=http://localhost:9000  # Browser access
```

### **2. Start Database Services**
```bash
# Navigate to database directory and start local containers
cd docker/database
docker-compose -f docker-compose.local.yml up -d

# Verify all services are running
docker ps
```

### **3. Install Python Dependencies (Using uv)**
```bash
# Return to backend directory
cd ../..

# Install platform-specific dependencies (MUCH FASTER!)
# Choose based on your operating system:

# Windows:
uv pip install -r requirements-windows.txt

# Linux/macOS:  
uv pip install -r requirements-linux.txt

# Alternative: Traditional pip (slower)
# pip install -r requirements-windows.txt  # Windows
# pip install -r requirements-linux.txt    # Linux/macOS
```

> **🚀 Performance Note:** uv is ~10x faster than pip! A 785-package install that takes 3-5 minutes with pip completes in 15-30 seconds with uv.

### **4. Run Database Migrations**
```bash
# Run migrations to set up database schema
python run_migrations.py
```

### **5. Start Backend Application**
```bash
# Start the FastAPI application locally
python start_app.py

# Or use the original development script
python start_dev.py
```

### **6. (Optional) Start CodeSandbox for Local Development**
If your backend needs CodeSandbox integration, you have two options:

```bash
# Option A: Direct port access (recommended for local backend development)
cd ../CodeSandbox
python docker_setup_and_run.py start --local

# Option B: Full Traefik integration (use when backend is also in Docker)
python docker_setup_and_run.py start --dev
```

**CodeSandbox Local vs Dev:**
- **Local**: Direct port mapping (8080), perfect for host-based backend development
- **Dev**: Traefik integration, use when backend runs in Docker containers

## 🗄️ **Database Services Architecture**

### **Local Development Ports**
| Service | Port | Container | Purpose |
|---------|------|-----------|---------|
| **PostgreSQL** | 5432 | `postgres` | Main database |
| **Redis** | 6379 | `redis` | Caching & sessions |
| **Qdrant** | 6333 | `qdrant` | Vector database |
| **Neo4j** | 7687/7474 | `neo4j` | Graph database |
| **MinIO** | 9000/9001 | `minio` | Object storage |

### **Database Credentials (Local)**
```bash
PostgreSQL: app_local_user:app_local_password@localhost:5432/app_local_db
Redis: redis://localhost:6379/0 (no auth)
Neo4j: neo4j:neo4j_password@bolt://localhost:7687
Qdrant: http://localhost:6333 (no auth)

# MinIO (Local Development - Single Endpoint)
MinIO API: http://localhost:9000
MinIO Console: http://localhost:9001
Credentials: minioadmin:minioadmin123

# Environment Configuration:
S3_ENDPOINT_URL=http://localhost:9000
S3_PRESIGNED_URL_ENDPOINT=http://localhost:9000  # Same for local development
```

## 🛠️ **Database Management Commands**

### **Start/Stop Services**
```bash
cd docker/database

# Start all local database services
docker-compose -f docker-compose.local.yml up -d

# Stop all services
docker-compose -f docker-compose.local.yml down

# Restart services
docker-compose -f docker-compose.local.yml restart
```

### **Health Checks**
```bash
# Check if containers are running
docker ps

# Check individual service
python ../../scripts/check_docker_services.py

# View container health status
docker-compose -f docker-compose.local.yml ps
```

### **View Logs**
```bash
# View logs for all services
docker-compose -f docker-compose.local.yml logs

# View specific service logs
docker logs postgres
docker logs redis
docker logs neo4j
docker logs qdrant
docker logs minio
```

### **CodeSandbox Management (Optional)**
```bash
cd ../CodeSandbox

# Start CodeSandbox for local backend development
python docker_setup_and_run.py start --local

# Check available environments
python docker_setup_and_run.py envs

# View CodeSandbox logs  
docker-compose -f docker-compose.local.yml logs -f

# Stop CodeSandbox
docker-compose -f docker-compose.local.yml down
```

## 📁 **Project Structure for Local Dev**

```
backend/
├── .env                           # Your local environment (from env.local.example)
├── env.local.example             # Template for local development
├── start_app.py                  # Universal startup script
├── run_migrations.py             # Database migrations
├── docker/database/              # Database containers
│   ├── docker-compose.local.yml  # Local database services (manual)
│   └── db_manager.py             # Database management (dev/staging/prod only)
└── app/                          # Your application code
```

---

## 📦 **Managing Dependencies During Development**

### **Adding New Packages**
```bash
# 1. Add to requirements.in (the source file)
echo "new-awesome-package>=1.0.0" >> requirements.in

# 2. Regenerate platform-specific files
uv pip compile --python-platform windows --python-version 3.10 requirements.in -o requirements-windows.txt --upgrade
uv pip compile --python-platform linux --python-version 3.10 requirements.in -o requirements-linux.txt --upgrade

# 3. Install locally (choose your platform)
uv pip install -r requirements-windows.txt  # Windows
# OR
uv pip install -r requirements-linux.txt    # Linux/macOS

# 4. Commit all changes
git add requirements.in requirements-windows.txt requirements-linux.txt
git commit -m "Add new-awesome-package dependency"
```

### **Updating Dependencies**
```bash
# Update all packages to latest versions
uv pip compile --python-platform windows --python-version 3.10 requirements.in -o requirements-windows.txt --upgrade
uv pip compile --python-platform linux --python-version 3.10 requirements.in -o requirements-linux.txt --upgrade

# Install updates locally
uv pip install -r requirements-windows.txt --upgrade  # Windows
# OR  
uv pip install -r requirements-linux.txt --upgrade    # Linux/macOS
```

### **Key Files:**
- **`requirements.in`** - Edit this file to add/remove dependencies
- **`requirements-windows.txt`** - Auto-generated for Windows development  
- **`requirements-linux.txt`** - Auto-generated for Docker/Linux containers
- **`requirements.txt`** - Legacy file, no longer used

> **💡 Pro Tip:** Never edit the generated `.txt` files directly. Always edit `requirements.in` and regenerate!

> **📖 Detailed Guide:** See [UV_PACKAGE_MANAGEMENT_GUIDE.md](UV_PACKAGE_MANAGEMENT_GUIDE.md) for comprehensive uv usage instructions.

---

## 🔍 **Troubleshooting**

### **Database Connection Issues**
```bash
# Check if containers are running
docker ps

# Check container logs
docker logs postgres
docker logs redis

# Test connectivity
python scripts/check_docker_services.py
```

### **Port Conflicts**
If you get port conflicts, make sure no other services are using:
- 5432 (PostgreSQL)
- 6379 (Redis) 
- 6333 (Qdrant)
- 7687/7474 (Neo4j)
- 9000/9001 (MinIO)

### **Migration Issues**
```bash
# Check migration status
alembic current
alembic history

# Reset migrations (⚠️ DATA LOSS)
alembic downgrade base
alembic upgrade head
```

## 🌐 **Access Services**

Once running, you can access:

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **MinIO Console**: http://localhost:9001
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## 🎯 **Development Workflow**

### **Daily Development Process:**
1. **Daily startup**: `cd docker/database && docker-compose -f docker-compose.local.yml up -d`
2. **Update dependencies** (if requirements.in changed): `uv pip install -r requirements-windows.txt` (Windows) or `uv pip install -r requirements-linux.txt` (Linux/macOS)
3. **Run migrations**: `python run_migrations.py` (if schema changes)
4. **Start backend**: `python start_app.py`
5. **Code & test**: Your FastAPI app runs locally with hot reload
6. **Shutdown**: `docker-compose -f docker-compose.local.yml down` (optional)

### **When Adding New Dependencies:**
1. **Edit source**: Add package to `requirements.in`
2. **Generate files**: Use uv to regenerate platform-specific requirements
3. **Install locally**: `uv pip install -r requirements-[platform].txt`
4. **Commit changes**: Add all requirements files to git
5. **Continue development**: New packages are ready to use!

## ⚠️ **Important Notes**

- **Environment File**: Always use `.env` created from `env.local.example`
- **API Keys**: Add your actual OpenAI API key to `.env`
- **MinIO Configuration**: Include both `S3_ENDPOINT_URL` and `S3_PRESIGNED_URL_ENDPOINT` for proper file access
- **CodeSandbox Options**: Choose `--local` for host-based backend, `--dev` for containerized backend
- **Data Persistence**: Database data persists in Docker volumes
- **Network**: Services communicate via `localhost` (not Docker networking)
- **Hot Reload**: Application supports hot reload for development

Your local development environment is now ready! 🎉
