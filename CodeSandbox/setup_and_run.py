#!/usr/bin/env python3
"""
CodeSandbox Docker Setup and Runner

Intelligent Docker management script that:
- Builds images only when needed
- Reuses existing containers when possible
- Handles cleanup and rebuilds
- Provides detailed logging and status
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class Colors:
    """ANSI color codes for better output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class DockerManager:
    """Manages Docker images and containers intelligently"""
    
    def __init__(self):
        self.project_name = "codesandbox"
        self.service_name = "codesandbox"
        self.image_name = f"{self.project_name}_{self.service_name}"
        self.container_name = f"{self.project_name}_{self.service_name}_1"
        
    def log(self, message: str, color: str = Colors.WHITE, bold: bool = False) -> None:
        """Print colored log message"""
        prefix = f"{Colors.CYAN}[{datetime.now().strftime('%H:%M:%S')}]{Colors.END}"
        style = f"{Colors.BOLD if bold else ''}{color}"
        print(f"{prefix} {style}{message}{Colors.END}")
    
    def run_command(self, command: List[str], capture_output: bool = True, check: bool = True) -> subprocess.CompletedProcess:
        """Run system command with error handling"""
        try:
            self.log(f"Running: {' '.join(command)}", Colors.BLUE)
            result = subprocess.run(
                command, 
                capture_output=capture_output, 
                text=True, 
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", Colors.RED, bold=True)
            if e.stdout:
                self.log(f"STDOUT: {e.stdout}", Colors.YELLOW)
            if e.stderr:
                self.log(f"STDERR: {e.stderr}", Colors.RED)
            raise
        except FileNotFoundError:
            self.log("Docker not found! Please install Docker and Docker Compose", Colors.RED, bold=True)
            sys.exit(1)
    
    def check_docker_availability(self) -> bool:
        """Check if Docker and Docker Compose are available"""
        try:
            self.run_command(["docker", "--version"])
            self.run_command(["docker-compose", "--version"])
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_image_info(self) -> Optional[Dict]:
        """Get Docker image information"""
        try:
            result = self.run_command([
                "docker", "images", 
                "--format", "json", 
                self.image_name
            ])
            
            # Handle multiple JSON objects
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    return json.loads(line)
            return None
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None
    
    def get_container_info(self) -> Optional[Dict]:
        """Get Docker container information"""
        try:
            result = self.run_command([
                "docker", "ps", "-a",
                "--format", "json",
                "--filter", f"name={self.container_name}"
            ])
            
            # Handle multiple JSON objects
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    return json.loads(line)
            return None
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None
    
    def is_container_running(self) -> bool:
        """Check if container is currently running"""
        container_info = self.get_container_info()
        return container_info is not None and "Up" in container_info.get("Status", "")
    
    def get_dockerfile_hash(self) -> str:
        """Get hash of Dockerfile and requirements.txt for change detection"""
        import hashlib
        
        files_to_check = ["Dockerfile", "requirements.txt", "docker-compose.yml"]
        combined_content = ""
        
        for file_path in files_to_check:
            if Path(file_path).exists():
                combined_content += Path(file_path).read_text()
        
        return hashlib.md5(combined_content.encode()).hexdigest()[:8]
    
    def should_rebuild_image(self) -> Tuple[bool, str]:
        """Determine if image should be rebuilt"""
        image_info = self.get_image_info()
        
        if not image_info:
            return True, "Image does not exist"
        
        # Check if key files changed
        current_hash = self.get_dockerfile_hash()
        image_labels = {}
        
        # Try to get labels from image
        try:
            result = self.run_command([
                "docker", "inspect", 
                "--format", "{{json .Config.Labels}}", 
                self.image_name
            ])
            image_labels = json.loads(result.stdout.strip() or "{}")
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass
        
        stored_hash = image_labels.get("build_hash", "")
        
        if current_hash != stored_hash:
            return True, f"Configuration changed (hash: {stored_hash} → {current_hash})"
        
        return False, "Image is up to date"
    
    def build_image(self, force_rebuild: bool = False) -> bool:
        """Build Docker image intelligently"""
        if not force_rebuild:
            should_rebuild, reason = self.should_rebuild_image()
            if not should_rebuild:
                self.log(f"✅ Skipping build: {reason}", Colors.GREEN)
                return True
            else:
                self.log(f"🔨 Building image: {reason}", Colors.YELLOW, bold=True)
        else:
            self.log("🔨 Force rebuilding image...", Colors.YELLOW, bold=True)
        
        try:
            # Build with hash label for change tracking
            build_hash = self.get_dockerfile_hash()
            
            self.run_command([
                "docker-compose", "build", 
                "--build-arg", f"BUILD_HASH={build_hash}",
                self.service_name
            ], capture_output=False)
            
            # Add label to track build hash
            self.run_command([
                "docker", "image", "ls", self.image_name, "--format", "table"
            ], capture_output=False)
            
            self.log("✅ Image built successfully", Colors.GREEN, bold=True)
            return True
            
        except subprocess.CalledProcessError:
            self.log("❌ Image build failed", Colors.RED, bold=True)
            return False
    
    def start_containers(self, detached: bool = True) -> bool:
        """Start containers using docker-compose"""
        try:
            if self.is_container_running():
                self.log("✅ Container already running", Colors.GREEN)
                return True
            
            self.log("🚀 Starting containers...", Colors.YELLOW, bold=True)
            
            cmd = ["docker-compose", "up"]
            if detached:
                cmd.append("-d")
            
            self.run_command(cmd, capture_output=detached)
            
            if detached:
                # Wait a moment and check if container started successfully
                time.sleep(2)
                if self.is_container_running():
                    self.log("✅ Container started successfully", Colors.GREEN, bold=True)
                    return True
                else:
                    self.log("❌ Container failed to start", Colors.RED, bold=True)
                    return False
            
            return True
            
        except subprocess.CalledProcessError:
            self.log("❌ Failed to start containers", Colors.RED, bold=True)
            return False
    
    def stop_containers(self) -> bool:
        """Stop containers"""
        try:
            self.log("🛑 Stopping containers...", Colors.YELLOW)
            self.run_command(["docker-compose", "down"])
            self.log("✅ Containers stopped", Colors.GREEN)
            return True
        except subprocess.CalledProcessError:
            self.log("❌ Failed to stop containers", Colors.RED)
            return False
    
    def show_logs(self, follow: bool = True) -> None:
        """Show container logs"""
        try:
            cmd = ["docker-compose", "logs"]
            if follow:
                cmd.append("-f")
            
            self.log("📋 Showing logs (Press Ctrl+C to stop)...", Colors.CYAN)
            self.run_command(cmd, capture_output=False)
            
        except KeyboardInterrupt:
            self.log("\n📋 Log viewing stopped", Colors.CYAN)
        except subprocess.CalledProcessError:
            self.log("❌ Failed to show logs", Colors.RED)
    
    def show_status(self) -> None:
        """Show current status of images and containers"""
        self.log("📊 Current Status:", Colors.CYAN, bold=True)
        
        # Image status
        image_info = self.get_image_info()
        if image_info:
            self.log(f"   🖼️  Image: {image_info['Repository']}:{image_info['Tag']} ({image_info['Size']})", Colors.GREEN)
        else:
            self.log(f"   🖼️  Image: Not found", Colors.YELLOW)
        
        # Container status
        container_info = self.get_container_info()
        if container_info:
            status = container_info['Status']
            color = Colors.GREEN if "Up" in status else Colors.YELLOW
            self.log(f"   📦 Container: {container_info['Names']} - {status}", color)
        else:
            self.log(f"   📦 Container: Not found", Colors.YELLOW)
        
        # Check if service is accessible
        if self.is_container_running():
            try:
                # Try to get port info
                result = self.run_command([
                    "docker-compose", "port", self.service_name, "8080"
                ])
                port_info = result.stdout.strip()
                if port_info:
                    self.log(f"   🌐 Service: Available at http://{port_info}", Colors.GREEN)
                else:
                    self.log(f"   🌐 Service: Port not exposed", Colors.YELLOW)
            except subprocess.CalledProcessError:
                self.log(f"   🌐 Service: Status unknown", Colors.YELLOW)
    
    def cleanup(self, full: bool = False) -> bool:
        """Clean up containers and optionally images"""
        try:
            self.log("🧹 Cleaning up...", Colors.YELLOW)
            
            # Stop containers
            self.stop_containers()
            
            if full:
                # Remove containers and images
                self.log("🗑️  Removing containers and images...", Colors.YELLOW)
                self.run_command(["docker-compose", "down", "--rmi", "all", "--volumes"])
                self.log("✅ Full cleanup completed", Colors.GREEN)
            else:
                # Just remove containers
                self.run_command(["docker-compose", "down", "--volumes"])
                self.log("✅ Cleanup completed", Colors.GREEN)
            
            return True
            
        except subprocess.CalledProcessError:
            self.log("❌ Cleanup failed", Colors.RED)
            return False


def main():
    """Main script execution"""
    docker_manager = DockerManager()
    
    # Parse command line arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else ["start"]
    command = args[0].lower()
    
    docker_manager.log("🐳 CodeSandbox Docker Manager", Colors.CYAN, bold=True)
    
    # Check Docker availability
    if not docker_manager.check_docker_availability():
        docker_manager.log("❌ Docker or Docker Compose not available", Colors.RED, bold=True)
        sys.exit(1)
    
    # Check if .env file exists
    if not Path(".env").exists():
        docker_manager.log("⚠️  .env file not found - using defaults", Colors.YELLOW)
    
    # Execute commands
    try:
        if command == "start":
            docker_manager.log("🚀 Starting CodeSandbox...", Colors.CYAN, bold=True)
            
            # Build image if needed
            if not docker_manager.build_image():
                sys.exit(1)
            
            # Start containers
            if not docker_manager.start_containers(detached=True):
                sys.exit(1)
            
            # Show status
            docker_manager.show_status()
            
            # Show logs option
            show_logs = input(f"\n{Colors.CYAN}Show logs? (y/N): {Colors.END}").lower().strip()
            if show_logs in ['y', 'yes']:
                docker_manager.show_logs(follow=True)
        
        elif command == "stop":
            docker_manager.stop_containers()
        
        elif command == "restart":
            docker_manager.log("🔄 Restarting CodeSandbox...", Colors.CYAN, bold=True)
            docker_manager.stop_containers()
            if docker_manager.build_image() and docker_manager.start_containers():
                docker_manager.show_status()
        
        elif command == "rebuild":
            docker_manager.log("🔨 Rebuilding CodeSandbox...", Colors.CYAN, bold=True)
            docker_manager.stop_containers()
            if docker_manager.build_image(force_rebuild=True) and docker_manager.start_containers():
                docker_manager.show_status()
        
        elif command == "logs":
            docker_manager.show_logs(follow=True)
        
        elif command == "status":
            docker_manager.show_status()
        
        elif command == "cleanup":
            full_cleanup = "--full" in args
            docker_manager.cleanup(full=full_cleanup)
        
        elif command in ["help", "-h", "--help"]:
            print(f"""
{Colors.CYAN}{Colors.BOLD}CodeSandbox Docker Manager{Colors.END}

{Colors.YELLOW}Usage:{Colors.END}
    python setup_and_run.py [command]

{Colors.YELLOW}Commands:{Colors.END}
    {Colors.GREEN}start{Colors.END}      Start the application (default)
    {Colors.GREEN}stop{Colors.END}       Stop containers
    {Colors.GREEN}restart{Colors.END}    Stop and start containers
    {Colors.GREEN}rebuild{Colors.END}    Force rebuild image and restart
    {Colors.GREEN}logs{Colors.END}       Show container logs
    {Colors.GREEN}status{Colors.END}     Show current status
    {Colors.GREEN}cleanup{Colors.END}    Clean up containers (add --full to remove images)
    {Colors.GREEN}help{Colors.END}       Show this help message

{Colors.YELLOW}Examples:{Colors.END}
    python setup_and_run.py start
    python setup_and_run.py logs
    python setup_and_run.py cleanup --full
            """)
        
        else:
            docker_manager.log(f"❌ Unknown command: {command}", Colors.RED)
            docker_manager.log("Run 'python setup_and_run.py help' for usage", Colors.YELLOW)
            sys.exit(1)
    
    except KeyboardInterrupt:
        docker_manager.log("\n⚠️  Operation interrupted by user", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        docker_manager.log(f"❌ Unexpected error: {e}", Colors.RED, bold=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 