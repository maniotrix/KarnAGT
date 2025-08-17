#!/usr/bin/env python3
"""
Backend Docker Manager
A lightweight, JSON-configurable Docker orchestration tool for Application Backend.

Core Purpose: Get backend containers up and running for different environments seamlessly.
Follows the same pattern as CodeSandbox docker manager.
"""

import json
import subprocess
import sys
import os
import time
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


class BackendDockerManager:
    """Lightweight Docker manager for Application Backend containers"""
    
    def __init__(self, config_file: str = "backend_docker_config.json"):
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
    
    def _get_database_network_name(self, env: str) -> Optional[str]:
        """Get database network name for environment - now uses unified network"""
        return self._get_network_name(env)
    
    def _get_codesandbox_network_name(self, env: str) -> Optional[str]:
        """Get CodeSandbox network name for environment - now uses unified network"""
        return self._get_network_name(env)
    
    def _check_prerequisites(self, env: str) -> bool:
        """Check if all required files exist for the environment"""
        env_config = self._get_env_config(env)
        issues = []
        
        # Check required files
        required_files = [
            env_config['compose_file'],
            env_config['dockerfile'],
            env_config['env_file']
        ]
        
        for file_path in required_files:
            if not (self.base_dir / file_path).exists():
                issues.append(f"Missing file: {file_path}")
        
        # Check unified network configuration (used by database and CodeSandbox services)
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
                self._info(f"💡 Start database services first: python docker/database/db_manager.py start --env={env}")
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
    
    def validate(self, env: str) -> None:
        """Validate environment setup"""
        self._info(f"Validating {env} environment...")
        
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
                print(f"   🏗️ Services: Backend, Database services, CodeSandbox, Traefik")
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
    
    def start(self, env: str, build: bool = False) -> None:
        """Start containers for environment"""
        self._info(f"Starting {env} environment...")
        
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
                    response = requests.get('http://localhost:8000/api/v1/health', timeout=5)
                    if response.status_code == 200:
                        self._success("Backend API health check passed")
                    else:
                        self._warning(f"Backend API health check returned status {response.status_code}")
                except ImportError:
                    self._info("Install requests to enable API health checks: pip install requests")
                except Exception as e:
                    self._warning(f"Backend API health check failed: {e}")
            else:
                self._error(f"Container {service_name} is not running")
                
        except subprocess.CalledProcessError:
            self._error("Failed to check container status")


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Application Backend Docker Manager")
    parser.add_argument('command', choices=['envs', 'validate', 'build', 'start', 'stop', 'restart', 'status', 'logs', 'health'],
                       help='Command to execute')
    parser.add_argument('--env', '--environment', default=None,
                       help='Environment to use (dev, staging, prod)')
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
    
    args = parser.parse_args()
    
    # Handle environment shortcuts
    if args.dev:
        args.env = 'dev'
    elif args.staging:
        args.env = 'staging'
    elif args.prod:
        args.env = 'prod'
    
    manager = BackendDockerManager()
    
    # Commands that don't need environment
    if args.command == 'envs':
        manager.envs()
        return
    
    # Commands that need environment
    if not args.env:
        args.env = manager.config['default_environment']
        print(f"Using default environment: {args.env}")
    
    if args.command == 'validate':
        manager.validate(args.env)
    elif args.command == 'build':
        manager.build(args.env)
    elif args.command == 'start':
        manager.start(args.env, build=args.build)
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
