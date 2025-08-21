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
    
    def _run_command(self, command: List[str], description: str = "") -> bool:
        """Run shell command with error handling"""
        try:
            cmd_str = " ".join(command)
            self._info(f"Running: {cmd_str}")
            
            result = subprocess.run(
                command,
                capture_output=False,
                text=True,
                check=True
            )
            return True
            
        except subprocess.CalledProcessError as e:
            self._error(f"{description} failed: {e}")
            return False
        except FileNotFoundError:
            self._error("Docker or docker-compose not found. Please install Docker.")
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
    
    def start(self, env: str) -> bool:
        """Build and start containers for specified environment"""
        self._log(f"🚀 Starting {env} environment...", Colors.CYAN, bold=True)
        
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
    
    def restart(self, env: str) -> bool:
        """Stop, rebuild, and start containers for specified environment"""
        self._log(f"🔄 Restarting {env} environment...", Colors.YELLOW, bold=True)
        
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
        return self.start(env)
    
    def validate(self, env: str) -> bool:
        """Just validate environment without any Docker operations"""
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

{Colors.YELLOW}Examples:{Colors.END}
    python docker_setup_and_run.py start --env=dev
    python docker_setup_and_run.py build --env=prod  
    python docker_setup_and_run.py start --prod-aws
    python docker_setup_and_run.py restart --env=test
    python docker_setup_and_run.py validate --dev
    python docker_setup_and_run.py envs
        """)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Parse environment flag
    env = None
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
            success = manager.start(env)
        elif command == "restart":
            success = manager.restart(env)
        elif command in ["validate", "check"]:
            success = manager.validate(env)
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
