# Local Production Simulation Guide - Windows

## Overview
This guide provides complete step-by-step instructions to simulate your production deployment locally on Windows using Docker Desktop. You'll get an identical production environment running on your local machine with custom domain names.

## Prerequisites

### Required Software
- ✅ **Windows 10/11** with WSL2 enabled
- ✅ **Docker Desktop for Windows** (latest version)
- ✅ **PowerShell 5.0+** (built into Windows)
- ✅ **Administrator privileges** (for hosts file editing)

### Verify Prerequisites
```powershell
# Check Docker Desktop is running
docker --version
docker info

# Check PowerShell version
$PSVersionTable.PSVersion

# Check WSL2 is enabled
wsl --version
```

## Step 1: Configure Windows Hosts File

### 1.1 Open Hosts File as Administrator
```powershell
# Open notepad as administrator to edit hosts file
Start-Process notepad -Verb runAs -ArgumentList "C:\Windows\System32\drivers\etc\hosts"
```

### 1.2 Add Domain Entries
Add these entries to the bottom of your hosts file:
```hosts
# Local Production Simulation - ChatGPT Clone
127.0.0.1    myappdomain.com              # Main frontend domain
127.0.0.1    api.myappdomain.com          # Backend API
127.0.0.1    app.myappdomain.com          # Alternative frontend route
127.0.0.1    files.myappdomain.com        # MinIO file storage
127.0.0.1    sandbox.myappdomain.com      # CodeSandbox service
127.0.0.1    console.myappdomain.com      # MinIO admin console
```

### 1.3 Verify Domain Resolution
```powershell
# Test domain resolution
nslookup myappdomain.com
nslookup api.myappdomain.com

# Alternative test with ping
ping myappdomain.com
ping api.myappdomain.com
```

**Expected Output:**
```
Server:  UnKnown
Address:  192.168.1.1

Name:    myappdomain.com
Address:  127.0.0.1
```

## Step 2: Update Configuration Files

### 2.1 Backend Environment File
Open `backend/env.docker.app.prod` and update these values:

```bash
# Base URL Configuration (Production)
BASE_URL=https://api.myappdomain.com
DOMAIN=api.myappdomain.com

# Cookie Configuration (Production - Maximum Security)
COOKIE_DOMAIN=.myappdomain.com

# Service-to-Service Authentication (Production)
TRUSTED_INTERNAL_DOMAINS=myappdomain.com,api.myappdomain.com

# CORS (Strict Production Settings)
CORS_ORIGINS=https://myappdomain.com,https://app.myappdomain.com
ALLOWED_HOSTS=myappdomain.com,api.myappdomain.com

# Object Storage - MinIO (Production Container - Internal Port 9000)
S3_PRESIGNED_URL_ENDPOINT=https://files.myappdomain.com

# Image Processing (Production)
IMAGE_BASE_URL=https://api.myappdomain.com/api/images
```

### 2.2 Backend Docker Compose
In `backend/docker-compose.prod.yml`, update the Traefik routing rule:

**Line 89:** Change from:
```yaml
- "traefik.http.routers.backend.rule=Host(`api.yourdomain.com`) && PathPrefix(`/api`)"
```

**To:**
```yaml
- "traefik.http.routers.backend.rule=Host(`api.myappdomain.com`) && PathPrefix(`/api`)"
```

### 2.3 Frontend Docker Compose
In `frontend/chatgpt-frontend/docker-compose.prod.yml`, update these values:

**Lines 17, 24, 29:** Change from:
```yaml
VITE_API_URL: https://api.yourdomain.com
# and
VITE_API_URL=https://api.yourdomain.com
# and
- "traefik.http.routers.frontend.rule=Host(`yourdomain.com`)"
```

**To:**
```yaml
VITE_API_URL: https://api.myappdomain.com
# and
VITE_API_URL=https://api.myappdomain.com
# and
- "traefik.http.routers.frontend.rule=Host(`myappdomain.com`)"
```

