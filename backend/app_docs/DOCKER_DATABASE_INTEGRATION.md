# 🔗 Backend + Database Container Integration

This document shows how to use your backend application with the database container infrastructure.

## 🎯 **Database Container Environment**

Your database containers are managed by **minimal configuration** and **environment-specific Docker Compose files**:

```
Modern Database Infrastructure with Traefik
├── db_config.json              (Minimal configuration - 28 lines, only essentials)
├── docker-compose.dev.yml      (Development containers + Traefik)
├── docker-compose.staging.yml  (Staging containers + Traefik)  
└── docker-compose.prod.yml     (Production containers + Traefik)
├── Unified Networks: dev-network, staging-network, prod-network
└── Traefik Integration: SSL/TLS, routing, security headers
```

**Key Features:**
- ✅ **Traefik Reverse Proxy** - Modern SSL/TLS termination and routing
- ✅ **Unified Network Architecture** - Single network per environment for simplicity
- ✅ **MinIO Dual Endpoint Solution** - Fixed presigned URL browser access issues
- ✅ **Minimal Configuration** - Clean `db_config.json` with no unused resource profiles
- ✅ **Configuration-Driven** - `db_manager.py` reads compose file paths from config
- ✅ **No Resource Limits** - Services can use whatever resources they need
- ✅ **Mixed Security Model** - System users where appropriate, root where needed for compatibility

## 🚀 **Complete Deployment Workflows**

### **Development Environment**
```bash
# 1. Start database containers
cd backend/docker/database
python db_manager.py start --env=dev

# 2. Verify database health
python db_manager.py health --env=dev

# 3. Start your backend application (in new terminal)
cd backend
# Option A: Container-based development (recommended)
python backend_docker_manager.py start --dev

# Option B: Local development 
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Run database migrations manually (ALWAYS MANUAL)
# IMPORTANT: Must be in backend directory for networking
cd backend
docker-compose -f docker-compose.dev.yml run --rm app-backend-dev python run_migrations.py
```

### **Staging Environment**
```bash
# 1. Start staging database containers  
cd backend/docker/database
python db_manager.py start --env=staging

# 2. Verify health
python db_manager.py health --env=staging

# 3. Start backend with staging config
cd backend
python backend_docker_manager.py start --staging

# 4. Run database migrations manually (PRODUCTION SAFE)
# IMPORTANT: Must be in backend directory for networking
cd backend
docker-compose -f docker-compose.staging.yml run --rm app-backend-staging python run_migrations.py
```

### **Production Environment**
```bash
# 1. Validate production environment
cd backend/docker/database
python db_manager.py validate --env=prod

# 2. Create safety backup
python db_manager.py backup --env=prod

# 3. Start production containers
python db_manager.py start --env=prod

# 4. Verify all services are healthy
python db_manager.py health --env=prod

# 5. Start backend with production config
cd backend
python backend_docker_manager.py start --prod

# 6. Run database migrations manually (CRITICAL - PRODUCTION SAFE)  
# IMPORTANT: Must be in backend directory for networking
cd backend
docker-compose -f docker-compose.prod.yml run --rm app-backend-prod python run_migrations.py

# 7. Verify application health
python backend_docker_manager.py health --prod
```

## 🔌 **Connection Matrix**

### **🐳 Container-to-Container (Docker Service Discovery)**
**Use these for your backend application environment files:**

| Service | All Environments | Backend Variable | Internal Port |
|---------|-------------------|------------------|---------------|
| **PostgreSQL** | `postgres:5432` | `DATABASE_URL` | 5432 |
| **Redis** | `redis:6379` | `REDIS_URL` | 6379 |
| **Neo4j** | `neo4j:7687` | `NEO4J_URL` | 7687 |
| **Qdrant** | `qdrant:6333` | `QDRANT_URL` | 6333 |
| **MinIO Operations** | `minio:9000` | `S3_ENDPOINT_URL` | 9000 |
| **MinIO Presigned URLs** | External Endpoint | `S3_PRESIGNED_URL_ENDPOINT` | Via Traefik |

### **🖥️ External Access (Admin Tools from Host)**
**Use these for database administration from your local machine:**

| Service | Development | Staging | Production |
|---------|-------------|---------|------------|
| **PostgreSQL** | `localhost:5433` | `localhost:5434` | `localhost:5432` |
| **Redis** | `localhost:6380` | `localhost:6381` | `localhost:6379` |
| **Neo4j** | `localhost:7688` | `localhost:7689` | `localhost:7687` |
| **Qdrant** | `localhost:6335` | `localhost:6337` | `localhost:6333` |
| **MinIO** | `localhost:9002` | `localhost:9004` | `localhost:9000` |

