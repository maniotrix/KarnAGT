#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HTTP-based tests for the FastAPI Code Executor Service.
Tests all endpoints, file handling, session management, and error cases.
"""

import os
import sys
import time
import threading
import requests
from typing import Dict, Optional
import uvicorn

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from aicore.code_executor.logger import get_logger

# Configure logger
logger = get_logger()

# Test configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8081
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
SERVER_START_TIMEOUT = 10  # seconds to wait for server startup

class CodeExecutorHTTPTests:
    """HTTP-based test suite for the FastAPI code executor service."""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.test_session_id: Optional[str] = None
        self.server_process = None
        
    def start_server(self) -> bool:
        """Start the FastAPI server in a separate thread."""
        try:
            # Import here to avoid circular imports
            from fastapi_server import app
            
            def run_server():
                uvicorn.run(
                    app,
                    host=SERVER_HOST,
                    port=SERVER_PORT,
                    log_level="info",
                    access_log=False
                )
            
            # Start server in daemon thread
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to be ready
            for _ in range(SERVER_START_TIMEOUT):
                try:
                    response = self.session.get(f"{self.base_url}/health", timeout=1)
                    if response.status_code == 200:
                        logger.info(f"Server started successfully on {self.base_url}")
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(1)
                    
            logger.error("Server failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            return False
    
    def test_health_check(self) -> bool:
        """Test the health check endpoint."""
        logger.info("Testing health check endpoint...")
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "version" in data  
                assert "timestamp" in data
                assert data["status"] == "healthy"
                logger.info("✓ Health check passed")
                return True
            else:
                logger.error(f"Health check failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False
    
    def test_create_session(self) -> bool:
        """Test session creation."""
        logger.info("Testing session creation...")
        
        try:
            response = self.session.post(f"{self.base_url}/session")
            
            if response.status_code == 200:
                data = response.json()
                assert "session_id" in data
                assert "created_at" in data
                assert "workspace_path" in data
                
                self.test_session_id = data["session_id"]
                logger.info(f"✓ Session created: {self.test_session_id}")
                return True
            else:
                logger.error(f"Session creation failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return False
    
    def test_get_session_info(self) -> bool:
        """Test getting session information."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing get session info...")
        
        try:
            response = self.session.get(f"{self.base_url}/session/{self.test_session_id}")
            
            if response.status_code == 200:
                data = response.json()
                assert data["session_id"] == self.test_session_id
                assert "created_at" in data
                assert "workspace_path" in data
                assert "input_files" in data
                assert "output_files" in data
                logger.info("✓ Session info retrieved successfully")
                return True
            else:
                logger.error(f"Get session info failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Get session info error: {e}")
            return False
    
    def test_file_upload(self) -> bool:
        """Test file upload functionality."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing file upload...")
        
        try:
            # Create test CSV data
            test_data = "name,age,city\nAlice,30,New York\nBob,25,San Francisco\nCharlie,35,Chicago"
            
            # Create test files
            files = {
                'files': ('test_data.csv', test_data, 'text/csv'),
                'files': ('readme.txt', 'This is a test file for upload', 'text/plain')
            }
            
            response = self.session.post(
                f"{self.base_url}/session/{self.test_session_id}/upload",
                files=[
                    ('files', ('test_data.csv', test_data, 'text/csv')),
                    ('files', ('readme.txt', 'This is a test file for upload', 'text/plain'))
                ]
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "uploaded_files" in data
                assert len(data["uploaded_files"]) == 2
                assert data["session_id"] == self.test_session_id
                logger.info(f"✓ Files uploaded successfully: {len(data['uploaded_files'])} files")
                return True
            else:
                logger.error(f"File upload failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"File upload error: {e}")
            return False
    
    def test_list_files(self) -> bool:
        """Test listing session files."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing file listing...")
        
        try:
            response = self.session.get(f"{self.base_url}/session/{self.test_session_id}/files")
            
            if response.status_code == 200:
                data = response.json()
                assert "session_id" in data
                assert "input_files" in data
                assert "output_files" in data
                assert len(data["input_files"]) >= 1  # Should have uploaded files
                logger.info(f"✓ Files listed: {len(data['input_files'])} input files, {len(data['output_files'])} output files")
                return True
            else:
                logger.error(f"File listing failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"File listing error: {e}")
            return False
    
    def test_simple_code_execution(self) -> bool:
        """Test simple Python code execution."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing simple code execution...")
        
        try:
            code = """
# Simple calculation
result = 2 + 2
print(f"2 + 2 = {result}")
print("Hello from code executor!")
"""
            
            payload = {
                "code": code,
                "session_id": self.test_session_id
            }
            
            response = self.session.post(
                f"{self.base_url}/execute",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "execution_id" in data
                assert "session_id" in data
                assert data["status"] == "success"
                assert "2 + 2 = 4" in data["stdout"]
                assert "Hello from code executor!" in data["stdout"]
                logger.info(f"✓ Simple code executed successfully: {data['execution_time']:.3f}s")
                return True
            else:
                logger.error(f"Code execution failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            return False
    
    def test_file_processing_code(self) -> bool:
        """Test code execution with file processing."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing code execution with file processing...")
        
        try:
            code = """
import pandas as pd
import os

# Read the uploaded CSV file
df = pd.read_csv('inputs/test_data.csv')
print(f"Loaded dataset with {len(df)} rows and {len(df.columns)} columns")
print("Columns:", df.columns.tolist())
print("First few rows:")
print(df.head())

# Process the data
df['age_group'] = df['age'].apply(lambda x: 'young' if x < 30 else 'older')
summary = df.groupby('age_group').size()
print("\\nAge group summary:")
print(summary)

# Save processed data
df.to_csv('outputs/processed_data.csv', index=False)
summary.to_csv('outputs/age_summary.csv')

print("\\nFiles saved to outputs directory")

result = {
    'total_rows': len(df),
    'columns': df.columns.tolist(),
    'age_groups': summary.to_dict()
}
"""
            
            payload = {
                "code": code,
                "session_id": self.test_session_id
            }
            
            response = self.session.post(
                f"{self.base_url}/execute",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "Loaded dataset with" in data["stdout"]
                assert len(data["output_files"]) >= 2  # Should have created 2 CSV files
                logger.info(f"✓ File processing code executed: {len(data['output_files'])} output files created")
                return True
            else:
                logger.error(f"File processing failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return False
    
    def test_plot_generation(self) -> bool:
        """Test code execution with plot generation."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing plot generation...")
        
        try:
            code = """
import matplotlib
matplotlib.use('Agg')  # Ensure non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Create sample data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Create plots
plt.figure(figsize=(12, 8))

# Subplot 1
plt.subplot(2, 2, 1)
plt.plot(x, y1, 'b-', label='sin(x)')
plt.plot(x, y2, 'r-', label='cos(x)')
plt.title('Trigonometric Functions')
plt.legend()
plt.grid(True)

# Subplot 2 - Bar chart
plt.subplot(2, 2, 2)
categories = ['A', 'B', 'C', 'D']
values = [23, 45, 56, 78]
plt.bar(categories, values, color=['red', 'green', 'blue', 'orange'])
plt.title('Sample Bar Chart')

# Subplot 3 - Scatter plot
plt.subplot(2, 2, 3)
x_scatter = np.random.randn(50)
y_scatter = np.random.randn(50)
plt.scatter(x_scatter, y_scatter, alpha=0.6)
plt.title('Random Scatter Plot')

# Subplot 4 - Histogram
plt.subplot(2, 2, 4)
data = np.random.normal(0, 1, 1000)
plt.hist(data, bins=30, alpha=0.7)
plt.title('Normal Distribution Histogram')

plt.tight_layout()
plt.savefig('outputs/comprehensive_plots.png', dpi=150, bbox_inches='tight')
plt.close()

# Individual plot
plt.figure(figsize=(8, 6))
plt.plot(x, y1 * y2, 'g-', linewidth=2)
plt.title('sin(x) * cos(x)')
plt.xlabel('x')
plt.ylabel('sin(x) * cos(x)')
plt.grid(True)
plt.savefig('outputs/product_plot.png', dpi=150)
plt.close()

print("Generated comprehensive_plots.png and product_plot.png")
result = "Plots generated successfully"
"""
            
            payload = {
                "code": code,
                "session_id": self.test_session_id
            }
            
            response = self.session.post(
                f"{self.base_url}/execute",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                logger.info(f"Response status: {data['status']}")
                logger.info(f"Stdout contains success message: {'Plots generated successfully' in data['stdout']}")
                logger.info(f"Total output files: {len(data['output_files'])}")
                
                for i, file in enumerate(data['output_files']):
                    logger.info(f"  File {i+1}: {file['name']} ({file.get('size', 'unknown')} bytes)")
                
                assert data["status"] == "success"
                assert "Generated comprehensive_plots.png and product_plot.png" in data["stdout"]
                
                # Check for PNG files in output
                png_files = [f for f in data["output_files"] if f["name"].endswith('.png')]
                
                logger.info(f"PNG files found: {len(png_files)}")
                logger.info(f"PNG file names: {[f['name'] for f in png_files]}")
                
                if len(png_files) < 2:
                    logger.error(f"Expected 2+ PNG files, but found {len(png_files)}: {[f['name'] for f in png_files]}")
                    logger.error("This suggests scan_output_files() is not finding all the files that were created")
                    return False
                    
                logger.info(f"✓ Plot generation successful: {len(png_files)} PNG files created")
                return True
            else:
                logger.error(f"Plot generation failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Plot generation error: {e}")
            return False
    
    def test_file_download(self) -> bool:
        """Test downloading output files."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing file download...")
        
        try:
            # First, get list of output files
            files_response = self.session.get(f"{self.base_url}/session/{self.test_session_id}/files")
            if files_response.status_code != 200:
                logger.error("Could not get file list for download test")
                return False
                
            files_data = files_response.json()
            output_files = files_data.get("output_files", [])
            
            if not output_files:
                logger.error("No output files available for download test")
                return False
            
            # Download first output file
            test_file = output_files[0]
            filename = test_file["name"]
            
            download_response = self.session.get(
                f"{self.base_url}/session/{self.test_session_id}/download/outputs/{filename}"
            )
            
            if download_response.status_code == 200:
                # Check that we got some content
                content = download_response.content
                assert len(content) > 0
                logger.info(f"✓ File download successful: {filename} ({len(content)} bytes)")
                return True
            else:
                logger.error(f"File download failed with status {download_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"File download error: {e}")
            return False
    
    def test_system_command(self) -> bool:
        """Test system command execution."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing system command execution...")
        
        try:
            payload = {
                "command": "python -c \"print('System command test'); print('Current directory:', __import__('os').getcwd())\"",
                "session_id": self.test_session_id
            }
            
            response = self.session.post(
                f"{self.base_url}/system-command",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "execution_id" in data
                assert data["status"] == "success"
                assert "System command test" in data["stdout"]
                logger.info("✓ System command executed successfully")
                return True
            else:
                logger.error(f"System command failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"System command error: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling with invalid code."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing error handling...")
        
        try:
            # Test with invalid Python code
            code = """
# This code has intentional errors
import non_existent_module
undefined_variable = some_undefined_var
result = 1 / 0  # Division by zero
"""
            
            payload = {
                "code": code,
                "session_id": self.test_session_id
            }
            
            response = self.session.post(
                f"{self.base_url}/execute",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "error"
                assert data["error"] is not None
                assert len(data["stderr"]) > 0
                logger.info("✓ Error handling working correctly")
                return True
            else:
                logger.error(f"Error handling test failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling test error: {e}")
            return False
    
    def test_invalid_session(self) -> bool:
        """Test behavior with invalid session ID."""
        logger.info("Testing invalid session handling...")
        
        try:
            fake_session_id = "invalid-session-id-123"
            
            response = self.session.get(f"{self.base_url}/session/{fake_session_id}")
            
            if response.status_code == 404:
                logger.info("✓ Invalid session correctly returns 404")
                return True
            else:
                logger.error(f"Invalid session test failed: expected 404, got {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Invalid session test error: {e}")
            return False
    
    def test_list_active_sessions(self) -> bool:
        """Test listing active sessions."""
        logger.info("Testing active sessions listing...")
        
        try:
            response = self.session.get(f"{self.base_url}/sessions")
            
            if response.status_code == 200:
                data = response.json()
                assert "active_sessions" in data
                assert "sessions" in data
                assert data["active_sessions"] >= 1  # Should have at least our test session
                logger.info(f"✓ Active sessions listed: {data['active_sessions']} sessions")
                return True
            else:
                logger.error(f"Sessions listing failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Sessions listing error: {e}")
            return False
    
    def test_cleanup_session(self) -> bool:
        """Test session deletion/cleanup."""
        if not self.test_session_id:
            logger.error("No test session ID available")
            return False
            
        logger.info("Testing session cleanup...")
        
        try:
            response = self.session.delete(f"{self.base_url}/session/{self.test_session_id}")
            
            if response.status_code == 200:
                data = response.json()
                assert "message" in data
                logger.info("✓ Session deleted successfully")
                
                # Verify session is gone
                verify_response = self.session.get(f"{self.base_url}/session/{self.test_session_id}")
                if verify_response.status_code == 404:
                    logger.info("✓ Session deletion verified")
                    return True
                else:
                    logger.error("Session still exists after deletion")
                    return False
            else:
                logger.error(f"Session deletion failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all HTTP tests and return results."""
        print("="*80)
        print("STARTING HTTP TESTS FOR FASTAPI CODE EXECUTOR SERVICE")
        print("="*80)
        
        # Start the server
        if not self.start_server():
            logger.error("Failed to start server, cannot run tests")
            return {"server_startup": False}
        
        # Define test methods in execution order
        tests = [
            ("Health Check", self.test_health_check),
            ("Create Session", self.test_create_session),
            ("Get Session Info", self.test_get_session_info),
            ("File Upload", self.test_file_upload),
            ("List Files", self.test_list_files),
            ("Simple Code Execution", self.test_simple_code_execution),
            ("File Processing Code", self.test_file_processing_code),
            ("Plot Generation", self.test_plot_generation),
            ("File Download", self.test_file_download),
            ("System Command", self.test_system_command),
            ("Error Handling", self.test_error_handling),
            ("Invalid Session", self.test_invalid_session),
            ("List Active Sessions", self.test_list_active_sessions),
            ("Cleanup Session", self.test_cleanup_session)
        ]
        
        results = {}
        passed = 0
        total = len(tests)
        
        for test_name, test_method in tests:
            print(f"\n[{passed+1}/{total}] {test_name}")
            print("-" * 40)
            
            try:
                result = test_method()
                results[test_name] = result
                if result:
                    passed += 1
                    print(f"✅ PASSED: {test_name}")
                else:
                    print(f"❌ FAILED: {test_name}")
            except Exception as e:
                results[test_name] = False
                print(f"❌ ERROR: {test_name} - {e}")
                logger.error(f"Test '{test_name}' raised exception: {e}")
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Passed: {passed}/{total} tests")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("❌ Some tests failed. See details above.")
            
        print("\nDetailed Results:")
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL" 
            print(f"  {status} - {test_name}")
        
        return results

def main():
    """Main test runner."""
    # Ensure matplotlib uses non-interactive backend
    import matplotlib
    matplotlib.use('Agg')
    
    # Create and run tests
    tester = CodeExecutorHTTPTests()
    results = tester.run_all_tests()
    
    # Return exit code based on results
    all_passed = all(results.values())
    return 0 if all_passed else 1

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code) 