# 🗄️ Database Container Infrastructure

Complete database infrastructure management for development, staging, and production environments.

> **✨ Simple & Clean:** All custom configurations are commented out by default. The containers work perfectly with their default settings, just like your original setup. Uncomment config files only if you need custom tuning.

> **🎯 Image Consistency:** All environments use **identical Docker images** with **pinned versions** (`postgres:15`, `redis:7`, `neo4j:5.19`, `qdrant/qdrant:v1.14.1`, `minio/minio:RELEASE.2025-05-24T17-08-30Z`) for proven stability and true environment parity.

## 🚀 Quick Start

### 1. Start Development Environment ⚡ INSTANT SETUP!
```bash
cd backend/docker/database
python db_manager.py start --env=dev  # Works immediately - no setup required!
```
> 🎉 **No secrets to create!** Development passwords are already included for instant team collaboration.

### 2. Check Health
```bash
python db_manager.py health --env=dev
```

### 3. View Status
```bash
python db_manager.py status --env=dev
```

### 4. Stop Environment
```bash
python db_manager.py stop --env=dev
```

## 📊 Services & Ports

### Development Environment
| Service      | Port(s)      | Purpose                    | Access                          |
|--------------|--------------|----------------------------|---------------------------------|
| PostgreSQL   | 5433         | Primary database           | `postgresql://app_dev_user:password@localhost:5433/app_dev_db` |
| Redis        | 6380         | Cache & sessions           | `redis://:password@localhost:6380` |
| Neo4j        | 7475, 7688   | Graph database             | Browser: http://localhost:7475, Bolt: bolt://localhost:7688 |
| Qdrant       | 6335, 6336   | Vector database            | API: http://localhost:6335 |
| MinIO        | 9002, 9003   | Object storage             | API: http://localhost:9002, Console: http://localhost:9003 |

### Production Environment
| Service      | Port(s)      | Purpose                    |
|--------------|--------------|----------------------------|
| PostgreSQL   | 5432         | Primary database (standard port) |
| Redis        | 6379         | Cache & sessions (standard port) |
| Neo4j        | 7474, 7687   | Graph database (standard ports) |
| Qdrant       | 6333, 6334   | Vector database (standard ports) |
| MinIO        | 9000, 9001   | Object storage (standard ports) |

## 🔧 Database Manager Commands

### Environment Management
```bash
# Start all database containers
python db_manager.py start --env=dev

# Stop all containers
python db_manager.py stop --env=dev

# Restart all containers
python db_manager.py restart --env=dev

# Check container status
python db_manager.py status --env=dev

# Health check all services
python db_manager.py health --env=dev
```

### Monitoring & Logs
```bash
# View logs for all services
python db_manager.py logs --env=dev

# View logs for specific service
python db_manager.py logs --env=dev --service=postgres

# Follow logs in real-time
python db_manager.py logs --env=dev --service=redis --follow
```

### Backup & Recovery
```bash
# Backup all databases
python db_manager.py backup --env=dev

# Backup specific service
python db_manager.py backup --env=dev --service=postgres

# Alternative: Use automated backup script
./scripts/backup.sh dev

# Restore from backup
./scripts/restore.sh dev 20240101_120000

# Restore specific service
./scripts/restore.sh dev 20240101_120000 postgres

# Validate environment before deployment
python db_manager.py validate --env=dev

# Clean up old backups and resources
python db_manager.py cleanup --env=dev
```

### Health Monitoring
```bash
# Comprehensive health check
python db_manager.py health --env=dev

# Alternative: Detailed health script
./scripts/health_check.sh dev --detailed

# Quick health overview
./scripts/health_check.sh dev
```

## 🏗️ Architecture

### Environment Isolation
```
Development:     app_db_network_dev     (ports: 5433, 6380, 7475, 7688, 6335, 9002, 9003)
Staging:         app_db_network_staging (ports: 5434, 6381, 7476, 7689, 6337, 9004, 9005)
Production:      app_db_network_prod    (ports: 5432, 6379, 7474, 7687, 6333, 9000, 9001)
```

