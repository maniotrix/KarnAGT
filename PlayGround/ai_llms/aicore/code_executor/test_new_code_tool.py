#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test file for the HTTP-based code executor module with LLM-generated code strings.

This test uses HTTP-based code execution through FastAPI server for secure,
isolated execution with automatic file handling. The server provides:

- Per-execution isolated workspaces
- Automatic file uploads/downloads
- Secure code execution in isolated environment
- Plot generation with automatic retrieval

The test automatically starts a FastAPI server before running tests.
"""

import sys
import os
# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import asyncio
import logging
import time
import tempfile
import gc
import shutil
import threading
import requests  # Required for HTTP server health checks
from agents import Agent, Runner  # Fixed import
from aicore.code_executor.logger import get_logger, set_log_level
from aicore.code_executor.new_code_agent import HTTPCodeExecutorAgent  # Updated to use new HTTP agent
from aicore.path_config import PLOTS_DIR
from aicore.code_executor.utils import execution_cleanup
from typing import Dict, Any

# Get logger with test-specific name
logger = get_logger("test_new_code_tool")

# Define a fixed directory for plot outputs (for display purposes)
os.makedirs(PLOTS_DIR, exist_ok=True)

# FastAPI server configuration
FASTAPI_SERVER_HOST = "127.0.0.1"
FASTAPI_SERVER_PORT = 8080
FASTAPI_SERVER_URL = f"http://{FASTAPI_SERVER_HOST}:{FASTAPI_SERVER_PORT}"


# Server management functions
def start_fastapi_server():
    """Start the FastAPI server in a background thread"""
    try:
        # Import here to avoid circular imports
        from aicore.code_executor.fastapi_server import app
        import uvicorn
        
        def run_server():
            uvicorn.run(
                app,
                host=FASTAPI_SERVER_HOST,
                port=FASTAPI_SERVER_PORT,
                log_level="warning",  # Reduce log noise
                access_log=False
            )
        
        # Start server in daemon thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to be ready
        for attempt in range(30):  # 30 second timeout
            try:
                response = requests.get(f"{FASTAPI_SERVER_URL}/health", timeout=1)
                if response.status_code == 200:
                    logger.info(f"FastAPI server started successfully on {FASTAPI_SERVER_URL}")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(1)
                
        logger.error("FastAPI server failed to start within timeout")
        return False
        
    except Exception as e:
        logger.error(f"Error starting FastAPI server: {e}")
        return False

def check_server_health():
    """Check if the FastAPI server is running and healthy"""
    try:
        response = requests.get(f"{FASTAPI_SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


# Advanced test prompts for complex tasks, data analysis, and heavier computation
ADVANCED_TEST_PROMPTS = [
    # 1. Data analysis with actual results
    "Analyze these two datasets representing daily temperatures [72, 75, 73, 70, 76] and [65, 63, 68, 70, 71]. Calculate the average, min, max for each dataset and determine if there's a statistically significant difference between them.",
    
    # 2. Financial calculations
    "I have two investment options: Option A with initial investment of $5000 and 7% annual return, and Option B with initial investment of $7000 and 5.5% annual return. Compare their values after 10 years and tell me which option yields better returns.",
    
    # 3. Text processing and sentiment analysis
    "Analyze these two customer reviews: 'This product exceeded my expectations, highly recommend!' and 'Disappointed with quality, wouldn't buy again'. Score their sentiment on a scale of -1 to 1 and extract key positive/negative phrases.",
    
    # 4. Recommendation system simulation
    "Based on two user preferences arrays [5, 3, 4, 1, 5] and [2, 4, 5, 1, 3] for categories [movies, books, games, sports, music], recommend top 2 categories for each user and explain your reasoning.",
    
    # 5. Data transformation for reporting
    "Transform these raw sales data for two regions: Region A [120, 145, 190, 210, 180] and Region B [150, 135, 160, 175, 190] into quarter-over-quarter growth percentages and create a summary comparing their performance.",
    
    # 6. Practical algorithm application
    "Sort these two lists of customer IDs [1005, 1001, 1020, 1003] and [2007, 2001, 2015] by priority, where lower numbers have higher priority. Then merge them into a single prioritized queue while maintaining order.",
    
    # 7. Decision making and optimization
    "I need to schedule 8 hours of work time between two projects. Project A earns $50 per hour but has a 5-hour maximum, while Project B earns $30 per hour. Calculate the optimal allocation of time to maximize earnings and show the reasoning.",
    
    # 8. Time series forecasting
    "Given these historical sales data for two products: Product A [100, 120, 140, 160, 180] and Product B [200, 190, 195, 205, 210], forecast the next two values for each product and explain which product is trending better.",
    
    # 9. Classification task
    "Classify these email subjects into priority categories (High, Medium, Low): 'URGENT: Server down' and 'Weekly newsletter'. Explain your classification reasoning and confidence level.",
    
    # 10. Risk analysis
    "Analyze the risk profiles of two investment strategies: Strategy A with 70% success probability and $1000 return vs. Strategy B with 40% success probability and $3000 return. Calculate expected values and tell me which has better risk-adjusted returns.",
    
    # 11. Graph algorithm
    "Given a graph with nodes A, B, C, D, E and edges [(A,B,3), (A,C,5), (B,C,2), (B,D,6), (C,D,1), (C,E,4), (D,E,2)] where the third value is the weight, find the shortest path from A to E using Dijkstra's algorithm and show each step.",
    
    # 12. Image processing
    "Create a function to generate a simple 5x5 image represented as a 2D array. Then apply a blur effect by replacing each pixel with the average of itself and its adjacent pixels.",
    
    # 13. Cryptography
    "Implement a Caesar cipher function that takes a string and a shift value, then encrypts the string by shifting each letter by the specified amount. Then decrypt the message to verify correctness.",
    
    # 14. Object-oriented design
    "Design a basic banking system with classes for Account, Customer, and Transaction. Include methods for deposit, withdrawal, and transfer between accounts with appropriate validation.",
    
    # 15. Recursion and dynamic programming
    "Calculate the nth Fibonacci number using both recursive and dynamic programming approaches. Compare their performance for n=20 and explain the difference.",
    
    # 16. Web API simulation
    "Create a function that simulates fetching data from an API by parsing this JSON string: '{\"users\": [{\"id\": 1, \"name\": \"Alice\"}, {\"id\": 2, \"name\": \"Bob\"}]}'. Then filter users by a given criterion.",
    
    # 17. Probability and simulation
    "Simulate rolling two dice 1000 times and analyze the distribution of their sum. Calculate the probability of each possible sum and compare with theoretical probabilities.",
    
    # 18. File operations
    "Write and run a function that creates a temporary file with sample data, reads it line by line, performs word count analysis, and returns statistics on most frequent words.",
    
    # 19. Machine learning basics
    "Implement a simple k-Nearest Neighbors classifier from scratch. Test it on these points: Class A [(1,2), (2,3), (3,1)] and Class B [(5,6), (6,5), (7,7)]. Classify point (4,5).",
    
    # 20. String manipulation
    "Create a function to check if two strings are anagrams of each other, ignoring spaces and case. Test with 'listen' and 'silent' as well as 'conversation' and 'voices rant on'.",
]


def save_downloaded_file_locally(filename: str, content: bytes, plots_dir: str) -> str:
    """Save downloaded file content to local directory for display purposes"""
    try:
        local_path = os.path.join(plots_dir, filename)
        with open(local_path, 'wb') as f:
            f.write(content)
        logger.info(f"Saved downloaded file locally: {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Error saving file {filename}: {e}")
        return ""

def display_message_plots(agent: HTTPCodeExecutorAgent, message_id=None):
    """Display plots for a specific message or all messages using the new structured file tracking"""
    import matplotlib.pyplot as plt
    
    if message_id:
        # Use new structured approach
        message_files = agent.file_tracker.get_message_files(message_id)
        if not message_files:
            print(f"No files found for message {message_id}")
            return
            
        plot_files = message_files.get_plot_files()
        print(f"Displaying {len(plot_files)} plots for message {message_id}")
        
        for filename, file_metadata in plot_files.items():
            print(f"  📊 {filename}")
            print(f"      🔗 URL: {file_metadata.download_url}")
            print(f"      📏 Size: {file_metadata.size} bytes")
            print(f"      🏷️  Type: {file_metadata.mime_type}")
            
            # Only display if we have content
            if file_metadata.has_content() and filename.lower().endswith('.png'):
                local_path = save_downloaded_file_locally(filename, file_metadata.content, PLOTS_DIR)
                if local_path:
                    plt.figure(figsize=(10, 6))
                    img = plt.imread(local_path)
                    plt.imshow(img)
                    plt.axis('off')
                    plt.title(f"Message ID: {message_id} - {filename}")
                    plt.show()
            elif not file_metadata.has_content():
                print(f"      ⚠️  No content (URL-only mode)")
    else:
        # Display all messages
        total_plots = 0
        total_with_content = 0
        
        for msg_id, message_files in agent.file_tracker.messages.items():
            plot_files = message_files.get_plot_files()
            total_plots += len(plot_files)
            
            print(f"\n📂 Message {msg_id}:")
            stats = message_files.get_stats()
            print(f"   📊 {stats['plots']} plots, {stats['with_content']} with content, {stats['url_only']} URL-only")
            
            for filename, file_metadata in plot_files.items():
                print(f"   📄 {filename} ({file_metadata.size} bytes)")
                
                if file_metadata.has_content() and filename.lower().endswith('.png'):
                    total_with_content += 1
                    local_path = save_downloaded_file_locally(filename, file_metadata.content, PLOTS_DIR)
                    if local_path:
                        plt.figure(figsize=(10, 6))
                        img = plt.imread(local_path)
                        plt.imshow(img)
                        plt.axis('off')
                        plt.title(f"Message ID: {msg_id} - {filename}")
                        plt.show()
        
        print(f"\n📈 Summary: {total_plots} total plots, {total_with_content} displayed with content")

async def test_with_prompt(prompt, agent: HTTPCodeExecutorAgent):
    """Run a test with the given prompt and return the result."""
    # Generate a new message ID for this test
    message_id = agent.set_message_id()
    
    print(f"\n--- Testing agent with prompt [{message_id}]: {prompt} ---")
    
    # Use the context manager for resource cleanup
    with execution_cleanup():
        result = await Runner.run(
            agent, 
            input=prompt
        )
        print("-"*100)
        print("\033[1;32mAgent response:\033[0m")
        print(result.final_output)
        print("-"*100)
        
        # Use new structured approach to get file information
        message_files = agent.file_tracker.get_message_files(message_id)
        if message_files:
            stats = message_files.get_stats()
            print(f"📊 Generated Files: {stats['total_files']} total, {stats['plots']} plots")
            print(f"   💾 With content: {stats['with_content']}, 🔗 URL-only: {stats['url_only']}")
            
            # Show file details
            for filename, file_metadata in message_files.files.items():
                print(f"   📄 {filename}: {file_metadata.size} bytes ({file_metadata.mime_type})")
                if file_metadata.has_content():
                    print(f"      ✅ Content downloaded")
                else:
                    print(f"      🔗 URL available: {file_metadata.download_url}")
        
        # Return result with structured file information
        return {
            'message_id': message_id,
            'response': result.final_output,
            'message_files': message_files,
            'file_stats': message_files.get_stats() if message_files else {}
        }

async def main(run_advanced_tests=True) -> Dict[str, Any]:
    """
    Run tests with the HTTP-based code execution agent.
    
    This test uses the new HTTP-based code execution through FastAPI server.
    The server provides secure, isolated code execution with automatic file handling.
    Demonstrates both download modes and structured file tracking.
    
    Args:
        run_advanced_tests: If True, runs the advanced data analysis and computational prompts
    
    Returns:
        Dictionary containing test results and agent statistics
    """
    
    import matplotlib
    matplotlib.use('Agg')
    
    # Verify server is healthy
    if not check_server_health():
        logger.error("FastAPI server is not healthy. Cannot run tests.")
        return {'message_results': [], 'url_only_stats': {}, 'download_stats': {}, 'agents': {}}
        
    logger.info("FastAPI server is running and healthy - ready for HTTP-based code execution")
    
    # Test both download modes
    print("🔄 Testing URL-only mode (lightweight)...")
    url_only_agent = HTTPCodeExecutorAgent(
        name="URL-Only Agent",
        should_download_files=False
    )
    
    print("🔄 Testing full download mode...")
    download_agent = HTTPCodeExecutorAgent(
        name="Download Agent", 
        should_download_files=True
    )
    
    # Run tests with both agents
    message_results = []
    filtered_prompts = ADVANCED_TEST_PROMPTS[16:17]  # File operations test
    
    print("\n" + "="*80)
    print("TESTING URL-ONLY MODE (should_download_files=False)")
    print("="*80)
    for i, prompt in enumerate(filtered_prompts):
        print(f"Running URL-only test {i+1}")
        result = await test_with_prompt(prompt, url_only_agent)
        result['agent_mode'] = 'url_only'
        message_results.append(result)
    
    print("\n" + "="*80)
    print("TESTING FULL DOWNLOAD MODE (should_download_files=True)")
    print("="*80)
    for i, prompt in enumerate(filtered_prompts):
        print(f"Running download test {i+1}")
        result = await test_with_prompt(prompt, download_agent)
        result['agent_mode'] = 'full_download'
        message_results.append(result)
    
    # Demonstrate structured file access
    print("\n" + "="*80)
    print("STRUCTURED FILE TRACKING DEMONSTRATION")
    print("="*80)
    
    # URL-only agent stats
    url_stats = url_only_agent.file_tracker.get_overall_stats()
    file_counts = url_only_agent.file_tracker.get_file_counts()
    plots_by_msg = url_only_agent.file_tracker.get_plots_by_message()
    
    print("📊 URL-Only Agent Statistics:")
    print(f"   📁 Total files: {url_stats['total_files']}")
    print(f"   💾 With content: {file_counts['with_content']}")
    print(f"   🔗 URL-only: {file_counts['url_only']}")
    print(f"   📈 Plot messages: {len(plots_by_msg)}")
    
    # Download agent stats  
    download_stats = download_agent.file_tracker.get_overall_stats()
    download_counts = download_agent.file_tracker.get_file_counts()
    download_plots = download_agent.file_tracker.get_plots_by_message()
    
    print("\n📊 Download Agent Statistics:")
    print(f"   📁 Total files: {download_stats['total_files']}")
    print(f"   💾 With content: {download_counts['with_content']}")
    print(f"   🔗 URL-only: {download_counts['url_only']}")
    print(f"   📈 Plot messages: {len(download_plots)}")
    print(f"   💽 Total size: {download_stats['total_size_bytes']} bytes")
    
    # Demonstrate structured access
    print("\n🔍 Detailed File Analysis:")
    for agent_name, agent in [("URL-Only", url_only_agent), ("Download", download_agent)]:
        print(f"\n--- {agent_name} Agent Files ---")
        for message_id, message_files in agent.file_tracker.messages.items():
            print(f"📂 Message {message_id}:")
            
            # File type breakdown
            all_files = message_files.files
            images = {name: f for name, f in all_files.items() if f.is_image()}
            plots = message_files.get_plot_files()
            content_files = message_files.get_files_with_content()
            
            print(f"   📄 All files: {len(all_files)}")
            print(f"   🖼️  Images: {len(images)}")
            print(f"   📊 Plots: {len(plots)}")
            print(f"   💾 With content: {len(content_files)}")
            
            # Show individual file details
            for filename, file_metadata in all_files.items():
                content_indicator = "💾" if file_metadata.has_content() else "🔗"
                print(f"   {content_indicator} {filename} ({file_metadata.size} bytes)")
    
    # Display plots from download agent only (since it has content)
    print("\n📈 Displaying plots from Download Agent...")
    matplotlib.use('TkAgg')  # Switch to interactive backend for display
    display_message_plots(download_agent)
    
    # Return comprehensive results
    return {
        'message_results': message_results,
        'url_only_stats': url_stats,
        'download_stats': download_stats,
        'agents': {
            'url_only': url_only_agent,
            'download': download_agent
        }
    }

if __name__ == "__main__":
    # Run the test with HTTP-based code execution
    from dotenv import load_dotenv
    
    # Attempt to load environment variables from .env file
    load_dotenv()
    
    # Set logging level for cleaner output
    set_log_level(logging.INFO)
    
    print("="*80)
    print("STARTING HTTP-BASED CODE EXECUTION TESTS")
    print("="*80)
    print("This test uses FastAPI server for secure, isolated code execution")
    print("with automatic per-execution workspaces and file downloading.")
    print("="*80)
    print(f"🔄 Testing Features:")
    print(f"  • should_download_files=True (downloads content + URLs)")
    print(f"  • should_download_files=False (tracks URLs only)")
    print(f"  • Structured file tracking with FileMetadata classes")
    print(f"  • Automatic file type detection and categorization")
    print("="*80)
    
    # Clean up the plots directory at the start of the run
    logger.info(f"Cleaning up plots directory: {PLOTS_DIR}")
    try:
        for file_path in os.listdir(PLOTS_DIR):
            file_full_path = os.path.join(PLOTS_DIR, file_path)
            try:
                if os.path.isfile(file_full_path):
                    os.unlink(file_full_path)
                elif os.path.isdir(file_full_path):
                    shutil.rmtree(file_full_path)
            except Exception as e:
                logger.warning(f"Error cleaning up file {file_full_path}: {e}")
    except Exception as e:
        logger.warning(f"Error during plots directory cleanup: {e}")
    
    # Run tests
    results = asyncio.run(main())
    
    if results and isinstance(results, dict) and 'message_results' in results:
        message_results = results['message_results']
        print("\n" + "="*80)
        print("HTTP-BASED CODE EXECUTION TESTS COMPLETED")
        print("="*80)
        print(f"✅ Completed {len(message_results)} tests successfully")
        print(f"🚀 Used FastAPI server: {FASTAPI_SERVER_URL}")
        print("📁 All files automatically downloaded via HTTP")
        print("\nTest Message IDs:")
        for result in message_results:
            if isinstance(result, dict):
                print(f"  - {result.get('message_id', 'unknown')} ({result.get('agent_mode', 'unknown')})")
                message_files = result.get('message_files')
                if message_files and hasattr(message_files, 'files'):
                    print(f"    Files: {list(message_files.files.keys())}")
        
        # Show comparison between modes
        url_stats = results.get('url_only_stats', {})
        download_stats = results.get('download_stats', {})
        print(f"\n📊 Mode Comparison:")
        print(f"   URL-Only: {url_stats.get('total_files', 0)} files, {url_stats.get('total_size_bytes', 0)} bytes")
        print(f"   Download: {download_stats.get('total_files', 0)} files, {download_stats.get('total_size_bytes', 0)} bytes")
        print("="*80)
    else:
        print("❌ No test results to display")
