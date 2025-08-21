# Docker Context Validation Guide

## Overview
This safety mechanism prevents accidental production deployments to `prod_aws` environment from local machines without proper Docker Context configuration.

**✅ ZERO IMPACT**: Only validates `prod_aws` environment - all other environments (`dev`, `staging`, `prod`) work normally on any machine.

**✅ ZERO DEPENDENCIES**: Uses only built-in Python libraries - no `pip install` required.

## How It Works

### Comprehensive AWS Detection Methods
The system uses 8 detection methods to identify ANY AWS compute service using **ONLY built-in Python libraries**:

1. **AWS Instance Metadata Service** (Most reliable)
   - Uses `urllib.request` to query `http://169.254.169.254/latest/meta-data/instance-id`
   - Works on EC2, ECS, Fargate, and other AWS compute services

2. **ECS/Fargate Task Metadata**
   - Checks `ECS_CONTAINER_METADATA_URI_V4` and `ECS_CONTAINER_METADATA_URI` environment variables
   - Detects containerized AWS services

3. **AWS Lambda Detection**
   - Checks `AWS_LAMBDA_FUNCTION_NAME` environment variable
   - Detects serverless function environments

4. **AWS Batch Detection**
   - Checks `AWS_BATCH_JOB_ID` environment variable
   - Detects batch computing environments

5. **Hypervisor UUID Check**
   - Reads `/sys/hypervisor/uuid` for EC2/Amazon identifiers
   - EC2-specific hardware characteristics

6. **DMI Product Information**
   - Reads `/sys/class/dmi/id/product_name` directly (no external commands)
   - Detects Amazon hardware without `dmidecode` dependency

7. **AWS Hostname Pattern Analysis**
   - Analyzes hostname for AWS-specific patterns: `ec2`, `aws`, `amazon`, `compute-1`, `ip-10-`, etc.
   - Covers most AWS naming conventions

8. **AWS Network Interface Detection**
   - Checks for AWS-specific network interfaces: `ens5`, `ens6`, `ens7`
   - Common on AWS instances

### Running Directly on AWS Instances

When you SSH into an AWS instance and run the deployment scripts directly, the validation system automatically detects the AWS environment and **completely bypasses Docker context validation**:

**🚀 AWS Instance Deployment Flow:**
```
1. User runs: python db_manager.py start --env=prod_aws
2. AWS Detection: ✅ Running on AWS: True (using methods above)
3. Context Check: ✅ BYPASSED - AWS environment detected
4. Deployment: ✅ Proceeds immediately without any context validation
```

**Expected Output:**
```bash
$ python backend/docker/database/db_manager.py start --env=prod_aws
🚀 Starting database containers for prod_aws environment...
ℹ️  Environment: prod_aws
ℹ️  Running on AWS: True
ℹ️  Docker context: default
✅ Running on AWS instance - deployment allowed
🔐 Setting up AWS environment variables from secrets folder...
✅ Loaded POSTGRES_PASSWORD from postgres_password.txt
✅ Loaded NEO4J_AUTH from neo4j_auth.txt
✅ Loaded MINIO_ROOT_USER from minio_user.txt  
✅ Loaded MINIO_ROOT_PASSWORD from minio_password.txt
🔐 Successfully loaded 4 AWS environment variables
Creating network "prod_aws_network" with the default driver
Creating postgres_prod ... done
Creating redis_prod ... done
Creating neo4j_prod ... done
Creating qdrant_prod ... done
Creating minio_prod ... done
✅ Database containers started successfully for prod_aws environment
```

**Key Benefits of Direct AWS Deployment:**
- ✅ **Zero Configuration**: No Docker context setup required
- ✅ **Automatic Detection**: Works on EC2, ECS, Fargate, Lambda, Batch
- ✅ **Immediate Deployment**: No confirmation prompts or countdown timers
- ✅ **Built-in Safety**: Still protected by environment-specific validation
- ✅ **Full Compatibility**: Works with any Docker context (default, etc.)

**Supported AWS Services:**
- ✅ **EC2 Instances**: All instance types and sizes
- ✅ **ECS Tasks**: Both EC2 and Fargate launch types
- ✅ **AWS Fargate**: Serverless containers
- ✅ **AWS Lambda**: Function environments (if Docker available)  
- ✅ **AWS Batch**: Batch computing jobs

