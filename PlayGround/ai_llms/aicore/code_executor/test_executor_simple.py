#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple direct test for the timeout enhancement of the code executor
"""

import sys
import os
import asyncio
import time
import logging

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from aicore.code_executor.code_executor import execute_code_string, DEFAULT_TIMEOUT
from aicore.code_executor.logger import get_logger, set_log_level

# Set up logging
logger = get_logger()
set_log_level(logging.INFO)

# Test the timeout functionality
async def test_timeout():
    print("\n=== Testing Timeout ===")
    
    # Code with infinite loop
    infinite_loop_code = """
# This will run an infinite loop
import time
start_time = time.time()

print("Starting infinite loop...")
result = 0  # Set initial result
while True:
    result += 1
    # Print progress every million iterations
    if result % 1000000 == 0:
        elapsed = time.time() - start_time
        print(f"Completed {result:,} iterations in {elapsed:.2f} seconds")
"""
    
    # Run with default timeout
    print(f"Running infinite loop with default timeout ({DEFAULT_TIMEOUT}s)...")
    start_time = time.time()
    
    try:
        # Execute with default timeout
        result = await execute_code_string(infinite_loop_code)  # Use default timeout
        elapsed = time.time() - start_time
        
        # Print results
        print(f"\nExecution completed in {elapsed:.2f} seconds")
        print(f"Status: {result.status}")
        print(f"Error: {result.error}")
        print(f"Stdout: {result.stdout}")
        
        # Check if timeout worked
        if result.status == "error" and "timed out" in result.error:
            print("\nSUCCESS: Code execution timed out as expected!")
        else:
            print("\nFAILED: Infinite loop didn't timeout as expected")
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\nError occurred after {elapsed:.2f} seconds: {type(e).__name__} - {e}")
    
    # Small delay to let logs catch up in the console
    await asyncio.sleep(1)
    print("\nTimeout test complete")

async def main():
    print(f"Testing code executor timeout mechanism (default: {DEFAULT_TIMEOUT}s)")
    
    # Run the timeout test
    await test_timeout()
    
    print("\nAll tests completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__} - {e}") 