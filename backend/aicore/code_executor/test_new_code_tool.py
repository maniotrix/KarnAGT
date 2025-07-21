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

# Get logger
logger = get_logger()

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
    """Display plots for a specific message or all messages using downloaded files"""
    import matplotlib.pyplot as plt
    
    if message_id:
        files = agent.get_downloaded_files_for_message(message_id)
        plot_files = [(name, content) for name, content in files.items() 
                     if name.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.pdf'))]
        print(f"Displaying {len(plot_files)} plots for message {message_id}")
        
        for filename, content in plot_files:
            # Save file locally for display
            local_path = save_downloaded_file_locally(filename, content, PLOTS_DIR)
            if local_path and filename.lower().endswith('.png'):
                plt.figure(figsize=(10, 6))
                img = plt.imread(local_path)
                plt.imshow(img)
                plt.axis('off')
                plt.title(f"Message ID: {message_id} - {filename}")
                plt.show()
    else:
        all_files = agent.get_all_downloaded_files()
        total_plots = 0
        
        for msg_id, files in all_files.items():
            plot_files = [(name, content) for name, content in files.items() 
                         if name.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.pdf'))]
            total_plots += len(plot_files)
            
            for filename, content in plot_files:
                # Save file locally for display
                local_path = save_downloaded_file_locally(filename, content, PLOTS_DIR)
                if local_path and filename.lower().endswith('.png'):
                    plt.figure(figsize=(10, 6))
                    img = plt.imread(local_path)
                    plt.imshow(img)
                    plt.axis('off')
                    plt.title(f"Message ID: {msg_id} - {filename}")
                    plt.show()
        
        print(f"Displayed {total_plots} plots from {len(all_files)} messages")

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
        
        # Extract downloaded files from the agent's tools if any were generated
        # Note: We need to check the actual execution results for downloaded files
        # The agent's tools should handle this automatically, but we can verify
        
        # Return result with the message ID we generated
        return {
            'message_id': message_id,
            'response': result.final_output,
            'downloaded_files': agent.get_downloaded_files_for_message(message_id)
        }

async def main(run_advanced_tests=True):
    """
    Run tests with the HTTP-based code execution agent.
    
    This test uses the new HTTP-based code execution through FastAPI server.
    The server provides secure, isolated code execution with automatic file handling.
    
    Args:
        run_advanced_tests: If True, runs the advanced data analysis and computational prompts
    """
    
    import matplotlib
    matplotlib.use('Agg')
    
    # # Start the FastAPI server for HTTP-based code execution
    # logger.info("Starting FastAPI code execution server...")
    # if not start_fastapi_server():
    #     logger.error("Failed to start FastAPI server. Cannot run tests.")
    #     return []
    
    # Verify server is healthy
    if not check_server_health():
        logger.error("FastAPI server is not healthy. Cannot run tests.")
        return []
        
    logger.info("FastAPI server is running and healthy - ready for HTTP-based code execution")
    
    # Create HTTP-based agent instance (no root_plots_dir needed)
    agent = HTTPCodeExecutorAgent(
        name="HTTP Code Executor Agent"
    )
    
    # Run advanced tests if requested
    message_results = []
    filtered_prompts = ADVANCED_TEST_PROMPTS[16:17]
    
    for i, prompt in enumerate(filtered_prompts):
        print("#"*100)
        print(f"Running advanced test {i+1} of {len(filtered_prompts)}")
        print("#"*100)
        result = await test_with_prompt(prompt, agent)
        message_results.append(result)
    
    # Get all plots from the agent with message ids
    plots_info = agent.get_all_plots_with_message_id()
    print(f"--- All plots (via HTTP file downloads)---:\n {plots_info}")
    
    # Display agent statistics
    stats = agent.get_stats()
    print(f"--- Agent Statistics ---:")
    print(f"Total messages: {stats['total_messages']}")
    print(f"Total files: {stats['total_files']}")
    print(f"Total size: {stats['total_size_bytes']} bytes")
    print(f"Messages with plots: {stats['messages_with_plots']}")
    
    # Display information about HTTP-based execution
    logger.info("Tests completed using HTTP-based code execution with automatic file downloading")
    logger.info(f"FastAPI server: {FASTAPI_SERVER_URL}")
    
    # Uncomment to display plots
    matplotlib.use('TkAgg')  # Switch to interactive backend for display
    display_message_plots(agent)
    
    return message_results

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
    message_results = asyncio.run(main())
    
    if message_results:
        print("\n" + "="*80)
        print("HTTP-BASED CODE EXECUTION TESTS COMPLETED")
        print("="*80)
        print(f"✅ Completed {len(message_results)} tests successfully")
        print(f"🚀 Used FastAPI server: {FASTAPI_SERVER_URL}")
        print("📁 All files automatically downloaded via HTTP")
        print("\nTest Message IDs:")
        for result in message_results:
            print(f"  - {result['message_id']}")
            if result['downloaded_files']:
                print(f"    Files: {list(result['downloaded_files'].keys())}")
        print("="*80)