### Docker Context Validation
- Checks current Docker context using `docker context show`
- Validates if context is appropriate for production deployment

## Safety Behavior

### Scenario 1: Running on AWS Instance ✅
```bash
# On ANY AWS compute service (EC2, ECS, Fargate, Lambda, Batch, etc.)
python backend/docker/database/db_manager.py start --env=prod_aws

# Output:
🚀 Starting database containers for prod_aws environment...
ℹ️  Environment: prod_aws
ℹ️  Running on AWS: True
ℹ️  Docker context: default
✅ Running on AWS instance - deployment allowed
# Deployment proceeds...
```

### Scenario 2: Local Machine with Default Context ❌
```bash
# On local machine
python backend/docker/database/db_manager.py start --env=prod_aws

# Output:
🚀 Starting database containers for prod_aws environment...
ℹ️  Environment: prod_aws
ℹ️  Running on AWS: False  
ℹ️  Docker context: default
🚫 DEPLOYMENT BLOCKED!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRODUCTION DEPLOYMENT SAFETY CHECK FAILED 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  You are trying to deploy prod_aws from a local machine
⚠️  Your current Docker context is: default

📋 To deploy prod_aws environment, you must:

1. Set up Docker Context for AWS EC2:
   docker context create aws-prod --docker "host=ssh://ec2-user@your-elastic-ip"

2. Switch to AWS context:
   docker context use aws-prod

3. Verify context:
   docker context show

4. Then re-run your deployment command

Alternative: SSH into EC2 and run directly:
   ssh -i your-key.pem ec2-user@your-elastic-ip

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Script exits with error code
```

### Scenario 3: Local Machine with AWS Context ✅
```bash
# Set up Docker context first
docker context create aws-prod --docker "host=ssh://ec2-user@52.23.45.67"
docker context use aws-prod

# Then deploy
python backend/docker/database/db_manager.py start --env=prod_aws

# Output:
🚀 Starting database containers for prod_aws environment...
ℹ️  Environment: prod_aws
ℹ️  Running on AWS: False
ℹ️  Docker context: aws-prod
✅ Docker context validation passed: aws-prod
# Deployment proceeds via Docker Context...
```

### Scenario 4: Suspicious Context Warning ⚠️
```bash
# With non-AWS context
docker context use staging-server
python backend/docker/database/db_manager.py start --env=prod_aws

# Output:
🚀 Starting database containers for prod_aws environment...
ℹ️  Environment: prod_aws
ℹ️  Running on AWS: False
ℹ️  Docker context: staging-server
⚠️  Docker context 'staging-server' doesn't seem AWS-related
⚠️  Make sure you're deploying to the correct environment

ℹ️  Proceeding in 5 seconds... Press Ctrl+C to cancel
# User has 5 seconds to cancel before deployment proceeds
```

### Scenario 5: Skip Validation Flag (Override) ✅
```bash
# Use --skip-validation to bypass validation for any cloud provider (GCP, Azure, etc.)
python backend/docker/database/db_manager.py start --env=prod_aws --skip-validation
python backend/backend_docker_manager.py start --env=prod_aws --skip-validation
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=prod_aws --skip-validation
python CodeSandbox/docker_setup_and_run.py start --prod-aws --skip-validation

# Output with validation bypass:
🚀 Starting prod_aws environment...
⚠️  Validation skipped via --skip-validation flag
⚠️  Ensure you're deploying to the correct environment!
# Deployment proceeds without any validation checks
```

### Scenario 6: Development/Staging Environments (No Validation) ✅
```bash
# ALL of these work normally on ANY machine - NO validation applied:

# Development environments
python backend/docker/database/db_manager.py start --env=dev
python backend/backend_docker_manager.py start --env=dev
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=dev
python CodeSandbox/docker_setup_and_run.py start --env=dev

# Staging environments  
python backend/docker/database/db_manager.py start --env=staging
python backend/backend_docker_manager.py start --env=staging

# Regular production environments
python backend/docker/database/db_manager.py start --env=prod
python backend/backend_docker_manager.py start --env=prod

# Output: Normal startup without any validation checks
🚀 Starting [environment] environment...
# No AWS detection or context validation performed
```

## Setting Up Docker Context

## Supported AWS Services

The validation detects **ALL** AWS compute services:

