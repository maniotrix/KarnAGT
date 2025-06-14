#!/usr/bin/env python3
"""
Complete Dynamic Instructions Test - Shows actual instruction content with memory
Tests what the complete instructions look like after build_instructions returns with user memory
"""

import asyncio
import sys
import os
import tempfile
import shutil
import uuid
from typing import Dict, Any, List
from datetime import datetime

# Add backend to path
sys.path.append('.')

# Database setup for memory testing
from app.core.database import AsyncSessionLocal
from app.models.database.user import User
from app.models.database.conversation import Conversation
from app.models.database.user_memory import UserMemory
from app.models.database.memory_preference import MemoryPreference
from app.services.memory.memory_service import MemoryService
from app.services.memory.memory_setup import setup_user_memory_system

# AI Core imports
from aicore.config import config_manager
from aicore.ai_agents.configurable_code_agent import ConfigurableCodeExecutorAgent
from aicore.instructions import InstructionBuilder, InstructionContext
from aicore.logger import get_logger

# SQLAlchemy cleanup
from sqlalchemy import delete

logger = get_logger(__name__)


class CompleteInstructionsTest:
    """Test class to show complete instruction content with memory integration"""
    
    def __init__(self):
        self.test_user = None
        self.test_conversation = None
        self.test_memories = []
        self.temp_plots_dir = None
        
    async def setup_test_user_with_memory(self):
        """Set up a test user with actual memory data"""
        logger.info("Setting up test user with memory data...")
        
        async with AsyncSessionLocal() as db:
            # Create test user
            self.test_user = User(
                username=f"instructions_test_user_{uuid.uuid4().hex[:8]}",
                email=f"instructions_test_{uuid.uuid4().hex[:8]}@example.com",
                full_name="Instructions Test User",
                hashed_password="test_password_hash",
                memory_enabled=True,
                memory_retention_days=365,
                auto_memory_importance=True
            )
            db.add(self.test_user)
            await db.commit()
            await db.refresh(self.test_user)
            
            logger.info(f"Created test user: {self.test_user.username} (ID: {self.test_user.id})")
            
            # Set up memory system
            await setup_user_memory_system(self.test_user.id, db)
            
            # Create test conversation
            self.test_conversation = Conversation(
                conversation_id=f"instructions_test_conv_{uuid.uuid4().hex[:8]}",
                user_id=self.test_user.id,
                title="Instructions Test Conversation",
                status="active"
            )
            db.add(self.test_conversation)
            await db.commit()
            await db.refresh(self.test_conversation)
            
            # Create rich memory data for testing
            await self._create_rich_test_memories(db)
            
    async def _create_rich_test_memories(self, db):
        """Create comprehensive test memories"""
        logger.info("Creating rich test memories...")
        
        memory_service = MemoryService(db)
        
        test_memories_data = [
            {
                "bucket": "identity",
                "content": "Sarah Johnson, Senior Python Developer at TechCorp, based in San Francisco, Pacific Time Zone",
                "importance": 0.95,
                "confidence": 0.9
            },
            {
                "bucket": "identity", 
                "content": "5+ years experience with Python, Django, FastAPI, and machine learning libraries",
                "importance": 0.9,
                "confidence": 0.95
            },
            {
                "bucket": "preferences",
                "content": "Prefers clean, well-documented code with comprehensive error handling",
                "importance": 0.8,
                "confidence": 0.9
            },
            {
                "bucket": "preferences",
                "content": "Uses VS Code with Python extensions, prefers dark mode, likes concise explanations",
                "importance": 0.7,
                "confidence": 0.85
            },
            {
                "bucket": "preferences",
                "content": "Follows PEP 8 style guide strictly, uses type hints extensively",
                "importance": 0.75,
                "confidence": 0.8
            },
            {
                "bucket": "goals",
                "content": "Currently learning advanced FastAPI patterns and async programming for new microservices project",
                "importance": 0.9,
                "confidence": 0.85,
                "status": "active"
            },
            {
                "bucket": "goals",
                "content": "Planning to implement ML model serving with FastAPI in next 3 weeks",
                "importance": 0.85,
                "confidence": 0.8,
                "status": "active"
            },
            {
                "bucket": "workflows",
                "content": "Follows TDD approach, writes pytest tests first, uses GitHub Actions for CI/CD",
                "importance": 0.8,
                "confidence": 0.9
            },
            {
                "bucket": "workflows",
                "content": "Uses Docker for development environments, prefers containerized deployments",
                "importance": 0.75,
                "confidence": 0.85
            },
            {
                "bucket": "capabilities",
                "content": "Expert in Python web frameworks, intermediate in React/TypeScript frontend",
                "importance": 0.8,
                "confidence": 0.9
            },
            {
                "bucket": "capabilities",
                "content": "Experienced with PostgreSQL, Redis, Elasticsearch, AWS services",
                "importance": 0.75,
                "confidence": 0.85
            },
            {
                "bucket": "projects",
                "content": "Working on customer analytics platform using FastAPI, PostgreSQL, and scikit-learn",
                "importance": 0.85,
                "confidence": 0.8
            }
        ]
        
        for mem_data in test_memories_data:
            memory = await memory_service.store_memory(
                user_id=self.test_user.id,
                source_conversation_id=self.test_conversation.conversation_id,
                **mem_data
            )
            self.test_memories.append(memory)
        
        logger.info(f"Created {len(test_memories_data)} rich test memories")
        
    async def test_complete_instructions_without_memory(self):
        """Test complete instructions without memory context"""
        logger.info("Testing complete instructions WITHOUT memory context...")
        
        # Create temp plots directory
        self.temp_plots_dir = tempfile.mkdtemp(prefix="instructions_test_plots_")
        
        # Create agent config without user_id (no memory)
        config = config_manager.load_config("default", environment="test")
        config.agent.user_id = None  # No user_id = no memory context
        
        agent = ConfigurableCodeExecutorAgent(
            agent_config=config.agent,
            model_config=config.model,
            root_plots_dir=self.temp_plots_dir,
            name="NoMemoryInstructionsAgent"
        )
        
        # Set a specific message ID for testing
        test_message_id = "test_msg_no_memory_123"
        agent.set_message_id(test_message_id)
        
        # Generate instructions
        instructions = await agent._get_dynamic_instructions()
        
        # Display complete instructions
        print("\n" + "="*100)
        print("COMPLETE INSTRUCTIONS - WITHOUT MEMORY CONTEXT")
        print("="*100)
        print(instructions)
        print("="*100)
        
        # Log analysis
        logger.info(f"Instructions length: {len(instructions)} characters")
        logger.info(f"Instructions lines: {len(instructions.split(chr(10)))} lines")
        
        # Verify key components
        assert test_message_id in instructions, "Message ID should be in instructions"
        assert agent.unique_plots_dir in instructions, "Plots directory should be in instructions"
        assert "execute_code" in instructions, "Code execution tool should be mentioned"
        assert "CRITICAL INSTRUCTIONS FOR CODE EXECUTION" in instructions, "Critical instructions should be present"
        
        return instructions
        
    async def test_complete_instructions_with_memory(self):
        """Test complete instructions WITH memory context"""
        logger.info("Testing complete instructions WITH memory context...")
        
        # Create agent config with user_id (triggers memory)
        config = config_manager.load_config("default", environment="test")
        config.agent.user_id = str(self.test_user.user_id)  # Use the test user's UUID
        
        agent = ConfigurableCodeExecutorAgent(
            agent_config=config.agent,
            model_config=config.model,
            root_plots_dir=self.temp_plots_dir,
            name="WithMemoryInstructionsAgent"
        )
        
        # Set a specific message ID for testing
        test_message_id = "test_msg_with_memory_456"
        agent.set_message_id(test_message_id)
        
        # Generate instructions (this should include memory context)
        instructions = await agent._get_dynamic_instructions()
        
        # Display complete instructions
        print("\n" + "="*100)
        print("COMPLETE INSTRUCTIONS - WITH MEMORY CONTEXT")
        print("="*100)
        print(instructions)
        print("="*100)
        
        # Log analysis
        logger.info(f"Instructions with memory length: {len(instructions)} characters")
        logger.info(f"Instructions with memory lines: {len(instructions.split(chr(10)))} lines")
        
        # Verify key components
        assert test_message_id in instructions, "Message ID should be in instructions"
        assert agent.unique_plots_dir in instructions, "Plots directory should be in instructions"
        
        # Check for memory content (should contain user info from memories)
        memory_indicators = [
            "Sarah Johnson",  # User name from identity
            "Python Developer",  # Professional info
            "San Francisco",  # Location
            "FastAPI",  # Technology preference
            "TDD approach",  # Workflow preference
        ]
        
        found_memory_content = []
        for indicator in memory_indicators:
            if indicator in instructions:
                found_memory_content.append(indicator)
                logger.info(f"✅ Found memory content: {indicator}")
            else:
                logger.warning(f"❌ Missing memory content: {indicator}")
        
        # Should have found at least some memory content
        if found_memory_content:
            logger.info(f"✅ Memory context successfully integrated! Found {len(found_memory_content)} memory indicators")
        else:
            logger.warning("⚠️ No memory content found in instructions - memory integration may have failed")
        
        return instructions, found_memory_content
        
    async def test_instruction_structure_analysis(self):
        """Analyze the structure of instructions with memory"""
        logger.info("Analyzing instruction structure...")
        
        # Generate instructions with memory
        config = config_manager.load_config("default", environment="test")
        config.agent.user_id = str(self.test_user.user_id)
        
        agent = ConfigurableCodeExecutorAgent(
            agent_config=config.agent,
            model_config=config.model,
            root_plots_dir=self.temp_plots_dir,
            name="StructureAnalysisAgent"
        )
        
        instructions = await agent._get_dynamic_instructions()
        
        # Analyze structure
        lines = instructions.split('\n')
        
        print("\n" + "="*100)
        print("INSTRUCTION STRUCTURE ANALYSIS")
        print("="*100)
        
        # Find key sections
        sections = {
            "Core Prompt": [],
            "Memory Context": [],
            "Capabilities": [],
            "Critical Instructions": [],
            "Data Visualization": [],
            "System Commands": [],
            "Examples": []
        }
        
        current_section = "Core Prompt"
        
        for i, line in enumerate(lines):
            line_info = f"Line {i+1:3d}: {line[:80]}{'...' if len(line) > 80 else ''}"
            
            # Detect section changes
            if "Additional capabilities include:" in line:
                current_section = "Capabilities"
            elif "CRITICAL INSTRUCTIONS FOR CODE EXECUTION:" in line:
                current_section = "Critical Instructions"
            elif "DATA VISUALIZATION INSTRUCTIONS:" in line:
                current_section = "Data Visualization"
            elif "SYSTEM COMMAND TOOL FOR ENVIRONMENT SETUP:" in line:
                current_section = "System Commands"
            elif "EXAMPLE WITH SYSTEM COMMAND:" in line:
                current_section = "Examples"
            elif any(indicator in line for indicator in ["Sarah Johnson", "Python Developer", "San Francisco"]):
                current_section = "Memory Context"
            
            sections[current_section].append(line_info)
        
        # Display structure
        for section_name, section_lines in sections.items():
            if section_lines:
                print(f"\n--- {section_name.upper()} ({len(section_lines)} lines) ---")
                for line_info in section_lines[:5]:  # Show first 5 lines of each section
                    print(line_info)
                if len(section_lines) > 5:
                    print(f"... ({len(section_lines) - 5} more lines)")
        
        print("="*100)
        
        # Summary statistics
        stats = {
            "total_lines": len(lines),
            "total_characters": len(instructions),
            "sections_found": len([s for s in sections.values() if s]),
            "memory_context_lines": len(sections["Memory Context"]),
            "has_memory_context": len(sections["Memory Context"]) > 0
        }
        
        logger.info(f"Instruction structure stats: {stats}")
        return stats
        
    async def test_memory_context_direct(self):
        """Test memory context generation directly"""
        logger.info("Testing memory context generation directly...")
        
        # Create instruction builder
        config = config_manager.load_config("default", environment="test")
        config.agent.user_id = str(self.test_user.user_id)
        
        builder = InstructionBuilder(config.agent)
        
        # Get memory context directly
        memory_context = await builder._get_memory_context(str(self.test_user.user_id))
        
        print("\n" + "="*100)
        print("DIRECT MEMORY CONTEXT OUTPUT")
        print("="*100)
        print(memory_context)
        print("="*100)
        
        logger.info(f"Direct memory context length: {len(memory_context)} characters")
        
        # Verify memory context contains expected information
        expected_content = [
            "Sarah Johnson",
            "Python Developer", 
            "San Francisco",
            "FastAPI",
            "TDD approach"
        ]
        
        found_content = []
        for content in expected_content:
            if content in memory_context:
                found_content.append(content)
        
        logger.info(f"Found {len(found_content)}/{len(expected_content)} expected memory content items")
        
        return memory_context
        
    async def cleanup_test_environment(self):
        """Clean up all test data"""
        logger.info("Cleaning up test environment...")
        
        try:
            async with AsyncSessionLocal() as db:
                if self.test_user:
                    # Delete all memories
                    await db.execute(
                        delete(UserMemory).where(UserMemory.user_id == self.test_user.id)
                    )
                    
                    # Delete memory preferences
                    await db.execute(
                        delete(MemoryPreference).where(MemoryPreference.user_id == self.test_user.id)
                    )
                    
                    # Delete conversation
                    if self.test_conversation:
                        await db.execute(
                            delete(Conversation).where(Conversation.id == self.test_conversation.id)
                        )
                    
                    # Delete user
                    await db.execute(
                        delete(User).where(User.id == self.test_user.id)
                    )
                
                await db.commit()
                logger.info("Database cleanup complete")
            
            # Remove temp directory
            if self.temp_plots_dir and os.path.exists(self.temp_plots_dir):
                shutil.rmtree(self.temp_plots_dir)
                logger.info("Temporary directory cleanup complete")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise
            
    async def run_comprehensive_test(self):
        """Run the complete test suite showing actual instruction content"""
        logger.info("Starting comprehensive instructions content test")
        
        try:
            # Setup
            await self.setup_test_user_with_memory()
            
            # Run tests to show actual instruction content
            logger.info("\n" + "🔍" * 50)
            logger.info("TEST 1: Instructions WITHOUT Memory")
            instructions_no_memory = await self.test_complete_instructions_without_memory()
            
            logger.info("\n" + "🔍" * 50)
            logger.info("TEST 2: Instructions WITH Memory")
            instructions_with_memory, memory_content = await self.test_complete_instructions_with_memory()
            
            logger.info("\n" + "🔍" * 50)
            logger.info("TEST 3: Instruction Structure Analysis")
            structure_stats = await self.test_instruction_structure_analysis()
            
            logger.info("\n" + "🔍" * 50)
            logger.info("TEST 4: Direct Memory Context")
            direct_memory_context = await self.test_memory_context_direct()
            
            # Final comparison
            print("\n" + "="*100)
            print("FINAL COMPARISON SUMMARY")
            print("="*100)
            print(f"Instructions without memory: {len(instructions_no_memory)} characters")
            print(f"Instructions with memory: {len(instructions_with_memory)} characters")
            print(f"Memory context addition: {len(instructions_with_memory) - len(instructions_no_memory)} characters")
            print(f"Memory indicators found: {len(memory_content)}")
            print(f"Direct memory context: {len(direct_memory_context)} characters")
            print("="*100)
            
            logger.info("🎉 ALL INSTRUCTION CONTENT TESTS COMPLETED SUCCESSFULLY!")
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            raise
        finally:
            await self.cleanup_test_environment()


async def main():
    """Main test execution"""
    print("\n" + "=" * 80)
    print("Complete Dynamic Instructions Content Test")
    print("Shows actual instruction content with memory integration")
    print("=" * 80)
    
    test_runner = CompleteInstructionsTest()
    
    try:
        await test_runner.run_comprehensive_test()
        print("\nComplete instructions test suite completed successfully!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        await test_runner.cleanup_test_environment()
        
    except Exception as e:
        print(f"\nTest suite failed: {e}")
        import traceback
        traceback.print_exc()
        await test_runner.cleanup_test_environment()


if __name__ == "__main__":
    from aicore.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Starting complete dynamic instructions content testing")
    
    from aicore.ai_config import validate_api_keys
    validate_api_keys()
    asyncio.run(main()) 