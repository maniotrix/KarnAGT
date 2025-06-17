#!/usr/bin/env python3
"""
Simple Instructions Test - Isolate the issue
"""

import asyncio
import sys
import tempfile

# Add backend to path
sys.path.append('.')

from aicore.config import config_manager
from aicore.ai_agents.configurable_code_agent import ConfigurableCodeExecutorAgent
from aicore.instructions import InstructionBuilder, InstructionContext
from aicore.logger import get_logger

logger = get_logger(__name__)


async def test_instruction_building():
    """Test instruction building step by step"""
    
    # Create temp plots directory
    temp_plots_dir = tempfile.mkdtemp(prefix="simple_test_")
    
    print("=" * 60)
    print("SIMPLE INSTRUCTION BUILDING TEST")
    print("=" * 60)
    
    # Test 1: Basic instruction context without user_id (no memory)
    print("\n1. Testing basic instruction context (no memory)...")
    
    config = config_manager.load_config("default", environment="test")
    config.agent.user_id = None  # No memory
    
    builder = InstructionBuilder(config.agent)
    
    context = InstructionContext(
        message_id="test_123",
        plots_directory=temp_plots_dir,
        os_type="Windows",
        user_id=None,  # No user_id = no memory context
        session_id=None
    )
    
    try:
        instructions = await builder.build_instructions(context)
        print(f"✅ Basic instructions generated successfully: {len(instructions)} chars")
        print(f"Full instructions: {instructions}")
    except Exception as e:
        print(f"❌ Basic instructions failed: {e}")
        return False
    
    # Test 2: With user_id but we'll mock the memory function to return safe content
    print("\n2. Testing with user_id but safe memory content...")
    
    # Temporarily replace the memory function
    original_get_memory = builder._get_memory_context
    
    async def safe_mock_memory(user_uuid: str) -> str:
        return "## USER CONTEXT\nIDENTITY: John Smith, Developer\nPREFERENCES: Likes clean code"
    
    builder._get_memory_context = safe_mock_memory
    
    context_with_user = InstructionContext(
        message_id="test_456",
        plots_directory=temp_plots_dir,
        os_type="Windows",
        user_id="test_user_uuid",
        session_id=None
    )
    
    try:
        instructions_with_memory = await builder.build_instructions(context_with_user)
        print(f"✅ Instructions with safe memory generated: {len(instructions_with_memory)} chars")
        print(f"Contains memory context: {'USER CONTEXT' in instructions_with_memory}")
    except Exception as e:
        print(f"❌ Instructions with memory failed: {e}")
        return False
    finally:
        # Restore original function
        builder._get_memory_context = original_get_memory
    
    # Test 3: Try with the real memory function (might fail)
    print("\n3. Testing with real memory function...")
    
    config.agent.user_id = "test_user_uuid"
    
    try:
        real_instructions = await builder.build_instructions(context_with_user)
        print(f"✅ Real memory instructions generated: {len(real_instructions)} chars")
    except Exception as e:
        print(f"❌ Real memory instructions failed: {e}")
        print(f"Error details: {str(e)}")
        
        # This is where we can see the actual error
        import traceback
        traceback.print_exc()
        
        return False
    
    print("\n✅ All instruction building tests passed!")
    return True


if __name__ == "__main__":
    asyncio.run(test_instruction_building())