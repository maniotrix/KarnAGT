# Frontend Production Setup Guide

> **⚠️ AWS Users**: For AWS EC2 production deployment with `karnagt.com` domains, use the dedicated [AWS Production Deployment Guide](../../backend/app_docs/AWS_PRODUCTION_DEPLOYMENT_GUIDE.md) instead. This guide uses generic `myappdomain.com` examples for non-AWS deployments.

## Overview
This document explains the production setup for the frontend application following the unified architecture pattern established by the backend, database, and CodeSandbox services.

## Architecture Summary

### Unified Network Approach
- **Network**: `prod-network` (created by database services)
- **All services** connect to the same Docker network for internal communication
- **Traefik** runs in the backend compose and routes external traffic to all services

### Service Routing
- **Frontend**: `Host('yourdomain.com')` → Main application
- **Backend**: `Host('api.yourdomain.com') && PathPrefix('/api')` → API endpoints
- **CodeSandbox**: `Host('sandbox.yourdomain.com')` → Code execution
- **MinIO**: `Host('files.yourdomain.com')` → File storage

### AWS vs Generic Production

| Configuration | Generic Production | AWS Production |
|---------------|-------------------|----------------|
| **Environment** | `--env=prod` | `--env=prod_aws` |
| **Network** | `prod-network` | `prod_aws_network` |
| **Domains** | `myappdomain.com` | `karnagt.com` |
| **Volumes** | Docker volumes | EBS bind mounts |
| **Guide** | This guide | [AWS Guide](../../backend/app_docs/AWS_PRODUCTION_DEPLOYMENT_GUIDE.md) |

## Production Deployment

