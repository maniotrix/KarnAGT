#!/usr/bin/env python3
"""
Database Manager - Container Lifecycle Management Tool
=====================================================

This tool manages database container infrastructure across all environments (dev, staging, prod).
It focuses exclusively on container lifecycle - does NOT handle application migrations.

Usage:
    python db_manager.py start --env=dev              # Start all database containers
    python db_manager.py stop --env=dev               # Stop all containers  
    python db_manager.py restart --env=dev            # Restart containers
    python db_manager.py status --env=dev             # Container status
    python db_manager.py health --env=dev             # Health check all services
    python db_manager.py logs --env=dev               # View container logs
    python db_manager.py backup --env=dev             # Backup everything
    python db_manager.py validate --env=dev           # Pre-deployment validation
    python db_manager.py validate-passwords --env=dev # Validate password security
    python db_manager.py cleanup --env=dev            # Clean up old resources

Author: Database Infrastructure Team
Version: 1.0.0
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DatabaseManager:
    """
    Database Container Lifecycle Manager
    
    Manages PostgreSQL, Redis, Neo4j, Qdrant, and MinIO containers
    across development, staging, and production environments.
    """
    
    def __init__(self, base_dir: Path = None):
        """Initialize the database manager."""
        self.base_dir = base_dir or Path(__file__).parent
        self.config = self._load_config()
        self.supported_environments = self.config.get('supported_environments', ['dev', 'staging', 'prod', 'prod_aws'])
        self.services = ['postgres', 'redis', 'neo4j', 'qdrant', 'minio']
        
    def _load_config(self) -> Dict:
        """Load configuration from db_config.json or use defaults."""
        config_file = self.base_dir / 'db_config.json'
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration if file doesn't exist
        return {
            "description": "Simplified database infrastructure",
            "supported_environments": ["dev", "staging", "prod"],
            "environments": {
                "dev": {"compose_file": "docker-compose.dev.yml"},
                "staging": {"compose_file": "docker-compose.staging.yml"},
                "prod": {"compose_file": "docker-compose.prod.yml"},
                "prod_aws": {"compose_file": "docker-compose-prod-aws.yml"}
            },
            "settings": {
                "docker_compose_timeout": 300,
                "health_check_timeout": 120
            },
            "required_secrets": [
                "postgres_password.txt",
                "neo4j_auth.txt",
                "minio_user.txt",
                "minio_password.txt"
            ]
        }
    
    def _run_command(self, cmd: List[str], capture_output: bool = False, 
                     cwd: Path = None) -> Tuple[int, str, str]:
        """
        Run a shell command and return status code, stdout, stderr.
        
        Args:
            cmd: Command and arguments as list
            capture_output: Whether to capture and return output
            cwd: Working directory for command
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            cwd = cwd or self.base_dir
            print(f"🔧 Running: {' '.join(cmd)}")
            
            if capture_output:
                result = subprocess.run(
                    cmd, 
                    cwd=cwd, 
                    capture_output=True, 
                    text=True,
                    timeout=self.config['settings']['docker_compose_timeout']
                )
                return result.returncode, result.stdout, result.stderr
            else:
                result = subprocess.run(
                    cmd, 
                    cwd=cwd,
                    timeout=self.config['settings']['docker_compose_timeout']
                )
                return result.returncode, "", ""
                
        except subprocess.TimeoutExpired:
            print(f"❌ Command timed out: {' '.join(cmd)}")
            return 1, "", "Command timed out"
        except Exception as e:
            print(f"❌ Command failed: {e}")
            return 1, "", str(e)
    
    def _validate_environment(self, env: str) -> bool:
        """Validate that environment is supported."""
        if env not in self.supported_environments:
            print(f"❌ Invalid environment: {env}")
            print(f"   Supported environments: {', '.join(self.supported_environments)}")
            return False
        return True
    
    def _get_compose_file(self, env: str) -> Path:
        """Get the Docker Compose file path for environment."""
        env_config = self.config.get('environments', {}).get(env, {})
        compose_file = env_config.get('compose_file', f"docker-compose.{env}.yml")
        return self.base_dir / compose_file
    
    def _validate_password(self, password: str, service: str, env: str) -> Tuple[bool, List[str]]:
        """
        Validate password against security requirements.
        
        Args:
            password: Password to validate
            service: Service name (postgres, neo4j, minio)
            env: Environment (dev, staging, prod)
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        password_config = self.config.get('password_validation', {})
        
        if not password_config.get('enabled', False):
            return True, []
        
        requirements = password_config.get('requirements', {})
        errors = []
        
        # Check pattern (lowercase alphanumeric only)
        pattern = requirements.get('pattern', '^[a-z0-9]+$')
        if not re.match(pattern, password):
            description = requirements.get('description', 'lowercase alphanumeric only')
            reason = requirements.get('reason', 'Invalid character format')
            errors.append(f"Password must be {description}. {reason}")
        
        # Check length
        min_length = requirements.get('min_length', 12)
        max_length = requirements.get('max_length', 128)
        
        if len(password) < min_length:
            errors.append(f"Password too short (minimum {min_length} characters)")
        elif len(password) > max_length:
            errors.append(f"Password too long (maximum {max_length} characters)")
        
        # Check forbidden characters
        forbidden_chars = requirements.get('forbidden_chars', [])
        found_forbidden = [char for char in forbidden_chars if char in password]
        if found_forbidden:
            errors.append(f"Password contains forbidden characters: {', '.join(found_forbidden)}")
        
        # Service-specific validation
        if service == 'neo4j' and ':' in password:
            errors.append("Neo4j passwords cannot contain ':' (conflicts with auth format)")
        
        return len(errors) == 0, errors
    
    def _validate_all_passwords(self, env: str) -> bool:
        """
        Validate all passwords for an environment.
        
        Args:
            env: Environment to validate
            
        Returns:
            True if all passwords are valid
        """
        password_config = self.config.get('password_validation', {})
        
        if not password_config.get('enabled', False):
            print("ℹ️  Password validation disabled")
            return True
        
        print(f"🔐 Validating passwords for {env} environment...")
        
        secrets_dir = self.base_dir / 'secrets' / env
        if not secrets_dir.exists():
            print(f"❌ Secrets directory not found: {secrets_dir}")
            return False
        
        affected_services = password_config.get('affected_services', ['postgres', 'neo4j', 'minio'])
        all_valid = True
        
        # Validate PostgreSQL password
        if 'postgres' in affected_services:
            postgres_file = secrets_dir / 'postgres_password.txt'
            if postgres_file.exists():
                try:
                    password = postgres_file.read_text().strip()
                    is_valid, errors = self._validate_password(password, 'postgres', env)
                    if is_valid:
                        print(f"   ✅ PostgreSQL password: Valid")
                    else:
                        print(f"   ❌ PostgreSQL password: Invalid")
                        for error in errors:
                            print(f"      - {error}")
                        all_valid = False
                except Exception as e:
                    print(f"   ❌ PostgreSQL password: Error reading file - {e}")
                    all_valid = False
        
        # Validate Neo4j password
        if 'neo4j' in affected_services:
            neo4j_file = secrets_dir / 'neo4j_auth.txt'
            if neo4j_file.exists():
                try:
                    auth_content = neo4j_file.read_text().strip()
                    if '/' in auth_content:
                        _, password = auth_content.split('/', 1)
                        is_valid, errors = self._validate_password(password, 'neo4j', env)
                        if is_valid:
                            print(f"   ✅ Neo4j password: Valid")
                        else:
                            print(f"   ❌ Neo4j password: Invalid")
                            for error in errors:
                                print(f"      - {error}")
                            all_valid = False
                    else:
                        print(f"   ❌ Neo4j auth file: Invalid format (expected neo4j/password)")
                        all_valid = False
                except Exception as e:
                    print(f"   ❌ Neo4j password: Error reading file - {e}")
                    all_valid = False
        
        # Validate MinIO password
        if 'minio' in affected_services:
            minio_file = secrets_dir / 'minio_password.txt'
            if minio_file.exists():
                try:
                    password = minio_file.read_text().strip()
                    is_valid, errors = self._validate_password(password, 'minio', env)
                    if is_valid:
                        print(f"   ✅ MinIO password: Valid")
                    else:
                        print(f"   ❌ MinIO password: Invalid")
                        for error in errors:
                            print(f"      - {error}")
                        all_valid = False
                except Exception as e:
                    print(f"   ❌ MinIO password: Error reading file - {e}")
                    all_valid = False
        
        if all_valid:
            print(f"✅ All passwords validated successfully")
        else:
            print(f"❌ Password validation failed")
            requirements = password_config.get('requirements', {})
            print(f"📋 Password requirements:")
            print(f"   - Format: {requirements.get('description', 'lowercase alphanumeric only')}")
            print(f"   - Length: {requirements.get('min_length', 12)}-{requirements.get('max_length', 128)} characters")
            print(f"   - Reason: {requirements.get('reason', 'Security requirement')}")
        
        return all_valid

    
    def _check_prerequisites(self, env: str) -> bool:
        """Check if all prerequisites exist for environment."""
        compose_file = self._get_compose_file(env)
        secrets_dir = self.base_dir / 'secrets' / env
        
        missing = []
        
        if not compose_file.exists():
            missing.append(f"Docker Compose file: {compose_file}")
            
        if not secrets_dir.exists():
            missing.append(f"Secrets directory: {secrets_dir}")
        else:
            # Check for required secret files
            required_secrets = self.config.get('required_secrets', [
                'postgres_password.txt',
                'neo4j_auth.txt',
                'minio_user.txt',
                'minio_password.txt'
            ])
            for secret in required_secrets:
                secret_file = secrets_dir / secret
                if not secret_file.exists():
                    missing.append(f"Secret file: {secret_file}")
        
        if missing:
            print(f"❌ Missing prerequisites for {env} environment:")
            for item in missing:
                print(f"   - {item}")
            return False
        
        # Validate passwords if enabled
        password_config = self.config.get('password_validation', {})
        if password_config.get('validation_on_startup', True):
            if not self._validate_all_passwords(env):
                if password_config.get('fail_on_invalid_passwords', True):
                    print(f"❌ Password validation failed - startup aborted")
                    print(f"💡 Fix passwords or disable validation in db_config.json")
                    return False
                else:
                    print(f"⚠️ Password validation failed - continuing anyway")
            
        return True
    
    def start(self, env: str) -> bool:
        """Start all database containers for environment."""
        print(f"🚀 Starting database containers for {env} environment...")
        
        if not self._validate_environment(env) or not self._check_prerequisites(env):
            return False
        
        compose_file = self._get_compose_file(env)
        
        cmd = [
            'docker-compose',
            '-f', str(compose_file),
            'up', '-d'
        ]
        
        return_code, stdout, stderr = self._run_command(cmd)
        
        if return_code == 0:
            print(f"✅ Successfully started {env} database containers")
            print("🔍 Checking container health...")
            time.sleep(5)  # Give containers time to start
            self.health(env, quiet=True)
            return True
        else:
            print(f"❌ Failed to start {env} containers")
            if stderr:
                print(f"Error: {stderr}")
            return False
    
    def stop(self, env: str) -> bool:
        """Stop all database containers for environment."""
        print(f"🛑 Stopping database containers for {env} environment...")
        
        if not self._validate_environment(env):
            return False
        
        compose_file = self._get_compose_file(env)
        
        cmd = [
            'docker-compose',
            '-f', str(compose_file),
            'down'
        ]
        
        return_code, stdout, stderr = self._run_command(cmd)
        
        if return_code == 0:
            print(f"✅ Successfully stopped {env} database containers")
            return True
        else:
            print(f"❌ Failed to stop {env} containers")
            if stderr:
                print(f"Error: {stderr}")
            return False
    
    def restart(self, env: str) -> bool:
        """Restart all database containers for environment."""
        print(f"🔄 Restarting database containers for {env} environment...")
        
        if self.stop(env):
            time.sleep(2)  # Brief pause between stop and start
            return self.start(env)
        
        return False
    
    def status(self, env: str) -> bool:
        """Show status of all database containers for environment."""
        print(f"📊 Status of database containers for {env} environment:")
        
        if not self._validate_environment(env):
            return False
        
        compose_file = self._get_compose_file(env)
        
        cmd = [
            'docker-compose',
            '-f', str(compose_file),
            'ps'
        ]
        
        return_code, stdout, stderr = self._run_command(cmd, capture_output=True)
        
        if return_code == 0:
            print(stdout)
            return True
        else:
            print(f"❌ Failed to get container status")
            if stderr:
                print(f"Error: {stderr}")
            return False
    
    def health(self, env: str, quiet: bool = False) -> bool:
        """Check health of all database services for environment."""
        if not quiet:
            print(f"🩺 Health check for {env} database services...")
        
        if not self._validate_environment(env):
            return False
        
        # Container name mappings
        containers = {
            'postgres': f'postgres_{env}',
            'redis': f'redis_{env}',
            'neo4j': f'neo4j_{env}',
            'qdrant': f'qdrant_{env}',
            'minio': f'minio_{env}'
        }
        
        all_healthy = True
        
        for service, container_name in containers.items():
            # Check if container is running
            cmd = ['docker', 'ps', '--filter', f'name={container_name}', '--format', 'table {{.Names}}\t{{.Status}}']
            return_code, stdout, stderr = self._run_command(cmd, capture_output=True)
            
            if return_code == 0 and container_name in stdout:
                if 'Up' in stdout:
                    status = "🟢 Running"
                else:
                    status = "🔴 Stopped"
                    all_healthy = False
            else:
                status = "🔴 Not Found"
                all_healthy = False
            
            if not quiet:
                print(f"   {service:>10}: {status}")
        
        if not quiet:
            if all_healthy:
                print("✅ All services healthy")
            else:
                print("❌ Some services have issues")
        
        return all_healthy
    
    def logs(self, env: str, service: str = None, follow: bool = False) -> bool:
        """Show logs for database containers."""
        if service:
            print(f"📋 Logs for {service} service in {env} environment:")
        else:
            print(f"📋 Logs for all database services in {env} environment:")
        
        if not self._validate_environment(env):
            return False
        
        compose_file = self._get_compose_file(env)
        
        cmd = [
            'docker-compose',
            '-f', str(compose_file),
            'logs'
        ]
        
        if follow:
            cmd.append('-f')
            
        if service:
            cmd.append(service)
        
        return_code, stdout, stderr = self._run_command(cmd)
        return return_code == 0
    
    def backup(self, env: str, service: str = None) -> bool:
        """Create backup of database services."""
        if service:
            print(f"💾 Creating backup for {service} service in {env} environment...")
        else:
            print(f"💾 Creating comprehensive backup for all services in {env} environment...")
        
        if not self._validate_environment(env):
            return False
        
        # Create backup directory if it doesn't exist
        backup_dir = self.base_dir / 'backups' / env
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        success = True
        
        services_to_backup = [service] if service else self.services
        
        for svc in services_to_backup:
            backup_file = backup_dir / f"{svc}_backup_{timestamp}.sql"
            print(f"   📦 Backing up {svc}...")
            
            if svc == 'postgres':
                success &= self._backup_postgres(env, backup_file)
            elif svc == 'redis':
                success &= self._backup_redis(env, backup_dir / f"redis_backup_{timestamp}.rdb")
            elif svc == 'neo4j':
                success &= self._backup_neo4j(env, backup_dir / f"neo4j_backup_{timestamp}.dump")
            elif svc == 'qdrant':
                success &= self._backup_qdrant(env, backup_dir / f"qdrant_backup_{timestamp}")
            elif svc == 'minio':
                success &= self._backup_minio(env, backup_dir / f"minio_backup_{timestamp}")
        
        if success:
            print(f"✅ Backup completed successfully")
        else:
            print(f"❌ Some backups failed")
        
        return success
    
    def _backup_postgres(self, env: str, backup_file: Path) -> bool:
        """Backup PostgreSQL database."""
        container_name = f"postgres_{env}"
        
        # Dynamic user and database names based on environment
        env_config = {
            'dev': ('app_dev_user', 'app_dev_db'),
            'staging': ('app_staging_user', 'app_staging_db'),
            'prod': ('app_prod_user', 'app_prod_db')
        }
        
        pg_user, pg_db = env_config.get(env, ('app_dev_user', 'app_dev_db'))
        
        # Create both SQL dump and custom format backup
        try:
            # SQL dump (human readable)
            cmd = [
                'docker', 'exec', '-e', f'PGPASSWORD=$(cat /run/secrets/postgres_password)',
                container_name, 'pg_dump', '-U', pg_user, '-d', pg_db, '--verbose'
            ]
            
            with open(backup_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                print(f"      ❌ PostgreSQL SQL dump failed: {result.stderr}")
                return False
            
            # Custom format backup (for faster restore)
            custom_backup = backup_file.parent / f"postgres_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dump"
            cmd_custom = [
                'docker', 'exec', '-e', f'PGPASSWORD=$(cat /run/secrets/postgres_password)',
                container_name, 'pg_dump', '-U', pg_user, '-d', pg_db, '-Fc', '-v'
            ]
            
            with open(custom_backup, 'wb') as f:
                result = subprocess.run(cmd_custom, stdout=f, stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                print(f"      ✅ PostgreSQL backup: {backup_file}")
                print(f"      ✅ PostgreSQL custom backup: {custom_backup}")
                return True
            else:
                print(f"      ❌ PostgreSQL custom backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"      ❌ PostgreSQL backup failed: {e}")
            return False
    
    def _backup_redis(self, env: str, backup_file: Path) -> bool:
        """Backup Redis database."""
        container_name = f"redis_{env}"
        
        try:
            # Force Redis to create a background save
            cmd_bgsave = [
                'docker', 'exec', container_name,
                'redis-cli', 'BGSAVE'
            ]
            
            result = subprocess.run(cmd_bgsave, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"      ❌ Redis BGSAVE failed: {result.stderr}")
                return False
            
            # Wait for background save to complete
            import time
            time.sleep(2)
            
            # Copy the dump.rdb file from container
            cmd_copy = [
                'docker', 'cp',
                f'{container_name}:/data/dump.rdb',
                str(backup_file)
            ]
            
            result = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"      ✅ Redis backup: {backup_file}")
                return True
            else:
                print(f"      ❌ Redis backup copy failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"      ❌ Redis backup failed: {e}")
            return False
    
    def _backup_neo4j(self, env: str, backup_file: Path) -> bool:
        """Backup Neo4j database."""
        container_name = f"neo4j_{env}"
        
        # Database name based on environment
        db_name = f"app_{env}_graph"
        
        try:
            # Create dump using neo4j-admin
            cmd_dump = [
                'docker', 'exec', container_name,
                'neo4j-admin', 'database', 'dump',
                '--database', db_name,
                '--to-path', '/backups',
                '--overwrite-destination'
            ]
            
            result = subprocess.run(cmd_dump, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"      ❌ Neo4j dump failed: {result.stderr}")
                return False
            
            # Copy the dump file from container
            dump_filename = f"{db_name}.dump"
            cmd_copy = [
                'docker', 'cp',
                f'{container_name}:/backups/{dump_filename}',
                str(backup_file)
            ]
            
            result = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"      ✅ Neo4j backup: {backup_file}")
                
                # Also create a Cypher export for human readability
                cypher_backup = backup_file.parent / f"neo4j_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.cypher"
                cmd_export = [
                    'docker', 'exec', container_name,
                    'cypher-shell', '-u', 'neo4j', '-p', '$(cat /run/secrets/neo4j_auth | cut -d/ -f2)',
                    '-d', db_name,
                    "CALL apoc.export.cypher.all('/backups/export.cypher', {format:'cypher-shell'});"
                ]
                
                export_result = subprocess.run(cmd_export, capture_output=True, text=True)
                if export_result.returncode == 0:
                    # Copy the export file
                    subprocess.run([
                        'docker', 'cp',
                        f'{container_name}:/backups/export.cypher',
                        str(cypher_backup)
                    ], capture_output=True)
                    print(f"      ✅ Neo4j cypher export: {cypher_backup}")
                
                return True
            else:
                print(f"      ❌ Neo4j backup copy failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"      ❌ Neo4j backup failed: {e}")
            return False
    
    def _backup_qdrant(self, env: str, backup_file: Path) -> bool:
        """Backup Qdrant database."""
        container_name = f"qdrant_{env}"
        
        # Get port configuration
        port_config = {
            'dev': 6335,
            'staging': 6337,
            'prod': 6333
        }
        
        port = port_config.get(env, 6335)
        
        try:
            # Create snapshot via API
            cmd_snapshot = [
                'docker', 'exec', container_name,
                'curl', '-X', 'POST', f'http://localhost:6333/snapshots'
            ]
            
            result = subprocess.run(cmd_snapshot, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"      ❌ Qdrant snapshot creation failed: {result.stderr}")
                return False
            
            # Wait for snapshot to be created
            import time
            time.sleep(3)
            
            # Copy the entire storage directory as a tar archive
            backup_dir = backup_file.parent
            tar_file = backup_dir / f"qdrant_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
            
            # Create tar archive of qdrant storage
            cmd_tar = [
                'docker', 'exec', container_name,
                'tar', '-czf', '/tmp/qdrant_backup.tar.gz', '-C', '/qdrant', 'storage', 'snapshots'
            ]
            
            result = subprocess.run(cmd_tar, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"      ❌ Qdrant tar creation failed: {result.stderr}")
                return False
            
            # Copy the tar file from container
            cmd_copy = [
                'docker', 'cp',
                f'{container_name}:/tmp/qdrant_backup.tar.gz',
                str(tar_file)
            ]
            
            result = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"      ✅ Qdrant backup: {tar_file}")
                
                # Also get collection info via API for documentation
                cmd_collections = [
                    'docker', 'exec', container_name,
                    'curl', '-s', f'http://localhost:6333/collections'
                ]
                
                collections_result = subprocess.run(cmd_collections, capture_output=True, text=True)
                if collections_result.returncode == 0:
                    collections_file = backup_dir / f"qdrant_collections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(collections_file, 'w') as f:
                        f.write(collections_result.stdout)
                    print(f"      ✅ Qdrant collections info: {collections_file}")
                
                return True
            else:
                print(f"      ❌ Qdrant backup copy failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"      ❌ Qdrant backup failed: {e}")
            return False
    
    def _backup_minio(self, env: str, backup_file: Path) -> bool:
        """Backup MinIO data."""
        container_name = f"minio_{env}"
        
        try:
            # Create tar archive of MinIO data directory
            backup_dir = backup_file.parent
            tar_file = backup_dir / f"minio_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
            
            # Create tar archive of minio data
            cmd_tar = [
                'docker', 'exec', container_name,
                'tar', '-czf', '/tmp/minio_backup.tar.gz', '-C', '/data', '.'
            ]
            
            result = subprocess.run(cmd_tar, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"      ❌ MinIO tar creation failed: {result.stderr}")
                return False
            
            # Copy the tar file from container
            cmd_copy = [
                'docker', 'cp',
                f'{container_name}:/tmp/minio_backup.tar.gz',
                str(tar_file)
            ]
            
            result = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"      ✅ MinIO backup: {tar_file}")
                
                # Get bucket information and metadata
                bucket_info_file = backup_dir / f"minio_buckets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                
                # List buckets using mc (MinIO client)
                cmd_buckets = [
                    'docker', 'exec', container_name,
                    'find', '/data', '-type', 'd', '-name', '.minio.sys', '-prune', '-o', '-type', 'd', '-print'
                ]
                
                buckets_result = subprocess.run(cmd_buckets, capture_output=True, text=True)
                if buckets_result.returncode == 0:
                    with open(bucket_info_file, 'w') as f:
                        f.write("MinIO Backup Metadata\n")
                        f.write("===================\n")
                        f.write(f"Environment: {env}\n")
                        f.write(f"Backup Date: {datetime.now().isoformat()}\n")
                        f.write(f"Container: {container_name}\n\n")
                        f.write("Directory Structure:\n")
                        f.write(buckets_result.stdout)
                    print(f"      ✅ MinIO metadata: {bucket_info_file}")
                
                # Get object count and sizes
                cmd_stats = [
                    'docker', 'exec', container_name,
                    'du', '-sh', '/data/*'
                ]
                
                stats_result = subprocess.run(cmd_stats, capture_output=True, text=True)
                if stats_result.returncode == 0:
                    stats_file = backup_dir / f"minio_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(stats_file, 'w') as f:
                        f.write("MinIO Storage Statistics\n")
                        f.write("======================\n")
                        f.write(stats_result.stdout)
                    print(f"      ✅ MinIO statistics: {stats_file}")
                
                return True
            else:
                print(f"      ❌ MinIO backup copy failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"      ❌ MinIO backup failed: {e}")
            return False
    
    def validate(self, env: str) -> bool:
        """Validate environment configuration before deployment."""
        print(f"🔍 Validating {env} environment configuration...")
        
        if not self._validate_environment(env):
            return False
        
        # Check all prerequisites
        if not self._check_prerequisites(env):
            return False
        
        # Check Docker is running
        cmd = ['docker', 'info']
        return_code, _, _ = self._run_command(cmd, capture_output=True)
        if return_code != 0:
            print("❌ Docker is not running or accessible")
            return False
        
        # Check Docker Compose is available
        cmd = ['docker-compose', '--version']
        return_code, _, _ = self._run_command(cmd, capture_output=True)
        if return_code != 0:
            print("❌ Docker Compose is not available")
            return False
        
        print(f"✅ {env} environment validation passed")
        return True
    
    def validate_passwords(self, env: str) -> bool:
        """
        Validate passwords for an environment (public method).
        
        Args:
            env: Environment to validate
            
        Returns:
            True if all passwords are valid
        """
        if not self._validate_environment(env):
            return False
        
        return self._validate_all_passwords(env)
    
    def cleanup(self, env: str) -> bool:
        """Clean up old resources for environment."""
        print(f"🧹 Cleaning up old resources for {env} environment...")
        
        if not self._validate_environment(env):
            return False
        
        # Clean up old backup files (keep last 5)
        backup_dir = self.base_dir / 'backups' / env
        if backup_dir.exists():
            for service in self.services:
                service_backups = sorted(backup_dir.glob(f"{service}_backup_*.sql"))
                if len(service_backups) > 5:
                    for old_backup in service_backups[:-5]:
                        old_backup.unlink()
                        print(f"   🗑️ Removed old backup: {old_backup.name}")
        
        # Clean up unused Docker volumes and networks
        print("   🧹 Cleaning up unused Docker resources...")
        self._run_command(['docker', 'system', 'prune', '-f'], capture_output=True)
        
        print(f"✅ Cleanup completed for {env} environment")
        return True


def main():
    """Main entry point for the database manager CLI."""
    parser = argparse.ArgumentParser(
        description="Database Container Lifecycle Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db_manager.py start --env=dev              # Start development databases
  python db_manager.py health --env=prod            # Check production health
  python db_manager.py start --env=prod_aws         # Start AWS EC2 production with EBS volumes
  python db_manager.py validate-passwords --env=prod_aws # Validate AWS production passwords
  python db_manager.py backup --env=staging         # Backup staging databases
  python db_manager.py logs --env=dev --service=postgres  # View PostgreSQL logs
        """
    )
    
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'restart', 'status', 'health', 'logs', 'backup', 'validate', 'validate-passwords', 'cleanup'],
        help='Action to perform'
    )
    
    parser.add_argument(
        '--env',
        choices=['dev', 'staging', 'prod', 'prod_aws'],
        required=True,
        help='Environment to operate on'
    )
    
    parser.add_argument(
        '--service',
        choices=['postgres', 'redis', 'neo4j', 'qdrant', 'minio'],
        help='Specific service to operate on (optional)'
    )
    
    parser.add_argument(
        '--follow',
        action='store_true',
        help='Follow logs (only for logs action)'
    )
    
    args = parser.parse_args()
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Execute requested action
    try:
        if args.action == 'start':
            success = db_manager.start(args.env)
        elif args.action == 'stop':
            success = db_manager.stop(args.env)
        elif args.action == 'restart':
            success = db_manager.restart(args.env)
        elif args.action == 'status':
            success = db_manager.status(args.env)
        elif args.action == 'health':
            success = db_manager.health(args.env)
        elif args.action == 'logs':
            success = db_manager.logs(args.env, args.service, args.follow)
        elif args.action == 'backup':
            success = db_manager.backup(args.env, args.service)
        elif args.action == 'validate':
            success = db_manager.validate(args.env)
        elif args.action == 'validate-passwords':
            success = db_manager.validate_passwords(args.env)
        elif args.action == 'cleanup':
            success = db_manager.cleanup(args.env)
        else:
            print(f"❌ Unknown action: {args.action}")
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⏸️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
