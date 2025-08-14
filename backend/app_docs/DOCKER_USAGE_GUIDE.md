# 🐳 Backend Docker Usage Guide

## 🎯 **Quick Start**

### **1. Start Database Infrastructure First**
```bash
cd backend/docker/database
python db_manager.py start --env=dev
```

### **2. Start Backend Container**
```bash
cd backend
python backend_docker_manager.py start --dev
```

### **3. Run Migrations Manually**
```bash
docker exec -it app-backend-development python run_migrations.py
```

**✨ That's it!** You have full control over when migrations run.

## 📋 **Complete Workflow**

### **🔧 Development Environment**
```bash
# 1. Start databases
cd backend/docker/database
python db_manager.py start --env=dev

# 2. Start backend container
cd backend
python backend_docker_manager.py start --dev

# 3. Run migrations manually
docker exec -it app-backend-development python run_migrations.py

# 4. Check health
python backend_docker_manager.py health --dev
```

### **🚀 Production Environment**
```bash
# 1. Start production databases
cd backend/docker/database
python db_manager.py start --env=prod

# 2. Start production containers
cd backend
python backend_docker_manager.py start --prod --build

# 3. Run migrations manually
docker exec -it app-backend-production python run_migrations.py

# 4. Verify health
python backend_docker_manager.py health --prod
```

## 🗄️ **Database Migrations Strategy**

### **🔧 Manual Migration Control (Default)**
Migrations are run **manually** for complete control:

```bash
# Inside the running container
docker exec -it app-backend-development python run_migrations.py
```

**Benefits:**
- ✅ **Full Control** - You decide exactly when migrations run
- ✅ **Zero Race Conditions** - No concurrent migration attempts
- ✅ **Production Safe** - Never accidentally run migrations
- ✅ **Debug Friendly** - Can troubleshoot migrations separately
- ✅ **Rollback Ready** - Can run `alembic downgrade` if needed

### **🗄️ Migration Commands**

**Run migrations inside container:**
```bash
# Development
docker exec -it app-backend-development python run_migrations.py

# Staging  
docker exec -it app-backend-staging python run_migrations.py

# Production
docker exec -it app-backend-production python run_migrations.py
```

**Check migration status:**
```bash
# Inside container
docker exec -it app-backend-development alembic current
docker exec -it app-backend-development alembic history --verbose
```

**Rollback migrations (if needed):**
```bash
# DANGER: This can cause data loss
docker exec -it app-backend-development alembic downgrade -1
```

## 🪣 **MinIO Setup**

### **Automatic Container Setup**
MinIO buckets are created automatically inside containers by `start_app.py`:
```
🪣 Checking MinIO setup...
✅ MinIO bucket 'app-files-dev' exists
```

**How it works:**
- Each container automatically connects to MinIO on startup
- Creates the required bucket if it doesn't exist  
- Gracefully handles bucket creation failures
- No manual intervention required

## 🔧 **Docker Manager Commands**

### **Environment Management**
```bash
# List available environments
python backend_docker_manager.py envs

# Validate environment setup
python backend_docker_manager.py validate --dev
python backend_docker_manager.py validate --staging
python backend_docker_manager.py validate --prod
```

### **Container Operations**
```bash
# Build only
python backend_docker_manager.py build --dev

# Start containers
python backend_docker_manager.py start --dev
python backend_docker_manager.py start --staging
python backend_docker_manager.py start --prod --build

# Stop containers
python backend_docker_manager.py stop --dev

# Restart with fresh build
python backend_docker_manager.py restart --dev
```

### **Monitoring & Debugging**
```bash
# Check container status
python backend_docker_manager.py status --dev

# View logs
python backend_docker_manager.py logs --dev
python backend_docker_manager.py logs --dev --follow

# Health checks
python backend_docker_manager.py health --dev
```

## 🚨 **Troubleshooting**

### **Common Issues & Solutions**

#### **1. Database Connection Failed**
```
❌ Database connection failed: connection refused
```
**Solution:**
```bash
# Make sure database containers are running
cd backend/docker/database
python db_manager.py start --env=dev
python db_manager.py health --env=dev
```