## 🔐 **Security & Credentials**

### **Development** (Relaxed Security)
- Simple passwords for easy development
- Debug logging enabled
- CORS permissive
- Email verification disabled

### **Staging** (Production-like Security)
- Strong passwords
- HTTPS cookies
- Restricted CORS
- Email verification enabled
- Production logging levels

### **Production** (Maximum Security)
- Ultra-strong passwords
- All security features enabled
- Strict CORS and domain restrictions
- Minimal logging for performance

## 📊 **Database Credentials Reference**

### **🐳 Backend Application Environment (Docker Service Discovery)**
**Use these in your `.env.docker.app.*` files:**

```bash
# PostgreSQL (Internal Port - All Environments)
DATABASE_URL=postgresql://app_dev_user:dev_postgres_password_123@postgres:5432/app_dev_db

# Redis (Internal Port - All Environments)
REDIS_URL=redis://redis:6379/0

# Neo4j (Internal Port - All Environments)  
NEO4J_URL=bolt://neo4j:7687
NEO4J_PASSWORD=dev_neo4j_password_123

# MinIO Dual Endpoint Configuration (CRITICAL UPDATE)
S3_ENDPOINT_URL=http://minio:9000                    # Internal operations
S3_PRESIGNED_URL_ENDPOINT=http://localhost:9000     # Development browser access
# S3_PRESIGNED_URL_ENDPOINT=https://files.yourdomain.com  # Production browser access
S3_ACCESS_KEY_ID=devuser
S3_SECRET_ACCESS_KEY=YOUR_DEV_S3_SECRET_KEY

# Qdrant (Internal Port - All Environments)
QDRANT_URL=http://qdrant:6333
```

### **🖥️ External Access (Admin Tools from Host)**
**Use these for database administration:**

```bash
# Development Environment
postgresql://app_dev_user:dev_postgres_password_123@localhost:5433/app_dev_db
redis://localhost:6380/0
bolt://localhost:7688
http://localhost:6335  # Qdrant
http://localhost:9002  # MinIO
```


## 🔄 **Environment Management**

### **Database Environment Management**
Database containers are managed independently from your backend application:

```bash
# Start development database containers
cd backend/docker/database
python db_manager.py start --env=dev

# Start staging database containers
python db_manager.py start --env=staging

# Start production database containers
python db_manager.py start --env=prod
```

### **Verify Your Configuration**
```python
# In your backend application, add this verification endpoint
@app.get("/health/database")
async def database_health():
    return {
        "environment": os.getenv("ENVIRONMENT"),
        "postgres_host": os.getenv("DATABASE_URL").split("@")[1].split("/")[0],  # Should show "postgres:5432"
        "redis_host": os.getenv("REDIS_URL").split("@")[1].split("/")[0],        # Should show "redis:6379"
        "neo4j_host": os.getenv("NEO4J_URL").replace("bolt://", ""),            # Should show "neo4j:7687"
        "qdrant_host": os.getenv("QDRANT_URL").replace("http://", ""),          # Should show "qdrant:6333"
        "minio_host": os.getenv("S3_ENDPOINT_URL").replace("http://", "")       # Should show "minio:9000"
    }
```

**✅ Expected Output (Container-to-Container Communication):**
```json
{
    "environment": "development",
    "postgres_host": "postgres:5432",
    "redis_host": "redis:6379", 
    "neo4j_host": "neo4j:7687",
    "qdrant_host": "qdrant:6333",
    "minio_host": "minio:9000"
}
```

## 🔗 **MinIO Internal/External URL Architecture**

### **Modern Container Networking Solution**
MinIO now uses **clean internal/external URL separation** without complex workarounds:

### **🎯 Smart URL Selection**
The file proxy automatically selects the correct URL based on the caller:

```python
# File proxy endpoints (app/api/v1/file_proxy.py)
if isinstance(auth, ServiceAuth):
    # Backend service calls - use internal container networking
    url = await storage.get_internal_presigned_url(key)  # http://minio:9000
else:
    # Browser requests - use external proxy URLs
    url = await storage.get_presigned_url(key)           # https://localhost:9000
```

### **🏗️ Storage Service Architecture**  
```python
# Storage service has dual URL capability
class S3StorageBackend:
    def __init__(self):
        # Internal operations client (container-to-container)
        self.s3_client = boto3.client('s3', endpoint_url='http://minio:9000')
        
        # External presigned URLs client (browser access)
        self.s3_presigned_client = boto3.client('s3', endpoint_url='https://localhost:9000')
```

