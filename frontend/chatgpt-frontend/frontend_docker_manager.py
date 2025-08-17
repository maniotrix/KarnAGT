#!/usr/bin/env python3
"""
Frontend Docker Manager - Simple container management for development
"""
import subprocess
import sys
import argparse
from pathlib import Path

def run_command(cmd, check=True):
    """Run shell command and return result"""
    print(f"🔧 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        sys.exit(1)

def check_backend_network():
    """Check if backend dev-network exists"""
    try:
        result = subprocess.run(['docker', 'network', 'inspect', 'dev-network'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Backend dev-network found")
            return True
        else:
            print("❌ Backend dev-network not found")
            print("💡 Start backend services first: cd ../../backend && python backend_docker_manager.py start --env=dev")
            return False
    except Exception as e:
        print(f"❌ Error checking network: {e}")
        return False

def start_frontend():
    """Start frontend development container"""
    print("🚀 Starting frontend development container...")
    
    if not check_backend_network():
        print("⚠️  Backend network required. Starting anyway...")
    
    run_command(['docker', 'compose', '-f', 'docker-compose.dev.yml', 'up', '-d', '--build'])
    print("✅ Frontend container started!")
    print("🌐 Frontend available at: http://localhost")
    print("📊 Traefik dashboard: http://localhost:8080")

def stop_frontend():
    """Stop frontend development container"""
    print("🛑 Stopping frontend development container...")
    run_command(['docker', 'compose', '-f', 'docker-compose.dev.yml', 'down'])
    print("✅ Frontend container stopped!")

def restart_frontend():
    """Restart frontend development container"""
    print("🔄 Restarting frontend development container...")
    stop_frontend()
    start_frontend()

def logs_frontend():
    """Show frontend container logs"""
    print("📋 Frontend container logs:")
    run_command(['docker', 'compose', '-f', 'docker-compose.dev.yml', 'logs', '-f'])

def status_frontend():
    """Show frontend container status"""
    print("📊 Frontend container status:")
    run_command(['docker', 'compose', '-f', 'docker-compose.dev.yml', 'ps'])

def main():
    parser = argparse.ArgumentParser(description='Frontend Docker Manager')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'logs', 'status'],
                        help='Action to perform')
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    print(f"📁 Working directory: {script_dir}")
    import os
    os.chdir(script_dir)
    
    if args.action == 'start':
        start_frontend()
    elif args.action == 'stop':
        stop_frontend()
    elif args.action == 'restart':
        restart_frontend()
    elif args.action == 'logs':
        logs_frontend()
    elif args.action == 'status':
        status_frontend()

if __name__ == '__main__':
    main()
