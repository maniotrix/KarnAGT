import asyncio
import sys
import os
import logging
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

sys.path.append(backend_dir)

from agents import Agent, Runner
from app.aicore.code_executor.tools.default_llm_code_tools import create_workspace, upload_file, execute_code
from app.aicore.code_executor.services.health_service import HealthService

from app.logging.logger import get_logger

logger = get_logger(__name__)

logger.setLevel(logging.DEBUG)


class TestResults:
    """Simple test results tracker"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []
    
    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
            print(f"✅ {message}")
        else:
            self.failed += 1
            self.failures.append(message)
            print(f"❌ {message}")
    
    def assert_false(self, condition: bool, message: str):
        self.assert_true(not condition, message)
    
    def skip(self, message: str):
        self.skipped += 1
        print(f"⏭️ SKIPPED: {message}")
    
    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*50}")
        print(f"TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"⏭️ Skipped: {self.skipped}")
        
        if self.failures:
            print(f"\nFAILED TESTS:")
            for failure in self.failures:
                print(f"  - {failure}")
        
        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")

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




test_agent = Agent(
    name="test_agent",
    model="gpt-4o-mini-2024-07-18",
    instructions="""
    **CODE EXECUTION WORKFLOW:**
    1. ALWAYS call create_workspace() FIRST before any code execution
    2. Use the returned workspace_id for ALL subsequent execute_code() calls
    3. NEVER use arbitrary workspace IDs like "1", "test", etc.
    
    **DATA VISUALIZATION INSTRUCTIONS:**
    1. DO NOT use plt.show() as it will cause errors in the execution environment.
    2. Use plt.savefig() to save plots, then plt.close() to free memory
    """,
    tools=[create_workspace, upload_file, execute_code],
)

health_service = HealthService()


async def check_sandbox_health(results: TestResults):
    print("\n2. Testing CodeSandbox health check...")
    codesandbox_health = await health_service.check_codesandbox_health()
    results.assert_true(isinstance(codesandbox_health, dict), "CodeSandbox health returns dictionary")
    results.assert_true('healthy' in codesandbox_health, "CodeSandbox health includes 'healthy' field")
    results.assert_true('status' in codesandbox_health, "CodeSandbox health includes 'status' field")

async def test_with_prompt(prompt, agent: Agent):
    """Run a test with the given prompt and return the result."""
    print(f"\n--- Testing agent with prompt: {prompt} ---")
    
    result = await Runner.run(
            agent, 
            input=prompt
        )
    print("-"*100)
    print("\033[1;32mAgent response:\033[0m")
    print(result.final_output)
    print("-"*100)

async def main():
    results = TestResults()
    await check_sandbox_health(results)
    filtered_prompts = ADVANCED_TEST_PROMPTS[0:10]  # File operations test
    for i, prompt in enumerate(filtered_prompts):
        print(f"--- Running test {i+1} ---")
        await test_with_prompt(prompt, test_agent)
    results.summary()

if __name__ == "__main__":
    asyncio.run(main())

