#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Instruction Builder - Dynamic instruction generation based on configuration
"""

import os
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

# Use absolute imports to avoid circular import issues
from aicore.config.agent_config import AgentConfig, CodeExecutionConfig, WebSearchConfig
from aicore.prompt_utils import INITIAL_CORE_PROMPT


@dataclass
class InstructionContext:
    """Context information for instruction generation"""
    message_id: str
    plots_directory: str
    os_type: str = "Windows"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=lambda: None)


class InstructionBuilder:
    """Builds dynamic instructions based on agent configuration and context"""
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the instruction builder
        
        Args:
            config: Agent configuration to use for instruction generation
        """
        self.config = config
        self.template_cache: Dict[str, str] = {}
        
    def build_instructions(self, context: InstructionContext) -> str:
        """
        Build complete instructions based on configuration and context
        
        Args:
            context: Context information for instruction generation
            
        Returns:
            Complete instruction string
        """
        # Start with core prompt
        instructions = self._get_core_prompt()
        
        # Add capability descriptions
        instructions += self._build_capabilities_section()
        
        # Add tool instructions
        if self.config.code_execution.enabled:
            instructions += self._build_code_execution_instructions(context)
        
        if self.config.web_search.enabled:
            instructions += self._build_web_search_instructions()
        
        # Add output formatting instructions
        instructions += self._build_output_formatting_instructions(context)
        
        # Add constraints and guidelines
        instructions += self._build_constraints_section()
        
        # Add context-specific information
        instructions += self._build_context_section(context)
        
        return instructions
    
    def _get_core_prompt(self) -> str:
        """Get the core prompt for the agent"""
        if self.config.core_prompt:
            return self.config.core_prompt
        return INITIAL_CORE_PROMPT
    
    def _build_capabilities_section(self) -> str:
        """Build the capabilities section"""
        capabilities = [
            "- Answering questions with accurate, up-to-date information",
            "- Problem-solving and strategic thinking",
            "- Creative ideation and brainstorming",
            "- Explaining complex concepts in accessible ways"
        ]
        
        if self.config.code_execution.enabled:
            capabilities.extend([
                "- Executing Python code for analysis and computation",
                "- Creating data visualizations and plots"
            ])
        
        if self.config.web_search.enabled:
            capabilities.append("- Searching the web for current information")
        
        return f"\n\nYour core capabilities include:\n" + "\n".join(capabilities) + "\n"
    
    def _build_code_execution_instructions(self, context: InstructionContext) -> str:
        """Build code execution instructions"""
        config = self.config.code_execution
        
        instructions = f"""
**CODE EXECUTION CAPABILITIES:**

You have access to tools for executing Python code (running on a '{context.os_type}' host):
1. A tool that executes Python scripts
"""
        
        if config.system_commands_enabled:
            instructions += "2. A tool that executes system commands for environment setup\n"
        
        instructions += f"""
**CRITICAL INSTRUCTIONS FOR CODE EXECUTION:**
1. Your code is not run in any jupyter kernel or memory of variables, globals, etc from previous tool calls.
   It runs as a standalone script with no memory of previous tool calls.
   Hence, The tool must be called only once with the entire code to be executed at once. 
   So before calling the tool, you must have already written the entire code to be executed at once.
2. Your code **MUST** be a single, self-contained Python script provided as the `code` argument.
3. All necessary imports must be included within the script.
4. If you need the script to produce an output value, you **MUST** assign that value to a variable named `result` within the script.

**EXECUTION TIMEOUT:** {config.timeout_seconds} seconds
"""
        
        if config.plots_enabled:
            instructions += self._build_plotting_instructions(context)
        
        if config.system_commands_enabled:
            instructions += self._build_system_commands_instructions(config)
        
        return instructions
    
    def _build_plotting_instructions(self, context: InstructionContext) -> str:
        """Build plotting-specific instructions"""
        return f"""
**DATA VISUALIZATION INSTRUCTIONS:**
1. DO NOT use plt.show() as it will cause errors in the execution environment.
2. INSTEAD, save plots to files in this fixed directory: {context.plots_directory}
3. Use message_id and timestamps for unique filenames in the format {context.message_id}_plot_timestamp.png
4. ALWAYS include the paths to saved plots in your 'result' variable.
5. Example:
```python
import matplotlib.pyplot as plt
import time

# Create your plot
plt.figure()
plt.plot([1, 2, 3], [4, 5, 6])
plt.title("My Plot")

# Save it with a unique filename including timestamp
filename = f"{context.plots_directory}/{context.message_id}_plot_{int(time.time())}.png"
plt.savefig(filename)
plt.close()

# Include the path in your result
result = {{"data": your_data, "plot_path": filename}}
```

**PLOT SAVING INSTRUCTIONS:**
Your output directory is: {context.plots_directory}
Your unique message ID is: '{context.message_id}' - ALWAYS include this in your filenames.
Use this ID with timestamps for unique filenames (e.g., '{context.message_id}_plot_timestamp.png').
"""
    
    def _build_system_commands_instructions(self, config: CodeExecutionConfig) -> str:
        """Build system commands instructions"""
        allowed_prefixes = ", ".join([f"'{prefix}'" for prefix in config.allowed_command_prefixes])
        
        return f"""
**SYSTEM COMMAND TOOL FOR ENVIRONMENT SETUP:**
If your code requires special packages or data to be downloaded, use the system command tool FIRST:

Tool Signature:
`execute_system_command(command: str) -> SystemCommandResult`

- Only commands starting with {allowed_prefixes} are allowed
- Examples: 
  - `execute_system_command(command="python -m nltk.downloader vader_lexicon")`
  - `execute_system_command(command="pip install somepackage")`

What `SystemCommandResult` contains:
- `stdout`: Standard output from the command
- `stderr`: Standard error from the command
- `status`: 'success' or 'error'
- `exit_code`: Exit code of the command (0 typically means success)

**TIMEOUT:** {config.timeout_seconds} seconds
"""
    
    def _build_web_search_instructions(self) -> str:
        """Build web search instructions"""
        config = self.config.web_search
        location_info = f" (searching from {config.location.get('city', 'unknown location')})" if config.location else ""
        
        return f"""
**WEB SEARCH CAPABILITIES:**
You have access to web search functionality{location_info}.
Use this to find current information, recent developments, or verify facts.

**SEARCH GUIDELINES:**
- Use specific, targeted search queries
- Verify information from multiple sources when possible
- Maximum {config.max_results} results per search
- Cite sources when using search results
"""
    
    def _build_output_formatting_instructions(self, context: InstructionContext) -> str:
        """Build output formatting instructions"""
        return """
**OUTPUT FORMATTING:**
- Provide clear, well-structured responses
- Use markdown formatting for better readability
- Include relevant code examples when helpful
- Explain your reasoning and approach
- If you generate plots or files, mention their locations
"""
    
    def _build_constraints_section(self) -> str:
        """Build constraints and safety guidelines"""
        constraints = [
            "- Be accurate and truthful in your responses",
            "- Acknowledge when you don't know something",
            "- Avoid generating harmful, offensive, or inappropriate content",
            "- Respect privacy and confidentiality"
        ]
        
        if self.config.guardrails.max_input_length:
            constraints.append(f"- Input length limit: {self.config.guardrails.max_input_length} characters")
        
        if self.config.guardrails.max_output_length:
            constraints.append(f"- Output length limit: {self.config.guardrails.max_output_length} characters")
        
        return "\n**GUIDELINES AND CONSTRAINTS:**\n" + "\n".join(constraints) + "\n"
    
    def _build_context_section(self, context: InstructionContext) -> str:
        """Build context-specific information"""
        context_info = f"""
**CONTEXT INFORMATION:**
- Message ID: {context.message_id}
- Operating System: {context.os_type}
- Plots Directory: {context.plots_directory}
"""
        
        if context.user_id:
            context_info += f"- User ID: {context.user_id}\n"
        
        if context.session_id:
            context_info += f"- Session ID: {context.session_id}\n"
        
        if context.metadata:
            context_info += f"- Additional Context: {context.metadata}\n"
        
        return context_info
    
    def get_instruction_function(self) -> Callable:
        """
        Get a function that can be used with the Agent's dynamic instructions
        
        Returns:
            Function that takes (run_context, agent) and returns instructions
        """
        def generate_instructions(run_context, agent) -> str:
            # Extract context information
            # This will be populated by the agent when it calls this function
            context = InstructionContext(
                message_id=getattr(agent, 'current_message_id', 'unknown'),
                plots_directory=getattr(agent, 'unique_plots_dir', '/tmp/plots'),
                os_type=getattr(self.config, 'os_type', 'Windows'),
                user_id=getattr(run_context.context, 'user_id', None) if run_context.context else None,
                session_id=getattr(run_context.context, 'session_id', None) if run_context.context else None,
            )
            
            return self.build_instructions(context)
        
        return generate_instructions
    
    def update_config(self, new_config: AgentConfig):
        """Update the agent configuration"""
        self.config = new_config
        self.template_cache.clear()  # Clear cache when config changes 