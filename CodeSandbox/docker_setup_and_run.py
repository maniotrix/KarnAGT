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
    
    def __init__(self, mode: str = "prod"):
        self.project_name = "codesandbox"
        self.mode = mode
        
        # Set compose file and service name based on mode
        if mode == "dev":
            self.compose_file = "docker-compose.dev.yml"
            self.service_name = "codesandbox-dev"
            self.container_name = "codesandbox-development"
        else:
            self.compose_file = "docker-compose.prod.yml"
            self.service_name = "codesandbox-prod"
            self.container_name = "codesandbox-production"
        
        self.image_name = f"{self.project_name}_{self.service_name}"
        
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
            
            # Check if compose file exists
            if not Path(self.compose_file).exists():
                self.log(f"❌ Compose file {self.compose_file} not found", Colors.RED, bold=True)
                return False
                
            # Check if mode-specific Dockerfile exists
            dockerfile_name = f"Dockerfile.{self.mode}"
            if not Path(dockerfile_name).exists():
                self.log(f"❌ Dockerfile {dockerfile_name} not found", Colors.RED, bold=True)
                return False
                
            # Check if mode-specific environment file exists
            env_file_name = f".env.docker.{self.mode}"
            if not Path(env_file_name).exists():
                self.log(f"❌ Environment file {env_file_name} not found", Colors.RED, bold=True)
                self.log(f"💡 Create it by copying: cp .env.docker.{self.mode}.template .env.docker.{self.mode}", Colors.YELLOW)
                return False
                
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_image_info(self) -> Optional[Dict]:
        """Get Docker image information using multiple fallback methods"""
        
        # Method 1: Get image name from running container
        try:
            container_info = self.get_container_info()
            if container_info:
                # Try to get image from container inspect
                container_name = container_info.get('Name', '')
                if container_name:
                    inspect_result = self.run_command([
                        "docker", "inspect", "--format", "{{.Config.Image}}", container_name
                    ])
                    image_name = inspect_result.stdout.strip()
                    if image_name:
                        # Get detailed image info
                        image_result = self.run_command([
                            "docker", "images", "--format", "json", image_name
                        ])
                        for line in image_result.stdout.strip().split('\n'):
                            if line.strip():
                                return json.loads(line)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass
        
        # Method 2: Try docker-compose images (if container method failed)
        try:
            result = self.run_command([
                "docker-compose", "-f", self.compose_file, "images", "--format", "json", self.service_name
            ])
            
            if result.stdout.strip():
                images_list = json.loads(result.stdout.strip())
                for compose_info in images_list:
                    actual_image_name = compose_info.get("Repository")
                    if actual_image_name:
                        image_result = self.run_command([
                            "docker", "images", "--format", "json", actual_image_name
                        ])
                        for image_line in image_result.stdout.strip().split('\n'):
                            if image_line.strip():
                                return json.loads(image_line)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass
            
        # Method 3: Try common image name patterns
        possible_names = [
            f"{self.project_name}-{self.service_name}",
            f"{self.project_name}_{self.service_name}",
            f"{self.service_name}",
        ]
        
        for image_name in possible_names:
            try:
                result = self.run_command([
                    "docker", "images", "--format", "json", image_name
                ])
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        return json.loads(line)
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                continue
                
        return None
    
    def get_container_info(self) -> Optional[Dict]:
        """Get Docker container information using docker-compose (no hardcoded names)"""
        try:
            # Use docker-compose ps to get info for our specific service (includes stopped containers)
            result = self.run_command([
                "docker-compose", "-f", self.compose_file, "ps", "-a", "--format", "json", self.service_name
            ])
            
            # Parse the JSON output
            if result.stdout.strip():
                return json.loads(result.stdout.strip())
            return None
            
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            # Fallback: try without service filter (includes stopped containers)
            try:
                result = self.run_command([
                    "docker-compose", "-f", self.compose_file, "ps", "-a", "--format", "json"
                ])
                
                # Find our service in the list
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        container_info = json.loads(line)
                        if container_info.get("Service") == self.service_name:
                            return container_info
                return None
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                return None
    
    def is_container_running(self) -> bool:
        """Check if container is currently running"""
        container_info = self.get_container_info()
        if container_info is None:
            return False
        
        # docker-compose ps uses "State" field, not "Status"
        state = container_info.get("State", "").lower()
        return "running" in state or "up" in state
    
    def get_dockerfile_hash(self) -> str:
        """Get hash of mode-specific Dockerfile and related files for change detection"""
        import hashlib
        
        # Check mode-specific files
        dockerfile_name = f"Dockerfile.{self.mode}"
        env_file_name = f".env.docker.{self.mode}"
        
        files_to_check = [dockerfile_name, "requirements.txt", self.compose_file]
        
        # Also include environment file if it exists (affects container behavior)
        if Path(env_file_name).exists():
            files_to_check.append(env_file_name)
        
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
        
        # Simple approach: Check if key files are newer than image
        dockerfile_name = f"Dockerfile.{self.mode}"
        env_file_name = f".env.docker.{self.mode}"
        
        files_to_check = [dockerfile_name, "requirements.txt", self.compose_file]
        
        # Also check environment file if it exists
        if Path(env_file_name).exists():
            files_to_check.append(env_file_name)
        
        # Get image creation time
        try:
            image_created = image_info.get("CreatedAt", "")
            if not image_created:
                return True, "Cannot determine image age"
            
            # Parse image creation time (format: 2025-07-24 07:33:08 +0530 IST)
            from datetime import datetime
            import re
            
            # Extract datetime part before timezone
            created_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', image_created)
            if not created_match:
                return True, "Cannot parse image creation time"
            
            image_time = datetime.strptime(created_match.group(1), "%Y-%m-%d %H:%M:%S")
            
            # Check if any key files are newer than image
            for file_path in files_to_check:
                if Path(file_path).exists():
                    file_time = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                    if file_time > image_time:
                        return True, f"{file_path} changed since last build"
            
            return False, "Image is up to date"
            
        except Exception as e:
            # If we can't determine age, it's safer to rebuild
            return True, f"Cannot determine if rebuild needed: {e}"
    
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
            # Build image using docker-compose
            self.run_command([
                "docker-compose", "-f", self.compose_file, "build", self.service_name
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
            
            cmd = ["docker-compose", "-f", self.compose_file, "up"]
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
            self.run_command(["docker-compose", "-f", self.compose_file, "down"])
            self.log("✅ Containers stopped", Colors.GREEN)
            return True
        except subprocess.CalledProcessError:
            self.log("❌ Failed to stop containers", Colors.RED)
            return False
    
    def show_logs(self, follow: bool = True) -> None:
        """Show container logs"""
        try:
            cmd = ["docker-compose", "-f", self.compose_file, "logs"]
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
            # docker-compose ps output uses different field names
            name = container_info.get('Name', container_info.get('Names', 'unknown'))
            state = container_info.get('State', container_info.get('Status', 'unknown'))
            color = Colors.GREEN if "running" in state.lower() or "up" in state.lower() else Colors.YELLOW  
            self.log(f"   📦 Container: {name} - {state}", color)
        else:
            self.log(f"   📦 Container: Not found", Colors.YELLOW)
        
        # Check if service is accessible
        if self.is_container_running():
            try:
                # Try to get port info
                result = self.run_command([
                    "docker-compose", "-f", self.compose_file, "port", self.service_name, "8080"
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
                self.run_command(["docker-compose", "-f", self.compose_file, "down", "--rmi", "all", "--volumes"])
                self.log("✅ Full cleanup completed", Colors.GREEN)
            else:
                # Just remove containers
                self.run_command(["docker-compose", "-f", self.compose_file, "down", "--volumes"])
                self.log("✅ Cleanup completed", Colors.GREEN)
            
            return True
            
        except subprocess.CalledProcessError:
            self.log("❌ Cleanup failed", Colors.RED)
            return False


def main():
    """Main script execution"""
    # Parse command line arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else ["start"]
    command = args[0].lower() if args else "start"
    
    # Determine mode based on flags
    mode = "prod"  # Default to production
    if "--dev" in args:
        mode = "dev"
    elif "--prod" in args:
        mode = "prod"
    
    docker_manager = DockerManager(mode=mode)
    
    docker_manager.log("🐳 CodeSandbox Docker Manager", Colors.CYAN, bold=True)
    docker_manager.log(f"📁 Mode: {mode.upper()} (using {docker_manager.compose_file})", Colors.BLUE)
    docker_manager.log(f"📦 Container: {docker_manager.container_name}", Colors.BLUE)
    
    # Check Docker availability
    if not docker_manager.check_docker_availability():
        docker_manager.log("❌ Docker or Docker Compose not available", Colors.RED, bold=True)
        sys.exit(1)
    
    # Environment file validation is now handled in check_docker_availability()
    
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
            
            # Check for --clean flag
            clean_rebuild = "--clean" in args
            if clean_rebuild:
                docker_manager.log("🧹 Clean rebuild requested - removing old images...", Colors.YELLOW)
                docker_manager.cleanup(full=True)
            else:
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
        
        elif command == "shell":
            # Check for --root flag
            is_root = "--root" in args
            user_flag = "--user root" if is_root else ""
            user_desc = "root" if is_root else "code_sandbox"
            
            docker_manager.log(f"🐚 Opening shell as {user_desc} user...", Colors.CYAN)
            
            try:
                subprocess.run(f"docker-compose -f {docker_manager.compose_file} exec {user_flag} {docker_manager.service_name} bash", shell=True)
            except KeyboardInterrupt:
                docker_manager.log("\n🐚 Shell session ended", Colors.GREEN)
        
        elif command in ["help", "-h", "--help"]:
            print(f"""
{Colors.CYAN}{Colors.BOLD}CodeSandbox Docker Manager{Colors.END}

{Colors.YELLOW}Usage:{Colors.END}
    python setup_and_run.py [command] [--dev|--prod] [options]

{Colors.YELLOW}Commands:{Colors.END}
    {Colors.GREEN}start{Colors.END}      Start the application (default)
    {Colors.GREEN}stop{Colors.END}       Stop containers
    {Colors.GREEN}restart{Colors.END}    Stop and start containers
    {Colors.GREEN}rebuild{Colors.END}    Force rebuild image and restart (add --clean for fresh build)
    {Colors.GREEN}logs{Colors.END}       Show container logs
    {Colors.GREEN}status{Colors.END}     Show current status
    {Colors.GREEN}shell{Colors.END}      Open bash shell (add --root for root access)
    {Colors.GREEN}cleanup{Colors.END}    Clean up containers (add --full to remove images)
    {Colors.GREEN}help{Colors.END}       Show this help message

{Colors.YELLOW}Mode Flags:{Colors.END}
    {Colors.GREEN}--dev{Colors.END}      Development mode (with volume mounts for hot reload)
    {Colors.GREEN}--prod{Colors.END}     Production mode (code baked into image) - DEFAULT

{Colors.YELLOW}Setup Requirements:{Colors.END}
    Before first use, create environment files:
    cp .env.docker.dev.template .env.docker.dev    # For development mode
    cp .env.docker.prod.template .env.docker.prod  # For production mode

{Colors.YELLOW}Examples:{Colors.END}
    python setup_and_run.py start --dev             # Development with hot reload
    python setup_and_run.py start --prod            # Production mode
    python setup_and_run.py logs --dev              # View dev container logs
    python setup_and_run.py rebuild --clean --prod  # Clean production rebuild
    python setup_and_run.py shell --root --dev      # Dev shell as root
    python setup_and_run.py cleanup --full --dev    # Clean dev environment
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