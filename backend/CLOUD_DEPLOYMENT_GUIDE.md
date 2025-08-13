# ☁️ Cloud Deployment Guide

## 🚨 **CRITICAL: Environment Upload First!**

**⚠️ ALWAYS upload environment files BEFORE building/starting containers after git pull**

Environment files are NOT in the git repository for security reasons. After pulling code updates, containers will fail to build/start without proper environment files.

---

## 📋 **Prerequisites**

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

### **Step 1: Update Code on Cloud VM**
```bash
# SSH into your cloud VM
ssh user@your-cloud-vm

# Navigate to project directory  
cd /opt/your-project  # or wherever you cloned

# Pull latest code
git pull origin main
```

### **Step 2: Upload Environment Files (REQUIRED)**
```bash
# From your LOCAL machine (not on cloud VM)  
cd your-project

# For Production
python cloud_env_uploader.py --env=prod --host=user@your-cloud-vm --remote-repo-root-path=/opt/your-project

# For Staging  
python cloud_env_uploader.py --env=staging --host=user@staging-vm --remote-repo-root-path=/opt/your-project
```

### **Step 3: Build & Start Containers**
```bash
# Back on cloud VM after env upload
cd /opt/your-project

# Backend
cd backend
python backend_docker_manager.py stop --prod
python backend_docker_manager.py start --prod --build

# CodeSandbox
cd ../CodeSandbox
python codesandbox_docker_manager.py restart --prod
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
# 1. Update code (on cloud VM)
git pull origin main

# 2. Upload environments (from local machine - run from project root)
python cloud_env_uploader.py --env=prod --host=user@cloud-vm --remote-repo-root-path=/opt/your-project

# 3. Rebuild everything (on cloud VM)
cd backend && python backend_docker_manager.py restart --prod
cd ../CodeSandbox && python codesandbox_docker_manager.py restart --prod
```

### **Staging Deployment**
```bash
# Same process but for staging
git pull origin main
python cloud_env_uploader.py --env=staging --host=user@staging-vm --remote-repo-root-path=/opt/your-project
# ... rebuild staging containers
```

---

## 🔍 **Troubleshooting**

### **Container Build Failures**
```
Error: .env file not found
```
**Solution:** You forgot Step 2! Upload environment files first.

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

---

## 📝 **Important Notes**

1. **Set up SSH keys first** - avoids multiple password prompts during upload
2. **Test SSH connection** - ensure `ssh user@your-cloud-vm` works before running script
3. **Never commit `.env` files to git** - they contain secrets
4. **Always upload env files after git pull** - code won't work without them
5. **Test locally first** - ensure your env files work before uploading
6. **Backup important env files** - keep secure local copies
7. **Use staging first** - test deployments on staging before prod

---

## ❌ **Common Mistakes**

### **DON'T:**
- ❌ Run script without testing SSH connection first
- ❌ Use password auth if you'll upload frequently (set up SSH keys)
- ❌ Start containers without uploading env files first
- ❌ Commit real env files to git repository  
- ❌ Upload to prod without testing on staging
- ❌ Forget to rebuild containers after env upload

### **DO:**
- ✅ Set up SSH keys for seamless uploads
- ✅ Test SSH connection: `ssh user@your-cloud-vm` before running script
- ✅ Always follow: git pull → env upload → container rebuild
- ✅ Test environment files locally first
- ✅ Use staging environment for testing deployments
- ✅ Keep secure backups of environment files
