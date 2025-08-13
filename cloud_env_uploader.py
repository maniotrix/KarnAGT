#!/usr/bin/env python3
"""
Environment File Uploader for Production Deployments
Uploads environment files to cloud VMs after git pull and before container builds.

Usage:
    python cloud_env_uploader.py --env=prod --host=user@cloud-vm --remote-repo-root-path=/opt/your-project
    python cloud_env_uploader.py --env=staging --host=user@staging-vm --remote-repo-root-path=/home/deploy/project --force
    python cloud_env_uploader.py --list-files --env=prod

Safety Features:
- Supports prod and staging environments only
- Uses actual environment file names from your project
- Prevents overwriting without explicit consent
- Verifies remote file existence before upload
- Uses absolute remote paths (no directory creation)
- Direct SCP upload to specified remote project location
- Prompts for image rebuild after successful upload
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class EnvUploader:
    """Upload environment files to cloud VMs for deployment"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent  # Project root (script is now in root)
        self.supported_envs = ['prod', 'staging']
        
        # Environment file mappings: local_path -> remote_relative_path
        self.env_mappings = {
            'backend': {
                'prod': {
                    '.env.docker.app.prod': 'backend/.env.docker.app.prod'
                },
                'staging': {
                    '.env.docker.app.staging': 'backend/.env.docker.app.staging'
                }
            },
            'codesandbox': {
                'prod': {
                    '.env.docker.prod': 'CodeSandbox/.env.docker.prod'
                }
                # No staging env file for CodeSandbox
            }
        }
    
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
        self._log(f"⚠️  {message}", Colors.YELLOW)
    
    def _run_command(self, command: List[str], description: str = "") -> bool:
        """Run shell command with error handling"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return True
            
        except subprocess.CalledProcessError as e:
            self._error(f"{description} failed: {e}")
            if e.stderr:
                print(f"  Error output: {e.stderr.strip()}")
            return False
        except FileNotFoundError:
            self._error(f"Command not found: {command[0]}")
            return False
    
    def _build_remote_path(self, remote_base: str, relative_path: str) -> str:
        """Build absolute remote path from base and relative path"""
        return f"{remote_base.rstrip('/')}/{relative_path}"
    
    def _check_local_files(self, env: str, remote_path: str) -> List[Tuple[str, str, str]]:
        """Check which local env files exist and return (project, local_path, absolute_remote_path)"""
        files_to_upload = []
        
        for project, env_configs in self.env_mappings.items():
            if env not in env_configs:
                self._info(f"Skipping {project} - no {env} environment file configured")
                continue
                
            for local_file, remote_relative_file in env_configs[env].items():
                if project == 'backend':
                    local_path = self.base_dir / 'backend' / local_file
                else:  # codesandbox
                    local_path = self.base_dir / 'CodeSandbox' / local_file
                
                # Build absolute remote path
                absolute_remote_path = self._build_remote_path(remote_path, remote_relative_file)
                
                if local_path.exists():
                    files_to_upload.append((project, str(local_path), absolute_remote_path))
                else:
                    self._warning(f"Local file not found: {local_path}")
        
        return files_to_upload
    
    def _check_remote_files(self, host: str, files_to_upload: List[Tuple[str, str, str]]) -> List[str]:
        """Check which remote files already exist"""
        existing_files = []
        
        for project, local_path, remote_path in files_to_upload:
            # Check if remote file exists
            check_cmd = ['ssh', host, f'test -f {remote_path} && echo "exists" || echo "missing"']
            
            try:
                result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
                if result.stdout.strip() == "exists":
                    existing_files.append(remote_path)
            except subprocess.CalledProcessError:
                # Assume file doesn't exist if ssh fails
                pass
        
        return existing_files
    
    def _get_user_consent(self, existing_files: List[str]) -> bool:
        """Get user consent for overwriting existing files"""
        if not existing_files:
            return True
        
        self._warning("The following remote files already exist:")
        for file_path in existing_files:
            print(f"  • {file_path}")
        
        print()
        response = input(f"{Colors.YELLOW}Overwrite existing files? (yes/no): {Colors.END}").strip().lower()
        return response in ['yes', 'y']
    
    def _upload_file(self, host: str, local_path: str, remote_path: str) -> bool:
        """Upload a single file via scp directly (no directory creation)"""
        scp_cmd = ['scp', local_path, f'{host}:{remote_path}']
        return self._run_command(scp_cmd, f"Upload {Path(local_path).name}")
    
    def _prompt_rebuild(self, env: str, host: str, remote_path: str) -> None:
        """Prompt user to rebuild images after successful upload"""
        self._info("Environment files uploaded successfully!")
        print()
        self._warning("IMPORTANT: You need to rebuild Docker images to use the new environment files.")
        self._info("Existing containers will continue using the old image until rebuilt and restarted.")
        print()
        
        response = input(f"{Colors.CYAN}Would you like to rebuild images now? (yes/no): {Colors.END}").strip().lower()
        
        if response in ['yes', 'y']:
            self._info("To rebuild, SSH into the cloud VM and run:")
            print(f"  {Colors.WHITE}ssh {host}{Colors.END}")
            print(f"  {Colors.WHITE}cd {remote_path}{Colors.END}")
            print(f"  {Colors.WHITE}# Database containers first{Colors.END}")
            print(f"  {Colors.WHITE}cd backend/docker/database && python db_manager.py start --env={env}{Colors.END}")
            print(f"  {Colors.WHITE}# Backend application{Colors.END}")
            print(f"  {Colors.WHITE}cd ../../ && python backend_docker_manager.py restart --{env}{Colors.END}")
            if env == 'prod':  # Only prod has CodeSandbox env file
                print(f"  {Colors.WHITE}# CodeSandbox{Colors.END}")
                print(f"  {Colors.WHITE}cd ../CodeSandbox && python docker_setup_and_run.py restart --env={env}{Colors.END}")
        else:
            self._warning("Remember to rebuild and restart containers manually to use new environment files!")
    
    def list_files(self, env: str) -> None:
        """List environment files that would be uploaded"""
        if env not in self.supported_envs:
            self._error(f"Unsupported environment: {env}")
            self._info(f"Supported environments: {', '.join(self.supported_envs)}")
            return
        
        self._info(f"Environment files for {env.upper()}:")
        print()
        
        found_files = False
        for project, env_configs in self.env_mappings.items():
            if env not in env_configs:
                self._info(f"Skipping {project} - no {env} environment file configured")
                continue
                
            for local_file, remote_relative_file in env_configs[env].items():
                if project == 'backend':
                    local_path = self.base_dir / 'backend' / local_file
                else:  # codesandbox
                    local_path = self.base_dir / 'CodeSandbox' / local_file
                
                status = "✅ EXISTS" if local_path.exists() else "❌ MISSING"
                print(f"  {Colors.BOLD}{project.upper()}{Colors.END}")
                print(f"    Local:  {local_path}")  
                print(f"    Remote: <remote-path>/{remote_relative_file}")
                print(f"    Status: {status}")
                print()
                found_files = True
        
        if not found_files:
            self._warning(f"No environment files configured for {env} environment")
    
    def upload(self, env: str, host: str, remote_path: str, force: bool = False) -> None:
        """Upload environment files to cloud VM"""
        if env not in self.supported_envs:
            self._error(f"Unsupported environment: {env}")
            self._info(f"Supported environments: {', '.join(self.supported_envs)}")
            return
        
        self._info(f"Starting {env.upper()} environment upload to {host}:{remote_path}")
        print()
        
        # Check local files
        files_to_upload = self._check_local_files(env, remote_path)
        
        if not files_to_upload:
            self._error(f"No environment files found for {env} environment")
            self._info("Run with --list-files to see expected file locations")
            return
        
        # Check remote files
        existing_files = self._check_remote_files(host, files_to_upload)
        
        # Get user consent if files exist and not forced
        if not force and existing_files:
            if not self._get_user_consent(existing_files):
                self._info("Upload cancelled by user")
                return
        
        # Upload files
        success_count = 0
        total_count = len(files_to_upload)
        
        for project, local_path, absolute_remote_path in files_to_upload:
            self._info(f"Uploading {project} environment file...")
            if self._upload_file(host, local_path, absolute_remote_path):
                success_count += 1
                self._success(f"Uploaded {Path(local_path).name}")
            else:
                self._error(f"Failed to upload {Path(local_path).name}")
        
        # Summary
        print()
        if success_count == total_count:
            self._success(f"All {total_count} environment files uploaded successfully!")
            self._prompt_rebuild(env, host, remote_path)
        else:
            self._error(f"Upload incomplete: {success_count}/{total_count} files uploaded")
            sys.exit(1)


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Upload environment files for production deployment")
    parser.add_argument('--env', choices=['prod', 'staging'], required=True,
                       help='Environment to deploy (prod or staging only)')
    parser.add_argument('--host', 
                       help='Cloud VM host (user@hostname or user@ip)')
    parser.add_argument('--remote-repo-root-path', required=False,
                       help='Absolute path to project directory on remote server (e.g., /opt/your-project)')
    parser.add_argument('--force', action='store_true',
                       help='Force overwrite existing files without confirmation')
    parser.add_argument('--list-files', action='store_true',
                       help='List environment files that would be uploaded')
    
    args = parser.parse_args()
    
    uploader = EnvUploader()
    
    if args.list_files:
        uploader.list_files(args.env)
    else:
        if not args.host:
            print("Error: --host is required for upload operation")
            sys.exit(1)
        if not args.remote_repo_root_path:
            print("Error: --remote-repo-root-path is required for upload operation")
            sys.exit(1)
        uploader.upload(args.env, args.host, args.remote_repo_root_path, args.force)


if __name__ == "__main__":
    main()
