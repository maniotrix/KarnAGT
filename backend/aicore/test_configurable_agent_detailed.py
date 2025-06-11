#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive ConfigurableCodeExecutorAgent Test Script
Shows detailed agent inspection at initialization and after configuration updates
"""

import os
import sys
import json
import uuid
import pprint
from typing import Dict, Any, List
from dataclasses import asdict
from pathlib import Path

# Add backend to path for imports
# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import configuration classes
from aicore.config.agent_config import (
    AgentConfig, WebSearchConfig, CodeExecutionConfig, 
    GuardrailConfig, ToolUseStrategy
)
from aicore.config.model_config import (
    ModelConfig, ModelProvider, ModelParameters, 
    ProviderSettings, ModelCapabilities, CostSettings, ModelFamily
)

# Import the configurable agent
from aicore.ai_agents.configurable_code_agent import ConfigurableCodeExecutorAgent

# Import instruction classes
from aicore.instructions.instruction_builder import InstructionBuilder, InstructionContext

# Import path config
from aicore.path_config import PLOTS_DIR

# Pretty printer setup
pp = pprint.PrettyPrinter(indent=2, width=120, depth=10)

def print_header(title: str, level: int = 1):
    """Print styled headers"""
    if level == 1:
        print(f"\n{'='*80}")
        print(f"  {title.upper()}")
        print(f"{'='*80}")
    elif level == 2:
        print(f"\n{'-'*60}")
        print(f"  {title}")
        print(f"{'-'*60}")
    else:
        print(f"\n• {title}")

def safe_dict_conversion(obj, max_depth=3, current_depth=0):
    """Safely convert objects to dictionaries for display"""
    if current_depth > max_depth:
        return f"<{type(obj).__name__}> (max depth reached)"
    
    if hasattr(obj, '__dict__'):
        try:
            if hasattr(obj, '__dataclass_fields__'):
                # It's a dataclass
                return {k: safe_dict_conversion(v, max_depth, current_depth + 1) 
                       for k, v in asdict(obj).items()}
            else:
                # Regular object with __dict__
                return {k: safe_dict_conversion(v, max_depth, current_depth + 1) 
                       for k, v in obj.__dict__.items()}
        except Exception as e:
            return f"<{type(obj).__name__}> (conversion error: {str(e)})"
    elif isinstance(obj, (list, tuple)):
        if len(obj) > 5:  # Limit list display
            return [safe_dict_conversion(item, max_depth, current_depth + 1) 
                   for item in obj[:3]] + [f"... and {len(obj) - 3} more items"]
        return [safe_dict_conversion(item, max_depth, current_depth + 1) for item in obj]
    elif isinstance(obj, dict):
        return {k: safe_dict_conversion(v, max_depth, current_depth + 1) 
               for k, v in obj.items()}
    elif callable(obj):
        return f"<function: {getattr(obj, '__name__', 'unknown')}>"
    elif isinstance(obj, str) and len(obj) > 200:
        return f"{obj[:200]}... (truncated, total length: {len(obj)})"
    else:
        return obj

def inspect_agent_detailed(agent: ConfigurableCodeExecutorAgent, stage_name: str):
    """Detailed inspection of the agent"""
    print_header(f"Agent Detailed Inspection - {stage_name}", 1)
    
    # Basic Information
    print_header("Basic Information", 2)
    basic_info = {
        "Agent Name": agent.name,
        "Agent Class": type(agent).__name__,
        "Agent ID": hex(id(agent)),
        "Current Message ID": agent.current_message_id,
        "Unique Plots Directory": agent.unique_plots_dir,
        "Plots Directory Exists": os.path.exists(agent.unique_plots_dir),
    }
    pp.pprint(basic_info)
    
    # Model Configuration Details
    print_header("Model Configuration", 2)
    model_config_details = safe_dict_conversion(agent.model_config)
    pp.pprint(model_config_details)
    
    # Agent Configuration Details
    print_header("Agent Configuration", 2)
    agent_config_details = safe_dict_conversion(agent.agent_config)
    pp.pprint(agent_config_details)
    
    # Inherited Agent Properties (from SDK)
    print_header("SDK Agent Properties", 2)
    sdk_properties = {
        "name": agent.name,
        "model": agent.model,
        "instructions_type": type(agent.instructions).__name__,
        "instructions_callable": callable(agent.instructions),
        "tools_count": len(agent.tools),
        "tools": [
            {
                "name": getattr(tool, "name", "unknown"),
                "type": type(tool).__name__,
                "description": getattr(tool, "description", "no description")[:100] if hasattr(tool, "description") else "no description"
            } for tool in agent.tools
        ],
        "handoffs_count": len(agent.handoffs),
        "tool_use_behavior": agent.tool_use_behavior,
        "reset_tool_choice": agent.reset_tool_choice,
        "output_type": agent.output_type,
        "mcp_servers_count": len(agent.mcp_servers),
        "input_guardrails_count": len(agent.input_guardrails),
        "output_guardrails_count": len(agent.output_guardrails),
    }
    pp.pprint(sdk_properties)
    
    # Instruction Builder Details
    print_header("Instruction Builder", 2)
    if hasattr(agent, 'instruction_builder'):
        builder_info = {
            "builder_type": type(agent.instruction_builder).__name__,
            "config_reference": type(agent.instruction_builder.config).__name__,
            "config_name": agent.instruction_builder.config.name if hasattr(agent.instruction_builder.config, 'name') else 'unknown'
        }
        pp.pprint(builder_info)
    else:
        print("No instruction builder found")
    
    # Configuration Summary
    print_header("Configuration Summary", 2)
    try:
        summary = agent.get_configuration_summary()
        pp.pprint(summary)
    except Exception as e:
        print(f"Error getting configuration summary: {e}")

def test_instruction_generation(agent: ConfigurableCodeExecutorAgent):
    """Test instruction generation"""
    print_header("Instruction Generation Test", 1)
    
    # Create test context
    test_context = InstructionContext(
        message_id=agent.current_message_id,
        plots_directory=agent.unique_plots_dir,
        os_type="Windows",
        user_id="test_user_12345",
        session_id="test_session_67890",
        metadata={"test_key": "test_value", "environment": "testing"}
    )
    
    print_header("Test Context", 2)
    context_info = safe_dict_conversion(test_context)
    pp.pprint(context_info)
    
    # Generate instructions using the instruction builder
    print_header("Generated Instructions", 2)
    try:
        instructions = agent.instruction_builder.build_instructions(test_context)
        print(f"Instructions Length: {len(instructions)} characters")
        print(f"First 500 characters:")
        print("-" * 60)
        print(instructions[:500])
        print("-" * 60)
        print(f"Last 300 characters:")
        print(instructions[-300:])
        print("-" * 60)
        
        # Count different sections
        print_header("Instruction Analysis", 3)
        analysis = {
            "total_length": len(instructions),
            "lines_count": len(instructions.split('\n')),
            "contains_core_prompt": "AI assistant" in instructions,
            "contains_code_execution": "execute_code" in instructions,
            "contains_plots_directory": agent.unique_plots_dir in instructions,
            "contains_message_id": agent.current_message_id in instructions,
            "contains_system_commands": "execute_system_command" in instructions,
        }
        pp.pprint(analysis)
        
    except Exception as e:
        print(f"Error generating instructions: {e}")
        import traceback
        traceback.print_exc()

def create_initial_configs():
    """Create initial configurations for testing"""
    print_header("Creating Initial Configurations", 1)
    
    # Model Configuration
    print_header("Initial Model Configuration", 2)
    model_config = ModelConfig(
        name="gpt-4o-mini-2024-07-18",
        display_name="GPT-4 Omni Mini",
        family=ModelFamily.GPT4,
        version="2024-07-18",
        provider=ProviderSettings(
            provider=ModelProvider.OPENAI,
            api_key_env_var="OPENAI_API_KEY",
            timeout_seconds=60,
            max_retries=3,
            retry_delay_seconds=1.0
        ),
        parameters=ModelParameters(
            temperature=0.7,
            top_p=0.95,
            max_tokens=4000,
            frequency_penalty=0.0,
            presence_penalty=0.0
        ),
        capabilities=ModelCapabilities(
            supports_functions=True,
            supports_vision=False,
            supports_streaming=True,
            supports_json_mode=True,
            max_context_tokens=128000,
            max_output_tokens=4000
        ),
        costs=CostSettings(
            track_costs=True,
            input_token_cost=0.000150,  # $0.150 per 1M tokens
            output_token_cost=0.000600,  # $0.600 per 1M tokens
            max_cost_per_request=1.0,
            max_cost_per_session=10.0
        )
    )
    
    # Agent Configuration
    print_header("Initial Agent Configuration", 2)
    agent_config = AgentConfig(
        name="Test Configurable Code Agent",
        description="A comprehensive test agent for configuration demonstration",
        core_prompt="You are a helpful AI assistant specialized in code execution and data analysis. You excel at solving complex problems through systematic approaches.",
        instruction_template="default",
        dynamic_instructions=True,
        model_name="gpt-4o-mini-2024-07-18",
        web_search=WebSearchConfig(
            enabled=True,
            location={"type": "approximate", "city": "New Delhi"},
            max_results=5
        ),
        code_execution=CodeExecutionConfig(
            enabled=True,
            timeout_seconds=300,
            allowed_packages=[
                "matplotlib", "numpy", "pandas", "seaborn", "scipy", 
                "sklearn", "requests", "beautifulsoup4", "pillow", "nltk"
            ],
            plots_enabled=True,
            system_commands_enabled=True,
            allowed_command_prefixes=["python", "pip", "python -m"]
        ),
        guardrails=GuardrailConfig(
            input_guardrails=["length_check"],
            output_guardrails=["safety_check"],
            max_input_length=50000,
            max_output_length=100000,
            content_filtering=True
        ),
        tool_use_strategy=ToolUseStrategy.RUN_LLM_AGAIN,
        reset_tool_choice=True,
        maintain_conversation_history=True,
        max_context_messages=20,
        context_window_strategy="sliding",
        handoffs_enabled=False,
        available_handoffs=[],
        output_type="str",
        tags=["code-execution", "data-analysis", "configurable", "test"],
        version="1.0.0",
        created_by="test_script"
    )
    
    print("Initial configurations created successfully")
    return agent_config, model_config

def create_updated_configs():
    """Create updated configurations for testing updates"""
    print_header("Creating Updated Configurations", 1)
    
    # Updated Model Configuration
    print_header("Updated Model Configuration", 2)
    updated_model_config = ModelConfig(
        name="gpt-4o-2024-08-06",  # Different model
        display_name="GPT-4 Omni (August 2024)",
        family=ModelFamily.GPT4,
        version="2024-08-06",
        provider=ProviderSettings(
            provider=ModelProvider.OPENAI,
            api_key_env_var="OPENAI_API_KEY",
            timeout_seconds=120,  # Longer timeout
            max_retries=5,  # More retries
            retry_delay_seconds=2.0
        ),
        parameters=ModelParameters(
            temperature=0.3,  # Lower temperature for more focused responses
            top_p=0.9,
            max_tokens=8000,  # More tokens
            frequency_penalty=0.1,
            presence_penalty=0.1
        ),
        capabilities=ModelCapabilities(
            supports_functions=True,
            supports_vision=True,  # Vision support
            supports_streaming=True,
            supports_json_mode=True,
            max_context_tokens=128000,
            max_output_tokens=8000
        ),
        costs=CostSettings(
            track_costs=True,
            input_token_cost=0.000250,  # Higher cost for advanced model
            output_token_cost=0.001000,
            max_cost_per_request=2.0,
            max_cost_per_session=20.0
        )
    )
    
    # Updated Agent Configuration
    print_header("Updated Agent Configuration", 2)
    updated_agent_config = AgentConfig(
        name="Enhanced Configurable Code Agent",  # Different name
        description="An enhanced test agent with advanced capabilities and stricter safety measures",
        core_prompt="You are an advanced AI assistant with enhanced code execution capabilities. You approach problems methodically and provide detailed explanations of your reasoning.",
        instruction_template="advanced",
        dynamic_instructions=True,
        model_name="gpt-4o-2024-08-06",
        web_search=WebSearchConfig(
            enabled=True,
            location={"type": "approximate", "city": "San Francisco"},  # Different location
            max_results=10  # More results
        ),
        code_execution=CodeExecutionConfig(
            enabled=True,
            timeout_seconds=600,  # Longer timeout
            allowed_packages=[
                "matplotlib", "numpy", "pandas", "seaborn", "scipy", 
                "sklearn", "requests", "beautifulsoup4", "pillow", "nltk",
                "tensorflow", "pytorch", "opencv-python"  # Added ML packages
            ],
            plots_enabled=True,
            system_commands_enabled=False,  # Disabled for security
            allowed_command_prefixes=["python", "pip"]  # Restricted commands
        ),
        guardrails=GuardrailConfig(
            input_guardrails=["length_check", "content_filter", "safety_check"],  # More guardrails
            output_guardrails=["safety_check", "content_filter"],
            max_input_length=75000,  # Increased limits
            max_output_length=150000,
            content_filtering=True
        ),
        tool_use_strategy=ToolUseStrategy.STOP_ON_FIRST_TOOL,  # Different strategy
        reset_tool_choice=False,  # Changed behavior
        maintain_conversation_history=True,
        max_context_messages=50,  # More context
        context_window_strategy="truncate",  # Different strategy
        handoffs_enabled=True,  # Enabled handoffs
        available_handoffs=["data_analyst", "code_reviewer", "security_checker"],
        output_type="str",
        tags=["code-execution", "data-analysis", "enhanced", "secure", "updated"],
        version="2.0.0",
        created_by="test_script_updated"
    )
    
    print("Updated configurations created successfully")
    return updated_agent_config, updated_model_config

def main():
    """Main test function"""
    print_header("ConfigurableCodeExecutorAgent Comprehensive Test Suite", 1)
    
    # Set dummy API key for testing (not making real calls)
    os.environ['OPENAI_API_KEY'] = 'sk-test-dummy-key-for-inspection-only'
    
    # Ensure plots directory exists
    os.makedirs(PLOTS_DIR, exist_ok=True)
    print(f"Using plots directory: {PLOTS_DIR}")
    
    try:
        # Step 1: Create initial configurations
        initial_agent_config, initial_model_config = create_initial_configs()
        
        # Step 2: Initialize the agent
        print_header("STEP 1: Agent Initialization", 1)
        agent = ConfigurableCodeExecutorAgent(
            agent_config=initial_agent_config,
            model_config=initial_model_config,
            root_plots_dir=PLOTS_DIR,
            name="Custom Test Agent Name"  # Testing name override
        )
        
        # Step 3: Detailed inspection after initialization
        inspect_agent_detailed(agent, "Initial State")
        
        # Step 4: Test instruction generation
        test_instruction_generation(agent)
        
        # Step 5: Test message ID update
        print_header("STEP 2: Message ID Update", 1)
        old_message_id = agent.current_message_id
        new_message_id = agent.set_message_id("custom_msg_12345")
        
        print_header("Message ID Update Results", 2)
        message_id_results = {
            "old_message_id": old_message_id,
            "new_message_id": new_message_id,
            "current_message_id": agent.current_message_id,
            "update_successful": agent.current_message_id == "custom_msg_12345"
        }
        pp.pprint(message_id_results)
        
        # Step 6: Configuration updates
        print_header("STEP 3: Configuration Updates", 1)
        updated_agent_config, updated_model_config = create_updated_configs()
        
        # Apply updates
        print_header("Applying Configuration Updates", 2)
        agent.update_configuration(
            agent_config=updated_agent_config,
            model_config=updated_model_config
        )
        
        # Step 7: Detailed inspection after updates
        inspect_agent_detailed(agent, "After Configuration Update")
        
        # Step 8: Test instruction generation with updated config
        test_instruction_generation(agent)
        
        # Step 9: Test plots functionality
        print_header("STEP 4: Plots Directory Testing", 1)
        plots_info = {
            "plots_directory": agent.unique_plots_dir,
            "directory_exists": os.path.exists(agent.unique_plots_dir),
            "directory_contents": os.listdir(agent.unique_plots_dir) if os.path.exists(agent.unique_plots_dir) else [],
            "plots_with_message_id": agent.get_all_plots_with_message_id()
        }
        pp.pprint(plots_info)
        
        # Step 10: Final summary
        print_header("FINAL SUMMARY", 1)
        final_summary = {
            "test_status": "COMPLETED SUCCESSFULLY",
            "agent_name": agent.name,
            "agent_type": type(agent).__name__,
            "current_message_id": agent.current_message_id,
            "model_name": agent.model,
            "tools_count": len(agent.tools),
            "configuration_version": agent.agent_config.version,
            "plots_directory": agent.unique_plots_dir,
            "total_test_steps": 4
        }
        pp.pprint(final_summary)
        
        print_header("TEST COMPLETED SUCCESSFULLY! ✅", 1)
        
    except Exception as e:
        print_header("TEST FAILED ❌", 1)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 