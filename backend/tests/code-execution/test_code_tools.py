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
from app.aicore.code_executor.services.health_service import HealthService
from app.aicore.code_executor.workspace_session import WorkspaceExecutionSession, create_session_aware_code_tools
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



def create_test_agent(workspace_session: WorkspaceExecutionSession) -> Agent:
    """Create test agent with session-aware tools"""
    return Agent(
        name="test_agent",
        model="gpt-4o-mini-2024-07-18",
        instructions="""
        # CODE EXECUTION INSTRUCTIONS:
        Execute Python code in a isolated workspace with a valid workspace_id with persistent state and file generation capabilities.
        
        Make sure to strictly follow all the code execution instructions and requirements below.
        
        ## CRITICAL REQUIREMENT FOR CODE EXECUTION: 
        - You MUST have a valid workspace_id before calling this function
        - If you don't have one, call create_workspace() FIRST to get a workspace_id
        - NEVER use arbitrary workspace IDs like "1", "test", etc.
        - ALWAYS use the exact workspace_id returned by create_workspace()
        - ALWAYS check if the execution succeeded before using any outputs
        
        ## CRITICAL TIMEOUT HANDLING:
        - If a piece of code times-out, do not execute **the same timed-out code** again.
        - DO NOT make up or estimate results for failed or timed out code executions
        - If you receive a timeout error, you MUST:
            1. Analyze why the code timed out
            2. Optimize the code (e.g., use more efficient algorithms)
            3. Reduce computational complexity
            4. Only then try to execute the OPTIMIZED code
        - NEVER retry the exact same code after a timeout

        ## REQUIRED PARAMETERS:
        - workspace_id: Valid workspace ID from create_workspace()
        - code: Python code string

        ## RETURN VALUE STRUCTURE:
        The tool returns an ExecutionOperationResult containing:
        - **success**: boolean indicating if execution completed successfully
        - **standard output**: text that was printed during execution  
        - **error messages**: any error messages that occurred
        - **generated files**: list of files created during execution with full HTTP download URLs
        - **result data**: the final computed result (if any)
        
        ## CODE EXECUTION ENVIRONMENT:
        - Jupyter kernel with persistent variables/imports across calls
        - Working directory: workspace root (contains uploaded files)
        - Full Python standard library + common packages (numpy, pandas, matplotlib, etc.)
        - Output capture: stdout, stderr, and execution results
        - Your code will be executed with a timeout of 30 seconds.
        
        ## FILE OPERATIONS:
        - **Read files**: open('filename.txt', 'r') - access uploaded files directly
        - **Create files**: open('output.csv', 'w') - any file you create gets tracked
        - **Generate plots**: plt.savefig('chart.png') - saved plots are automatically detected

        ## EXAMPLES:
        ```python
        # Data analysis with CSV output
        df.to_csv('analysis_results.csv', index=False)
        
        # Visualization with plot file
        plt.figure(figsize=(10,6))
        plt.plot(data)
        plt.savefig('visualization.png', dpi=300, bbox_inches='tight')
        
        # Generate reports or documents  
        with open('report.txt', 'w') as f:
            f.write(f"Analysis completed: {results}")
        ```

        ## BEST PRACTICES and DATA VISUALIZATION INSTRUCTIONS:
        - DO NOT use plt.show() as it will cause errors in the execution environment.
        - Always close plt figures: plt.close() after plt.savefig()
        - Use descriptive filenames with extensions
        - Save files you want users to access (they get full HTTP download URLs automatically)
        - Use result = your_final_value to return computed results
        """,
        tools=create_session_aware_code_tools(workspace_session),
    )

health_service = HealthService()


async def check_sandbox_health(results: TestResults):
    print("\n2. Testing CodeSandbox health check...")
    codesandbox_health = await health_service.check_codesandbox_health()
    results.assert_true(isinstance(codesandbox_health, dict), "CodeSandbox health returns dictionary")
    results.assert_true('healthy' in codesandbox_health, "CodeSandbox health includes 'healthy' field")
    results.assert_true('status' in codesandbox_health, "CodeSandbox health includes 'status' field")

async def test_with_prompt(prompt: str):
    """Run a test with the given prompt using workspace session for automatic cleanup."""
    print(f"\n--- Testing agent with prompt: {prompt} ---")
    
    # Use workspace session as context manager for automatic cleanup
    async with WorkspaceExecutionSession() as session:
        print(f"Created workspace session: {session.session_id}")
        
        # Create agent with session-aware tools
        agent = create_test_agent(session)
        
        # Run the agent
        result = await Runner.run(agent, input=prompt)
        
        print("-"*100)
        print("\033[1;32mAgent response:\033[0m")
        print(result.final_output)
        print("-"*100)
        
        # Show session info
        session_info = session.get_session_info()
        print(f"Session {session.session_id} created {session_info['tracked_workspaces']} workspaces")
        
    # Workspaces are automatically cleaned up when exiting the context manager
    print(f"Session {session.session_id} cleanup completed")
    print(f"Session Info: {session.get_session_info()}")

async def test_agent_with_upload_file():
    """Run a test with the given prompt using workspace session for automatic cleanup."""
    print(f"\n--- Testing agent with upload file ---")
    
    # HTTP URL
    http_file_url = 'https://raw.githubusercontent.com/orangetw/Tiny-URL-Fuzzer/master/samples.txt'
    
    prompt = f"Here is the file link: {http_file_url}. Please analyze the file details, metadata and show me the top 10 lines."
    additional_prompt = f"After that, also solve this {ADVANCED_TEST_PROMPTS[14]} in a different workspace."
    final_prompt = f"Critical: Must run both tasks in different workspaces."
    prompt = f"{prompt}\n{additional_prompt}\n{final_prompt}"
    
    await test_with_prompt(prompt)
        

async def main():
    results = TestResults()
    await check_sandbox_health(results)
    # filtered_prompts = ADVANCED_TEST_PROMPTS[14:15]  # Simple timeout test
    # for i, prompt in enumerate(filtered_prompts):
    #     print(f"--- Running test {i+1} ---")
    #     await test_with_prompt(prompt)
    
    await test_agent_with_upload_file()
    
    results.summary()

if __name__ == "__main__":
    asyncio.run(main())