### **Environment Configuration**
```bash
# Development (All environments use HTTPS for browser access)
S3_ENDPOINT_URL=http://minio:9000                    # Internal container operations  
S3_PRESIGNED_URL_ENDPOINT=https://localhost:9000    # Browser access via Traefik

# Staging
S3_ENDPOINT_URL=http://minio:9000                           # Internal container operations
S3_PRESIGNED_URL_ENDPOINT=https://files-staging.yourdomain.com  # Browser access via load balancer

# Production  
S3_ENDPOINT_URL=http://minio:9000                        # Internal container operations
S3_PRESIGNED_URL_ENDPOINT=https://files.yourdomain.com  # Browser access via load balancer
```

### **Why This Architecture is Superior**
- ✅ **Pure Docker Networking** - No `extra_hosts` or SSL workarounds needed
- ✅ **Zero SSL Overhead** - Internal service calls use direct HTTP container communication
- ✅ **Secure Browser Access** - External URLs go through Traefik with proper SSL termination
- ✅ **Automatic Caller Detection** - ServiceAuth vs User authentication determines URL type
- ✅ **Clean Separation of Concerns** - Internal services vs external user access handled separately
- ✅ **Production Ready** - Same architecture works across dev/staging/prod environments

## 📋 **Minimal Configuration Benefits**

The database infrastructure now uses a **clean, minimal configuration approach**:

### **Before (Complex Setup)**
```json
// Old db_config.json: 107 lines with unused resource profiles
{
  "resource_profiles": {
    "minimal": {"postgres": {"memory": "512M", "cpus": "0.5"}},
    "medium": {"postgres": {"memory": "2G", "cpus": "1"}},
    // ... 80+ more unused lines
  }
}
```

### **Now (Minimal & Clean)**
```json
// New db_config.json: 28 lines, only essentials
{
  "supported_environments": ["dev", "staging", "prod"],
  "environments": {
    "dev": {"compose_file": "docker-compose.dev.yml"},
    "staging": {"compose_file": "docker-compose.staging.yml"}, 
    "prod": {"compose_file": "docker-compose.prod.yml"}
  },
  "settings": {
    "docker_compose_timeout": 300,
    "health_check_timeout": 120,
    "backup_parallel_jobs": 2
  },
  "required_secrets": ["postgres_password.txt", "neo4j_auth.txt", "minio_user.txt", "minio_password.txt"]
}
```

### **What Changed**
- ✅ **79 fewer lines** - Removed all unused resource profiles and service configs
- ✅ **Configuration-driven compose files** - `db_manager.py` reads file paths from config instead of hardcoding
- ✅ **No resource limits** - Services can use whatever memory/CPU they need (no startup failures)
- ✅ **Flexible setup** - Easy to add new environments or change compose file names
- ✅ **Essential only** - Contains only what's actually used by the system

## 🎯 **Environment Parity Achievement**

✅ **Same Docker Images**: All environments use identical database versions
✅ **Same Container Structure**: Identical volumes, networks, health checks  
✅ **Same Operational Commands**: `db_manager.py` works identically everywhere
✅ **Modern Reverse Proxy**: Traefik integration across all environments
✅ **Unified Network Architecture**: Single network per environment for simplicity
✅ **MinIO Dual Endpoint**: Consistent presigned URL solution everywhere
✅ **Environment-Specific Settings**: Only ports, passwords, and resources differ
✅ **Perfect Coordination**: Database containers use consistent, conflict-free ports

## 🚀 **Ready to Use!**

Your backend application will now:
- **Connect to the correct databases** based on your backend environment configuration
- **Use appropriate security settings** per environment
- **Scale resources properly** (dev uses less memory, prod uses more)
- **Behave identically** across all environments (same database versions, same features)

**This achieves true environment parity** - database containers are identical across environments, only ports, passwords, and resources differ!

## 🔧 **Docker Network Troubleshooting**

### **Container Network Communication Issues**

#### **Traefik IP Caching Problems**
```
❌ Error while Peeking first byte error="read tcp 172.19.0.X:8000->172.19.0.1:XXXXX: i/o timeout"
```

**Root Cause:** When containers restart, Docker assigns new IP addresses, but Traefik continues trying to reach the old cached IPs.

**Quick Fix:**
```bash
docker restart traefik-dev
# Forces Traefik to rediscover all container IPs on dev-network
```

**Best Practice:**
```bash
# Start backend + Traefik together to avoid IP mismatches
cd backend && docker-compose -f docker-compose.dev.yml up -d
```