| AWS Service | Detection Method | Support Level |
|-------------|-----------------|---------------|
| **EC2 Instances** | Metadata + UUID + DMI | ✅ **Full Support** |
| **ECS Tasks** | Task Metadata URI | ✅ **Full Support** |
| **Fargate Tasks** | Task Metadata URI | ✅ **Full Support** |
| **AWS Lambda** | Environment Variables | ✅ **Full Support** |
| **AWS Batch** | Environment Variables | ✅ **Full Support** |
| **Lightsail** | Metadata + Hostname | ✅ **Likely Support** |
| **WorkSpaces** | Hostname Patterns | ✅ **Likely Support** |
| **Any AWS Linux** | Multiple Methods | ✅ **Broad Support** |

### Zero Dependencies ✅
- **No `pip install` required** - uses only Python standard library
- **No external tools** - no `curl`, `dmidecode`, or other system commands
- **Works on any Python 3.5+** installation
- **Self-contained detection** - no network dependencies except AWS metadata

## Automated Secrets Management

For `prod_aws` environment, the `db_manager.py` script **automatically loads secrets** from the local `secrets/prod_aws/` folder into environment variables:

```bash
# Database manager automatically loads these files:
backend/docker/database/secrets/prod_aws/postgres_password.txt    → POSTGRES_PASSWORD
backend/docker/database/secrets/prod_aws/neo4j_auth.txt          → NEO4J_AUTH
backend/docker/database/secrets/prod_aws/minio_user.txt          → MINIO_ROOT_USER
backend/docker/database/secrets/prod_aws/minio_password.txt      → MINIO_ROOT_PASSWORD
```

**Example Output:**
```
🔐 Setting up AWS environment variables from secrets folder...
✅ Loaded POSTGRES_PASSWORD from postgres_password.txt
✅ Loaded NEO4J_AUTH from neo4j_auth.txt
✅ Loaded MINIO_ROOT_USER from minio_user.txt
✅ Loaded MINIO_ROOT_PASSWORD from minio_password.txt
🔐 Successfully loaded 4 AWS environment variables
```

## Quick Override for Other Cloud Providers

For deployments on **GCP, Azure, DigitalOcean, or any non-AWS cloud**:

```bash
# Simply add --skip-validation flag
python backend/docker/database/db_manager.py start --env=prod_aws --skip-validation
python backend/backend_docker_manager.py start --env=prod_aws --skip-validation
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=prod_aws --skip-validation
python CodeSandbox/docker_setup_and_run.py start --prod-aws --skip-validation
```

**⚠️ Use responsibly**: This bypasses all safety checks - ensure you're on the correct machine/environment.

## Setting Up Docker Context

### 1. Create AWS Docker Context
```bash
# Replace with your actual Elastic IP
docker context create aws-prod --docker "host=ssh://ec2-user@52.23.45.67"
```

### 2. List Available Contexts
```bash
docker context ls

# Output:
NAME        DESCRIPTION                         DOCKER ENDPOINT                     
default *   Current DOCKER_HOST based config   unix:///var/run/docker.sock        
aws-prod    AWS EC2 Production                  ssh://ec2-user@52.23.45.67
```

### 3. Switch to AWS Context
```bash
docker context use aws-prod
```

### 4. Verify Context
```bash
docker context show
# Output: aws-prod

# Test connection
docker ps
# Should show containers running on EC2
```

### 5. Switch Back to Local
```bash
docker context use default
```

## Implementation Details

### Files Modified
The validation has been integrated into **ALL** Docker manager scripts:

1. **`backend/backend_docker_manager.py`** ✅
   - Added EC2 detection methods
   - Added Docker context validation
   - Integrated into `start()` method

2. **`backend/docker/database/db_manager.py`** ✅
   - Added same validation methods
   - Integrated into `start()` method
   - Returns `False` to prevent deployment

3. **`frontend/chatgpt-frontend/frontend_docker_manager.py`** ✅
   - Added EC2 detection methods
   - Added Docker context validation
   - Integrated into `start()` method

4. **`CodeSandbox/docker_setup_and_run.py`** ✅
   - Added EC2 detection methods
   - Added Docker context validation
   - Integrated into `start()` method