### 2.4 CodeSandbox Docker Compose
In `CodeSandbox/docker-compose.prod.yml`, update line 21:

**Change from:**
```yaml
- "traefik.http.routers.codesandbox.rule=Host(`sandbox.yourdomain.com`)"
```

**To:**
```yaml
- "traefik.http.routers.codesandbox.rule=Host(`sandbox.myappdomain.com`)"
```

### 2.5 Database Docker Compose (MinIO)
In `backend/docker/database/docker-compose.prod.yml`, update these values:

**Line 248:** Change from:
```yaml
MINIO_BROWSER_REDIRECT_URL: https://console.yourdomain.com
```

**To:**
```yaml
MINIO_BROWSER_REDIRECT_URL: https://console.myappdomain.com
```

**Line 277:** Change from:
```yaml
- "traefik.http.routers.minio.rule=Host(`files.yourdomain.com`)"
```

**To:**
```yaml
- "traefik.http.routers.minio.rule=Host(`files.myappdomain.com`)"
```

## Step 3: Start Production Environment

### 3.1 Navigate to Backend Directory
```powershell
# Change to your backend directory
cd "C:\Users\Prince\Documents\GitHub\ChatGPT_Clone\backend"
```

### 3.2 Start Database Services First
```powershell
# Start database services (creates the unified prod-network)
python docker/database/db_manager.py start --env=prod

# Verify database services are running
python docker/database/db_manager.py status --env=prod
```

**Expected Output:**
```
✅ Environment 'prod' validation passed
✅ Production environment started successfully
ℹ️  Checking container health...
```

### 3.3 Start Backend Application
```powershell
# Start backend application with Traefik
python backend_docker_manager.py start --prod

# Check backend status
python backend_docker_manager.py status --prod
```

**Expected Output:**
```
✅ Build completed for prod environment
✅ Production environment started successfully
ℹ️  Checking container health...
```

### 3.4 Start CodeSandbox Service
```powershell
# Navigate to CodeSandbox directory
cd "../CodeSandbox"

# Start CodeSandbox production service
docker-compose -f docker-compose.prod.yml up -d

# Check CodeSandbox status
docker-compose -f docker-compose.prod.yml ps
```

### 3.5 Start Frontend Application
```powershell
# Navigate to frontend directory
cd "../frontend/chatgpt-frontend"

# Start frontend production service
docker-compose -f docker-compose.prod.yml up -d

# Check frontend status
docker-compose -f docker-compose.prod.yml ps
```

## Step 4: Verify Services are Running

### 4.1 Check All Containers
```powershell
# List all running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check unified network
docker network inspect prod-network
```

**Expected Containers:**
- `traefik-prod`
- `app-backend-production`
- `app-frontend-production`
- `codesandbox-production`
- `postgres_prod`
- `redis_prod`
- `neo4j_prod`
- `qdrant_prod`
- `minio_prod`

### 4.2 Check Traefik Dashboard (Optional)
If you want to see Traefik's internal status, temporarily enable dashboard:

```powershell
# Add these lines to traefik service in docker-compose.prod.yml:
# ports:
#   - "8080:8080"   # Dashboard
# command:
#   - --api.dashboard=true
#   - --api.insecure=true

# Then restart Traefik and visit: http://localhost:8080
```

## Step 5: Test Your Local Production Environment

### 5.1 Test Backend API
```powershell
# Test API health endpoint (ignore SSL warnings)
curl -k https://api.myappdomain.com/api/v1/health

# Using PowerShell's Invoke-WebRequest
Invoke-WebRequest -Uri "https://api.myappdomain.com/api/v1/health" -SkipCertificateCheck

# Test API documentation
curl -k https://api.myappdomain.com/api/v1/docs
```

### 5.2 Test Frontend Application
**Open Chrome and navigate to:**
1. `https://myappdomain.com`
2. You'll see: **"Your connection is not private"**
3. Click **"Advanced"**
4. Click **"Proceed to myappdomain.com (unsafe)"**
5. ✅ **Your frontend application should load**