#### **Frontend-Backend Routing Issues**
```
❌ Frontend gets 404 errors, no logs in backend container
❌ CORS errors: localhost:8000 vs https://localhost origin mismatch
```

**Root Cause:** Traefik entrypoint configuration mismatch between frontend and backend.

**Diagnostic Steps:**
```bash
# 1. Check if requests reach backend
docker logs app-backend-development --tail 20

# 2. If no logs, check entrypoint configuration
grep "entrypoints.*websecure" backend/docker-compose.dev.yml
grep "entrypoints.*websecure" frontend/chatgpt-frontend/docker-compose.dev.yml

# 3. Both should use websecure entrypoint for HTTPS (port 443)
```

**Solution:**
```yaml
# Ensure backend uses same entrypoint as frontend
- "traefik.http.routers.backend.entrypoints=websecure"  # Not "api"
- "traefik.http.routers.frontend.entrypoints=websecure" # Match this
```

**Environment Variable Issues:**
```bash
# Frontend calling wrong API URLs due to build-time environment variables
# Check if frontend uses correct VITE_API_URL
docker exec app-frontend-development printenv VITE_API_URL
# Should show: https://localhost

# Check built assets don't contain hardcoded localhost:8000
docker exec app-frontend-development grep -r "localhost:8000" /usr/share/nginx/html/assets/

# If found, frontend needs rebuild with correct build arguments:
cd frontend/chatgpt-frontend
docker-compose -f docker-compose.dev.yml build --no-cache
```

#### **Network Connectivity Debugging**
```bash
# Check network topology and IPs
docker network inspect dev-network --format '{{json .Containers}}'

# Test inter-container connectivity  
docker exec traefik-dev ping -c 2 app-backend-development
docker exec traefik-dev ping -c 2 app-frontend-development

# Check if containers are on the correct network
docker ps --format "table {{.Names}}\t{{.Networks}}"
```

#### **Frontend-Backend Communication Through Traefik**
```
❌ Frontend can't reach backend APIs
❌ CORS errors or 404 responses
```

**Common Issues:**
1. **Traefik routing rules conflict** - Check priority settings
2. **SSL redirect loops** - Verify security headers middleware
3. **Container startup order** - Frontend starts before backend is ready

**Debug Steps:**
```bash
# 1. Verify Traefik dashboard shows all services
curl http://localhost:8080/api/rawdata | jq '.http.services'

# 2. Test direct access (bypass Traefik)
docker exec app-backend-development curl -f http://127.0.0.1:8000/api/v1/health

# 3. Test Traefik routing
curl -H "Host: localhost" http://localhost:8000/api/v1/health  # Backend
curl -H "Host: localhost" http://localhost/  # Frontend

# 4. Check security headers middleware
curl -I https://localhost/api/v1/health 2>&1 | grep -E "(X-|Strict-)"
```

### **Container Health Check Issues**

#### **Health Checks Failing Inside Containers**
```
❌ Container shows "unhealthy" despite service running
```

**BusyBox vs Full Linux containers:**
```bash
# Identify container base image
docker exec container-name cat /etc/os-release

# BusyBox containers (Alpine/nginx):
# - Limited wget support
# - Use curl instead of wget
# - Use 127.0.0.1 instead of localhost

# Full Linux containers:
# - Full wget/curl support  
# - localhost usually works fine
```

**Testing health checks manually:**
```bash
# Test the exact health check command
docker exec container-name curl -f http://127.0.0.1:3000
docker exec container-name wget --spider http://127.0.0.1:3000

# Check what's actually listening
docker exec container-name netstat -tuln
```

### **Multi-Compose File Architecture**

**Understanding Your Setup:**
```
backend/docker-compose.dev.yml          ← Contains: Traefik + Backend + Databases
frontend/chatgpt-frontend/docker-compose.dev.yml  ← Contains: Frontend only
```

**Network Connection Strategy:**
```yaml
# Backend compose creates the network
networks:
  dev-network:
    driver: bridge
    name: dev-network

# Frontend compose connects to existing network  
networks:
  dev-network:
    external: true
    name: dev-network
```

**Startup Order Best Practices:**
```bash
# 1. Start infrastructure first (creates network + traefik)
cd backend && docker-compose -f docker-compose.dev.yml up -d

# 2. Wait for Traefik to be ready
docker logs traefik-dev --tail 5

# 3. Start frontend (connects to existing network)
cd frontend/chatgpt-frontend && docker-compose -f docker-compose.dev.yml up -d

# 4. If routing issues persist, restart Traefik
docker restart traefik-dev
```

## 🚨 **Migration Troubleshooting**

### **Common Directory Issues**

