#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test file for the code executor module with LLM-generated code strings.
"""

import sys
import os
# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import asyncio
import logging
import time
import glob
import tempfile
import gc
import shutil  # Force non-interactive backend to prevent GUI errors
from agents import Runner
from aicore.code_executor.logger import get_logger, set_log_level
from aicore.code_executor.code_agent import CodeExecutorAgent
from aicore.path_config import PLOTS_DIR
from aicore.code_executor.utils import execution_cleanup

# Get logger
logger = get_logger()

# Define a fixed directory for plot outputs
os.makedirs(PLOTS_DIR, exist_ok=True)


# Create an instance of our custom CodeExecutorAgent
# Remove global agent creation
# agent = CodeExecutorAgent(
#     name="Code Executor Agent",
#     root_plots_dir=PLOTS_DIR
# )


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


def display_message_plots(agent, message_id=None):
    """Display plots for a specific message or all messages"""
    import matplotlib.pyplot as plt
    
    if message_id:
        plot_files = sorted(glob.glob(f"{agent.unique_plots_dir}/{message_id}_*.png"))
        print(f"Displaying {len(plot_files)} plots for message {message_id}")
    else:
        plot_files = sorted(glob.glob(f"{agent.unique_plots_dir}/*.png"))
        print(f"Displaying all {len(plot_files)} plots")
    
    for plot_file in plot_files:
        filename = os.path.basename(plot_file)
        # Extract message ID from filename
        msg_id = filename.split('_')[0]
        
        plt.figure(figsize=(10, 6))
        img = plt.imread(plot_file)
        plt.imshow(img)
        plt.axis('off')
        plt.title(f"Message ID: {msg_id} - {filename}")
        plt.show()

async def test_with_prompt(prompt, agent : CodeExecutorAgent):
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
        
        # Return result with the message ID we generated
        return {
            'message_id': message_id,
            'response': result.final_output,
            'plots': glob.glob(f"{agent.unique_plots_dir}/{message_id}_*.png")
        }

async def main(run_advanced_tests=True, ):
    """
    Run tests with the code execution agent.
    
    Args:
        run_advanced_tests: If True, runs the advanced data analysis and computational prompts
        num_prompts: Number of advanced prompts to run (default: 1)
    """
    
    import matplotlib
    matplotlib.use('Agg')
    
    # Create agent instance after cleanup
    agent = CodeExecutorAgent(
        name="Code Executor Agent",
        root_plots_dir=PLOTS_DIR
    )
    
    # Run advanced tests if requested
    message_results = []
    length_of_prompts = len(ADVANCED_TEST_PROMPTS)  
    filtered_prompts = ADVANCED_TEST_PROMPTS[11:20]
    for i, prompt in enumerate(filtered_prompts):
        print("#"*100)
        print(f"Running advanced test {i} of {len(filtered_prompts)}")
        print("#"*100)
        result = await test_with_prompt(prompt, agent)
        message_results.append(result)
    
    # Get all plots from the agent with message ids
    print(f"--- All plots---:\n {agent.get_all_plots_with_message_id()}")
    
    # Uncomment to display plots
    matplotlib.use('TkAgg')  # Switch to interactive backend for display
    display_message_plots(agent)
    
    return message_results

if __name__ == "__main__":
    # Run the test
    from dotenv import load_dotenv
    
    # Attempt to load environment variables from .env file
    load_dotenv()
    
    # Disable logging for cleaner output
    set_log_level(logging.INFO)
    
    # Clean up the plots directory at the start of the run
    logger.info(f"Cleaning up plots directory: {PLOTS_DIR}")
    try:
        for file_path in glob.glob(os.path.join(PLOTS_DIR, "*")):
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.warning(f"Error cleaning up file {file_path}: {e}")
    except Exception as e:
        logger.warning(f"Error during plots directory cleanup: {e}")
    
    # Run tests
    message_results = asyncio.run(main())
    
    if message_results:
        print(f"\nCompleted {len(message_results)} tests with message IDs:")
        for result in message_results:
            print(f"- {result['message_id']}")
