#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test: CSV File Analysis with Workspace
Tests uploading CSV file and executing analysis code in workspace
"""

import asyncio
import sys
import os
from typing import Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(backend_dir)

from app.aicore.code_executor.services import WorkspaceService, FileService, ExecutionService
from app.aicore.code_executor.models import ExecutionOperationResult
from app.aicore.code_executor.clients import SandboxClient
from app.aicore.code_executor.clients.exceptions import NetworkError

class TestLogger:
    """Simple test logger"""
    
    def __init__(self) -> None:
        self.logs = []
    
    def info(self, message: str, **kwargs: Any) -> None:
        entry = f"[INFO] {message}"
        if kwargs:
            entry += f" | {kwargs}"
        self.logs.append(entry)
        print(entry)
    
    def error(self, message: str, **kwargs: Any) -> None:
        entry = f"[ERROR] {message}"
        if kwargs:
            entry += f" | {kwargs}"
        self.logs.append(entry)
        print(entry)

# CSV file path
csv_file_path = os.path.join(current_dir, 'sample_leads.csv')

# Analysis code to execute in workspace
ANALYSIS_CODE = '''
import pandas as pd
import numpy as np
from collections import Counter

print("🔍 Starting CSV Analysis...")

# Read the CSV file
try:
    df = pd.read_csv('sample_leads.csv')
    print(f"✅ Successfully loaded CSV with {len(df)} rows and {len(df.columns)} columns")
    print(f"📊 Columns: {list(df.columns)}")
except Exception as e:
    print(f"❌ Error reading CSV: {e}")
    raise

# Basic dataset info
print("\\n" + "="*50)
print("📈 DATASET OVERVIEW")
print("="*50)
print(f"Total Records: {len(df):,}")
print(f"Total Columns: {len(df.columns)}")
print(f"Memory Usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")

# Show first few rows
print("\\n📋 Sample Data (First 3 rows):")
print(df.head(3).to_string())

# Column data types and missing values
print("\\n" + "="*50)
print("🔍 DATA QUALITY ANALYSIS")
print("="*50)
print("Column Info:")
for col in df.columns:
    missing_count = df[col].isnull().sum()
    missing_pct = (missing_count / len(df)) * 100
    dtype = str(df[col].dtype)
    print(f"  {col:<20} | {dtype:<10} | Missing: {missing_count:>4} ({missing_pct:>5.1f}%)")

# Deal Stage Analysis
print("\\n" + "="*50)
print("💼 DEAL STAGE ANALYSIS")
print("="*50)
if 'Deal Stage' in df.columns:
    stage_counts = df['Deal Stage'].value_counts()
    print("Deal Stage Distribution:")
    for stage, count in stage_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {stage:<20}: {count:>4} deals ({percentage:>5.1f}%)")
    
    # Success rate
    closed_won = stage_counts.get('Closed Won', 0)
    success_rate = (closed_won / len(df)) * 100
    print(f"\\n🎯 Success Rate: {success_rate:.1f}% ({closed_won}/{len(df)} deals closed)")

# Lead Source Analysis
print("\\n" + "="*50)
print("🎯 LEAD SOURCE ANALYSIS")
print("="*50)
if 'Source' in df.columns:
    source_counts = df['Source'].value_counts()
    print("Lead Source Distribution:")
    for source, count in source_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {source:<20}: {count:>4} leads ({percentage:>5.1f}%)")

# Company Analysis
print("\\n" + "="*50)
print("🏢 COMPANY ANALYSIS")
print("="*50)
if 'Company' in df.columns:
    total_companies = df['Company'].nunique()
    top_companies = df['Company'].value_counts().head(5)
    print(f"Total Unique Companies: {total_companies}")
    print("\\nTop 5 Companies by Lead Count:")
    for company, count in top_companies.items():
        print(f"  {company:<30}: {count} leads")

# Lead Owner Performance
print("\\n" + "="*50)
print("👥 LEAD OWNER PERFORMANCE")
print("="*50)
if 'Lead Owner' in df.columns:
    owner_counts = df['Lead Owner'].value_counts()
    print("Lead Distribution by Owner:")
    for owner, count in owner_counts.head(10).items():
        percentage = (count / len(df)) * 100
        print(f"  {owner:<20}: {count:>4} leads ({percentage:>5.1f}%)")

# Contact Information Completeness
print("\\n" + "="*50)
print("📞 CONTACT INFO COMPLETENESS")
print("="*50)
contact_fields = ['Phone 1', 'Phone 2', 'Email 1', 'Email 2', 'Website']
available_fields = [field for field in contact_fields if field in df.columns]

print("Contact Information Availability:")
for field in available_fields:
    non_null_count = df[field].notna().sum()
    completion_rate = (non_null_count / len(df)) * 100
    print(f"  {field:<12}: {non_null_count:>4}/{len(df)} ({completion_rate:>5.1f}%)")

# Multiple contact methods
if 'Phone 1' in df.columns and 'Email 1' in df.columns:
    has_phone = df['Phone 1'].notna()
    has_email = df['Email 1'].notna()
    has_both = has_phone & has_email
    has_either = has_phone | has_email
    
    print(f"\\n📊 Contact Method Coverage:")
    print(f"  Has Phone Only: {(has_phone & ~has_email).sum()}")
    print(f"  Has Email Only: {(has_email & ~has_phone).sum()}")
    print(f"  Has Both: {has_both.sum()}")
    print(f"  Has Either: {has_either.sum()}")
    print(f"  No Contact Info: {(~has_either).sum()}")

print("\\n🎉 Analysis Complete!")

# Create a summary report
summary_report = f"""
# Lead Analysis Summary Report