**Problem:** Migration commands fail with network errors
```bash
❌ Database connection failed: [Errno -2] Name or service not known
```

**Root Cause:** Migration container not connected to Docker network

**Solution:** Always run migration commands from the `backend/` directory
```bash
# ❌ Wrong: From project root
docker-compose -f docker-compose.prod.yml run --rm app-backend-prod python run_migrations.py

# ✅ Correct: From backend directory
cd backend
docker-compose -f docker-compose.prod.yml run --rm app-backend-prod python run_migrations.py
```

### **Why Directory Matters**

1. **Docker-compose networking** → Requires correct working directory for network resolution
2. **Service name resolution** → Database hostnames (`postgres`, `redis`) only exist within networks
3. **Volume mounts** → Migration files and configuration must be accessible
4. **Environment inheritance** → Container gets same config as production app

### **Alternative Solutions**

If you must run from different directory, use absolute path to compose file:
```bash
# From anywhere - specify full path to compose file
docker-compose -f /full/path/to/backend/docker-compose.prod.yml run --rm app-backend-prod python run_migrations.py
```

Or use direct docker run with network:
```bash
# Direct docker run with network (less preferred)  
docker run --rm --network prod-network backend-app-backend-prod:latest python run_migrations.py
```

### **Debugging Network Issues**

Check if container can reach database:
```bash
# Test network connectivity
cd backend
docker-compose -f docker-compose.prod.yml run --rm app-backend-prod ping postgres

# Check DNS resolution
docker-compose -f docker-compose.prod.yml run --rm app-backend-prod nslookup postgres

# List available networks
docker network ls

# Inspect specific network
docker network inspect prod-network
```

## 🔐 **Git Security & Team Collaboration**

### **🚨 Smart Security Protection**
Sensitive files are **automatically protected** by `.gitignore`:
- ✅ **Development secrets** (`secrets/dev/`) - **Committed for easy setup**
- ❌ **Staging secrets** (`secrets/staging/`) - **Protected from git**
- ❌ **Production secrets** (`secrets/prod/`) - **Protected from git**
- ❌ **Backup files** (`backups/`) - Database backups ignored  
- ❌ **Backend environment files** (`.env*`) - Your backend app credentials ignored
- ❌ **Database exports** (`*.sql`, `*.dump`) - Data exports ignored

### **🚀 Instant Team Setup**
When a teammate clones the repo:
1. **Gets everything for dev** - Structure, compose files, AND development secrets
2. **Starts immediately** - No setup required for development
3. **Creates secure secrets** - Only for staging/production when needed

```bash
# New team member setup - INSTANT START!
git clone your-repo
cd backend/docker/database

# Development works immediately (secrets already included)
python db_manager.py start --env=dev  # ✅ Works right away!

# Later, when they need staging/production:
# Create secure staging secrets
echo "secure_staging_password" > secrets/staging/postgres_password.txt
# ... other staging secrets

# Create ultra-secure production secrets  
echo "ultra_secure_production_password" > secrets/prod/postgres_password.txt
# ... other production secrets
```

### **🏢 Production Security**
- **Development secrets** are **generic and safe** to commit (easy team collaboration)
- **Staging/Production secrets** are **never committed** (secure and environment-specific)
- **Each environment** has separate, appropriate security levels
- **Infrastructure code** is shared, **sensitive data** stays protected
- **Deployment scripts** work the same way everywhere

## 🎊 **Perfect Developer Experience Achieved!**

### **✅ What You Get**
1. **🧹 Minimal Configuration** - Clean 28-line config vs complex 107-line setup
2. **📖 Configuration-Driven** - No hardcoded paths, reads from config
3. **🚀 Instant Development** - Clone repo, start containers immediately
4. **🔒 Smart Security** - Dev secrets shared, staging/prod protected  
5. **🎯 Environment Parity** - **Identical Docker images** across all environments
6. **🤝 Team Friendly** - No onboarding friction for new developers
7. **🏢 Production Ready** - Secure staging/prod with strong passwords
8. **📊 Comprehensive Backup** - All 5 database services protected
9. **⚙️ Professional Automation** - One tool manages all environments
10. **💪 No Resource Limits** - Services use whatever resources they need (no startup failures)

### **🎯 Image Consistency Principle**
- **Same pinned images everywhere**: `postgres:15`, `redis:7`, `neo4j:5.19`, `qdrant/qdrant:v1.14.1`, `minio/minio:RELEASE.2025-05-24T17-08-30Z`
- **Matches your running versions**: No migration issues, exact version consistency
- **True environment parity**: Containers behave identically, only configs change
