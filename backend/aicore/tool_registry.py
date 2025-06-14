#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tool Registry - Central registry for custom tools
Allows tools to be resolved by name for configuration-based tool loading
"""

from typing import Dict, Callable, Optional, Any, List
from functools import lru_cache
import inspect

from aicore.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Central registry for managing custom tools"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._tool_factories: Dict[str, Callable] = {}
        self._initialized = False
    
    def register_tool(self, name: str, tool: Callable):
        """
        Register a tool function directly
        
        Args:
            name: Tool name for lookup
            tool: The tool function (already decorated with @function_tool)
        """
        self._tools[name] = tool
        logger.debug(f"Registered tool: {name}")
    
    def register_tool_factory(self, name: str, factory: Callable):
        """
        Register a tool factory function that creates tools with runtime parameters
        
        Args:
            name: Tool name for lookup  
            factory: Function that returns a tool when called with parameters
        """
        self._tool_factories[name] = factory
        logger.debug(f"Registered tool factory: {name}")
    
    def get_tool(self, name: str, **kwargs) -> Optional[Callable]:
        """
        Get a tool by name, optionally passing parameters for factory tools
        
        Args:
            name: Tool name to lookup
            **kwargs: Parameters to pass to tool factory if needed
            
        Returns:
            Tool function or None if not found
        """
        # Try direct tool first
        if name in self._tools:
            return self._tools[name]
        
        # Try tool factory
        if name in self._tool_factories:
            factory = self._tool_factories[name]
            try:
                return factory(**kwargs)
            except Exception as e:
                logger.error(f"Error creating tool {name} from factory: {e}")
                return None
        
        logger.warning(f"Tool not found: {name}")
        return None
    
    def list_tools(self) -> List[str]:
        """Get list of all registered tool names"""
        return list(self._tools.keys()) + list(self._tool_factories.keys())
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered"""
        return name in self._tools or name in self._tool_factories
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a tool"""
        tool = None
        tool_type = None
        
        if name in self._tools:
            tool = self._tools[name]
            tool_type = "direct"
        elif name in self._tool_factories:
            tool = self._tool_factories[name]
            tool_type = "factory"
        
        if tool is None:
            return None
        
        # Get function signature and docstring
        try:
            sig = inspect.signature(tool)
            doc = inspect.getdoc(tool) or "No documentation available"
            
            return {
                "name": name,
                "type": tool_type,
                "signature": str(sig),
                "docstring": doc,
                "parameters": [param.name for param in sig.parameters.values()]
            }
        except Exception as e:
            logger.error(f"Error getting info for tool {name}: {e}")
            return {"name": name, "type": tool_type, "error": str(e)}


# Global tool registry instance
_global_registry = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _initialize_default_tools()
    return _global_registry


def _initialize_default_tools():
    """Initialize the registry with default tools"""
    global _global_registry
    if _global_registry is None or _global_registry._initialized:
        return
    
    logger.info("Initializing tool registry with default tools")
    
    # Register memory tool factories
    try:
        from app.services.memory.llm_memory_tools import (
            create_memory_retrieval_tool,
            create_memory_update_tool
        )
        
        _global_registry.register_tool_factory("memory_retrieval", create_memory_retrieval_tool)
        _global_registry.register_tool_factory("memory_update", create_memory_update_tool)
        
        logger.info("Memory tools registered successfully")
    except ImportError as e:
        logger.warning(f"Memory tools not available: {e}")
    
    # Add more default tools here as needed
    
    _global_registry._initialized = True
    logger.info(f"Tool registry initialized with {len(_global_registry.list_tools())} tools")


# Convenience functions
def register_tool(name: str, tool: Callable):
    """Register a tool in the global registry"""
    get_tool_registry().register_tool(name, tool)


def register_tool_factory(name: str, factory: Callable):
    """Register a tool factory in the global registry"""
    get_tool_registry().register_tool_factory(name, factory)


def get_tool(name: str, **kwargs) -> Optional[Callable]:
    """Get a tool from the global registry"""
    return get_tool_registry().get_tool(name, **kwargs)


def list_available_tools() -> List[str]:
    """List all available tools"""
    return get_tool_registry().list_tools() 