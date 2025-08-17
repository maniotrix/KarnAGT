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

### **3. Run Migrations Manually (RECOMMENDED APPROACH)**
```bash
# Using one-time container (RECOMMENDED)
cd backend
docker-compose -f docker-compose.dev.yml run --rm app-backend-dev python run_migrations.py

# Alternative: Using existing container (less reliable)
# docker exec -it app-backend-development python run_migrations.py
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

# 3. Run migrations manually (RECOMMENDED)
docker-compose -f docker-compose.dev.yml run --rm app-backend-dev python run_migrations.py

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

# 3. Run migrations manually (PRODUCTION SAFE)
docker-compose -f docker-compose.prod.yml run --rm app-backend-prod python run_migrations.py

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

**Run migrations using one-time containers (RECOMMENDED):**
```bash
# Development
cd backend
docker-compose -f docker-compose.dev.yml run --rm app-backend-dev python run_migrations.py

# Staging  
docker-compose -f docker-compose.staging.yml run --rm app-backend-staging python run_migrations.py

# Production
docker-compose -f docker-compose.prod.yml run --rm app-backend-prod python run_migrations.py
```

**Alternative - Run migrations inside existing container:**
```bash
# Development (if container is already running)
docker exec -it app-backend-development python run_migrations.py

# Staging  
docker exec -it app-backend-staging python run_migrations.py

# Production
docker exec -it app-backend-production python run_migrations.py
```

**Check migration status:**
```bash
# Using one-time container
cd backend
docker-compose -f docker-compose.dev.yml run --rm app-backend-dev alembic current
docker-compose -f docker-compose.dev.yml run --rm app-backend-dev alembic history --verbose

# Or using existing container
docker exec -it app-backend-development alembic current
docker exec -it app-backend-development alembic history --verbose
```

**Rollback migrations (if needed):**
```bash
# DANGER: This can cause data loss
# Using one-time container (RECOMMENDED)
docker-compose -f docker-compose.dev.yml run --rm app-backend-dev alembic downgrade -1

# Or using existing container
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

#### **1. Frontend Health Check Failures**
```
❌ Container shows as "unhealthy" despite running correctly
```
**Common Causes & Solutions:**

**A) BusyBox wget compatibility issues:**
```bash
# ❌ WRONG (BusyBox wget doesn't support these flags):
healthcheck:
  test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000"]

# ✅ CORRECT (Use curl instead):
healthcheck:
  test: ["CMD", "curl", "-f", "http://127.0.0.1:3000"]
```

**B) localhost vs 127.0.0.1 in containers:**
```bash
# Test both inside container to identify the issue
docker exec container-name curl -f http://localhost:3000    # May fail
docker exec container-name curl -f http://127.0.0.1:3000   # Usually works

# Use 127.0.0.1 for health checks in containers
healthcheck:
  test: ["CMD", "curl", "-f", "http://127.0.0.1:3000"]
```

**C) Check what ports nginx/service is actually listening on:**
```bash
docker exec container-name netstat -tuln
# Should show: 0.0.0.0:3000   LISTEN
```

#### **2. Traefik IP Caching and Routing Issues**
```
❌ Error while Peeking first byte error="read tcp 172.19.0.8:8000->172.19.0.1:54574: i/o timeout"
❌ Can't access frontend through https://localhost/
```
**Root Cause:** Traefik caches container IP addresses, but container restarts assign new IPs.

**Solution A - Restart Traefik (Quick Fix):**
```bash
docker restart traefik-dev
# Forces Traefik to rediscover all container IPs
```

**Solution B - Start containers together (Recommended):**
```bash
# Start all containers from the same compose file
cd backend && docker-compose -f docker-compose.dev.yml up -d
# This ensures Traefik and backend start together
```

**Debug Traefik routing:**
```bash
# Check Traefik dashboard
curl http://localhost:8080/dashboard/

# Check container network IPs
docker network inspect dev-network --format '{{json .Containers}}'

# View Traefik logs
docker logs traefik-dev --tail 20
```

#### **3. Container Startup Order Issues**
```
❌ Frontend can't connect to backend through Traefik
❌ Services started but routing not working
```
**Problem:** Starting containers from different compose files causes timing issues.

**Solution - Proper startup sequence:**
```bash
# 1. Start main infrastructure (backend + traefik)
cd backend && docker-compose -f docker-compose.dev.yml up -d

# 2. Then start frontend (connects to existing network)
cd frontend/chatgpt-frontend && docker-compose -f docker-compose.dev.yml up -d

# 3. If routing fails, restart Traefik
docker restart traefik-dev
```

#### **4. Database Connection Failed**
```
❌ Database connection failed: connection refused
```
**Common Causes & Solutions:**

**A) Database containers not running:**
```bash
# Make sure database containers are running
cd backend/docker/database
python db_manager.py start --env=dev
python db_manager.py health --env=dev
```

**B) Using localhost instead of service names:**
```bash
# ❌ WRONG (Will fail in containers):
DATABASE_URL=postgresql://user:pass@localhost:5433/db

# ✅ CORRECT (Container-to-container communication):
DATABASE_URL=postgresql://user:pass@postgres:5432/db
```

