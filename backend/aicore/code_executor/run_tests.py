#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple script to run HTTP tests for the FastAPI Code Executor Service.
"""

import os
import sys
import subprocess
import time

def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    
    requirements_files = [
        "requirements-fastapi.txt",
        "requirements-test.txt"
    ]
    
    for req_file in requirements_files:
        if os.path.exists(req_file):
            print(f"Installing from {req_file}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", req_file
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Warning: Failed to install from {req_file}")
                print(result.stderr)
            else:
                print(f"✓ Dependencies from {req_file} installed successfully")
        else:
            print(f"Warning: {req_file} not found")

def main():
    """Main function to run tests."""
    print("FastAPI Code Executor Service - Test Runner")
    print("=" * 50)
    
    # Install dependencies
    # install_dependencies()
    
    # Run the HTTP tests
    print("\nStarting HTTP tests...")
    print("=" * 50)
    
    try:
        # Import and run tests
        from test_http_server import main as run_tests
        return run_tests()
        
    except ImportError as e:
        print(f"Error importing test module: {e}")
        print("Make sure all dependencies are installed.")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    
    print(f"\nTests completed with exit code: {exit_code}")
    if exit_code == 0:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed.")
        
    sys.exit(exit_code) 