### Volume Management
Each environment has isolated volumes:
- `pgdata_dev` / `pgdata_staging` / `pgdata_prod`
- `redisdata_dev` / `redisdata_staging` / `redisdata_prod`
- `neo4jdata_dev` / `neo4jdata_staging` / `neo4jdata_prod`
- `qdrantdata_dev` / `qdrantdata_staging` / `qdrantdata_prod`
- `minio_data_dev` / `minio_data_staging` / `minio_data_prod`

## 🔐 Security

### Secrets Management
Passwords stored in separate files per environment:
```
secrets/dev/postgres_password.txt
secrets/dev/redis_password.txt
secrets/dev/neo4j_auth.txt
secrets/dev/minio_credentials.txt

secrets/staging/... (same structure)
secrets/prod/... (same structure)
```

### Container Security
- All containers run as non-root users
- `no-new-privileges` security option enabled
- File-based secrets (no plain text passwords)
- Network isolation per environment

## 📁 Directory Structure

```
backend/docker/database/
├── 📄 README.md                       # This file
├── 📄 db_config.json                  # Configuration
├── 🐍 db_manager.py                   # Management tool
├── 📄 docker-compose.dev.yml          # Development
├── 📄 docker-compose.staging.yml      # Staging
├── 📄 docker-compose.prod.yml         # Production
├── 📁 config/                        # Optional: Custom configurations (commented out by default)
│   ├── 📁 dev/                        # Dev configurations (optional)
│   ├── 📁 staging/                    # Staging configurations (optional)
│   └── 📁 prod/                       # Production configurations (optional)
├── 📁 secrets/
│   ├── 📁 dev/                        # Dev secrets
│   ├── 📁 staging/                    # Staging secrets
│   └── 📁 prod/                       # Production secrets
├── 📁 init-scripts/                  # Optional: Database initialization scripts (commented out)
│   ├── 📄 001-create-extensions.sql  # PostgreSQL extensions (optional)
│   └── 📄 002-setup-databases.sql    # Database setup (optional)
├── 📁 backups/
│   ├── 📁 dev/
│   ├── 📁 staging/
│   └── 📁 prod/
└── 📁 scripts/
    ├── 🔧 backup.sh                   # Automated backup script
    ├── 🔧 restore.sh                  # Database restore script
    └── 🔧 health_check.sh             # Comprehensive health monitoring
```

## 🔄 Backend Application Integration

Your backend application should use corresponding environment files:

### Development
```bash
# backend/.env.dev
DATABASE_URL=postgresql://app_dev_user:dev_password@localhost:5433/app_dev_db
REDIS_URL=redis://:dev_redis_password@localhost:6380
NEO4J_URI=bolt://localhost:7688
QDRANT_URL=http://localhost:6335
MINIO_ENDPOINT=localhost:9002
```

### Production
```bash
# backend/.env.prod
DATABASE_URL=postgresql://app_prod_user:strong_password@localhost:5432/app_prod_db
REDIS_URL=redis://:strong_redis_password@localhost:6379
NEO4J_URI=bolt://localhost:7687
QDRANT_URL=http://localhost:6333
MINIO_ENDPOINT=localhost:9000
```

## 🚀 Deployment Workflow

### Development
```bash
# 1. Start database infrastructure
cd backend/docker/database
python db_manager.py start --env=dev

# 2. Start backend application (in separate terminal)
cd backend
export $(cat .env.dev | xargs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
# 1. Validate environment
python db_manager.py validate --env=prod

# 2. Create safety backup
python db_manager.py backup --env=prod

# 3. Start database infrastructure
python db_manager.py start --env=prod

# 4. Check health
python db_manager.py health --env=prod

# 5. Start backend application
cd ../../ && export $(cat .env.prod | xargs) && uvicorn app.main:app
```

## 🔧 Manual Docker Commands (Alternative)

