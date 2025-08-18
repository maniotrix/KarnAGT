# Frontend Docker Development Setup

## Quick Start

### Prerequisites
Backend services must be running first (creates the dev-network):
```bash
cd ../../backend/docker/database
python db_manager.py start --env=dev

cd ../../
python backend_docker_manager.py start --env=dev
```

### Start Frontend Container
```bash
# Method 1: Using manager script
python frontend_docker_manager.py start

# Method 2: Direct docker compose
docker compose -f docker-compose.dev.yml up -d --build
```

### Access Points
- **Frontend App**: https://localhost (HTTPS via Traefik)
- **Backend API**: https://localhost/api/v1/ (HTTPS via Traefik)
- **Traefik Dashboard**: http://localhost:8080
- **MinIO Files**: https://localhost:9000/ (File downloads)

## Management Commands

```bash
# Start frontend container
python frontend_docker_manager.py start

# Stop frontend container  
python frontend_docker_manager.py stop

# Restart frontend container
python frontend_docker_manager.py restart

# View logs
python frontend_docker_manager.py logs

# Follow logs in real-time
python frontend_docker_manager.py logs --follow

# Check status
python frontend_docker_manager.py status

# Health check
python frontend_docker_manager.py health
```

## Log Management

### Automatic Log Rotation
Both development and production containers include smart log rotation to prevent disk space issues:

**Development Environment:**
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"         # Large files for debugging
    max-file: "3"           # 150MB total storage
    labels: "environment=dev,service=frontend"
```

**Benefits:**
- ✅ **Detailed Debugging**: Larger 50MB files capture more context
- ✅ **Controlled Storage**: Maximum 150MB total log storage
- ✅ **Easy Identification**: Labeled with environment and service tags
- ✅ **JSON Structured**: Compatible with log analysis tools

### Log Commands
```bash
# View recent logs
python frontend_docker_manager.py logs

# Follow logs in real-time (great for debugging)
python frontend_docker_manager.py logs --follow

# Direct Docker commands
docker logs app-frontend-development
docker logs app-frontend-development --follow --tail=100
```

## How Routing Works

**Traefik automatically routes HTTPS traffic based on URL path:**

```
https://localhost/              → Frontend Container (React app)
https://localhost/dashboard     → Frontend Container  
https://localhost/api/v1/auth   → Backend Container
https://localhost/api/v1/chat   → Backend Container
https://localhost:9000/         → MinIO (file downloads)
```

### Environment Variable Configuration

The frontend container requires build-time environment variables for API communication:

```yaml
# docker-compose.dev.yml
services:
  app-frontend-dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
      target: development  # Multi-stage build target
      args:
        VITE_API_URL: https://localhost  # Build-time variable
        NODE_ENV: development            # Environment setting
        FRONTEND_USER: app_frontend_dev  # Security user
```

**Important:** 
- `VITE_API_URL` must be passed at **build time**, not runtime, because Vite embeds environment variables during the build process
- Uses **Node.js 20.18.0 LTS** and **nginx 1.25.3** for stability and security
- **Multi-stage builds** optimize image size and layer caching
- **Console Logs**: Browser console logs are **enabled** in development for debugging (automatically disabled in production builds)

## Development Workflow

### Option 1: Both in Containers (Recommended)
```bash
# 1. Start database services (creates dev-network)
cd backend/docker/database && python db_manager.py start --env=dev

# 2. Start backend + Traefik
cd ../../ && python backend_docker_manager.py start --env=dev

# 3. Start frontend  
cd ../frontend/chatgpt-frontend && python frontend_docker_manager.py start

# Access: https://localhost (unified HTTPS access)
```

### Option 2: Local Frontend + Container Backend
```bash
# 1. Start database services
cd backend/docker/database && python db_manager.py start --env=dev

# 2. Start backend in container
cd ../../ && python backend_docker_manager.py start --env=dev

# 3. Start frontend locally (bypasses container)
cd ../frontend/chatgpt-frontend && npm run dev

# Frontend: http://localhost:3000 (local Vite server)
# Backend API: https://localhost/api/v1/ (via Traefik)
```

## Network Architecture

```
Browser (HTTPS)
   ↓