### Validation Logic Flow
```python
def _validate_deployment_context(self, environment: str) -> bool:
    if environment != 'prod_aws':
        return True  # Only validate prod_aws
        
    is_ec2 = self._is_running_on_ec2()
    current_context = self._get_docker_context()
    
    if is_ec2:
        return True  # EC2 deployment allowed
        
    if current_context == 'default':
        # Block deployment with detailed instructions
        return False
        
    if 'aws' not in current_context.lower():
        # Warn but allow (with 5-second cancel window)
        pass
        
    return True
```

## Benefits

### 1. **Prevents Accidents**
- No accidental production deployments from development machines
- Clear error messages with instructions
- Multiple confirmation layers

### 2. **Flexible Deployment**
- Direct deployment on ANY AWS instance (bypass validation)
- Docker Context remote deployment from local machines
- Warning system for suspicious contexts

### 3. **Developer Experience**
- Clear instructions when blocked
- Multiple deployment options provided
- Quick setup guide included in error message
- **Zero impact on existing workflows** - only `prod_aws` is validated

### 4. **Security**
- Production environment isolation
- Controlled deployment paths
- Audit trail of deployment method

### 5. **Zero Dependencies**
- Uses only Python standard library modules
- No `pip install` required
- No external system tools needed
- Works on any Python 3.5+ installation

### 6. **Flexible Override**
- `--skip-validation` flag for GCP, Azure, or other cloud providers
- Clear warning messages when validation is bypassed
- Maintains safety while allowing flexibility

## Testing the Validation

### Test All Manager Scripts on Local Machine (Should Block)
```bash
# ALL of these should be blocked with the same safety message:

# Database layer
python backend/docker/database/db_manager.py start --env=prod_aws

# Backend API
python backend/backend_docker_manager.py start --env=prod_aws

# Frontend
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=prod_aws

# CodeSandbox
python CodeSandbox/docker_setup_and_run.py start --env=prod_aws
```

### Test Non-Production Environments (Should Work Fine)
```bash
# ALL of these should work without any validation:

# Development environments
python backend/docker/database/db_manager.py start --env=dev
python backend/backend_docker_manager.py start --env=dev
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=dev
python CodeSandbox/docker_setup_and_run.py start --env=dev

# Staging environments
python backend/docker/database/db_manager.py start --env=staging
python backend/backend_docker_manager.py start --env=staging
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=staging
python CodeSandbox/docker_setup_and_run.py start --env=staging
```

### Test with Docker Context (Should Allow All)
```bash
# Set up Docker Context
docker context create test-aws --docker "host=ssh://user@test-server"
docker context use test-aws

# ALL production deployments should now work:
python backend/docker/database/db_manager.py start --env=prod_aws
python backend/backend_docker_manager.py start --env=prod_aws
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=prod_aws
python CodeSandbox/docker_setup_and_run.py start --env=prod_aws
```

### Test on AWS Instance (Should Allow All)
```bash
# SSH into ANY AWS instance (EC2, ECS, Fargate, etc.)
ssh -i key.pem ec2-user@your-elastic-ip

# ALL should work without any Docker context setup:
python backend/docker/database/db_manager.py start --env=prod_aws
python backend/backend_docker_manager.py start --env=prod_aws
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=prod_aws
python CodeSandbox/docker_setup_and_run.py start --env=prod_aws
```

### Complete Deployment Test Sequence
```bash
# Full deployment sequence (in correct order) - should work on AWS or with Docker Context:

# 1. Database layer (creates prod_aws_network + automated secrets loading)
python backend/docker/database/db_manager.py start --env=prod_aws

# 2. Build backend (don't start yet)
python backend/backend_docker_manager.py build --env=prod_aws

# 3. Run database migrations (CRITICAL - before backend starts)
docker-compose -f backend/docker-compose-prod-aws.yml run --rm app-backend-prod python run_migrations.py

# 4. Start backend API
python backend/backend_docker_manager.py start --env=prod_aws

# 5. Frontend
python frontend/chatgpt-frontend/frontend_docker_manager.py start --env=prod_aws --build

# 6. CodeSandbox
python CodeSandbox/docker_setup_and_run.py start --prod-aws
```

## Customization

### Environment Override
To disable validation temporarily (NOT recommended for production):
```bash
export SKIP_AWS_VALIDATION=true
python backend/docker/database/db_manager.py start --env=prod_aws
```

### Add to Other Environments
To extend validation to other environments:
```python
def _validate_deployment_context(self, environment: str) -> bool:
    if environment not in ['prod_aws', 'prod']:  # Add 'prod' here
        return True
    # ... validation logic
```

