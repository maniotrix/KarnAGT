#!/usr/bin/env python3
"""
Simple test runner for frontend simulation
"""

import asyncio
import sys
import os
sys.path.append(os.getcwd())
from run_stream_tests_clean import RealFrontendStreamTester

async def run_test():
    async with RealFrontendStreamTester() as tester:
        success = await tester.run_complete_frontend_simulation()
    return success

if __name__ == '__main__':
    result = asyncio.run(run_test())
    print(f'Test result: {result}') 