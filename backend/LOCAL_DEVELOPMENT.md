# 🚀 Local Development Setup

This guide covers setting up local development where database services run in Docker containers while the backend application runs locally on your host machine.

## 📋 **Prerequisites**

- Docker & Docker Compose installed
- Python 3.10.11+
- Git

## 🔧 **Quick Setup**

### **1. Setup Environment Variables**
```bash
# Copy the local template to create your .env file
cp env.local.example .env

# Edit .env and add your API keys (especially OPENAI_API_KEY)
nano .env  # or your preferred editor
```

### **2. Start Database Services**
```bash
# Navigate to database directory and start local containers
cd docker/database
docker-compose -f docker-compose.local.yml up -d

# Verify all services are running
docker ps
```

### **3. Install Python Dependencies**
```bash
# Return to backend directory
cd ../..

# Install dependencies
pip install -r requirements.txt
```

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
MinIO: minioadmin:minioadmin123@http://localhost:9000
Qdrant: http://localhost:6333 (no auth)
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

1. **Daily startup**: `cd docker/database && docker-compose -f docker-compose.local.yml up -d`
2. **Run migrations**: `python run_migrations.py` (if schema changes)
3. **Start backend**: `python start_app.py`
4. **Code & test**: Your FastAPI app runs locally with hot reload
5. **Shutdown**: `docker-compose -f docker-compose.local.yml down` (optional)

## ⚠️ **Important Notes**

- **Environment File**: Always use `.env` created from `env.local.example`
- **API Keys**: Add your actual OpenAI API key to `.env`
- **Data Persistence**: Database data persists in Docker volumes
- **Network**: Services communicate via `localhost` (not Docker networking)
- **Hot Reload**: Application supports hot reload for development

Your local development environment is now ready! 🎉
