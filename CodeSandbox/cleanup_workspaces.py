#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Cleanup Script

Simple script to clean up:
- <user_temp_base>/workspaces/ directory and all contents
- <user_temp_base>/logs/ directory and all contents
- kernel-*.json files (Jupyter connection files)
"""

import os
import shutil
import glob
import tempfile
from pathlib import Path

from dotenv import load_dotenv

def cleanup_workspaces():
    """Clean up workspaces, logs and kernel files"""
    print("🧹 Starting workspace cleanup...")
    
    cleaned_items = []
    
    # Get user configuration
    cs_user = os.getenv("CS_USER", "code_sandbox")
    user_temp_base_path = os.getenv(
        "USER_TEMP_BASE_PATH",
        str(Path(tempfile.gettempdir()) / cs_user),
    )
    
    # 1. Remove workspaces directory
    workspaces_dir = Path(user_temp_base_path) / "workspaces"
    if workspaces_dir.exists():
        try:
            shutil.rmtree(workspaces_dir)
            cleaned_items.append(f"📁 Removed directory: {workspaces_dir}")
            print(f"✅ Removed workspaces directory: {workspaces_dir}")
        except Exception as e:
            print(f"❌ Failed to remove workspaces directory: {e}")
    else:
        print(f"ℹ️  No workspaces directory found at: {workspaces_dir}")
    
    # 2. Remove logs directory
    logs_dir = Path(user_temp_base_path) / "logs"
    if logs_dir.exists():
        try:
            shutil.rmtree(logs_dir)
            cleaned_items.append(f"📁 Removed directory: {logs_dir}")
            print(f"✅ Removed logs directory: {logs_dir}")
        except Exception as e:
            print(f"❌ Failed to remove logs directory: {e}")
    else:
        print(f"ℹ️  No logs directory found at: {logs_dir}")

    # 3. Remove jupyter_runtime directory
    runtime_dir = Path(user_temp_base_path) / "jupyter_runtime"
    if runtime_dir.exists():
        try:
            shutil.rmtree(runtime_dir)
            cleaned_items.append(f"📁 Removed directory: {runtime_dir}")
            print(f"✅ Removed runtime directory: {runtime_dir}")
        except Exception as e:
            print(f"❌ Failed to remove runtime directory: {e}")
    else:
        print(f"ℹ️  No runtime directory found at: {runtime_dir}")

    # 4. Remove kernel-*.json files in current directory (project root)
    kernel_files = glob.glob("kernel-*.json")
    for kernel_file in kernel_files:
        try:
            os.remove(kernel_file)
            cleaned_items.append(f"🔧 Removed kernel file: {kernel_file}")
            print(f"✅ Removed kernel file: {kernel_file}")
        except Exception as e:
            print(f"❌ Failed to remove kernel file {kernel_file}: {e}")
    
    if not kernel_files:
        print("ℹ️  No kernel files found")
    
    # Summary
    print(f"\n🎯 Cleanup complete!")
    print(f"📊 Using user temp base path: {user_temp_base_path}")
    if cleaned_items:
        print(f"📊 Cleaned {len(cleaned_items)} items:")
        for item in cleaned_items:
            print(f"   {item}")
    else:
        print("📊 No items needed cleanup")

if __name__ == "__main__":
    load_dotenv()
    cleanup_workspaces() 