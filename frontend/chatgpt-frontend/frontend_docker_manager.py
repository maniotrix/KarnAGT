#!/usr/bin/env python3
"""
Frontend Docker Manager
A lightweight, JSON-configurable Docker orchestration tool for Application Frontend.

Core Purpose: Get frontend containers up and running for different environments seamlessly.
Follows the same pattern as Backend docker manager.
"""

import json
import subprocess
import sys
import os
import time
import platform
import socket
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class Colors:
    """ANSI color codes for output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class FrontendDockerManager:
    """Lightweight Docker manager for Application Frontend containers"""
    
    def __init__(self, config_file: str = "frontend_docker_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.base_dir = Path(__file__).parent
        
    def _load_config(self) -> Dict:
        """Load and validate JSON configuration"""
        try:
            if not Path(self.config_file).exists():
                self._error(f"Config file not found: {self.config_file}")
                sys.exit(1)
                
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            # Basic structure validation
            required_keys = ['project_name', 'environments', 'default_environment']
            for key in required_keys:
                if key not in config:
                    self._error(f"Missing required key in config: {key}")
                    sys.exit(1)
                    
            return config
            
        except json.JSONDecodeError as e:
            self._error(f"Invalid JSON in config file: {e}")
            sys.exit(1)
        except Exception as e:
            self._error(f"Failed to load config: {e}")
            sys.exit(1)
    
    def _log(self, message: str, color: str = Colors.WHITE, bold: bool = False) -> None:
        """Print colored log message"""
        timestamp = f"{Colors.CYAN}[{datetime.now().strftime('%H:%M:%S')}]{Colors.END}"
        style = f"{Colors.BOLD if bold else ''}{color}"
        print(f"{timestamp} {style}{message}{Colors.END}")
    
    def _error(self, message: str) -> None:
        """Print error message"""
        self._log(f"❌ {message}", Colors.RED, bold=True)
    
    def _success(self, message: str) -> None:
        """Print success message"""
        self._log(f"✅ {message}", Colors.GREEN, bold=True)
    
    def _info(self, message: str) -> None:
        """Print info message"""
        self._log(f"ℹ️  {message}", Colors.BLUE)
    
    def _warning(self, message: str) -> None:
        """Print warning message"""
        self._log(f"⚠️ {message}", Colors.YELLOW)
    
    def _is_running_on_aws(self) -> bool:
        """Detect if script is running on AWS (EC2, ECS, Fargate, etc.) - Uses ONLY built-in Python libraries"""
        try:
            # Method 1: AWS Instance Metadata Service (works on EC2, ECS, Fargate)
            try:
                request = urllib.request.Request(
                    'http://169.254.169.254/latest/meta-data/instance-id',
                    headers={'User-Agent': 'AWS-Instance-Detection/1.0'}
                )
                with urllib.request.urlopen(request, timeout=3) as response:
                    instance_id = response.read().decode('utf-8').strip()
                    if instance_id and (instance_id.startswith('i-') or len(instance_id) > 10):
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError, OSError):
                pass
            
            # Method 2: Check for AWS Task Metadata (ECS/Fargate)
            if os.environ.get('ECS_CONTAINER_METADATA_URI_V4') or os.environ.get('ECS_CONTAINER_METADATA_URI'):
                return True
                
            # Method 3: Check AWS Lambda/Batch environments
            if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('AWS_BATCH_JOB_ID'):
                return True
                
            # Method 4: Check hypervisor UUID (EC2 characteristic)
            try:
                if os.path.exists('/sys/hypervisor/uuid'):
                    with open('/sys/hypervisor/uuid', 'r') as f:
                        uuid = f.read().strip()
                        if uuid.startswith(('ec2', 'EC2')):
                            return True
            except:
                pass
                
            # Method 5: Check DMI product name (without external commands)
            try:
                if os.path.exists('/sys/class/dmi/id/product_name'):
                    with open('/sys/class/dmi/id/product_name', 'r') as f:
                        product = f.read().strip().lower()
                        if any(keyword in product for keyword in ['amazon', 'ec2']):
                            return True
            except:
                pass
                
            # Method 6: Check hostname patterns
            try:
                hostname = socket.gethostname().lower()
                aws_patterns = ['ec2', 'aws', 'amazon', 'compute-1', 'ip-10-', 'ip-172-', 'ip-192-168-']
                if any(pattern in hostname for pattern in aws_patterns):
                    return True
            except:
                pass
                
            return False
            
        except Exception:
            return False
    
    def _get_docker_context(self) -> str:
        """Get current Docker context"""
        try:
            result = subprocess.run(['docker', 'context', 'show'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
            return 'default'
        except Exception:
            return 'default'
    
    def _validate_deployment_context(self, environment: str, skip_validation: bool = False) -> None:
        """JSON-configured environment-specific deployment context validation"""
        validation_config = self._get_context_validation_config(environment)
        
        if not validation_config:
            return
            
        if skip_validation:
            self._warning("Validation skipped via --skip-validation flag")
            self._warning("Ensure you're deploying to the correct environment!")
            return
            
        is_aws = self._is_running_on_aws()
        current_context = self._get_docker_context()
        
        self._info(f"Environment: {environment}")
        self._info(f"Running on AWS: {is_aws}")
        self._info(f"Docker context: {current_context}")
        
        if validation_config.get('aws_detection_enabled', False) and is_aws:
            self._success("✅ Running on AWS instance - deployment allowed")
            return
            
        blocked_contexts = validation_config.get('blocked_contexts', [])
        if current_context in blocked_contexts:
            self._handle_blocked_context_json(environment, current_context, validation_config)
            
        allowed_patterns = validation_config.get('allowed_context_patterns', ['*'])
        if not self._is_context_allowed(current_context, allowed_patterns):
            self._handle_disallowed_context_json(environment, current_context, validation_config)
            
        validation_level = validation_config.get('validation_level', 'strict')
        if validation_level == 'strict':
            self._handle_strict_validation_json(environment, current_context, validation_config)
            
        self._success(f"✅ Docker context validation passed: {current_context}")
    
    def _get_context_validation_config(self, environment: str) -> Optional[Dict]:
        """Get context validation configuration from JSON config for specific environment"""
        try:
            validation_config = self.config.get('context_validation', {})
            enabled_environments = validation_config.get('enabled_environments', [])
            
            if environment not in enabled_environments:
                return None
                
            env_config = validation_config.get(environment)
            if not env_config:
                self._warning(f"Context validation enabled for {environment} but no rules found")
                return None
                
            return env_config
            
        except Exception as e:
            self._warning(f"Error loading context validation config: {e}")
            return None
    
    def _is_context_allowed(self, context: str, allowed_patterns: List[str]) -> bool:
        """Check if context matches any allowed pattern"""
        import fnmatch
        
        for pattern in allowed_patterns:
            if pattern == '*' or fnmatch.fnmatch(context.lower(), pattern.lower()):
                return True
        return False
    
    def _handle_blocked_context_json(self, environment: str, context: str, config: Dict) -> None:
        """Handle explicitly blocked contexts using JSON config"""
        error_msg = config.get('error_messages', {}).get('blocked_context', 
                               "Context '{context}' is blocked for {environment} deployments")
        
        self._error("🚫 DEPLOYMENT BLOCKED!")
        print()
        print(f"{Colors.RED}{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
        print(f"{Colors.RED}{Colors.BOLD} CONTEXT '{context.upper()}' IS BLOCKED FOR {environment.upper()} {Colors.END}")
        print(f"{Colors.RED}{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
        print()
        print(f"{Colors.YELLOW}⚠️  {error_msg.format(context=context, environment=environment)}{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  This is a safety measure to prevent accidental deployments{Colors.END}")
        print()
        print(f"{Colors.CYAN}📋 Allowed deployment methods:{Colors.END}")
        print()
        
        instructions = config.get('deployment_instructions', [])
        for i, instruction in enumerate(instructions, 1):
            if instruction.strip():
                if instruction.startswith('  '):
                    print(f"{Colors.GREEN}{instruction}{Colors.END}")
                else:
                    print(f"{i}. {instruction}")
            else:
                print()
        
        print()
        print("3. Override with --skip-validation (use with caution):")
        print(f"{Colors.GREEN}   python script.py {environment} --skip-validation{Colors.END}")
        print()
        print(f"{Colors.RED}{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
        sys.exit(1)
    
    def _handle_disallowed_context_json(self, environment: str, context: str, config: Dict) -> None:
        """Handle contexts not in allowed patterns list using JSON config"""
        error_msg = config.get('error_messages', {}).get('disallowed_pattern',
                               "Context '{context}' doesn't match allowed patterns for {environment}")
        
        allowed_patterns = config.get('allowed_context_patterns', [])
        
        self._error(f"{error_msg.format(context=context, environment=environment)}")
        self._info(f"📋 Allowed context patterns: {', '.join(allowed_patterns)}")
        self._info("💡 Use --skip-validation to override if this is intentional")
        sys.exit(1)
    
    def _handle_strict_validation_json(self, environment: str, context: str, config: Dict) -> None:
        """Handle strict validation using JSON config"""
        aws_warning = config.get('error_messages', {}).get('aws_warning',
                                 "Context '{context}' doesn't appear to be AWS-related")
        countdown_seconds = config.get('countdown_seconds', 5)
        
        aws_indicators = ['aws', 'prod', 'production', 'ec2']
        has_aws_indicator = any(indicator in context.lower() for indicator in aws_indicators)
        
        if not has_aws_indicator:
            self._warning(f"{aws_warning.format(context=context)}")
            self._info(f"Proceeding in {countdown_seconds} seconds... Press Ctrl+C to cancel")
            try:
                time.sleep(countdown_seconds)
            except KeyboardInterrupt:
                print()
                self._info("Deployment cancelled by user")
                sys.exit(1)
        
        self._success(f"✅ Strict context validation passed: {context}")
    
    def _run_command(self, command: List[str], description: str = "") -> bool:
        """Run shell command with error handling"""
        try:
            cmd_str = " ".join(command)
            self._info(f"Running: {cmd_str}")
            
            result = subprocess.run(
                command,
                capture_output=False,
                text=True,
                check=True,
                cwd=self.base_dir
            )
            return True
            
        except subprocess.CalledProcessError as e:
            self._error(f"{description} failed: {e}")
            return False
        except FileNotFoundError:
            self._error("Docker or docker-compose not found. Please install Docker.")
            return False
    
    def _get_env_config(self, env: str) -> Dict:
        """Get configuration for specific environment"""
        if env not in self.config['environments']:
            self._error(f"Environment '{env}' not found in config")
            available = ", ".join(self.config['environments'].keys())
            self._info(f"Available environments: {available}")
            sys.exit(1)
        return self.config['environments'][env]
    
    def _get_network_name(self, env: str) -> Optional[str]:
        """Get unified network name for environment from JSON config"""
        env_config = self._get_env_config(env)
        return env_config.get('network')
    
    def _check_prerequisites(self, env: str) -> bool:
        """Check if all required files exist for the environment"""
        env_config = self._get_env_config(env)
        issues = []
        
        # Check required files (no env_file needed for frontend)
        required_files = [
            env_config['compose_file'],
            env_config['dockerfile']
        ]
        
        for file_path in required_files:
            if not (self.base_dir / file_path).exists():
                issues.append(f"Missing file: {file_path}")
        
        # Check unified network configuration (created by database services)
        unified_network = self._get_network_name(env)
        if unified_network:
            self._info(f"Unified network configured: {unified_network}")
            
            # Check if network exists
            try:
                result = subprocess.run([
                    'docker', 'network', 'inspect', unified_network
                ], capture_output=True, check=True)
                self._success(f"Unified network '{unified_network}' exists")
            except subprocess.CalledProcessError:
                self._warning(f"Unified network '{unified_network}' not found")
                self._info(f"💡 Start database services first: python ../../backend/docker/database/db_manager.py start --env={env}")
                self._info(f"💡 Then start backend: python ../../backend/backend_docker_manager.py start --env={env}")
                self._info(f"💡 This will create the unified network for all services")
                issues.append(f"Unified network '{unified_network}' not found")
            except Exception as e:
                self._error(f"Error checking unified network: {e}")
                issues.append(f"Error checking unified network: {e}")
        else:
            self._warning(f"No unified network configured for {env} environment in config file")
            issues.append("No unified network configured")
        
        # Check if Docker is available
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues.append("Docker is not installed or not accessible")
        
        # Check if docker-compose is available
        try:
            subprocess.run(['docker', 'compose', 'version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(['docker-compose', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                issues.append("docker-compose is not installed or not accessible")
        
        if issues:
            self._error("Prerequisites check failed:")
            for issue in issues:
                print(f"  • {issue}")
            return False
        
        return True
    
    def validate(self, env: str, skip_validation: bool = False) -> None:
        """Validate environment setup and deployment context"""
        self._info(f"Validating {env} environment...")
        
        # Validate deployment context first (like db_manager does)
        self._validate_deployment_context(env, skip_validation)
        
        if self._check_prerequisites(env):
            self._success(f"Environment '{env}' validation passed")
        else:
            sys.exit(1)
    
    def envs(self) -> None:
        """List available environments and their status"""
        self._info(f"Available environments for {self.config['project_name']}:")
        print()
        
        for env_name, env_config in self.config['environments'].items():
            status_icon = "🟢" if self._check_prerequisites(env_name) else "🔴"
            default_marker = " (default)" if env_name == self.config['default_environment'] else ""
            
            print(f"{status_icon} {Colors.BOLD}{env_name}{default_marker}{Colors.END}")
            print(f"   📄 Compose: {env_config['compose_file']}")
            print(f"   🐳 Service: {env_config['service_name']}")  
            print(f"   📝 Description: {env_config['description']}")
            
            # Show unified network info
            unified_network = self._get_network_name(env_name)
            if unified_network:
                print(f"   🔗 Unified Network: {unified_network}")
                print(f"   🏗️ Services: Frontend connects to Backend, Database services, CodeSandbox via Traefik")
            else:
                print(f"   🔗 Unified Network: Not configured")
            print()
    
    def build(self, env: str) -> None:
        """Build container image for environment"""
        self._info(f"Building {env} environment...")
        
        if not self._check_prerequisites(env):
            sys.exit(1)
        
        env_config = self._get_env_config(env)
        compose_file = env_config['compose_file']
        
        success = self._run_command([
            'docker', 'compose', '-f', compose_file, 'build'
        ], f"Build {env}")
        
        if success:
            self._success(f"Build completed for {env} environment")
        else:
            sys.exit(1)
    
    def start(self, env: str, build: bool = False, skip_validation: bool = False) -> None:
        """Start containers for environment"""
        self._info(f"Starting {env} environment...")
        
        # Validate deployment context for prod_aws
        self._validate_deployment_context(env, skip_validation)
        
        if not self._check_prerequisites(env):
            sys.exit(1)
        
        env_config = self._get_env_config(env)
        compose_file = env_config['compose_file']
        
        # Build and start command
        cmd = ['docker', 'compose', '-f', compose_file, 'up', '-d']
        if build:
            cmd.append('--build')
        
        success = self._run_command(cmd, f"Start {env}")
        
        if success:
            self._success(f"{env.title()} environment started successfully")
            time.sleep(2)  # Give containers time to start
            self._info("Checking container health...")
            self.status(env)
            
            # Show access info
            env_config = self._get_env_config(env)
            domain = env_config.get('domain', 'localhost')
            if env == 'dev':
                self._info(f"🌐 Frontend available at: https://{domain}")
                self._info(f"📊 Traefik dashboard: http://localhost:8080") 
            else:
                self._info(f"🌐 Frontend available at: https://{domain}")
        else:
            sys.exit(1)
    
    def stop(self, env: str) -> None:
        """Stop containers for environment"""
        self._info(f"Stopping {env} environment...")
        
        env_config = self._get_env_config(env)
        compose_file = env_config['compose_file']
        
        success = self._run_command([
            'docker', 'compose', '-f', compose_file, 'down'
        ], f"Stop {env}")
        
        if success:
            self._success(f"{env.title()} environment stopped")
        else:
            sys.exit(1)
    
    def restart(self, env: str) -> None:
        """Restart containers for environment"""
        self._info(f"Restarting {env} environment...")
        self.stop(env)
        time.sleep(2)
        self.start(env, build=True)
    
    def status(self, env: str) -> None:
        """Show status of containers for environment"""
        env_config = self._get_env_config(env)
        compose_file = env_config['compose_file']
        
        self._info(f"Container status for {env} environment:")
        self._run_command([
            'docker', 'compose', '-f', compose_file, 'ps'
        ], f"Status {env}")
    
    def logs(self, env: str, follow: bool = False) -> None:
        """Show logs for environment"""
        env_config = self._get_env_config(env)
        compose_file = env_config['compose_file']
        
        cmd = ['docker', 'compose', '-f', compose_file, 'logs']
        if follow:
            cmd.append('-f')
        
        self._info(f"Showing logs for {env} environment" + (" (following)" if follow else ""))
        self._run_command(cmd, f"Logs {env}")
    
    def health(self, env: str) -> None:
        """Check health of containers"""
        env_config = self._get_env_config(env)
        service_name = env_config['service_name']
        
        self._info(f"Health check for {env} environment:")
        
        # Check if container is running
        try:
            result = subprocess.run([
                'docker', 'ps', '--filter', f'name={service_name}', '--format', 'table {{.Names}}\t{{.Status}}'
            ], capture_output=True, text=True, check=True)
            
            if service_name in result.stdout:
                self._success(f"Container {service_name} is running")
                
                # Try to health check endpoint if available
                try:
                    import requests
                    health_endpoint = self.config['service'].get('health_check', '/')
                    test_url = f'http://localhost:3000{health_endpoint}'
                    response = requests.get(test_url, timeout=5)
                    if response.status_code == 200:
                        self._success("Frontend health check passed")
                    else:
                        self._warning(f"Frontend health check returned status {response.status_code}")
                except ImportError:
                    self._info("Install requests to enable health checks: pip install requests")
                except Exception as e:
                    self._warning(f"Frontend health check failed: {e}")
            else:
                self._error(f"Container {service_name} is not running")
                
        except subprocess.CalledProcessError:
            self._error("Failed to check container status")


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Application Frontend Docker Manager")
    parser.add_argument('command', choices=['envs', 'validate', 'build', 'start', 'stop', 'restart', 'status', 'logs', 'health'],
                       help='Command to execute')
    parser.add_argument('--env', '--environment', default=None,
                       choices=['dev', 'staging', 'prod', 'prod_aws'],
                       help='Environment to use (dev, staging, prod, prod_aws)')
    parser.add_argument('--build', action='store_true',
                       help='Build images before starting (for start command)')
    parser.add_argument('--follow', '-f', action='store_true',
                       help='Follow logs (for logs command)')
    parser.add_argument('--dev', action='store_true',
                       help='Shorthand for --env=dev')
    parser.add_argument('--staging', action='store_true',
                       help='Shorthand for --env=staging')
    parser.add_argument('--prod', action='store_true',
                       help='Shorthand for --env=prod')
    parser.add_argument('--prod-aws', action='store_true',
                       help='Shorthand for --env=prod_aws')
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip deployment context validation (useful for GCP, Azure, etc.)')
    
    args = parser.parse_args()
    
    # Handle environment shortcuts
    if args.dev:
        args.env = 'dev'
    elif args.staging:
        args.env = 'staging'
    elif args.prod:
        args.env = 'prod'
    elif getattr(args, 'prod_aws', False):
        args.env = 'prod_aws'
    
    manager = FrontendDockerManager()
    
    # Commands that don't need environment
    if args.command == 'envs':
        manager.envs()
        return
    
    # Commands that need environment
    if not args.env:
        args.env = manager.config['default_environment']
        print(f"Using default environment: {args.env}")
    
    if args.command == 'validate':
        manager.validate(args.env, skip_validation=args.skip_validation)
    elif args.command == 'build':
        manager.build(args.env)
    elif args.command == 'start':
        manager.start(args.env, build=args.build, skip_validation=args.skip_validation)
    elif args.command == 'stop':
        manager.stop(args.env)
    elif args.command == 'restart':
        manager.restart(args.env)
    elif args.command == 'status':
        manager.status(args.env)
    elif args.command == 'logs':
        manager.logs(args.env, follow=args.follow)
    elif args.command == 'health':
        manager.health(args.env)


if __name__ == "__main__":
    main()