## Dataset Overview
- **Total Records**: {len(df):,}
- **Total Columns**: {len(df.columns)}
- **Data Quality**: {((df.notna().sum().sum() / (len(df) * len(df.columns))) * 100):.1f}% complete

## Key Insights
- **Most Common Deal Stage**: {df['Deal Stage'].mode().iloc[0] if 'Deal Stage' in df.columns else 'N/A'}
- **Top Lead Source**: {df['Source'].mode().iloc[0] if 'Source' in df.columns else 'N/A'}
- **Unique Companies**: {df['Company'].nunique() if 'Company' in df.columns else 'N/A'}
- **Lead Owners**: {df['Lead Owner'].nunique() if 'Lead Owner' in df.columns else 'N/A'}

## Recommendations
1. Focus on top-performing lead sources
2. Improve contact information completeness
3. Analyze successful deal patterns
4. Balance lead distribution among owners
"""

# Save the report
with open('lead_analysis_report.md', 'w') as f:
    f.write(summary_report)

print("\\n📄 Detailed report saved as 'lead_analysis_report.md'")

# Return key metrics
result = {
    'total_records': len(df),
    'columns': len(df.columns),
    'data_completeness': round(((df.notna().sum().sum() / (len(df) * len(df.columns))) * 100), 1),
    'unique_companies': df['Company'].nunique() if 'Company' in df.columns else 0,
    'deal_stages': df['Deal Stage'].value_counts().to_dict() if 'Deal Stage' in df.columns else {},
    'lead_sources': df['Source'].value_counts().to_dict() if 'Source' in df.columns else {}
}

print(f"\\n📊 Final Result: {result}")
result
'''

async def test_server_connectivity():
    """Test if CodeSandbox server is running"""
    logger = TestLogger()
    logger.info("Testing CodeSandbox server connectivity...")
    
    try:
        async with SandboxClient() as client:
            health = await client.health_check()
            logger.info("Server health check successful", status=health.status)
            return True, health
    except NetworkError as e:
        logger.error("Network error - server likely not running", error=str(e))
        return False, str(e)
    except Exception as e:
        logger.error("Unexpected error during health check", error=str(e))
        return False, str(e)

async def test_csv_analysis():
    """Run comprehensive CSV analysis test"""
    logger = TestLogger()
    
    print("=" * 80)
    print("CSV FILE ANALYSIS TEST")
    print("=" * 80)
    
    # Check if CSV file exists
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV file not found: {csv_file_path}")
        return
    
    print(f"📄 CSV file found: {csv_file_path}")
    file_size = os.path.getsize(csv_file_path) / 1024
    print(f"📊 File size: {file_size:.1f} KB")
    
    # Test 1: Server connectivity
    print("\\n1. Testing server connectivity...")
    server_running, server_info = await test_server_connectivity()
    
    if not server_running:
        print(f"❌ CodeSandbox server is not running: {server_info}")
        return
    
    print("✅ CodeSandbox server is running")
    
    # Test 2: Create workspace
    print("\\n2. Creating workspace...")
    try:
        workspace_service = WorkspaceService()
        workspace_result = await workspace_service.create_workspace()
        
        if not workspace_result.success or not workspace_result.workspace_info:
            print(f"❌ Failed to create workspace: {workspace_result.error}")
            return
        
        workspace_id = workspace_result.workspace_info.workspace_id
        print(f"✅ Workspace created: {workspace_id}")
        
    except Exception as e:
        print(f"❌ Workspace creation error: {e}")
        return
    
    # Test 3: Upload CSV file
    print("\\n3. Uploading CSV file to workspace...")
    try:
        file_service = FileService()
        upload_result = await file_service.download_and_upload_file_to_workspace(
            workspace_id=workspace_id,
            source=csv_file_path,
            file_name="sample_leads.csv",
            max_size_mb=20
        )
        
        if not upload_result.success:
            print(f"❌ Failed to upload CSV: {upload_result.error}")
            return
        
        file_info = upload_result.file_info
        if file_info:
            print(f"✅ CSV uploaded successfully: {file_info.filename} ({file_info.size} bytes)")
            if hasattr(file_info, 'download_url') and file_info.download_url:
                print(f"🔗 Download URL: {file_info.download_url}")
        
    except Exception as e:
        print(f"❌ File upload error: {e}")
        return
    
    # Test 4: Execute analysis code
    print("\\n4. Executing CSV analysis code...")
    try:
        execution_service = ExecutionService()
        execution_result: ExecutionOperationResult = await execution_service.execute_code(workspace_id, ANALYSIS_CODE)
        
        if not execution_result.success:
            print(f"❌ Code execution failed: {execution_result.error}")
            return
        
        print("✅ Analysis code executed successfully!")
        
        # Show execution output
        if execution_result.execution_result and execution_result.execution_result.stdout:
            print("\\n" + "="*50)
            print("📊 ANALYSIS OUTPUT")
            print("="*50)
            print(execution_result.execution_result.stdout)
        
        # Show any generated files
        if execution_result.execution_result and execution_result.execution_result.generated_files:
            print(f"\\n📁 Generated {len(execution_result.execution_result.generated_files)} file(s):")
            for file_info in execution_result.execution_result.generated_files:
                print(f"   📄 {file_info.filename} ({file_info.size} bytes)")
                if hasattr(file_info, 'download_url') and file_info.download_url:
                    print(f"      🔗 {file_info.download_url}")
        
        # Show final result
        if execution_result.execution_result and execution_result.execution_result.result_data:
            print(f"\\n🎯 Final Analysis Result:")
            print(f"   {execution_result.execution_result.result_data}")
        
    except Exception as e:
        print(f"❌ Code execution error: {e}")
        return
    
    # Test 5: Cleanup
    print(f"\\n5. Cleaning up workspace {workspace_id}...")
    try:
        delete_result = await workspace_service.delete_workspace(workspace_id)
        if delete_result.success:
            print("✅ Workspace cleaned up successfully")
        else:
            print(f"⚠️ Workspace cleanup failed: {delete_result.error}")
    except Exception as e:
        print(f"⚠️ Workspace cleanup error: {e}")
    
    print("\\n🎉 CSV Analysis Test Completed!")

if __name__ == "__main__":
    asyncio.run(test_csv_analysis())


