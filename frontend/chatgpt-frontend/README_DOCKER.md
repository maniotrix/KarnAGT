# Frontend Docker Development Setup

## Quick Start

### Prerequisites
Backend services must be running first:
```bash
cd ../../backend
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

# Check status
python frontend_docker_manager.py status
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
      args:
        VITE_API_URL: https://localhost  # Build-time variable
```

**Important:** `VITE_API_URL` must be passed at **build time**, not runtime, because Vite embeds environment variables during the build process.

## Development Workflow

### Option 1: Both in Containers
```bash
# Start backend
cd backend && python backend_docker_manager.py start --env=dev

# Start frontend  
cd frontend/chatgpt-frontend && python frontend_docker_manager.py start

# Access: https://localhost
```

### Option 2: Local Frontend + Container Backend
```bash
# Start backend in container
cd backend && python backend_docker_manager.py start --env=dev

# Start frontend locally
cd frontend/chatgpt-frontend && npm run dev

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/api/v1/
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

## Troubleshooting

**Frontend container won't start:**
```bash
# Check if backend network exists
docker network ls | grep dev-network

# If missing, start backend first
cd ../../backend && python backend_docker_manager.py start --env=dev
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
#   args:
#     VITE_API_URL: https://localhost

# Force rebuild to pick up new build args:
docker-compose -f docker-compose.dev.yml build --no-cache --pull
```

**SSL/Certificate warnings:**
- Browsers may show SSL warnings for localhost self-signed certificates
- Click "Advanced" → "Proceed to localhost (unsafe)" to continue
- This is normal for local development with HTTPS
