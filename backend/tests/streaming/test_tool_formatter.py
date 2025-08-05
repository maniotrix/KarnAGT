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

from app.aicore.core.stream_events import ToolCallStartEvent, ToolCallOutputEvent, ToolType, ToolStatus
from app.utils.tool_calls_event_formatter import ToolCallsEventFormatter, ToolRegistry, ActualToolType
from app.services.memory.llm_memory_tools import MemoryToolsInfo
from app.services.knowledge.llm_knowledge_tools import KnowledgeToolsInfo
from app.aicore.code_executor.workspace_session import WorkspaceSessionToolsInfo
from app.logging.logger import get_logger

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)


def test_tool_registry():
    """Test the ToolRegistry dynamic lookup functionality"""
    print("\n🧪 Testing ToolRegistry...")
    
    # Test knowledge tools
    knowledge_tool = "search_user_uploaded_documents"
    tool_type = ToolRegistry.get_tool_type(knowledge_tool)
    display_name = ToolRegistry.get_display_name(knowledge_tool)
    
    print(f"✅ Knowledge Tool: {knowledge_tool}")
    print(f"   Type: {tool_type} (expected: {ActualToolType.KNOWLEDGE_TOOLS})")
    print(f"   Display: {display_name}")
    assert tool_type == ActualToolType.KNOWLEDGE_TOOLS
    assert display_name == "Search User Uploaded Documents"
    
    # Test memory tools
    memory_tool = "retrieve_user_memory"
    tool_type = ToolRegistry.get_tool_type(memory_tool)
    display_name = ToolRegistry.get_display_name(memory_tool)
    
    print(f"✅ Memory Tool: {memory_tool}")
    print(f"   Type: {tool_type} (expected: {ActualToolType.MEMORY_TOOLS})")
    print(f"   Display: {display_name}")
    assert tool_type == ActualToolType.MEMORY_TOOLS
    assert display_name == "Retrieve User Memory"
    
    # Test workspace tools
    workspace_tool = "create_workspace"
    tool_type = ToolRegistry.get_tool_type(workspace_tool)
    display_name = ToolRegistry.get_display_name(workspace_tool)
    
    print(f"✅ Workspace Tool: {workspace_tool}")
    print(f"   Type: {tool_type} (expected: {ActualToolType.WORKSPACE_SESSION_TOOLS})")
    print(f"   Display: {display_name}")
    assert tool_type == ActualToolType.WORKSPACE_SESSION_TOOLS
    assert display_name == "Create Workspace"
    
    # Test unknown tool
    unknown_tool = "unknown_fake_tool"
    tool_type = ToolRegistry.get_tool_type(unknown_tool)
    display_name = ToolRegistry.get_display_name(unknown_tool)
    
    print(f"✅ Unknown Tool: {unknown_tool}")
    print(f"   Type: {tool_type} (expected: {ActualToolType.UNKNOWN})")
    print(f"   Display: {display_name}")
    assert tool_type == ActualToolType.UNKNOWN
    assert display_name == unknown_tool  # Should return original name
    
    print("✅ ToolRegistry tests passed!")