**C) Backend container not connected to database network:**
```bash
# Check if backend is connected to database network
docker network ls | grep app_db_network
python backend_docker_manager.py validate --dev
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

### **🐳 Container-to-Container Communication (Service Discovery)**
**Backend containers use these for database connections:**

| Service | Service Name | Internal Port | All Environments |
|---------|--------------|---------------|-------------------|
| **PostgreSQL** | `postgres` | 5432 | `postgres:5432` |
| **Redis** | `redis` | 6379 | `redis:6379` |
| **Neo4j** | `neo4j` | 7687 | `neo4j:7687` |
| **Qdrant** | `qdrant` | 6333 | `qdrant:6333` |
| **MinIO** | `minio` | 9000 | `minio:9000` |

### **🖥️ External Access Ports (Host to Container)**
**Use these for admin tools and external connections:**

| Environment | Backend | PostgreSQL | Redis | Neo4j | Qdrant | MinIO |
|-------------|---------|------------|-------|-------|--------|-------|
| **Development** | 8000 | 5433 | 6380 | 7688 | 6335 | 9002 |
| **Staging** | 8000 | 5434 | 6381 | 7689 | 6337 | 9004 |
| **Production** | 8000 | 5432 | 6379 | 7687 | 6333 | 9000 |

**🔑 Key Networking Concepts:**
- **Service Discovery**: Containers communicate using service names (e.g., `postgres:5432`)
- **External Access**: Host machine connects using `localhost:port` (e.g., `localhost:5433`)
- **Same Internal Ports**: All environments use identical internal ports for consistency
- **Different External Ports**: Each environment uses different external ports to avoid conflicts

## 🎯 **Best Practices**

### **Development**
```bash
# Development workflow:
1. python db_manager.py start --env=dev                     # Databases first
2. python backend_docker_manager.py start --dev            # Backend container
3. docker-compose -f docker-compose.dev.yml run --rm app-backend-dev python run_migrations.py  # Manual migrations (RECOMMENDED)
```

### **Production**
```bash
# Production deployment checklist:
1. python db_manager.py validate --env=prod                # Validate setup
2. python db_manager.py backup --env=prod                  # Backup existing data
3. python db_manager.py start --env=prod                   # Start databases
4. python backend_docker_manager.py start --prod --build   # Deploy container
5. docker-compose -f docker-compose.prod.yml run --rm app-backend-prod python run_migrations.py  # Manual migrations (PRODUCTION SAFE)
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
When you run migrations separately using the recommended approach:
```
$ cd backend
$ docker-compose -f docker-compose.dev.yml run --rm app-backend-dev python run_migrations.py

✅ Loaded environment from: /app/.env
✅ Encoding defaults set
🗄️ Database Migration Runner
========================================
🔍 Checking database connection...
✅ Database connection successful

🔄 Running database migrations...
==================================================
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0c8c6f5381e8, Initial migration
==================================================
✅ Migrations completed successfully

🎉 Migration process completed successfully!
You can now start the application containers.
```

**Why This Approach Works Better:**
- ✅ **Automatic Network Connection** - Uses Docker Compose networks automatically
- ✅ **Environment Inheritance** - Uses same environment as your app containers
- ✅ **Clean Execution** - Container is removed after completion (`--rm`)
- ✅ **Production Safe** - Same approach works across all environments

Your backend is now **production-ready with full migration control**! 🎯

---

## 🛡️ **Traefik Security Headers Middleware**

### **📁 File Structure**
```
backend/
├── docker-compose.dev.yml
├── docker-compose.staging.yml
├── docker-compose.prod.yml
└── traefik/
    └── middlewares.yml  ← Global security headers
```

### **🔧 Configuration**
Security headers are applied globally using Traefik's file provider:

**Middleware Definition (`backend/traefik/middlewares.yml`):**
```yaml
http:
  middlewares:
    security-headers:
      headers:
        browserXssFilter: true
        contentTypeNosniff: true
        frameDeny: true
        sslRedirect: true
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
```

**Docker Compose Configuration:**
```yaml
traefik:
  volumes:
    - ./traefik:/etc/traefik:ro  # Load middleware files
  command:
    - --providers.file.directory=/etc/traefik
    - --providers.file.watch=true
    # Apply globally to all HTTPS routes
    - --entrypoints.websecure.http.middlewares=security-headers@file
```

### **✨ Benefits**
- 🔒 **Automatic Security:** All HTTPS routes get security headers
- 🔄 **Hot Reload:** Edit `middlewares.yml` without restart
- 🎯 **DRY Principle:** Define once, apply everywhere
- 🏭 **Production Grade:** Industry standard approach

### **🧪 Testing Security Headers**
```bash
# Test any HTTPS endpoint
curl -I https://localhost/api/v1/health

# Should return headers like:
# X-Xss-Protection: 1; mode=block
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Your application now has enterprise-level security headers! 🛡️**