#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Cleanup Script

Simple script to clean up:
- workspaces/ directory and all contents
- kernel-*.json files (Jupyter connection files)
"""

import os
import shutil
import glob
from pathlib import Path

def cleanup_workspaces():
    """Clean up workspaces and kernel files"""
    print("🧹 Starting workspace cleanup...")
    
    cleaned_items = []
    
    # 1. Remove workspaces directory
    # Use environment variable or default to /tmp/workspaces
    workspace_base_path = os.getenv("WORKSPACE_BASE_PATH", "/tmp/workspaces")
    workspaces_dir = Path(workspace_base_path)
    if workspaces_dir.exists():
        try:
            shutil.rmtree(workspaces_dir)
            cleaned_items.append(f"📁 Removed directory: {workspaces_dir}")
            print(f"✅ Removed workspaces directory: {workspaces_dir}")
        except Exception as e:
            print(f"❌ Failed to remove workspaces directory: {e}")
    else:
        print("ℹ️  No workspaces directory found")
    
    # 2. Remove kernel-*.json files
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
    if cleaned_items:
        print(f"📊 Cleaned {len(cleaned_items)} items:")
        for item in cleaned_items:
            print(f"   {item}")
    else:
        print("📊 No items needed cleanup")

if __name__ == "__main__":
    cleanup_workspaces() 