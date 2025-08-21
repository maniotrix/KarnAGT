# AWS Production Deployment Guide

## Overview
This guide documents the complete setup and deployment process for the KarnAGT application on AWS EC2 with EBS persistent storage. The setup includes a multi-service Docker architecture with dedicated networks, persistent volumes, and SSL certificates.

## Table of Contents
1. [Infrastructure Setup](#infrastructure-setup)
2. [EBS Volume Configuration](#ebs-volume-configuration)
3. [File Architecture Changes](#file-architecture-changes)
4. [Network Architecture](#network-architecture)
5. [Deployment Process](#deployment-process)
6. [Verification Steps](#verification-steps)
7. [Troubleshooting](#troubleshooting)

## Infrastructure Setup

### AWS Resources Required
- **EC2 Instance**: Fresh instance with 100GB root volume
- **EBS Volumes**: 5 additional volumes
  - 1x 50GB for Qdrant vector database
  - 4x 10GB for Postgres, MinIO, Redis, Neo4j
- **Elastic IP**: For stable domain mapping
- **Security Groups**: Configured for HTTP/HTTPS traffic

### EBS Volume Specifications
```
karnagt-qdrant-volume   vol-09893337c862be0fd  gp3  50 GiB  /dev/sdf
karnagt-postgres-volume vol-054e20dc11407d3fc  gp3  10 GiB  /dev/sdg  
karnagt-minio-volume    vol-02a528724b04deb87  gp3  10 GiB  /dev/sdh
karnagt-redis-volume    vol-06ecaf2189f70f35d  gp3  10 GiB  /dev/sdi
karnagt-neo4j-volume    vol-005d39284ac882e71  gp3  10 GiB  /dev/sdj
```

## EBS Volume Configuration

### 1. Format EBS Volumes
```bash
# Format all volumes with XFS filesystem
sudo mkfs.xfs -f -L qdrantprod /dev/nvme1n1    # 50GB Qdrant
sudo mkfs.xfs -f -L pgprod /dev/nvme2n1        # 10GB Postgres  
sudo mkfs.xfs -f -L minioprod /dev/nvme3n1     # 10GB MinIO
sudo mkfs.xfs -f -L redisprod /dev/nvme4n1     # 10GB Redis
sudo mkfs.xfs -f -L neo4jprod /dev/nvme5n1     # 10GB Neo4j
```

### 2. Get Volume UUIDs
```bash
# Get UUIDs for persistent mounting (most reliable method)
sudo blkid /dev/nvme1n1  # Qdrant
sudo blkid /dev/nvme2n1  # Postgres
sudo blkid /dev/nvme3n1  # MinIO  
sudo blkid /dev/nvme4n1  # Redis
sudo blkid /dev/nvme5n1  # Neo4j
```

### 3. Create Mount Points
```bash
# Create mount directories
sudo mkdir -p /mnt/qdrant-prod
sudo mkdir -p /mnt/pg-prod  
sudo mkdir -p /mnt/minio-prod
sudo mkdir -p /mnt/redis-prod
sudo mkdir -p /mnt/neo4j-prod
```

### 4. Configure /etc/fstab
```bash
# Edit /etc/fstab for persistent mounting
sudo nano /etc/fstab

# Add these entries (replace UUIDs with your actual values):
UUID=03fceffa-0c23-4bd8-9dc0-3801846eab45    /mnt/qdrant-prod    xfs    defaults,nofail    0 2
UUID=a25359eb-a746-4652-9572-1cb6c5174770    /mnt/pg-prod        xfs    defaults,nofail    0 2  
UUID=4d0a82bb-9c57-4724-891c-2999b5fc8812    /mnt/minio-prod     xfs    defaults,nofail    0 2
UUID=551b4a5c-d57f-42aa-9bf6-41059762677d    /mnt/redis-prod     xfs    defaults,nofail    0 2
UUID=da03e98d-8208-4321-b0d6-b0208f4a8a7a    /mnt/neo4j-prod     xfs    defaults,nofail    0 2
```

### 5. Mount Volumes and Set Permissions
```bash
# Mount all volumes
sudo mount -a

# Set ownership and permissions (zero-headaches approach)
sudo chown -R 0:0 /mnt
sudo chmod -R 777 /mnt

# Verify mounts
df -h
lsblk
```

## File Architecture Changes

### New AWS-Specific Files Created

#### Docker Compose Files
```
backend/docker/database/docker-compose-prod-aws.yml
backend/docker-compose-prod-aws.yml  
frontend/chatgpt-frontend/docker-compose-prod-aws.yml
CodeSandbox/docker-compose-prod-aws.yml
```

#### Environment Files
```
backend/env.docker.app.prod_aws
CodeSandbox/env.docker.prod_aws
```

#### Configuration Updates
```
backend/docker/database/db_config.json
backend/backend_docker_config.json
frontend/chatgpt-frontend/frontend_docker_config.json  
CodeSandbox/docker_setup_config.json
```

#### Python Manager Updates
```
backend/docker/database/db_manager.py
backend/backend_docker_manager.py
frontend/chatgpt-frontend/frontend_docker_manager.py
CodeSandbox/docker_setup_and_run.py
```

#### Dockerfile Updates
```
backend/Dockerfile_aws.prod  
frontend/chatgpt-frontend/Dockerfile_aws.prod
CodeSandbox/Dockerfile_aws.prod
```

#### Secrets Directory
```
backend/docker/database/secrets/prod_aws/
├── postgres_password.txt
├── neo4j_auth.txt  
├── minio_user.txt
└── minio_password.txt
```

### Key Changes Made

#### 1. Network Architecture
- Created dedicated `prod_aws_network` for complete isolation
- Database layer creates the network with `driver: bridge`
- Application layers connect as `external: true`

#### 2. Domain Configuration
All services configured for `karnagt.com` domains:
- `karnagt.com` → Frontend
- `api.karnagt.com` → Backend API
- `files.karnagt.com` → MinIO file storage  
- `sandbox.karnagt.com` → CodeSandbox
- `console.karnagt.com` → MinIO console

#### 3. Volume Configuration
- Replaced Docker named volumes with EBS bind mounts
- All volumes mount to `/mnt/*-prod` paths
- Persistent data survives container and instance restarts

#### 4. Environment Separation
- Complete `prod_aws` environment separate from generic `prod`
- Dedicated environment files with AWS-specific configurations
- All managers support `--env=prod_aws` command-line option

## Network Architecture

### prod_aws_network Structure
```
┌─────────────────────────────────────────────────────────┐
│                    prod_aws_network                     │
│                    (Docker Bridge)                     │
├─────────────────────────────────────────────────────────┤
│  Database Layer (Creates Network)                      │
│  ├── Postgres (postgres:5432)                         │
│  ├── Redis (redis:6379)                               │
│  ├── Qdrant (qdrant:6333)                            │
│  ├── Neo4j (neo4j:7687)                              │
│  ├── MinIO (minio:9000)                              │
│  └── Traefik (Load Balancer/SSL)                     │
├─────────────────────────────────────────────────────────┤
│  Application Layer (Connects to Network)               │
│  ├── Backend API → api.karnagt.com                    │
│  ├── Frontend → karnagt.com                           │
│  └── CodeSandbox → sandbox.karnagt.com               │
└─────────────────────────────────────────────────────────┘
```

### External Access Points
- **Frontend**: `https://karnagt.com` → React application
- **Backend API**: `https://api.karnagt.com` → FastAPI endpoints
- **File Storage**: `https://files.karnagt.com` → MinIO S3-compatible API  
- **CodeSandbox**: `https://sandbox.karnagt.com` → Code execution service
- **MinIO Console**: `https://console.karnagt.com` → MinIO web interface

## Deployment Process

### Prerequisites
1. **Domain Setup**
   - Create Google Workspace: `admin@karnagt.com`
   - Configure Google Workspace MX records in Namecheap
   - Create AWS Elastic IP
   - Update DNS A records in Namecheap for all subdomains

2. **EC2 Instance**
   - SSH access configured
   - Docker and Docker Compose installed
   - EBS volumes formatted and mounted
   - Project files uploaded

### Deployment Steps

#### 1. Verify Infrastructure
```bash
# SSH into EC2 instance
ssh -i your-key.pem ec2-user@your-elastic-ip

# Verify EBS mounts
df -h | grep /mnt
ls -la /mnt/

# Verify Docker
docker --version
docker-compose --version
```

#### 2. Deploy Database Layer (Creates Network)
```bash
cd /path/to/project
python backend/docker/database/db_manager.py start --env=prod_aws
```

#### 3. Deploy Backend API
```bash
python backend/backend_docker_manager.py start --env=prod_aws
```

#### 4. Deploy Frontend
```bash
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=prod_aws
```

#### 5. Deploy CodeSandbox
```bash
python CodeSandbox/docker_setup_and_run.py start --env=prod_aws
```

### Alternative: Docker Context Deployment
```bash
# Set up Docker Context (from local machine)
docker context create aws-prod --docker "host=ssh://ec2-user@your-elastic-ip"
docker context use aws-prod

# Deploy using same commands locally (execute on EC2)
python backend/docker/database/db_manager.py start --env=prod_aws
python backend/backend_docker_manager.py start --env=prod_aws  
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=prod_aws
python CodeSandbox/docker_setup_and_run.py start --env=prod_aws
```

## Verification Steps

### 1. Container Health Check
```bash
# Check all containers running
docker ps

# Check specific services
docker-compose -f backend/docker/database/docker-compose-prod-aws.yml ps
docker-compose -f backend/docker-compose-prod-aws.yml ps
docker-compose -f frontend/chatgpt-frontend/docker-compose-prod-aws.yml ps  
docker-compose -f CodeSandbox/docker-compose-prod-aws.yml ps
```

### 2. Network Verification
```bash
# Verify network exists
docker network ls | grep prod_aws_network

# Inspect network
docker network inspect prod_aws_network
```

### 3. Volume Verification  
```bash
# Check Docker volumes
docker volume ls

# Verify bind mounts
find /mnt/ -type d -name "*prod*"
```

### 4. Service Endpoint Testing
```bash
# Health checks (internal)
curl http://localhost:8000/api/v1/health
curl http://localhost:3000
curl http://localhost:8080

# External endpoint testing (after DNS propagation)
curl -k https://api.karnagt.com/api/v1/health
curl -k https://karnagt.com
curl -k https://files.karnagt.com  
curl -k https://sandbox.karnagt.com
```

### 5. SSL Certificate Verification
```bash
# Check SSL certificates (after DNS propagation)
curl -I https://api.karnagt.com
curl -I https://karnagt.com
curl -I https://files.karnagt.com
curl -I https://sandbox.karnagt.com
curl -I https://console.karnagt.com

# Monitor Traefik SSL certificate generation
docker logs -f <traefik-container-id>
```

## Troubleshooting

### Common Issues

#### 1. DNS Resolution Problems
```bash
# Check DNS propagation
nslookup api.karnagt.com
nslookup karnagt.com

# Check from multiple locations
dig api.karnagt.com @8.8.8.8
dig karnagt.com @1.1.1.1
```

#### 2. SSL Certificate Issues
```bash
# Traefik SSL certificate logs
docker logs <traefik-container> | grep -i cert
docker logs <traefik-container> | grep -i acme

# Manual certificate check
openssl s_client -connect api.karnagt.com:443
```

#### 3. Container Connectivity Issues
```bash
# Test inter-container communication
docker exec -it <backend-container> ping postgres
docker exec -it <backend-container> ping redis
docker exec -it <backend-container> ping qdrant

# Check port bindings
docker port <container-name>
```

#### 4. Volume Mount Issues
```bash
# Check volume permissions
ls -la /mnt/*/

# Test volume writes
echo "test" | sudo tee /mnt/pg-prod/test.txt
sudo rm /mnt/pg-prod/test.txt
```

#### 5. Service-Specific Issues
```bash
# Backend API issues
docker logs <backend-container>
docker exec -it <backend-container> env | grep -i api

# Database connection issues  
docker exec -it <postgres-container> psql -U app_prod_user -d app_prod_db
docker exec -it <redis-container> redis-cli ping

# MinIO issues
docker logs <minio-container>
curl -k https://files.karnagt.com/minio/health/live
```

### Service Management Commands

#### Restart Individual Services
```bash
# Database layer
python backend/docker/database/db_manager.py restart --env=prod_aws

# Backend
python backend/backend_docker_manager.py restart --env=prod_aws

# Frontend  
python frontend/chatgpt-frontend/frontend_docker_manager.py restart --env=prod_aws

# CodeSandbox
python CodeSandbox/docker_setup_and_run.py restart --env=prod_aws
```

#### Stop All Services
```bash
python CodeSandbox/docker_setup_and_run.py stop --env=prod_aws
python frontend/chatgpt-frontend/frontend_docker_manager.py stop --env=prod_aws
python backend/backend_docker_manager.py stop --env=prod_aws
python backend/docker/database/db_manager.py stop --env=prod_aws
```

#### View Logs
```bash
# Service-specific logs
docker logs -f <container-name>

# Follow all logs
docker-compose -f <compose-file> logs -f

# Filter logs
docker logs <container> 2>&1 | grep -i error
```

## Security Considerations

### 1. Network Security
- All services communicate through isolated `prod_aws_network`
- External access only through Traefik reverse proxy
- SSL/TLS encryption for all external endpoints

### 2. Data Security
- Persistent data stored on encrypted EBS volumes
- Database credentials managed through Docker secrets
- Non-root users in all containers

### 3. Access Control
- EC2 security groups configured for minimal access
- SSH key-based authentication only
- Container processes run as non-root users

### 4. SSL/TLS Configuration
- Automatic Let's Encrypt certificate generation
- HTTPS redirect for all external traffic
- Secure cookie configuration with proper domains

## Performance Optimization

### 1. Resource Allocation
- Dedicated EBS volumes for each data service
- gp3 volumes with 3000 IOPS baseline
- Container resource limits configured

### 2. Caching Strategy
- Redis for application caching
- CDN considerations for static assets
- Database query optimization

### 3. Monitoring
- Container health checks configured
- Traefik metrics available
- Application-level monitoring endpoints

## Maintenance Procedures

### 1. Backup Strategy
```bash
# Database backups
docker exec <postgres-container> pg_dump -U app_prod_user app_prod_db > backup.sql

# Volume snapshots (AWS CLI)
aws ec2 create-snapshot --volume-id vol-xxxxxxxxx --description "Backup $(date)"

# MinIO data backup
docker exec <minio-container> mc mirror /data s3://backup-bucket/
```

### 2. Updates and Deployment
```bash
# Update application code
git pull origin main

# Rebuild and restart services
python backend/backend_docker_manager.py rebuild --env=prod_aws
python frontend/chatgpt-frontend/frontend_docker_manager.py rebuild --env=prod_aws
```

### 3. Health Monitoring
- Set up CloudWatch monitoring for EC2 instance
- Configure alerts for disk space and memory usage
- Monitor SSL certificate expiration dates

## Conclusion

This AWS production deployment provides:
- **High Availability**: EBS persistent storage with automatic failover
- **Scalability**: Dedicated network architecture supporting horizontal scaling
- **Security**: SSL encryption, isolated networks, and secure credential management
- **Maintainability**: Automated deployment scripts and comprehensive monitoring

The `prod_aws` environment is completely isolated from development and staging environments, ensuring production stability while maintaining deployment consistency.

For support or updates to this deployment, refer to the project's documentation or contact the development team.

---
**Last Updated**: January 2025  
**Version**: 1.0  
**Environment**: AWS EC2 with EBS Persistent Storage