### 5.3 Test File Storage (MinIO)
**Open Chrome and navigate to:**
1. `https://files.myappdomain.com`
2. Accept SSL warning as before
3. ✅ **MinIO API endpoint should respond**

**Test MinIO Console:**
1. `https://console.myappdomain.com`
2. Accept SSL warning
3. ✅ **MinIO login interface should load**

### 5.4 Test CodeSandbox Service
```powershell
# Test CodeSandbox health endpoint
curl -k https://sandbox.myappdomain.com/health

# Or via PowerShell
Invoke-WebRequest -Uri "https://sandbox.myappdomain.com/health" -SkipCertificateCheck
```

## Step 6: Understanding SSL Behavior

### 6.1 What Happens with Let's Encrypt
When you start your production containers:

1. ✅ **Traefik starts normally** with Let's Encrypt configuration
2. ⚠️ **ACME requests will FAIL** (Let's Encrypt can't validate local domains)
3. ✅ **Traefik automatically serves with fallback certificates**
4. ✅ **All services remain fully functional**

### 6.2 Expected Browser Behavior
**Chrome will show:**
- 🔒 **"Not secure"** in address bar
- ⚠️ **"Your connection is not private"** warning page
- ✅ **Click "Advanced" → "Proceed to [domain] (unsafe)"** to continue

**This is normal and expected for local production simulation!**

### 6.3 Traefik Logs to Expect
```powershell
# View Traefik logs
docker logs traefik-prod -f
```

**You'll see messages like:**
```
time="..." level=error msg="Unable to obtain ACME certificate for domains \"api.myappdomain.com\""
time="..." level=info msg="Serving default certificate for request: \"api.myappdomain.com\""
```

**This is expected behavior - services still work perfectly!**

## Step 7: Full System Testing

### 7.1 Complete Workflow Test
1. ✅ **Frontend loads:** `https://myappdomain.com`
2. ✅ **API responds:** `https://api.myappdomain.com/api/v1/health`
3. ✅ **File uploads work:** Test file upload functionality
4. ✅ **Code execution works:** Test CodeSandbox integration
5. ✅ **Database connections:** Check data persistence

### 7.2 Performance Testing
```powershell
# Test API response times
Measure-Command {Invoke-WebRequest -Uri "https://api.myappdomain.com/api/v1/health" -SkipCertificateCheck}

# Check container resource usage
docker stats --no-stream
```

## Step 8: Monitoring and Logs

### 8.1 View All Service Logs
```powershell
# Backend logs
python backend_docker_manager.py logs --prod --follow

# Database logs
python docker/database/db_manager.py logs --env=prod

# Frontend logs
cd "../frontend/chatgpt-frontend"
docker-compose -f docker-compose.prod.yml logs -f

# CodeSandbox logs
cd "../../CodeSandbox"
docker-compose -f docker-compose.prod.yml logs -f
```

### 8.2 Monitor Container Health
```powershell
# Check health status of all containers
docker ps --filter "health=healthy"
docker ps --filter "health=unhealthy"

# Detailed health check
docker inspect traefik-prod --format='{{.State.Health}}'
docker inspect app-backend-production --format='{{.State.Health}}'
```

## Step 9: Stopping the Environment

### 9.1 Stop All Services (Proper Order)
```powershell
# Navigate to backend directory
cd "C:\Users\Prince\Documents\GitHub\ChatGPT_Clone\backend"

# Stop frontend
cd "../frontend/chatgpt-frontend"
docker-compose -f docker-compose.prod.yml down

# Stop CodeSandbox
cd "../../CodeSandbox"
docker-compose -f docker-compose.prod.yml down

# Stop backend (includes Traefik)
cd "../backend"
python backend_docker_manager.py stop --prod

# Stop databases last
python docker/database/db_manager.py stop --env=prod
```

