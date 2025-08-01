CREATE_WORKSPACE_TOOL_DESCRIPTION = """
Create a new isolated workspace for Python code execution.
        
This workspace will be automatically tracked and cleaned up when the session ends.

HOW IT WORKS:
- Creates a fresh Python environment with Jupyter kernel
- Workspace automatically expires after specified hours
- Variables and imports persist across multiple code executions
- Automatically tracked for cleanup by session manager

WHEN TO USE:
- At the start of any coding task or data analysis
- When you need a clean environment for Python execution
- Before uploading files or running any code

WHAT YOU GET BACK:
- workspace_id: Use this for all subsequent upload_file and execute_code calls
- status: "ready" when workspace is available for use
- expires_at: When the workspace will be automatically cleaned up
"""

UPLOAD_FILE_TOOL_DESCRIPTION = """
Upload a file to a workspace so it can be accessed by Python code.
        
## CRITICAL FILE UPLOAD INSTRUCTIONS:
File URL must be a valid Full HTTP URL and the maximum file size allowed is 20MB.
You must provide a file_name to be used for the file in the workspace.

## REQUIRED PARAMETERS:
- workspace_id: Valid workspace ID from create_workspace()
- file_url: Valid Full HTTP URL
- file_name: Name of the file

## RETURN VALUE STRUCTURE:
The tool returns a FileUploadResult containing:
- **success**: boolean indicating if upload completed successfully
- **file_info**: FileInfo object with details about the uploaded file
- **error**: Optional error message if upload failed

## EXAMPLES:
upload_file(workspace_id="ws_abc123", file_url="https://example.com/data.csv", file_name="data.csv")
"""


EXECUTE_CODE_TOOL_DESCRIPTION = """
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
"""