def test_tool_call_start_event_formatting():
    """Test formatting of ToolCallStartEvent objects"""
    print("\n🧪 Testing ToolCallStartEvent formatting...")
    
    # Test knowledge tool start event
    knowledge_start_event = ToolCallStartEvent(
        tool_name="search_user_uploaded_documents",
        tool_type=ToolType.FUNCTION_CALL,
        tool_id="tool_knowledge_123",
        arguments={
            "query": "What are the key findings in the research paper?",
            "search_all_files": True
        }
    )
    
    formatted = ToolCallsEventFormatter.format_tool_calls_start_event(knowledge_start_event)
    
    print(f"✅ Knowledge Tool Start Event:")
    print(f"   Input: {knowledge_start_event.tool_name}")
    print(f"   Output: {formatted}")
    
    # Verify structure
    assert formatted["tool_name"] == "search_user_uploaded_documents"
    assert formatted["display_name"] == "Search User Uploaded Documents"
    assert formatted["tool_type"] == KnowledgeToolsInfo.TOOL_TYPE
    assert formatted["tool_id"] == "tool_knowledge_123"
    assert formatted["arguments"]["query"] == "What are the key findings in the research paper?"
    assert formatted["arguments"]["search_all_files"] == True
    
    # Test memory tool start event
    memory_start_event = ToolCallStartEvent(
        tool_name="save_user_memory",
        tool_type=ToolType.FUNCTION_CALL,
        tool_id="tool_memory_456",
        arguments={
            "content": "User prefers concise explanations with code examples",
            "bucket": "preferences",
            "importance": 0.8
        }
    )
    
    formatted = ToolCallsEventFormatter.format_tool_calls_start_event(memory_start_event)
    
    print(f"✅ Memory Tool Start Event:")
    print(f"   Input: {memory_start_event.tool_name}")
    print(f"   Output: {formatted}")
    
    # Verify structure
    assert formatted["tool_name"] == "save_user_memory"
    assert formatted["display_name"] == "Save User Memory"
    assert formatted["tool_type"] == MemoryToolsInfo.TOOL_TYPE
    assert formatted["tool_id"] == "tool_memory_456"
    assert formatted["arguments"]["content"] == "User prefers concise explanations with code examples"
    
    # Test workspace tool start event
    workspace_start_event = ToolCallStartEvent(
        tool_name="execute_code",
        tool_type=ToolType.FUNCTION_CALL,
        tool_id="tool_workspace_789",
        arguments={
            "workspace_id": "ws_abc123",
            "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head())"
        }
    )
    
    formatted = ToolCallsEventFormatter.format_tool_calls_start_event(workspace_start_event)
    
    print(f"✅ Workspace Tool Start Event:")
    print(f"   Input: {workspace_start_event.tool_name}")
    print(f"   Output: {formatted}")
    
    # Verify structure
    assert formatted["tool_name"] == "execute_code"
    assert formatted["display_name"] == "Execute Code"
    assert formatted["tool_type"] == WorkspaceSessionToolsInfo.TOOL_TYPE
    assert formatted["tool_id"] == "tool_workspace_789"
    assert "workspace_id" in formatted["arguments"]
    assert "code" in formatted["arguments"]
    
    print("✅ ToolCallStartEvent formatting tests passed!")