### 9.2 Clean Up (Optional)
```powershell
# Remove unused containers and networks
docker system prune -f

# Remove production volumes (WARNING: This deletes data!)
# docker volume prune -f
```

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Docker Desktop is not running"
**Solution:**
```powershell
# Start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait for it to start, then verify
docker --version
```

#### Issue 2: "Port already in use"
**Solution:**
```powershell
# Check what's using the port
netstat -ano | findstr ":80"
netstat -ano | findstr ":443"

# Stop conflicting services or change ports
```

#### Issue 3: "Cannot access https://api.myappdomain.com"
**Solution:**
1. ✅ **Check hosts file entries** are correct
2. ✅ **Verify containers are running:** `docker ps`
3. ✅ **Check Traefik logs:** `docker logs traefik-prod`
4. ✅ **Accept SSL warnings** in browser

#### Issue 4: "Network not found"
**Solution:**
```powershell
# Start database services first to create network
python docker/database/db_manager.py start --env=prod

# Then start other services
```

#### Issue 5: "502 Bad Gateway"
**Solution:**
```powershell
# Check backend container health
docker ps --filter "name=app-backend"

# Check backend logs
python backend_docker_manager.py logs --prod

# Restart backend if needed
python backend_docker_manager.py restart --prod
```

## Security Considerations

### What This Simulation Tests
✅ **Container orchestration and networking**
✅ **Service discovery and routing**
✅ **Database connections and data flow**
✅ **File storage and uploads**
✅ **Environment variable configuration**
✅ **Resource limits and health checks**
✅ **Production-identical Docker images**

### What This Doesn't Test
⚠️ **Real SSL certificate validation**
⚠️ **External DNS resolution**
⚠️ **Cloud provider integrations**
⚠️ **Load balancer behavior**
⚠️ **External firewall rules**

## Performance Benchmarks

### Expected Resource Usage
```
Container Memory Limits:
- Backend: 2GB (limit), 1GB (reservation)
- Traefik: ~100MB
- PostgreSQL: ~200MB
- Redis: ~50MB
- Neo4j: ~500MB
- Qdrant: ~300MB
- MinIO: ~100MB
```

### Windows Resource Requirements
- **RAM:** 8GB minimum, 16GB recommended
- **CPU:** 4 cores minimum
- **Disk:** 10GB free space for containers and volumes
- **Network:** Docker Desktop internal networking

## Advanced Configuration

### Enable Production Monitoring
```powershell
# Add monitoring ports to docker-compose.prod.yml
# Prometheus: 9090
# Grafana: 3000
# Add these to your services as needed
```

### Custom SSL Certificates (Advanced)
If you want to avoid browser warnings entirely:

```powershell
# Install mkcert (requires Chocolatey)
choco install mkcert

# Create locally trusted CA
mkcert -install

# Generate certificates for your domains
mkcert myappdomain.com api.myappdomain.com files.myappdomain.com sandbox.myappdomain.com

# Configure Traefik to use these certificates
# (requires additional Traefik configuration)
```

## Conclusion

This guide provides a complete production simulation environment on Windows. You now have:

✅ **Identical production configuration** running locally
✅ **All services communicating** through Traefik reverse proxy
✅ **Production database setup** with proper networking
✅ **HTTPS enabled** (with expected local SSL warnings)
✅ **Custom domain routing** working properly
✅ **Complete monitoring and logging** capabilities

**Your local environment now behaves exactly like production**, minus only the external DNS and real SSL certificates. This setup allows you to test deployments, configuration changes, and system behavior with confidence before deploying to actual production servers.

## Next Steps

1. **Test your application workflows** end-to-end
2. **Experiment with configuration changes** safely
3. **Practice deployment procedures** locally
4. **Use this setup for development** that needs production-like behavior
5. **Document any custom configurations** specific to your application

---

**Note:** Remember to accept SSL certificate warnings in your browser when accessing HTTPS URLs. This is expected behavior for local production simulation and doesn't affect the functionality testing of your application.
