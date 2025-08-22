#!/usr/bin/env python3
"""
Minimal Docker Manager
A lightweight, JSON-configurable Docker orchestration tool.

Core Purpose: Get containers up and running for different environments seamlessly.
Not a replacement for docker-compose commands, just a convenient wrapper.
"""

import json
import subprocess
import sys
import os
import platform
import socket
import time
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


class DockerManager:
    """Lightweight Docker manager focused on essential operations only"""
    
    def __init__(self, config_file: str = "docker_setup_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        
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
        countdown_seconds = config.get('countdown_seconds', 60)
        
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
        """Run shell command with real-time output streaming"""
        try:
            cmd_str = " ".join(command)
            self._info(f"Running: {cmd_str}")
            
            # Use Popen for real-time output streaming
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip(), flush=True)
            
            # Wait for process to complete and get return code
            return_code = process.poll()
            
            if return_code == 0:
                return True
            else:
                self._error(f"{description} failed with exit code: {return_code}")
                return False
            
        except FileNotFoundError:
            self._error("Docker or docker-compose not found. Please install Docker.")
            return False
        except Exception as e:
            self._error(f"{description} failed: {e}")
            return False
    
    def _check_docker_available(self) -> bool:
        """Check if Docker and docker-compose are available"""
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _validate_environment(self, env: str) -> Tuple[bool, str]:
        """Essential validation before Docker operations with detailed logging"""
        
        self._log(f"🔍 Validating '{env}' environment...", Colors.CYAN)
        
        # Check if environment exists in config
        if env not in self.config["environments"]:
            available = ", ".join(self.config["environments"].keys())
            self._error(f"Unknown environment '{env}'. Available: {available}")
            return False, f"Unknown environment '{env}'. Available: {available}"
        
        self._log(f"   ✅ Environment '{env}' found in config", Colors.GREEN)
        
        # Check Docker availability
        self._log("   🐳 Checking Docker availability...", Colors.BLUE)
        if not self._check_docker_available():
            self._error("   ❌ Docker or docker-compose not available")
            return False, "Docker or docker-compose not available"
        
        self._log("   ✅ Docker and docker-compose are available", Colors.GREEN)
        
        # Check required files exist
        env_config = self.config["environments"][env]
        missing_files = []
        validation_passed = True
        
        self._log("   📁 Validating required files...", Colors.BLUE)
        
        required_files = [
            ("compose_file", "Docker Compose file"),
            ("dockerfile", "Dockerfile"),
            ("env_file", "Environment file")
        ]
        
        for key, description in required_files:
            if key in env_config:
                file_path = env_config[key]
                if Path(file_path).exists():
                    self._log(f"   ✅ {description}: {file_path}", Colors.GREEN)
                else:
                    self._log(f"   ❌ {description}: {file_path} (NOT FOUND)", Colors.RED)
                    missing_files.append(f"{description}: {file_path}")
                    validation_passed = False
            else:
                self._log(f"   ⚠️  {description}: Not specified in config", Colors.YELLOW)
        
        if missing_files:
            files_list = "\n   - ".join(missing_files)
            error_msg = f"Missing files for '{env}' environment:\n   - {files_list}"
            self._error("Validation failed - missing required files")
            return False, error_msg
        
        self._success(f"Environment '{env}' validation passed")
        return True, "All required files present"
    
    def _get_env_config(self, env: str) -> Dict:
        """Get configuration for specific environment"""
        return self.config["environments"][env]
    
    def build(self, env: str) -> bool:
        """Build Docker image for specified environment"""
        self._log(f"🔨 Building {env} environment...", Colors.YELLOW, bold=True)
        
        # Check for Docker Context SSH build limitation
        current_context = self._get_docker_context()
        if current_context != 'default':
            # Check if this looks like an SSH context
            if ('ssh://' in current_context or 
                current_context.startswith(('aws-', 'ec2-', 'prod-')) or
                current_context in ['aws-prod', 'ec2-prod']):
                
                self._error("🚫 DOCKER BUILD LIMITATION DETECTED!")
                print()
                print(f"{Colors.RED}{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
                print(f"{Colors.RED}{Colors.BOLD} SSH CONTEXT CANNOT BUILD DOCKER IMAGES {Colors.END}")
                print(f"{Colors.RED}{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
                print()
                print(f"{Colors.YELLOW}⚠️  Current context: {current_context}{Colors.END}")
                print(f"{Colors.YELLOW}⚠️  Docker Context with SSH endpoints cannot build images{Colors.END}")
                print(f"{Colors.YELLOW}⚠️  Error you would get: 'Builder error Docker context using an SSH endpoint is not supported at the moment.'{Colors.END}")
                print()
                print(f"{Colors.CYAN}📋 Build alternatives:{Colors.END}")
                print("1. Build directly on EC2 instance:")
                print(f"{Colors.GREEN}   ssh karnagt-ec2{Colors.END}")
                print(f"{Colors.GREEN}   python CodeSandbox/docker_setup_and_run.py build --env={env}{Colors.END}")
                print()
                print("2. Build locally then deploy (hybrid approach):")
                print(f"{Colors.GREEN}   docker context use default{Colors.END}")
                print(f"{Colors.GREEN}   python CodeSandbox/docker_setup_and_run.py build --env={env}{Colors.END}")
                print(f"{Colors.GREEN}   # Push to registry then deploy to EC2{Colors.END}")
                print()
                print(f"{Colors.RED}{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
                return False
        
        # Validate first
        is_valid, message = self._validate_environment(env)
        if not is_valid:
            self._error(message)
            return False
        
        env_config = self._get_env_config(env)
        
        # Build the image
        command = [
            "docker-compose",
            "-f", env_config["compose_file"],
            "build", env_config["service_name"]
        ]
        
        success = self._run_command(command, f"Build {env}")
        
        if success:
            self._success(f"{env} environment built successfully")
        
        return success
    
    def start(self, env: str, skip_validation: bool = False) -> bool:
        """Build and start containers for specified environment"""
        self._log(f"🚀 Starting {env} environment...", Colors.CYAN, bold=True)
        
        # Validate deployment context for prod_aws
        self._validate_deployment_context(env, skip_validation)
        
        # Check for Docker Context SSH build limitation (start method builds by default)
        current_context = self._get_docker_context()
        if current_context != 'default':
            # Check if this looks like an SSH context
            if ('ssh://' in current_context or 
                current_context.startswith(('aws-', 'ec2-', 'prod-')) or
                current_context in ['aws-prod', 'ec2-prod']):
                
                self._error("🚫 DOCKER BUILD WITH SSH CONTEXT DETECTED!")
                print()
                print(f"{Colors.YELLOW}⚠️  Current context: {current_context}{Colors.END}")
                print(f"{Colors.YELLOW}⚠️  start command builds by default and cannot work with SSH contexts{Colors.END}")
                print(f"{Colors.CYAN}💡 Use: python CodeSandbox/docker_setup_and_run.py start --env={env} (on EC2 directly){Colors.END}")
                return False
        
        # Build first
        if not self.build(env):
            return False
        
        env_config = self._get_env_config(env)
        
        # Start containers
        command = [
            "docker-compose", 
            "-f", env_config["compose_file"],
            "up", "-d", env_config["service_name"]
        ]
        
        success = self._run_command(command, f"Start {env}")
        
        if success:
            self._success(f"{env} environment started successfully")
            self._info(f"Use 'docker-compose -f {env_config['compose_file']} logs -f' to view logs")
        
        return success
    
    def restart(self, env: str, skip_validation: bool = False) -> bool:
        """Stop, rebuild, and start containers for specified environment"""
        self._log(f"🔄 Restarting {env} environment...", Colors.YELLOW, bold=True)
        
        # Validate deployment context for prod_aws
        self._validate_deployment_context(env, skip_validation)
        
        # Validate first
        is_valid, message = self._validate_environment(env)
        if not is_valid:
            self._error(message)
            return False
        
        env_config = self._get_env_config(env)
        
        # Stop containers
        self._info(f"Stopping {env} containers...")
        stop_command = [
            "docker-compose",
            "-f", env_config["compose_file"],
            "down"
        ]
        
        if not self._run_command(stop_command, f"Stop {env}"):
            return False
        
        # Build and start
        return self.start(env, skip_validation=skip_validation)
    
    def validate(self, env: str, skip_validation: bool = False) -> bool:
        """Validate environment setup and deployment context"""
        self._info(f"Validating {env} environment...")
        
        # Validate deployment context first (like db_manager does)
        self._validate_deployment_context(env, skip_validation)
        
        is_valid, message = self._validate_environment(env)
        if not is_valid:
            self._error("Environment validation failed")
            return False
        
        self._success(f"Environment '{env}' is ready for Docker operations")
        return True
    
    def show_environments(self) -> None:
        """Show available environments from config with validation status"""
        self._log("📋 Available Environments:", Colors.CYAN, bold=True)
        
        for env_name, env_config in self.config["environments"].items():
            description = env_config.get("description", "No description")
            default_marker = " (default)" if env_name == self.config["default_environment"] else ""
            
            # Quick validation check for display
            is_valid = True
            missing_files = []
            
            required_files = [
                ("compose_file", "Compose"),
                ("dockerfile", "Dockerfile"),
                ("env_file", "Env file")
            ]
            
            for key, short_name in required_files:
                if key in env_config:
                    file_path = env_config[key]
                    if not Path(file_path).exists():
                        is_valid = False
                        missing_files.append(short_name)
            
            # Status indicator
            if is_valid:
                status = f"{Colors.GREEN}✅ Ready{Colors.END}"
            else:
                missing_str = ", ".join(missing_files)
                status = f"{Colors.RED}❌ Missing: {missing_str}{Colors.END}"
            
            self._log(f"   • {env_name}{default_marker}: {description}", Colors.WHITE)
            self._log(f"     {status}", Colors.WHITE)


def main():
    """Main entry point"""
    
    # Parse arguments
    if len(sys.argv) < 2:
        print(f"""
{Colors.CYAN}{Colors.BOLD}Minimal Docker Manager{Colors.END}

{Colors.YELLOW}Usage:{Colors.END}
    python docker_setup_and_run.py <command> [--env=<environment>]

{Colors.YELLOW}Commands:{Colors.END}
    {Colors.GREEN}build{Colors.END}      Build image for environment
    {Colors.GREEN}start{Colors.END}      Build and start containers  
    {Colors.GREEN}restart{Colors.END}    Stop, rebuild, and start containers
    {Colors.GREEN}validate{Colors.END}   Validate environment setup (files, Docker availability)
    {Colors.GREEN}envs{Colors.END}       Show available environments with validation status

{Colors.YELLOW}Options:{Colors.END}
    {Colors.GREEN}--skip-validation{Colors.END}   Skip deployment context validation (useful for GCP, Azure, etc.)

{Colors.YELLOW}Examples:{Colors.END}
    python docker_setup_and_run.py start --env=dev
    python docker_setup_and_run.py build --env=prod  
    python docker_setup_and_run.py start --prod-aws
    python docker_setup_and_run.py start --prod-aws --skip-validation
    python docker_setup_and_run.py restart --env=test
    python docker_setup_and_run.py validate --dev
    python docker_setup_and_run.py envs
        """)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Parse environment flag and options
    env = None
    skip_validation = False
    for arg in sys.argv[2:]:
        if arg.startswith("--env="):
            env = arg.split("=", 1)[1]
        elif arg in ["--dev", "-d"]:
            env = "dev"
        elif arg in ["--prod", "-p"]:
            env = "prod"
        elif arg == "--prod-aws":
            env = "prod_aws"
        elif arg in ["--test", "-t"]:
            env = "test"
        elif arg == "--skip-validation":
            skip_validation = True
    
    try:
        manager = DockerManager()
        
        # Handle commands that don't need environment
        if command == "envs":
            manager.show_environments()
            return
        
        # For other commands, determine environment
        if not env:
            env = manager.config["default_environment"]
            manager._info(f"Using default environment: {env}")
        
        # Execute command
        if command == "build":
            success = manager.build(env)
        elif command == "start":
            success = manager.start(env, skip_validation=skip_validation)
        elif command == "restart":
            success = manager.restart(env, skip_validation=skip_validation)
        elif command in ["validate", "check"]:
            success = manager.validate(env, skip_validation=skip_validation)
        else:
            manager._error(f"Unknown command: {command}")
            sys.exit(1)
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Operation interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ Unexpected error: {e}{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()