Traefik (Port 443 - HTTPS, Port 80 - HTTP redirect)
   ├── https://localhost/          → app-frontend-development:3000
   ├── https://localhost/api/      → app-backend-development:8000
   └── https://localhost:9000/     → minio:9000 (file downloads)
```

**Key Features:**
- **SSL Termination**: Traefik handles HTTPS certificates and SSL termination
- **Automatic HTTP→HTTPS**: HTTP requests redirect to HTTPS
- **Service Discovery**: Containers communicate using service names
- **File Proxy**: MinIO files accessible via HTTPS for browser compatibility

## 2025 Architecture Improvements

### Docker Optimizations
- **Node.js 20.18.0 LTS**: Long-term support with security patches (supported until April 2026)
- **nginx 1.25.3**: Latest stable with performance improvements and security fixes
- **Optimized Layers**: Reduced from 9 to 6 Docker layers for faster builds and smaller images
- **Industry-Standard .dockerignore**: Comprehensive file exclusion for build optimization

### Development/Production Consistency
- **Unified nginx Configuration**: Same `nginx.conf` for both dev and prod environments
- **Identical Build Process**: Same commands (`npm ci --include=dev`, `npm run build`) in both environments
- **Consistent Security**: Non-root users and security headers in all environments
- **Multi-Stage Builds**: Separate build and runtime stages for optimal image sizes

### Security Enhancements
- **Non-Root Execution**: All containers run as dedicated users (app_frontend_dev/prod)
- **Version Pinning**: Exact image versions prevent supply chain attacks
- **Security Headers**: X-Frame-Options, X-XSS-Protection, referrer policy via nginx
- **Health Monitoring**: Built-in health checks with proper endpoints

## Troubleshooting

**Frontend container won't start:**
```bash
# Check if dev-network exists (created by database services)
docker network ls | grep dev-network

# If missing, start services in correct order:
cd ../../backend/docker/database && python db_manager.py start --env=dev
cd ../../ && python backend_docker_manager.py start --env=dev
```

**Can't access frontend:**
- Check Traefik dashboard: http://localhost:8080
- Look for "frontend" router in HTTP section
- Check container logs: `python frontend_docker_manager.py logs`

**API calls failing (CORS errors):**
- Backend should be accessible at: https://localhost/api/v1/health  
- Check backend logs: `cd ../../backend && python backend_docker_manager.py logs --env=dev`

**Frontend calling localhost:8000 instead of https://localhost:**
```bash
# Root cause: VITE_API_URL not passed at build time
# Check built frontend for hardcoded URLs:
docker exec app-frontend-development grep -r "localhost:8000" /usr/share/nginx/html/assets/

# Solution: Rebuild with correct build arguments
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

**Build-time environment variable issues:**
```bash
# Ensure docker-compose.dev.yml has build args:
# build:
#   target: development  # Multi-stage build target
#   args:
#     VITE_API_URL: https://localhost
#     NODE_ENV: development
#     FRONTEND_USER: app_frontend_dev

# Force rebuild to pick up new build args:
python frontend_docker_manager.py restart --build
# OR manually:
docker-compose -f docker-compose.dev.yml build --no-cache --pull
```

**SSL/Certificate warnings:**
- Browsers may show SSL warnings for localhost self-signed certificates
- Click "Advanced" → "Proceed to localhost (unsafe)" to continue
- This is normal for local development with HTTPS

**Understanding Different Log Types:**
```bash
# 1. Browser Console Logs (React app logs)
# - Open browser DevTools → Console tab
# - Shows React component errors, API call logs, etc.
# - Enabled in development, disabled in production builds

# 2. Container Logs (nginx, system logs) 
python frontend_docker_manager.py logs --follow
# - Shows nginx access/error logs, container startup logs
# - Managed by Docker log rotation (50MB max in dev)
# - Always available for debugging container issues

# 3. Direct Docker inspection
docker logs app-frontend-development --tail=50
docker exec -it app-frontend-development cat /var/log/nginx/error.log
```