#### **2. Migration Failed**
```
❌ Migration failed: target database is not up to date
```
**Solution:**
```bash
# Check migration status
cd backend
alembic current
alembic history --verbose

# Reset migrations if needed (DANGER: DATA LOSS)
alembic downgrade base
alembic upgrade head
```

#### **3. MinIO Bucket Creation Failed**
```
⚠️ Could not create bucket 'app-files-dev' - will try at runtime
```
**Solution:**
```bash
# Check MinIO containers are running
docker ps | grep minio

# Restart the backend container to retry bucket creation
python backend_docker_manager.py restart --dev

# Check MinIO connection from inside container
docker exec -it app-backend-development python -c "
from app.core.config import settings
print('MinIO Endpoint:', settings.S3_ENDPOINT_URL)
print('MinIO Bucket:', settings.S3_BUCKET_NAME)
"
```

#### **4. Container Build Failed**
```
❌ Build dev failed: No such file or directory
```
**Solution:**
```bash
# Check required files exist
python backend_docker_manager.py validate --dev

# Rebuild from scratch
python backend_docker_manager.py stop --dev
python backend_docker_manager.py start --dev --build
```

## 📊 **Environment Port Matrix**

| Environment | Backend | PostgreSQL | Redis | Neo4j | Qdrant | MinIO |
|-------------|---------|------------|-------|-------|--------|-------|
| **Development** | 8000 | 5433 | 6380 | 7688 | 6335 | 9002 |
| **Staging** | 8000 | 5434 | 6381 | 7689 | 6337 | 9004 |
| **Production** | 8000 | 5432 | 6379 | 7687 | 6333 | 9000 |

## 🎯 **Best Practices**

### **Development**
```bash
# Development workflow:
1. python db_manager.py start --env=dev                     # Databases first
2. python backend_docker_manager.py start --dev            # Backend container
3. docker exec -it app-backend-development python run_migrations.py  # Manual migrations
```

### **Production**
```bash
# Production deployment checklist:
1. python db_manager.py validate --env=prod                # Validate setup
2. python db_manager.py backup --env=prod                  # Backup existing data
3. python db_manager.py start --env=prod                   # Start databases
4. python backend_docker_manager.py start --prod --build   # Deploy container
5. docker exec -it app-backend-production python run_migrations.py  # Manual migrations
6. python backend_docker_manager.py health --prod          # Verify health
```

### **CI/CD Integration**
```bash
# Example CI/CD pipeline
./scripts/deploy.sh --env=staging
```

## 📁 **File Organization**
```
backend/
├── 🖥️  HOST-ONLY FILES:
│   ├── backend_docker_manager.py      # Container orchestration
│   ├── backend_docker_config.json     # Environment configuration
│   ├── docker-compose.*.yml           # Container orchestration
│   ├── Dockerfile.*                   # Container definitions
│   └── scripts/                       # Host utilities (NOT copied)
│       ├── setup_minio.py             # Manual MinIO setup
│       ├── check_docker_services.py   # Connectivity testing
│       └── cleanup_*.py               # Maintenance tools
│
└── 🐳 CONTAINER FILES:
    ├── start_app.py                   # Universal startup script
    ├── run_migrations.py              # Database migration runner
    ├── app/                           # Application code
    ├── migrations/                    # Alembic migrations
    └── alembic.ini                    # Migration configuration
```

## 🎊 **Success Output**

### **Container Startup**
When the container starts correctly, you'll see:
```
🐳 Starting Application Backend Container (Development)...
🔧 Environment: development
🔄 Development mode: True
🐛 Debug enabled: True

🪣 Checking MinIO setup...
✅ MinIO bucket 'app-files-dev' exists

🌐 Starting server on 0.0.0.0:8000

🔧 Development configuration:
   • Hot reload: True
   • Workers: 1
   • Log level: debug
```

### **Manual Migration**
When you run migrations separately:
```
$ docker exec -it app-backend-development python run_migrations.py

🗄️ Database Migration Runner
========================================
🔍 Checking database connection...
✅ Database connection successful

🔄 Running database migrations...
✅ Migrations completed successfully

🎉 Migration process completed successfully!
You can now start the application containers.
```

Your backend is now **production-ready with full migration control**! 🎯