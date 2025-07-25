#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prompt Diff Test - Compare original vs new prompt generation

This test compares:
1. Original: prompt_utils.get_instructions_template() used in code_agent.py
2. New: instruction_builder.InstructionBuilder used in configurable agents

Shows full prompts and detailed differences.
"""

import os
import sys
import uuid
import difflib
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import original prompt system
from aicore.prompt_utils import get_instructions_template, INITIAL_CORE_PROMPT

# Import new configurable prompt system
from aicore.instructions.instruction_builder import InstructionBuilder, InstructionContext
from aicore.config.agent_config import AgentConfig, CodeExecutionConfig, WebSearchConfig, GuardrailConfig


def generate_original_prompt():
    """Generate prompt using the original system (code_agent.py approach)"""
    # Simulate the same setup as CodeExecutorAgent
    unique_id = "test123"  # Fixed for comparison
    plots_dir = f"/test/plots/{unique_id}"
    core_prompt = INITIAL_CORE_PROMPT
    
    # This is what code_agent.py does
    instructions_template = get_instructions_template(plots_dir, core_prompt=core_prompt)
    
    # Simulate message ID injection (what _get_dynamic_instructions does)
    message_id = "msg456"  # Fixed for comparison
    final_instructions = instructions_template.replace("{message_id}", message_id)
    
    return final_instructions


def generate_new_prompt():
    """Generate prompt using the new configurable system"""
    # Create equivalent configuration
    config = AgentConfig(
        name="Test Assistant",
        core_prompt=INITIAL_CORE_PROMPT,
        code_execution=CodeExecutionConfig(
            enabled=True,
            plots_enabled=True,
            system_commands_enabled=True,
            timeout_seconds=300,
            allowed_command_prefixes=["pip", "python", "conda", "npm"]
        ),
        web_search=WebSearchConfig(
            enabled=True,
            location={"type": "approximate", "city": "New Delhi"},
            max_results=10
        ),
        guardrails=GuardrailConfig()
    )
    
    # Create instruction builder
    builder = InstructionBuilder(config)
    
    # Create equivalent context
    context = InstructionContext(
        message_id="msg456",  # Same as original
        os_type="Windows",
        user_id=None,
        session_id=None
    )
    
    # Generate instructions
    instructions = builder.build_instructions(context)
    
    return instructions


def create_diff_html(original, new):
    """Create an HTML diff view"""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile='Original (code_agent.py)',
        tofile='New (instruction_builder.py)',
        lineterm=''
    )
    
    return ''.join(diff)


def print_section_separator(title):
    """Print a section separator"""
    print("\n" + "=" * 80)
    print(f"   {title}")
    print("=" * 80)


def print_prompt_with_line_numbers(prompt, title):
    """Print prompt with line numbers for easy reference"""
    print(f"\n{title}:")
    print("-" * 60)
    lines = prompt.split('\n')
    for i, line in enumerate(lines, 1):
        print(f"{i:3d}: {line}")
    print("-" * 60)


def analyze_differences(original, new):
    """Analyze and categorize the differences"""
    print_section_separator("DIFFERENCE ANALYSIS")
    
    original_lines = original.split('\n')
    new_lines = new.split('\n')
    
    print(f"Original prompt: {len(original_lines)} lines, {len(original)} characters")
    print(f"New prompt: {len(new_lines)} lines, {len(new)} characters")
    print(f"Difference: {len(new_lines) - len(original_lines)} lines, {len(new) - len(original)} characters")
    
    # Find unique sections
    original_set = set(original_lines)
    new_set = set(new_lines)
    
    only_in_original = original_set - new_set
    only_in_new = new_set - original_set
    
    if only_in_original:
        print(f"\nLines only in ORIGINAL ({len(only_in_original)}):")
        for line in sorted(only_in_original):
            if line.strip():  # Skip empty lines
                print(f"  - {line}")
    
    if only_in_new:
        print(f"\nLines only in NEW ({len(only_in_new)}):")
        for line in sorted(only_in_new):
            if line.strip():  # Skip empty lines
                print(f"  + {line}")


def main():
    """Main test function"""
    print_section_separator("PROMPT GENERATION COMPARISON TEST")
    print("Comparing original code_agent.py prompt vs new instruction_builder.py prompt")
    print("Using equivalent configurations and context for fair comparison")
    
    # Generate both prompts
    try:
        print("\nGenerating original prompt...")
        original_prompt = generate_original_prompt()
        print("✅ Original prompt generated successfully")
        #print(original_prompt)
        
        print("Generating new prompt...")
        new_prompt = generate_new_prompt()
        print("✅ New prompt generated successfully")
        # print(new_prompt)
        # return
    except Exception as e:
        print(f"❌ Error generating prompts: {e}")
        return
    
    # Show full prompts
    print_section_separator("FULL PROMPTS")
    print_prompt_with_line_numbers(original_prompt, "ORIGINAL PROMPT (code_agent.py)")
    print_prompt_with_line_numbers(new_prompt, "NEW PROMPT (instruction_builder.py)")
    
    # Create and show diff
    print_section_separator("UNIFIED DIFF")
    diff_output = create_diff_html(original_prompt, new_prompt)
    print(diff_output)
    
    # Analyze differences
    analyze_differences(original_prompt, new_prompt)
    
    # Summary
    print_section_separator("SUMMARY")
    if original_prompt == new_prompt:
        print("✅ IDENTICAL: Both systems generate exactly the same prompt")
    else:
        print("📊 DIFFERENT: The prompts have differences (see analysis above)")
        
        # Check for key functional equivalence
        key_elements = [
            "CODE EXECUTION",
            "DATA VISUALIZATION",
            "plt.savefig",
            "message_id",
            "outputs/",
            "WebSearchTool"
        ]
        
        missing_elements = []
        for element in key_elements:
            if element in original_prompt and element not in new_prompt:
                missing_elements.append(f"'{element}' missing in new prompt")
            elif element in new_prompt and element not in original_prompt:
                missing_elements.append(f"'{element}' added in new prompt")
        
        if missing_elements:
            print("⚠️  Key functional differences:")
            for missing in missing_elements:
                print(f"   - {missing}")
        else:
            print("✅ Key functional elements are present in both prompts")
    
    print("\nTest completed!")


if __name__ == "__main__":
    main() 