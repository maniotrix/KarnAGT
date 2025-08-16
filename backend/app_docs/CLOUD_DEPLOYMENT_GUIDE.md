# ☁️ Cloud Deployment Guide

## 🚀 **Updated for Modern Docker Security & uv Package Management**

> **💡 Latest Updates:**
> - ✅ **Security Best Practices** - All containers now use non-root pip installation
> - ✅ **Platform-Specific Requirements** - Linux/Windows requirements generated with uv
> - ✅ **S3 Integration** - No more local upload directories
> - ✅ **Comprehensive Dependencies** - Enhanced for AI/ML workloads
> - ✅ **Clean Container Architecture** - Minimal bind mounts, stateless design

## 🚀 **NEW: Choose Your Deployment Method**

### **⭐ RECOMMENDED: [Docker Context Direct Deployment](#-alternative-docker-context-direct-deployment)**
- 🏠 **Work entirely from local machine** - no SSH required
- ⚡ **Single command deployment** - no manual file copying
- 🚫 **No git operations** on remote server
- ✅ **Same scripts work** - zero code changes needed
- ⚡ **3-4 simple steps** vs 6-8 manual steps
- 🔐 **Automatic security** - Uses latest Docker security practices

### **🔄 Traditional: [Git-based Deployment](#-deployment-workflow)**
- 📡 Requires SSH into remote server
- 🔄 Manual git pull + environment file upload
- 📋 Multi-step process with intermediate steps
- ⏳ **6-8 manual steps** with context switching

---

## 🔒 **NEW: Docker Security & Platform-Specific Requirements**

### **🔐 Enhanced Security (Applied Across All Environments)**
All Docker containers now follow production security best practices:
- **Non-root pip installation** - Packages installed as application user (not root)
- **User-space package management** - All dependencies in `~/.local/` directories  
- **Minimal attack surface** - No unnecessary root privileges during runtime
- **Clean PATH configuration** - User packages properly accessible

### **🐍 Platform-Specific Python Requirements**
We now use **uv** to generate platform-optimized requirements files:

```bash
# For Linux containers (Docker/Production)
requirements-linux.txt    # ← Used in all Docker builds

# For Windows development (Local)
requirements-windows.txt   # ← Used for local Windows development

# Source file (edit this one)
requirements.in           # ← Add your dependencies here
```

**Key Benefits:**
- ✅ **No pywin32 errors** in Linux containers
- ✅ **CUDA packages** included for Linux AI/ML workloads  
- ✅ **Platform optimization** for better performance
- ✅ **Consistent deployments** across environments

### **☁️ S3-Native Architecture**
- **No upload bind mounts** - All file uploads go directly to S3
- **Stateless containers** - No local file persistence required
- **Cloud-native design** - Follows 12-factor app principles

### **🔗 Docker Service Discovery**
**CRITICAL: Environment files now use service names, not localhost**

**✅ Container-to-Container Communication (New Pattern):**
```bash
# Use these in your .env.docker.app.* files:
DATABASE_URL=postgresql://user:pass@postgres:5432/db
REDIS_URL=redis://:password@redis:6379/0
NEO4J_URL=bolt://neo4j:7687
QDRANT_URL=http://qdrant:6333
S3_ENDPOINT_URL=http://minio:9000
```

**🖥️ External Access (Admin Tools Only):**
```bash
# Use these for database administration from host:
localhost:5433  # PostgreSQL (dev)
localhost:6380  # Redis (dev)
localhost:7688  # Neo4j (dev)
```

**Key Benefits:**
- ✅ **Production-ready networking** - Uses Docker's internal DNS
- ✅ **Environment consistency** - Same internal ports everywhere
- ✅ **Independent container startup** - No health check dependencies
- ✅ **Network segmentation** - Isolated service networks

---

## 🚨 **CRITICAL: Environment Upload First! (Git-based method only)**

**⚠️ ALWAYS upload environment files BEFORE building/starting containers after git pull**

