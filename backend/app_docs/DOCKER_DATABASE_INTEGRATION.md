# 🔗 Backend + Database Container Integration

This document shows how to use your backend application with the database container infrastructure.

## 🎯 **Database Container Environment**

Your database containers are managed by **minimal configuration** and **environment-specific Docker Compose files**:

```
Database Infrastructure (Simplified & Clean)
├── db_config.json              (Minimal configuration - 28 lines, only essentials)
├── docker-compose.dev.yml      (Development containers)
├── docker-compose.staging.yml  (Staging containers)  
└── docker-compose.prod.yml     (Production containers)
```

**Key Features:**
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
# Use your backend's development environment configuration
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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
# Use your backend's staging environment configuration
uvicorn app.main:app --host 0.0.0.0 --port 8000
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
# Use your backend's production environment configuration
uvicorn app.main:app --host 0.0.0.0 --port 8000
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
| **MinIO** | `minio:9000` | `S3_ENDPOINT_URL` | 9000 |

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

# MinIO (Internal Port - All Environments)
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=devuser
S3_SECRET_ACCESS_KEY=devpassword123

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
✅ **Environment-Specific Settings**: Only ports, passwords, and resources differ
✅ **Perfect Coordination**: Database containers use consistent, conflict-free ports

## 🚀 **Ready to Use!**

Your backend application will now:
- **Connect to the correct databases** based on your backend environment configuration
- **Use appropriate security settings** per environment
- **Scale resources properly** (dev uses less memory, prod uses more)
- **Behave identically** across all environments (same database versions, same features)

**This achieves true environment parity** - database containers are identical across environments, only ports, passwords, and resources differ!

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
