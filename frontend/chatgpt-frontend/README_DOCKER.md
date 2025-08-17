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
- **Frontend App**: http://localhost
- **Backend API**: http://localhost/api/v1/
- **Traefik Dashboard**: http://localhost:8080

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

**Traefik automatically routes based on URL path:**

```
http://localhost/              → Frontend Container (React app)
http://localhost/dashboard     → Frontend Container  
http://localhost/api/v1/auth   → Backend Container
http://localhost/api/v1/chat   → Backend Container
```

## Development Workflow

### Option 1: Both in Containers
```bash
# Start backend
cd backend && python backend_docker_manager.py start --env=dev

# Start frontend  
cd frontend/chatgpt-frontend && python frontend_docker_manager.py start

# Access: http://localhost
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
Browser
   ↓
Traefik (Port 80)
   ├── frontend → app-frontend-development:3000
   └── /api     → app-backend-development:8000
```

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

**API calls failing:**
- Backend should be accessible at: http://localhost/api/v1/health
- Check backend logs: `cd ../../backend && python backend_docker_manager.py logs --env=dev`