Environment files are NOT in the git repository for security reasons. After pulling code updates, containers will fail to build/start without proper environment files.

---

## 📚 **Quick Navigation**

**🚀 [Docker Context Method (Recommended)](#-alternative-docker-context-direct-deployment)**
- [Prerequisites](#prerequisites-for-docker-context)
- [One-Time Setup](#-one-time-setup)
- [Deployment Workflow](#-streamlined-deployment-workflow)
- [Troubleshooting](#-troubleshooting-docker-context)

**📡 [Traditional Git Method](#-deployment-workflow)**
- [Prerequisites](#prerequisites)
- [Environment Uploader](#-environment-uploader-usage)
- [Full Deployment Steps](#deployment-workflow)
- [Troubleshooting](#troubleshooting)

---

## 📋 **Prerequisites (Git-based method)**

### **🔑 SSH Access Required**
The env uploader uses SCP (which runs over SSH) to transfer files. You **MUST** have SSH access configured:

#### **Option 1: SSH Keys (Recommended - No Password Prompts)**
```bash
# Generate SSH key on your local machine
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# Copy public key to cloud VM
ssh-copy-id user@your-cloud-vm

# Test connection (should connect without password)
ssh user@your-cloud-vm
```

#### **Option 2: Password Authentication (Will Prompt Multiple Times)**
```bash
# Test SSH connection first
ssh user@your-cloud-vm
# Enter password when prompted

# Script will prompt for password FOR EACH FILE uploaded
# For prod: 2 password prompts (backend + codesandbox)
# For staging: 1 password prompt (backend only)
```

### **🌐 Network Requirements**
- Your local machine must be able to reach the cloud VM
- SSH port (22) must be open and accessible
- No firewall blocking SCP/SSH traffic

### **📁 Remote Project Structure**
- Project must already be cloned on the remote server via `git clone`
- Directory structure must exist: `backend/` and `CodeSandbox/` folders
- You must know the **absolute path** where project is deployed

### **⚡ Quick Prerequisites Check**
Before using the env uploader, verify:
```bash
# 1. SSH connection works
ssh user@your-cloud-vm
exit

# 2. Remote project path exists
ssh user@your-cloud-vm "ls -la /opt/your-project/backend"
ssh user@your-cloud-vm "ls -la /opt/your-project/CodeSandbox"

# 3. Local env files exist
ls backend/.env.docker.app.*
ls CodeSandbox/.env.docker.*
```

---

## 📋 **Deployment Workflow**

### **Step 1: Prepare Platform-Specific Requirements (One-Time Setup)**
```bash
# On your LOCAL development machine
cd your-project/backend

# Generate platform-specific requirements (if not already done)
uv pip compile --python-platform linux --python-version 3.10 requirements.in -o requirements-linux.txt --upgrade
uv pip compile --python-platform windows --python-version 3.10 requirements.in -o requirements-windows.txt --upgrade

# Commit the new requirements files
git add requirements-linux.txt requirements-windows.txt
git commit -m "Update platform-specific requirements"
git push origin main
```

### **Step 2: Update Code on Cloud VM**
```bash
# SSH into your cloud VM
ssh user@your-cloud-vm

# Navigate to project directory  
cd /opt/your-project  # or wherever you cloned

# Pull latest code (includes new requirements-linux.txt)
git pull origin main
```

### **Step 3: Upload Environment Files (REQUIRED)**
```bash
# From your LOCAL machine (not on cloud VM)  
cd your-project

# For Production
python cloud_env_uploader.py --env=prod --host=user@your-cloud-vm --remote-repo-root-path=/opt/your-project

# For Staging  
python cloud_env_uploader.py --env=staging --host=user@staging-vm --remote-repo-root-path=/opt/your-project
```

### **Step 3: Start Database Containers (REQUIRED FIRST)**
```bash
# Back on cloud VM after env upload
cd /opt/your-project

# Start database containers FIRST
cd backend/docker/database
python db_manager.py start --env=prod

# Verify database health
python db_manager.py health --env=prod
```

### **Step 4: Build & Start Application Containers**
```bash
# Navigate back to project root
cd /opt/your-project

# Backend Application
cd backend
python backend_docker_manager.py restart --prod

# CodeSandbox (CORRECT SCRIPT NAME)
cd ../CodeSandbox
python docker_setup_and_run.py restart --env=prod
```

### **Step 5: Verify Deployment**
```bash
# Check backend status
cd /opt/your-project/backend
python backend_docker_manager.py status --prod
python backend_docker_manager.py health --prod

# Check database status  
cd docker/database
python db_manager.py status --env=prod

# Check CodeSandbox status
cd ../../CodeSandbox
python docker_setup_and_run.py validate --env=prod

# View logs if needed
cd ../backend
python backend_docker_manager.py logs --prod
```

---

## 🚀 **ALTERNATIVE: Docker Context Direct Deployment**

### **🌟 Streamlined Approach - No Git, No Manual File Copying**

Docker Context allows you to deploy directly from your **local machine** to remote servers without intermediate steps. Your local code, environment files, and configurations are automatically transferred during the build process.

#### **✅ Advantages over Traditional Git-based Deployment:**
- **🚫 No Git Operations**: No need to `git pull` on remote server
- **🚫 No Environment File Uploading**: Files transferred automatically
- **🏠 Work Entirely Local**: Never SSH into remote servers
- **⚡ Single Command Deployment**: One command builds and deploys everything
- **🔄 Instant Rollbacks**: Standard Docker commands for quick rollbacks
- **👀 Better Visibility**: All logs and errors visible locally

#### **📋 Prerequisites for Docker Context**

**Same SSH requirements as traditional method:**
- SSH access to remote server (keys recommended)
- Docker installed on both local and remote machines
- Network connectivity between local and remote

**Additional Requirements:**
- Docker version 19.03+ (for context support)
- Remote Docker daemon accessible via SSH
- Local project with all environment files present

#### **🔧 One-Time Setup**

```bash
# 1. Create Docker context for production server
docker context create production-server --docker "host=ssh://user@your-cloud-vm"

# 2. Create Docker context for staging server (if needed)
docker context create staging-server --docker "host=ssh://user@your-staging-vm"

# 3. List contexts to verify
docker context ls

# 4. Test connection to remote context
docker --context production-server ps
```

#### **🚀 Streamlined Deployment Workflow**

**Step 1: Switch to Remote Context**
```bash
# From your LOCAL machine, in your project directory
docker context use production-server

# Verify you're connected to remote
docker ps  # Shows containers on remote server
```

**Step 2: Deploy Everything**
```bash
# Deploy database containers FIRST
cd backend/docker/database
python db_manager.py start --env=prod

# Wait for database to be ready
python db_manager.py health --env=prod

# Deploy backend application
cd ../../  # back to backend/
python backend_docker_manager.py restart --prod

# Deploy CodeSandbox
cd ../CodeSandbox
python docker_setup_and_run.py restart --env=prod
```

**That's it!** Your existing scripts work exactly the same, but execute on the remote server.

#### **🔄 Switch Back to Local**
```bash
# Switch back to local Docker
docker context use default

# Now docker commands run locally again
docker ps  # Shows local containers
```

#### **📊 Deployment Comparison**

| Step | Traditional Git Method | Docker Context Method |
|------|----------------------|----------------------|
| **Code Sync** | SSH + `git pull` on remote | Automatic via build context |
| **Environment Files** | Manual `cloud_env_uploader.py` | Included automatically |
| **Location** | Work on remote server | Work entirely local |
| **Commands** | SSH in/out multiple times | Same commands, run locally |
| **Total Steps** | 6-8 manual steps | 3-4 simple steps |
| **Error Visibility** | Check logs on remote | All errors visible locally |

#### **🛠️ How It Works**

When you use Docker context:
1. **Build Context Transfer**: Docker automatically transfers your local project files (including env files) to remote during build
2. **Remote Execution**: All Docker commands execute on remote server
3. **Local Control**: You see all output, logs, and errors on your local machine
4. **Same Scripts**: Your existing `backend_docker_manager.py`, `db_manager.py`, etc. work unchanged

#### **📁 File Requirements**

**No changes needed to existing files:**
- ✅ Keep your current Dockerfiles
- ✅ Keep your current docker-compose files  
- ✅ Keep your current Python management scripts
- ✅ Keep your current environment files in same locations

**Just ensure environment files are in your local project:**
```
project-root/
├── backend/
│   ├── .env.docker.app.prod       ← Must exist locally
│   ├── .env.docker.app.staging    ← Must exist locally
│   └── ...
├── CodeSandbox/
│   ├── .env.docker.prod           ← Must exist locally
│   └── ...
```

#### **⚡ Quick Context Deployment Commands**

**Full Production Deployment:**
```bash
# Switch context
docker context use production-server

# Deploy (same commands as local)
cd backend/docker/database && python db_manager.py start --env=prod
cd ../../ && python backend_docker_manager.py restart --prod
cd ../CodeSandbox && python docker_setup_and_run.py restart --env=prod

# Verify deployment
cd ../backend && python backend_docker_manager.py health --prod
```

**Quick Status Check:**
```bash
# Check all containers on remote
docker context use production-server
docker ps

# Or check with your existing tools
cd backend && python backend_docker_manager.py status --prod
```

#### **🔧 Troubleshooting Docker Context**

**Context Connection Issues:**
```bash
# Test SSH connection first
ssh user@your-cloud-vm

# List and check contexts
docker context ls
docker context inspect production-server

# Test remote Docker connection
docker --context production-server version
```

**Build Context Too Large:**
```bash
# Check what's being transferred
du -sh .

# Use .dockerignore to exclude large files
echo "node_modules/" >> .dockerignore
echo "*.log" >> .dockerignore
echo ".git/" >> .dockerignore
```

**Switch Context Issues:**
```bash
# Reset to default context
docker context use default

# Remove and recreate problematic context
docker context rm production-server
docker context create production-server --docker "host=ssh://user@your-cloud-vm"
```

---

## 🛠️ **Environment Uploader Usage**

### **Basic Commands**
```bash
# Upload prod environment files
python cloud_env_uploader.py --env=prod --host=user@cloud-vm --remote-repo-root-path=/opt/your-project

# Upload staging environment files
python cloud_env_uploader.py --env=staging --host=user@staging-vm --remote-repo-root-path=/opt/your-project

# List files that would be uploaded (no actual upload)
python cloud_env_uploader.py --list-files --env=prod

# Force overwrite existing files without confirmation
python cloud_env_uploader.py --env=prod --host=user@cloud-vm --remote-repo-root-path=/opt/your-project --force
```

### **What Gets Uploaded**

**Production Environment:**
- `backend/.env.docker.app.prod` → `/remote-repo-root-path/backend/.env.docker.app.prod`
- `CodeSandbox/.env.docker.prod` → `/remote-repo-root-path/CodeSandbox/.env.docker.prod`

**Staging Environment:**
- `backend/.env.docker.app.staging` → `/remote-repo-root-path/backend/.env.docker.app.staging`  
- `CodeSandbox`: No staging environment file

**Note:** `/remote-repo-root-path` is the value you provide with `--remote-repo-root-path` argument.

## 💡 **How the Upload Process Works**

### **What to Expect During Upload**

#### **With SSH Keys (Recommended)**
```bash
python cloud_env_uploader.py --env=prod --host=user@vm --remote-repo-root-path=/opt/project

[12:34:56] ℹ️  Starting PROD environment upload to user@vm:/opt/project
[12:34:56] ℹ️  Uploading backend environment file...
[12:34:56] ✅ Uploaded .env.docker.app.prod
[12:34:56] ℹ️  Uploading codesandbox environment file...
[12:34:56] ✅ Uploaded .env.docker.prod
[12:34:56] ✅ All 2 environment files uploaded successfully!
```
**No password prompts - smooth and fast!**

#### **With Password Authentication**
```bash
python cloud_env_uploader.py --env=prod --host=user@vm --remote-repo-root-path=/opt/project

[12:34:56] ℹ️  Starting PROD environment upload to user@vm:/opt/project
[12:34:56] ℹ️  Uploading backend environment file...
user@vm's password: █              # ← Enter password for first file
[12:34:57] ✅ Uploaded .env.docker.app.prod
[12:34:57] ℹ️  Uploading codesandbox environment file...
user@vm's password: █              # ← Enter password for second file
[12:34:58] ✅ Uploaded .env.docker.prod
[12:34:58] ✅ All 2 environment files uploaded successfully!
```
**Password required for EACH file - consider setting up SSH keys!**

### **Why --remote-repo-root-path is Required**
- **No Remote SSH Required**: Script uploads directly from local machine
- **Flexible Deployment**: Works with any remote project location
- **No Directory Creation**: Assumes project structure exists (via git clone)
- **Absolute Paths**: No ambiguity about where files go

### **Example Deployment Scenarios**
```bash
# Different remote locations
python cloud_env_uploader.py --env=prod --host=user@server --remote-repo-root-path=/opt/myapp
python cloud_env_uploader.py --env=prod --host=admin@server --remote-repo-root-path=/var/www/myapp  
python cloud_env_uploader.py --env=prod --host=deploy@server --remote-repo-root-path=/home/deploy/myapp
```

---

## 🔒 **Safety Features**

### **Absolute Path Deployment**
- Uses absolute remote paths (e.g., `/opt/your-project/backend/.env.docker.app.prod`)
- No directory creation - assumes git clone created project structure
- Direct SCP upload to exact target location

### **Overwrite Protection**
- Script checks for existing files before upload
- Prompts for confirmation if files already exist
- Use `--force` flag to skip confirmation (use with caution)

### **Supported Environments**
- Supports `prod` and `staging` environments only  
- Uses actual environment file names from your project structure
- Prevents accidental uploads to wrong environments

### **File Validation**
- Checks if local environment files exist before upload
- Verifies successful uploads
- Shows exact local and remote file paths

---

## ⚡ **Container Behavior with New Images**

### **Important: Existing Containers Don't Auto-Update**

**Q: Do existing containers automatically use new images?**
**A: NO! Existing containers continue running the OLD image until manually rebuilt.**

```bash
# Current container keeps running old image
docker ps  # Shows container with old image hash

# New image exists but isn't used
docker images  # Shows new image, but container still uses old one

# To use new image, you MUST rebuild:
python backend_docker_manager.py stop --prod
python backend_docker_manager.py start --prod --build
```

### **Why Containers Don't Auto-Update**
- **Stability**: Running containers are isolated from new builds
- **Zero-Downtime**: You choose when to switch to new version
- **Rollback Safety**: Old container can be kept running during updates

### **Image vs Container Relationship**
```
Environment Files → New Docker Image → New Container
     ↓                    ↓               ↓
 (.env files)      (docker build)    (docker run)

Old Container ← Old Image ← Old Env Files
(still running)  (still exists)  (overwritten)
```

---

## 🚀 **Quick Deployment Commands**

### **Full Production Deployment**
```bash
# 1. Generate requirements (LOCAL - one-time setup)
cd backend && uv pip compile --python-platform linux --python-version 3.10 requirements.in -o requirements-linux.txt --upgrade

# 2. Update code (on cloud VM)
git pull origin main

# 3. Upload environments (from local machine - run from project root)
python cloud_env_uploader.py --env=prod --host=user@cloud-vm --remote-repo-root-path=/opt/your-project

# 4. Start database containers FIRST (on cloud VM)
cd backend/docker/database && python db_manager.py start --env=prod

# 5. Rebuild application containers with new security features (on cloud VM)
cd ../../ && python backend_docker_manager.py restart --prod
cd ../CodeSandbox && python docker_setup_and_run.py restart --env=prod

# 6. Verify deployment
cd ../backend && python backend_docker_manager.py health --prod
cd docker/database && python db_manager.py health --env=prod
```

### **Staging Deployment**
```bash
# Generate requirements (LOCAL - if not already done)
cd backend && uv pip compile --python-platform linux --python-version 3.10 requirements.in -o requirements-linux.txt --upgrade

# Same process but for staging (on cloud VM)
git pull origin main
python cloud_env_uploader.py --env=staging --host=user@staging-vm --remote-repo-root-path=/opt/your-project

# Start database containers
cd backend/docker/database && python db_manager.py start --env=staging

# Rebuild application containers with new security features
cd ../../ && python backend_docker_manager.py restart --staging
cd ../CodeSandbox && python docker_setup_and_run.py restart --env=staging
```

---

## 🔍 **Troubleshooting**

### **Database Container Issues**
```
ERROR: Failed to connect to database
```
**Solutions:**
1. **Database containers not started**: Run `cd backend/docker/database && python db_manager.py start --env=prod`
2. **Database not ready**: Check status with `python db_manager.py health --env=prod`
3. **Port conflicts**: Ensure database ports aren't already in use

### **Container Build Failures**
```
Error: .env file not found
```
**Solution:** You forgot Step 2! Upload environment files first.

```
Error: Could not connect to database during build
```
**Solution:** Start database containers first (Step 3) before building application containers.

### **Docker Networking Issues**
```
Error: connection refused (localhost)
```
**Solution:** Environment files are using localhost instead of service names.

**❌ Wrong (localhost pattern):**
```bash
DATABASE_URL=postgresql://user:pass@localhost:5433/db
REDIS_URL=redis://:password@localhost:6380/0
```

**✅ Correct (service discovery pattern):**
```bash  
DATABASE_URL=postgresql://user:pass@postgres:5432/db
REDIS_URL=redis://:password@redis:6379/0
```

### **Missing --remote-repo-root-path Argument**
```
Error: --remote-repo-root-path is required for upload operation
```
**Solution:** Specify where your project is deployed on the remote server:
```bash
python cloud_env_uploader.py --env=prod --host=user@vm --remote-repo-root-path=/opt/your-project
```

### **SSH Connection Issues**

#### **Permission Denied (Public Key)**
```
Permission denied (publickey)
```
**Solutions:**
1. **SSH key not set up**: Follow the SSH key setup in Prerequisites section
2. **Wrong username**: Verify the correct username for your cloud VM
3. **SSH key not loaded**: Run `ssh-add ~/.ssh/id_rsa` to load your key

#### **Permission Denied (Password)**
```
user@host: Permission denied, please try again.
```
**Solutions:**
1. **Wrong password**: Double-check your cloud VM password
2. **Password auth disabled**: Server may only accept SSH keys
3. **Account locked**: Too many failed attempts may lock the account

#### **Connection Timeout**
```
ssh: connect to host cloud-vm port 22: Connection timed out
```
**Solutions:**
1. **Wrong IP/hostname**: Verify the cloud VM address
2. **Firewall blocking**: Check if port 22 is open
3. **VM not running**: Ensure the cloud VM is started

### **File Not Found Locally**
```
Warning: Local file not found: .env.docker.app.prod
```
**Solution:** Create the missing environment file in your local project.

### **Remote Path Doesn't Exist**
```
scp: /opt/your-project/backend/.env.docker.app.prod: No such file or directory
```
**Solution:** 
1. Verify project was cloned to the correct remote path
2. Check that git clone created the backend/ directory structure

### **Container Won't Start After Rebuild**
1. Check if env files were uploaded correctly
2. Verify env file format and syntax
3. Check Docker logs: `docker logs container-name`

### **Useful Troubleshooting Commands**

#### **Backend Application:**
```bash
cd /opt/your-project/backend

# Check container status
python backend_docker_manager.py status --prod

# Health check
python backend_docker_manager.py health --prod

# View logs
python backend_docker_manager.py logs --prod

# Follow logs in real-time
python backend_docker_manager.py logs --prod --follow

# Validate environment
python backend_docker_manager.py validate --prod
```

#### **Database Containers:**
```bash
cd /opt/your-project/backend/docker/database

# Check database status
python db_manager.py status --env=prod

# Database health check
python db_manager.py health --env=prod

# View database logs
python db_manager.py logs --env=prod

# Validate database setup
python db_manager.py validate --env=prod
```

#### **CodeSandbox:**
```bash
cd /opt/your-project/CodeSandbox

# Validate environment
python docker_setup_and_run.py validate --env=prod

# Check available environments
python docker_setup_and_run.py envs
```

---

## 📝 **Important Notes**

### **🔐 Security & Requirements:**
1. **Use uv for requirements** - Generate platform-specific requirements with `uv pip compile --python-platform linux`
2. **Commit platform requirements** - Add `requirements-linux.txt` to git for deployments  
3. **Never commit `.env` files to git** - they contain secrets
4. **All containers use non-root users** - Enhanced security across all environments

### **🚀 Deployment Best Practices:**
5. **Set up SSH keys first** - avoids multiple password prompts during upload
6. **Test SSH connection** - ensure `ssh user@your-cloud-vm` works before running script
7. **Start database containers FIRST** - applications depend on database services
8. **Always upload env files after git pull** - code won't work without them
9. **Use staging first** - test deployments on staging before prod

### **📁 File Management:**
10. **Files go to S3** - No local upload directories, everything cloud-native
11. **Clean container logs** - Set up centralized logging when ready
12. **Test locally first** - ensure your env files work before uploading
13. **Backup important env files** - keep secure local copies
14. **Use correct script names** - `docker_setup_and_run.py` for CodeSandbox, not `codesandbox_docker_manager.py`

---

## ❌ **Common Mistakes**

### **DON'T:**
- ❌ Use old `requirements.txt` - Use platform-specific `requirements-linux.txt`
- ❌ Install packages as root in containers - Use non-root user installation
- ❌ Use `localhost` in environment files - Use service names (`postgres`, `redis`, etc.)
- ❌ Mix external ports in environment files - Use internal ports (5432, 6379, etc.)
- ❌ Run script without testing SSH connection first
- ❌ Use password auth if you'll upload frequently (set up SSH keys)
- ❌ Start application containers before database containers
- ❌ Start containers without uploading env files first
- ❌ Create local upload directories - Use S3 instead
- ❌ Use wrong script names (e.g., `codesandbox_docker_manager.py` doesn't exist)
- ❌ Commit real env files to git repository  
- ❌ Upload to prod without testing on staging
- ❌ Forget to rebuild containers after env upload

### **DO:**
- ✅ Generate requirements with uv: `uv pip compile --python-platform linux requirements.in -o requirements-linux.txt`
- ✅ Commit `requirements-linux.txt` and `requirements-windows.txt` to git
- ✅ Use Docker service discovery: `postgres:5432`, `redis:6379`, `neo4j:7687`, `qdrant:6333`, `minio:9000`
- ✅ Use internal ports in environment files for container-to-container communication
- ✅ Use S3 for all file uploads (cloud-native architecture)
- ✅ Set up SSH keys for seamless uploads
- ✅ Test SSH connection: `ssh user@your-cloud-vm` before running script
- ✅ Always follow: requirements generation → git pull → env upload → databases → application containers
- ✅ Use correct script names: `docker_setup_and_run.py` for CodeSandbox
- ✅ Start database containers first, then application containers
- ✅ Test environment files locally first
- ✅ Use staging environment for testing deployments
- ✅ Keep secure backups of environment files
- ✅ Trust the non-root security setup in all containers