def test_tool_call_output_event_formatting():
    """Test formatting of ToolCallOutputEvent objects"""
    print("\n🧪 Testing ToolCallOutputEvent formatting...")
    
    # Test knowledge tool output event
    knowledge_output_event = ToolCallOutputEvent(
        tool_name="list_user_uploaded_documents",
        tool_type=ToolType.FUNCTION_CALL,
        tool_id="tool_knowledge_123",
        result="**Available Knowledge Files (2 files):**\n\n1. **research_paper.pdf**\n   - Knowledge File ID: `kf_abc123`\n   - Documents: 1\n   - Chunks: 25",
        status=ToolStatus.COMPLETED
    )
    
    formatted = ToolCallsEventFormatter.format_tool_calls_output_event(knowledge_output_event)
    
    print(f"✅ Knowledge Tool Output Event:")
    print(f"   Input: {knowledge_output_event.tool_name}")
    print(f"   Output keys: {list(formatted.keys())}")
    
    # Verify structure
    assert formatted["tool_name"] == "list_user_uploaded_documents"
    assert formatted["display_name"] == "List User Uploaded Documents"
    assert formatted["tool_type"] == KnowledgeToolsInfo.TOOL_TYPE
    assert formatted["tool_id"] == "tool_knowledge_123"
    assert "research_paper.pdf" in formatted["result"]
    assert formatted["status"] == ToolStatus.COMPLETED
    
    # Test workspace tool output event with complex result
    workspace_output_event = ToolCallOutputEvent(
        tool_name="create_workspace",
        tool_type=ToolType.FUNCTION_CALL,
        tool_id="tool_workspace_456",
        result={
            "success": True,
            "workspace_info": {
                "workspace_id": "ws_xyz789",
                "status": "ready",
                "created_at": "2024-01-15T10:30:45.123456Z",
                "files_count": 0
            },
            "error": None
        },
        status=ToolStatus.COMPLETED
    )
    
    formatted = ToolCallsEventFormatter.format_tool_calls_output_event(workspace_output_event)
    
    print(f"✅ Workspace Tool Output Event:")
    print(f"   Input: {workspace_output_event.tool_name}")
    print(f"   Output keys: {list(formatted.keys())}")
    print(f"   Result type: {type(formatted['result'])}")
    
    # Verify structure
    assert formatted["tool_name"] == "create_workspace"
    assert formatted["display_name"] == "Create Workspace"
    assert formatted["tool_type"] == WorkspaceSessionToolsInfo.TOOL_TYPE
    assert formatted["tool_id"] == "tool_workspace_456"
    assert isinstance(formatted["result"], dict)
    assert formatted["result"]["success"] == True
    assert formatted["result"]["workspace_info"]["workspace_id"] == "ws_xyz789"
    assert formatted["status"] == ToolStatus.COMPLETED
    
    # Test memory tool output event
    memory_output_event = ToolCallOutputEvent(
        tool_name="retrieve_user_memory",
        tool_type=ToolType.FUNCTION_CALL,
        tool_id="tool_memory_789",
        result="User memories (showing 3 total memories):\n\n1. [IDENTITY] John Smith, Senior Software Engineer\n2. [PREFERENCES] Prefers concise explanations\n3. [GOALS] Learning React for upcoming project",
        status=ToolStatus.COMPLETED
    )
    
    formatted = ToolCallsEventFormatter.format_tool_calls_output_event(memory_output_event)
    
    print(f"✅ Memory Tool Output Event:")
    print(f"   Input: {memory_output_event.tool_name}")
    print(f"   Result preview: {formatted['result'][:50]}...")
    
    # Verify structure
    assert formatted["tool_name"] == "retrieve_user_memory"
    assert formatted["display_name"] == "Retrieve User Memory"
    assert formatted["tool_type"] == MemoryToolsInfo.TOOL_TYPE
    assert formatted["tool_id"] == "tool_memory_789"
    assert "John Smith" in formatted["result"]
    assert formatted["status"] == ToolStatus.COMPLETED
    
    print("✅ ToolCallOutputEvent formatting tests passed!")


def test_unknown_tool_handling():
    """Test handling of unknown/unregistered tools"""
    print("\n🧪 Testing unknown tool handling...")
    
    # Test unknown tool start event
    unknown_start_event = ToolCallStartEvent(
        tool_name="mysterious_unknown_tool",
        tool_type=ToolType.UNKNOWN,
        tool_id="tool_unknown_123",
        arguments={"param": "value"}
    )
    
    formatted = ToolCallsEventFormatter.format_tool_calls_start_event(unknown_start_event)
    
    print(f"✅ Unknown Tool Start Event:")
    print(f"   Input: {unknown_start_event.tool_name}")
    print(f"   Output: {formatted}")
    
    # Verify it handles unknown tools gracefully
    assert formatted["tool_name"] == "mysterious_unknown_tool"
    assert formatted["display_name"] == "mysterious_unknown_tool"  # Should return original name
    assert formatted["tool_type"] == "unknown"  # Should be UNKNOWN enum value
    assert formatted["tool_id"] == "tool_unknown_123"
    
    print("✅ Unknown tool handling tests passed!")


def run_all_tests():
    """Run all formatter tests"""
    print("🚀 Starting ToolCallsEventFormatter Tests...")
    print("=" * 60)
    
    try:
        test_tool_registry()
        test_tool_call_start_event_formatting()
        test_tool_call_output_event_formatting()
        test_unknown_tool_handling()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! ToolCallsEventFormatter is working correctly!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("=" * 60)
        raise
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    run_all_tests()
