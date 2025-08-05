from enum import Enum
from typing import Dict, Any, Type, List, Optional

from app.aicore.core.stream_events import (
    ToolCallStartEvent,
    ToolCallOutputEvent,
    EventType,
)

from app.services.knowledge.llm_knowledge_tools import KnowledgeToolsInfo
from app.services.memory.llm_memory_tools import MemoryToolsInfo
from app.aicore.code_executor.workspace_session import WorkspaceSessionToolsInfo


class ActualToolType(Enum):
    KNOWLEDGE_TOOLS = KnowledgeToolsInfo.TOOL_TYPE
    MEMORY_TOOLS = MemoryToolsInfo.TOOL_TYPE
    WORKSPACE_SESSION_TOOLS = WorkspaceSessionToolsInfo.TOOL_TYPE
    UNKNOWN = "unknown"


class ToolRegistry:
    """
    Dynamic tool registry that uses existing ToolsInfo classes
    """
    
    # Registry of all ToolsInfo classes - add new ones here
    _TOOLS_INFO_CLASSES = [
        KnowledgeToolsInfo,
        MemoryToolsInfo, 
        WorkspaceSessionToolsInfo,
    ]
    
    # Lazy-loaded lookup tables
    _tool_to_type_map: Optional[Dict[str, ActualToolType]] = None
    _tool_to_display_map: Optional[Dict[str, str]] = None
    
    @classmethod
    def _build_lookup_tables(cls):
        """Build lookup tables from existing ToolsInfo classes"""
        if cls._tool_to_type_map is not None:
            return
            
        cls._tool_to_type_map = {}
        cls._tool_to_display_map = {}
        
        # Dynamically build from existing classes
        for tools_info_class in cls._TOOLS_INFO_CLASSES:
            tool_type_str = tools_info_class.TOOL_TYPE
            tool_names = tools_info_class.TOOL_NAMES
            
            # Map tool type string to enum
            tool_type_enum = cls._get_enum_by_value(tool_type_str)
            
            # Add all tools from this class to lookup
            for tool_name in tool_names:
                cls._tool_to_type_map[tool_name] = tool_type_enum
                cls._tool_to_display_map[tool_name] = cls._make_display_name(tool_name)
    
    @classmethod
    def _get_enum_by_value(cls, value: str) -> ActualToolType:
        """Get enum by string value"""
        for enum_item in ActualToolType:
            if enum_item.value == value:
                return enum_item
        return ActualToolType.UNKNOWN
    
    @classmethod 
    def _make_display_name(cls, tool_name: str) -> str:
        """Convert snake_case tool name to display name"""
        return tool_name.replace('_', ' ').title()
    
    @classmethod
    def get_tool_type(cls, tool_name: str) -> ActualToolType:
        """Get tool type with O(1) lookup"""
        cls._build_lookup_tables()
        if cls._tool_to_type_map is None:
            return ActualToolType.UNKNOWN
        return cls._tool_to_type_map.get(tool_name, ActualToolType.UNKNOWN)
    
    @classmethod
    def get_display_name(cls, tool_name: str) -> str:
        """Get display name for tool"""
        cls._build_lookup_tables()
        if cls._tool_to_display_map is None:
            return tool_name
        return cls._tool_to_display_map.get(tool_name, tool_name)
    
    @classmethod
    def is_known_tool(cls, tool_name: str) -> bool:
        """Check if tool is registered"""
        cls._build_lookup_tables()
        if cls._tool_to_type_map is None:
            return False
        return tool_name in cls._tool_to_type_map


def get_actual_tool_type(tool_name: str) -> ActualToolType:
    """Get tool type using dynamic registry"""
    return ToolRegistry.get_tool_type(tool_name)


def get_actual_tool_name(tool_name: str, actual_tool_type: ActualToolType) -> str:
    """Get display name for tool"""
    return ToolRegistry.get_display_name(tool_name)

class ToolCallsEventFormatter():
    """
    Formats tool calls events using dynamic tool registry
    """
    
    @staticmethod
    def format_tool_calls_start_event(tool_calls_event: ToolCallStartEvent) -> Dict[str, Any]:
        """
        Formats the tool calls start event
        """
        actual_tool_type = ToolRegistry.get_tool_type(tool_calls_event.tool_name)
        display_name = ToolRegistry.get_display_name(tool_calls_event.tool_name)
        
        event_data = tool_calls_event.model_dump(mode='json')
        
        return {
            "tool_name": tool_calls_event.tool_name,
            "display_name": display_name,
            "tool_type": actual_tool_type.value,
            "openai_tool_data": event_data,
        }
    
    @staticmethod
    def format_tool_calls_output_event(tool_calls_output_event: ToolCallOutputEvent) -> Dict[str, Any]:
        """
        Formats the tool calls output event
        """
        actual_tool_type = ToolRegistry.get_tool_type(tool_calls_output_event.tool_name)
        display_name = ToolRegistry.get_display_name(tool_calls_output_event.tool_name)
        
        event_data = tool_calls_output_event.model_dump(mode='json')
        
        return {
            "tool_name": tool_calls_output_event.tool_name,
            "display_name": display_name,
            "tool_type": actual_tool_type.value,
            "openai_tool_data": event_data,
        }