### Custom Context Patterns
To accept additional context patterns:
```python
# In validation logic
valid_patterns = ['aws', 'prod', 'ec2', 'amazon']
if any(pattern in current_context.lower() for pattern in valid_patterns):
    # Allow deployment
    pass
```

## Deployment Methods Comparison

| Deployment Method | Location | AWS Detection | Context Check | Setup Required | Security Level |
|-------------------|----------|---------------|---------------|----------------|----------------|
| **Direct on AWS Instance** | SSH into EC2/ECS/Fargate | ✅ **True** | ❌ **BYPASSED** | ✅ **None** | 🔒 **Highest** |
| **Docker Context (Valid)** | Local machine | ❌ False | ✅ **aws-prod** | ⚠️  Context setup | 🔒 **High** |
| **Docker Context (Suspicious)** | Local machine | ❌ False | ⚠️  **some-server** | ⚠️  Context setup | ⚠️  **8-sec warning** |
| **Desktop Context** | Local machine | ❌ False | 🚫 **desktop-linux** | ❌ **BLOCKED** | 🛡️ **Protected** |
| **Default Context** | Local machine | ❌ False | 🚫 **default** | ❌ **BLOCKED** | 🛡️ **Protected** |

### Example Outputs

**✅ AWS Instance (Recommended):**
```bash
ℹ️  Environment: prod_aws
ℹ️  Running on AWS: True
ℹ️  Docker context: default
✅ Running on AWS instance - deployment allowed
# → Immediate deployment, no delays
```

**✅ Valid Docker Context:**
```bash
ℹ️  Environment: prod_aws  
ℹ️  Running on AWS: False
ℹ️  Docker context: aws-prod
✅ Docker context validation passed: aws-prod
# → Immediate deployment, no delays
```

**⚠️ Suspicious Docker Context:**
```bash
ℹ️  Environment: prod_aws
ℹ️  Running on AWS: False  
ℹ️  Docker context: some-server
⚠️  Context 'some-server' doesn't appear to be AWS-related
⚠️  Proceeding in 8 seconds... Press Ctrl+C to cancel
✅ Strict context validation passed: some-server
# → 8-second warning, then proceeds
```

**🚫 Blocked Context:**
```bash
ℹ️  Environment: prod_aws
ℹ️  Running on AWS: False
ℹ️  Docker context: desktop-linux
🚫 DEPLOYMENT BLOCKED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CONTEXT 'DESKTOP-LINUX' IS BLOCKED FOR PROD_AWS 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# → Deployment stopped, clear instructions provided
```

## Troubleshooting

### Docker Context Issues
```bash
# Context not working
docker context inspect aws-prod

# Remove broken context  
docker context rm aws-prod

# Recreate context
docker context create aws-prod --docker "host=ssh://ec2-user@new-ip"
```

### SSH Connection Issues
```bash
# Test SSH connectivity first
ssh -i your-key.pem ec2-user@your-elastic-ip

# Add SSH key if needed
ssh-add your-key.pem

# Fix SSH config
cat >> ~/.ssh/config << EOF
Host aws-prod
    HostName your-elastic-ip
    User ec2-user
    IdentityFile ~/path/to/your-key.pem
EOF

# Use SSH config in Docker context
docker context create aws-prod --docker "host=ssh://aws-prod"
```

### EC2 Detection Issues
If EC2 detection fails on actual EC2 instances:
```bash
# Test metadata service manually
curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/instance-id

# Check system characteristics
cat /sys/hypervisor/uuid 2>/dev/null || echo "Not found"
sudo dmidecode -s system-version 2>/dev/null || echo "Not found"
hostname
```

## Conclusion

This validation system provides a robust safety net for production deployments while maintaining flexibility for different deployment workflows. It prevents the most common cause of accidental production deployments while providing clear guidance on proper deployment procedures.

The system is designed to be:
- **Fail-safe**: Blocks by default, allows only with explicit configuration
- **Informative**: Provides clear error messages and setup instructions  
- **Flexible**: Supports multiple deployment methods
- **Extensible**: Easy to add to other manager scripts

---
**Security Note**: This validation is a safety mechanism, not a security control. Proper access controls, network security, and deployment pipelines should still be implemented for production systems.
