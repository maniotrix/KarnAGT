#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tool Configuration - Centralized tool settings
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ToolConfig:
    """Configuration for tools and tool management"""
    
    # Tool registry settings
    auto_discover_tools: bool = True
    tool_directories: List[str] = field(default_factory=list)
    
    # Tool execution settings
    tool_timeout_seconds: int = 300
    max_concurrent_tools: int = 5
    
    # Custom tool configurations
    custom_tool_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Tool-specific settings
    code_execution_timeout: int = 300
    web_search_timeout: int = 30
    system_command_timeout: int = 60
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.tool_timeout_seconds <= 0:
            raise ValueError("tool_timeout_seconds must be positive")
        
        if self.max_concurrent_tools <= 0:
            raise ValueError("max_concurrent_tools must be positive") 