If you prefer direct Docker commands:

```bash
# Development
docker-compose -f docker-compose.dev.yml --env-file env.dev up -d

# Check status
docker-compose -f docker-compose.dev.yml --env-file env.dev ps

# Stop
docker-compose -f docker-compose.dev.yml --env-file env.dev down
```

## 🔐 Security & Git Management

### **Git Ignore Protection**
All sensitive files are automatically protected by `.gitignore`:

```bash
# 🚨 NEVER committed to git:
secrets/staging/      # Staging passwords (secure)
secrets/prod/         # Production passwords (secure)
backups/              # Database backup files  
*.sql, *.dump, *.rdb  # Database exports
*.log                 # Log files
.env*                 # Environment files

# ✅ Safe to commit:
secrets/dev/          # Development passwords (generic, for easy setup)
README.md             # Documentation
db_manager.py         # Management scripts
docker-compose*.yml   # Container definitions
.gitkeep             # Directory structure
```

### **Directory Structure Maintenance**
- **`.gitkeep` files** maintain empty directories in git
- **Development secrets** are committed for easy team setup
- **Staging/Production secrets** are ignored for security
- **Backup directories** exist but all backup files are ignored

### **Best Practices**
1. **Development secrets** - Generic/simple passwords, safe to commit
2. **Staging/Production secrets** - Never committed, each environment has secure passwords
3. **Backup files stay local** - Too large and sensitive for git
4. **Easy onboarding** - New developers can start immediately with dev environment

## ❓ Troubleshooting

### Port Conflicts
If you get port conflicts:
1. Check what's using the ports: `netstat -tulpn | grep :5433`
2. Stop conflicting services
3. Or change ports in `env.dev` file

### Container Won't Start
1. Check logs: `python db_manager.py logs --env=dev --service=postgres`
2. Validate environment: `python db_manager.py validate --env=dev`
3. Check secrets exist: `ls -la secrets/dev/`

### Permission Issues
Make sure secrets files exist and have correct permissions:
```bash
chmod 600 secrets/dev/*.txt
```

### Missing Staging/Production Secrets
Development secrets are included, but you'll need to create staging/production secrets:

```bash
# Create staging secrets (use strong passwords!)
echo "strong_staging_postgres_password" > secrets/staging/postgres_password.txt
echo "strong_staging_redis_password" > secrets/staging/redis_password.txt
echo "neo4j/strong_staging_neo4j_password" > secrets/staging/neo4j_auth.txt
echo -e "stagingadmin\nstrong_staging_minio_password" > secrets/staging/minio_credentials.txt

# Create production secrets (use ultra-strong passwords!)
echo "ultra_secure_prod_postgres_password" > secrets/prod/postgres_password.txt
echo "ultra_secure_prod_redis_password" > secrets/prod/redis_password.txt
echo "neo4j/ultra_secure_prod_neo4j_password" > secrets/prod/neo4j_auth.txt
echo -e "prodadmin\nultra_secure_prod_minio_password" > secrets/prod/minio_credentials.txt

# Set proper permissions
chmod 600 secrets/staging/*.txt secrets/prod/*.txt
```

### Quick Development Start
Since dev secrets are committed, you can start immediately:
```bash
git clone your-repo
cd backend/docker/database
python db_manager.py start --env=dev  # Works immediately!
```

## 🎯 Next Steps

1. ✅ **Staging/production environments** - Complete with separate compose files
2. ✅ **Enhanced backup system** - Comprehensive backup/restore for all services  
3. ✅ **Security hardening** - File-based secrets and git protection
4. **Monitoring integration** with Prometheus/Grafana (optional)
5. **SSL/TLS configuration** for production (optional)
6. **High availability setup** with replicas (optional)

## 📞 Support

For issues or questions:
1. Check container logs: `python db_manager.py logs --env=dev`
2. Validate environment: `python db_manager.py validate --env=dev`
3. Check Docker status: `docker info`
4. Review configuration: `cat db_config.json`