### 1. Prerequisites
- Docker and docker-compose installed
- SSL certificates configured (Let's Encrypt)
- Domain DNS configured

### 2. Startup Order (IMPORTANT)
```bash
# 1. Start database services (creates prod-network)
cd backend/docker/database
python db_manager.py start --env=prod

# 2. Start CodeSandbox (connects to prod-network)
cd ../../../CodeSandbox
python docker_setup_and_run.py start --env=prod

# 3. Start backend + Traefik (reverse proxy)
cd ../backend
python backend_docker_manager.py start --env=prod

# 4. Start frontend (final service)
cd ../frontend/chatgpt-frontend
python frontend_docker_manager.py start --env=prod
```

### 3. Configuration Files

#### JSON Configuration
- `frontend_docker_config.json` - Environment definitions and settings
- Follows same pattern as backend and CodeSandbox managers

#### Docker Files
- `docker-compose.prod.yml` - Production container orchestration
- `Dockerfile.prod` - Multi-stage build for optimized production image (Node.js 20.18.0 LTS + nginxinc/nginx-unprivileged)
- `nginx.conf` - Unified nginx configuration for React SPA routing (shared with dev)

#### Environment Variables
- Environment variables are passed as build arguments in docker-compose.yml
- No separate .env files required - configured directly in compose files
- `VITE_API_URL` and `NODE_ENV` set at build time for optimal performance
- `VITE_GOOGLE_CLIENT_ID` set for Google OAuth authentication (production Client ID)

## Google OAuth Configuration

### Production Setup Requirements

**1. Google Cloud Console Configuration:**
- Create OAuth 2.0 Client ID in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
- **Authorized JavaScript origins:** `https://yourdomain.com`, `https://app.yourdomain.com`
- **Authorized redirect URIs:** Not required (using popup-based flow)
- **Client Type:** Web application

**2. Environment Configuration:**
```yaml
# docker-compose.prod.yml - Update with your production Client ID
build:
  args:
    VITE_GOOGLE_CLIENT_ID: your-prod-client-id.apps.googleusercontent.com
environment:
  - VITE_GOOGLE_CLIENT_ID=your-prod-client-id.apps.googleusercontent.com
```

**3. Security Notes:**
- ✅ **Client ID is public by design** - Safe to include in frontend builds
- ✅ **No client secret needed** - Frontend-only OAuth flow
- ✅ **Domain validation** - Google restricts usage to authorized origins
- ✅ **Backend validates tokens** - Server-side verification with Google's API

### Testing Google Login
```bash
# After production deployment
curl -X POST https://api.yourdomain.com/api/v1/auth/google-login \
  -H "Content-Type: application/json" \
  -d '{"google_id_token": "test_token"}'

# Expected: Backend validates with https://oauth2.googleapis.com/tokeninfo
```

## Manager Commands

```bash
# List available environments
python frontend_docker_manager.py envs

# Validate environment setup
python frontend_docker_manager.py validate --env=prod

# Build production image
python frontend_docker_manager.py build --env=prod

# Start production container
python frontend_docker_manager.py start --env=prod

# Check status
python frontend_docker_manager.py status --env=prod

# View logs
python frontend_docker_manager.py logs --env=prod --follow

# Health check
python frontend_docker_manager.py health --env=prod

# Stop containers
python frontend_docker_manager.py stop --env=prod
```

## Network Integration

### Internal Communication
- Frontend connects to `prod-network` (external network)
- No direct container-to-container communication
- All routing handled by Traefik reverse proxy

### Security
- Official nginx unprivileged image runs as 'nginx' user by default (no custom user creation needed)
- Latest LTS versions (Node.js 20.18.0, nginxinc/nginx-unprivileged 1.25-alpine) with security patches
- Simplified architecture with reduced attack surface
- Security headers via Nginx (X-Frame-Options, X-XSS-Protection, etc.)
- SSL/TLS termination at Traefik level
- **Controlled Log Growth**: Automatic log rotation prevents disk exhaustion attacks (10MB max files, 50MB total in prod)
- **Browser Console Logs**: Automatically disabled in production builds to prevent information leakage

## File Structure
```
frontend/chatgpt-frontend/
├── frontend_docker_config.json      # Environment configuration
├── frontend_docker_manager.py       # Management script (follows backend pattern)
├── docker-compose.dev.yml           # Development setup
├── docker-compose.prod.yml          # Production setup
├── Dockerfile.dev                   # Development build (Node 20.18.0 LTS)
├── Dockerfile.prod                  # Production build (Node 20.18.0 LTS)
├── nginx.conf                       # Unified nginx config (dev + prod)
├── .dockerignore                    # Build optimization (industry standard)
├── PRODUCTION_SETUP_GUIDE.md        # This file
└── README_DOCKER.md                 # Development guide
```

## Troubleshooting

### Common Issues

1. **Network not found**
   - Ensure database services are started first
   - Check network exists: `docker network ls | grep prod-network`

2. **Frontend not accessible**
   - Verify Traefik is running in backend service
   - Check Traefik dashboard: `http://localhost:8080` (dev only)
   - Verify domain DNS configuration

3. **Build failures**
   - Check Node.js version compatibility (using 20.18.0 LTS)
   - Verify all build arguments are set in docker-compose.yml
   - Check disk space for Docker builds
   - Check if .dockerignore is properly excluding unnecessary files

4. **Version mismatch issues**
   - Local Node.js vs Docker: Use `node --version` to compare
   - Docker images: Both environments use Node.js 20.18.0 LTS + nginxinc/nginx-unprivileged 1.25-alpine
   - Rebuild if versions don't match: `--build --no-cache` flags

5. **Log-related issues**
   - **Logs not visible**: Check if containers are running with `docker ps`
   - **Log files too large**: Automatic rotation prevents this (max 50MB in prod)
   - **Performance impact**: Logs are JSON structured and efficiently rotated
   - **Missing browser logs**: Production builds automatically remove console.log (security feature)

### Health Checks
- Frontend: `curl -f http://localhost:3000/`
- External: `https://yourdomain.com/`

## Logging & Monitoring

### Container Log Management
Both development and production environments include automated log rotation to prevent disk space issues:

**Production Logging:**
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"         # Smaller files for production efficiency
    max-file: "5"           # Keep 5 files for troubleshooting (50MB total)
    labels: "environment=prod,service=frontend"
```

**Development Logging:**
```yaml
logging:
  driver: "json-file" 
  options:
    max-size: "50m"         # Larger files for detailed debugging
    max-file: "3"           # 3 files total (150MB total)
    labels: "environment=dev,service=frontend"
```

### Monitoring Commands
```bash
# View container logs
python frontend_docker_manager.py logs --env=prod

# Follow logs in real-time
python frontend_docker_manager.py logs --env=prod --follow

# Check container performance
docker stats app-frontend-production

# Access Traefik dashboard (development only)
# http://localhost:8080
```

### Log Benefits
- **Automatic Rotation**: Prevents unlimited disk growth
- **Structured Logging**: JSON format with environment labels
- **Easy Integration**: Compatible with log aggregation tools (ELK, Splunk, etc.)
- **Environment Optimized**: Different limits for dev vs prod needs
